from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import BinaryIO
from urllib import error, request

from .config import AppConfig
from .persistence import atomic_write_json


@dataclass(slots=True)
class AudioPayload:
    data: bytes
    content_type: str
    extension: str
    provider: str
    requested_provider: str = ""
    attempted_providers: tuple[str, ...] = ()
    provider_failures: tuple[str, ...] = ()


ELEVENLABS_TTS_TIMEOUT_SECONDS = float(os.getenv("JARVIS_ELEVENLABS_TTS_TIMEOUT_SECONDS", "3.5"))
ELEVENLABS_STREAMING_LATENCY = int(os.getenv("JARVIS_ELEVENLABS_STREAMING_LATENCY", "3"))
ELEVENLABS_OUTPUT_FORMAT = os.getenv("JARVIS_ELEVENLABS_OUTPUT_FORMAT", "mp3_22050_32").strip() or "mp3_22050_32"
FISH_TTS_TIMEOUT_SECONDS = float(os.getenv("JARVIS_FISH_TTS_TIMEOUT_SECONDS", "10.0"))
VOICE_RUNTIME_STATUS_PATH = Path.cwd() / "data" / "settings" / "voice_runtime_status.json"


def resolve_tts_providers(config: AppConfig, preferred_provider: str | None = None) -> list[str]:
    provider = (preferred_provider or config.tts_provider).strip().lower()
    if provider == "auto":
        base = ["kokoro", "piper", "localai", "elevenlabs", "fish", "system"]
    else:
        base = [provider]
    return _dedupe(base + list(config.tts_fallbacks))


def resolve_stt_providers(config: AppConfig) -> list[str]:
    if config.stt_provider == "auto":
        base = ["mlx-whisper", "localai", "openai"]
    else:
        base = [config.stt_provider]
    return _dedupe(base + list(config.stt_fallbacks))


def synthesize_speech(config: AppConfig, text: str, voice_settings: dict | None = None) -> AudioPayload:
    errors: list[str] = []
    selected_provider = str((voice_settings or {}).get("tts_provider", "")).strip().lower()
    requested_provider = selected_provider or config.tts_provider.strip().lower() or "auto"
    selected_elevenlabs_voice = str((voice_settings or {}).get("elevenlabs_voice", "")).strip()
    selected_fish_reference = str((voice_settings or {}).get("fish_reference_id", "")).strip()
    selected_piper_model = str((voice_settings or {}).get("piper_model_path", "")).strip()
    selected_piper_speaker = str((voice_settings or {}).get("piper_speaker", "")).strip()
    attempted_providers: list[str] = []

    for provider in resolve_tts_providers(config, preferred_provider=selected_provider):
        attempted_providers.append(provider)
        try:
            if provider == "kokoro":
                payload = _synthesize_with_kokoro(config, text)
                return _with_audio_metadata(payload, requested_provider, attempted_providers, errors)
            if provider == "piper":
                override_model = Path(selected_piper_model) if selected_piper_model else None
                payload = _synthesize_with_piper(
                    config,
                    text,
                    model_path_override=override_model,
                    speaker_override=selected_piper_speaker or None,
                )
                return _with_audio_metadata(payload, requested_provider, attempted_providers, errors)
            if provider == "localai":
                payload = _synthesize_with_localai(config, text)
                return _with_audio_metadata(payload, requested_provider, attempted_providers, errors)
            if provider == "elevenlabs":
                payload = _run_with_timeout(
                    "elevenlabs",
                    partial(
                        _synthesize_with_elevenlabs,
                        config,
                        text,
                        requested_voice=selected_elevenlabs_voice or None,
                    ),
                    timeout_seconds=ELEVENLABS_TTS_TIMEOUT_SECONDS,
                )
                return _with_audio_metadata(payload, requested_provider, attempted_providers, errors)
            if provider == "fish":
                payload = _run_with_timeout(
                    "fish",
                    partial(
                        _synthesize_with_fish_audio,
                        config,
                        text,
                        requested_reference_id=selected_fish_reference or None,
                    ),
                    timeout_seconds=FISH_TTS_TIMEOUT_SECONDS,
                )
                return _with_audio_metadata(payload, requested_provider, attempted_providers, errors)
            if provider == "system":
                payload = _synthesize_with_system(config, text)
                return _with_audio_metadata(payload, requested_provider, attempted_providers, errors)
            raise RuntimeError(f"Unknown TTS provider: {provider}")
        except Exception as exc:
            errors.append(f"{provider}: {exc}")
    raise RuntimeError("No TTS providers succeeded. " + " | ".join(errors))


def transcribe_speech(
    config: AppConfig,
    audio_file: BinaryIO,
    model: str,
    prompt: str = "",
) -> str:
    errors: list[str] = []
    for provider in resolve_stt_providers(config):
        try:
            audio_file.seek(0)
            if provider == "mlx-whisper":
                return _transcribe_with_mlx_whisper(config, audio_file, prompt=prompt)
            if provider == "localai":
                return _transcribe_with_localai(config, audio_file, prompt=prompt)
            if provider == "openai":
                return _transcribe_with_openai(config, audio_file, model=model, prompt=prompt)
            raise RuntimeError(f"Unknown STT provider: {provider}")
        except Exception as exc:
            errors.append(f"{provider}: {exc}")
    raise RuntimeError("No STT providers succeeded. " + " | ".join(errors))


def voice_stack_status(config: AppConfig, voice_settings: dict | None = None) -> dict:
    piper_binary_ready = bool(shutil.which(config.piper_binary))
    selected_piper_model = str((voice_settings or {}).get("piper_model_path", "")).strip()
    selected_provider = str((voice_settings or {}).get("tts_provider", "")).strip().lower()
    requested_provider = selected_provider or config.tts_provider.strip().lower()
    localai_health = _localai_healthcheck(config.localai_base_url)
    effective_piper_model = Path(selected_piper_model) if selected_piper_model else config.piper_model_path
    runtime_diagnostics = load_voice_runtime_status()
    tts_order = resolve_tts_providers(config, preferred_provider=selected_provider)
    tts_provider_statuses = _build_tts_provider_statuses(
        config,
        tts_order=tts_order,
        requested_provider=requested_provider,
        effective_piper_model=effective_piper_model,
        piper_binary_ready=piper_binary_ready,
        localai_health=localai_health,
        runtime_diagnostics=runtime_diagnostics,
    )
    effective_tts_status = next((item for item in tts_provider_statuses if item["ready"]), None)
    selected_tts_status = _selected_tts_provider_status(
        requested_provider=requested_provider,
        provider_statuses=tts_provider_statuses,
        effective_tts_status=effective_tts_status,
    )
    selected_tts_live = _selected_tts_live_status(
        requested_provider=requested_provider,
        provider_statuses=tts_provider_statuses,
        effective_tts_status=effective_tts_status,
    )
    selected_tts_status = {
        **selected_tts_status,
        **selected_tts_live,
    }
    return {
        "tts_provider": config.tts_provider,
        "selected_tts_provider": requested_provider,
        "tts_fallbacks": list(config.tts_fallbacks),
        "tts_order": tts_order,
        "effective_tts_order": tts_order,
        "tts_provider_statuses": tts_provider_statuses,
        "selected_tts_provider_ready": selected_tts_status["ready"],
        "selected_tts_provider_state": selected_tts_status["state"],
        "selected_tts_provider_reason": selected_tts_status["reason"],
        "selected_tts_provider_live_ready": selected_tts_live["live_ready"],
        "selected_tts_provider_live_state": selected_tts_live["live_state"],
        "selected_tts_provider_live_reason": selected_tts_live["live_reason"],
        "effective_tts_provider": effective_tts_status["provider"] if effective_tts_status else "",
        "effective_tts_provider_state": effective_tts_status["state"] if effective_tts_status else "unavailable",
        "effective_tts_provider_reason": (
            effective_tts_status["reason"] if effective_tts_status else "No spoken-output provider is ready in the current fallback order."
        ),
        "last_live_requested_tts_provider": str(runtime_diagnostics.get("last_requested_provider", "")).strip(),
        "last_live_effective_tts_provider": str(runtime_diagnostics.get("last_effective_provider", "")).strip(),
        "last_live_attempted_tts_providers": list(runtime_diagnostics.get("last_attempted_providers", []) or []),
        "effective_tts_note": _tts_fallback_note(selected_tts_status, effective_tts_status, runtime_diagnostics),
        "voice_runtime_diagnostics": runtime_diagnostics,
        "stt_provider": config.stt_provider,
        "stt_fallbacks": list(config.stt_fallbacks),
        "stt_order": resolve_stt_providers(config),
        "effective_stt_order": resolve_stt_providers(config),
        "piper_binary": config.piper_binary,
        "piper_binary_ready": piper_binary_ready,
        "piper_ready": bool(
            piper_binary_ready and effective_piper_model and effective_piper_model.exists()
        ),
        "piper_model_path": str(effective_piper_model) if effective_piper_model else "",
        "localai_configured": bool(config.localai_base_url),
        "localai_healthy": localai_health,
        "localai_base_url": config.localai_base_url,
        "elevenlabs_ready": bool(os.getenv("ELEVENLABS_API_KEY", "").strip() or config.elevenlabs_api_key.strip()),
        "fish_ready": bool(
            (os.getenv("FISH_API_KEY", "").strip() or str(getattr(config, "fish_api_key", "")).strip())
            and str(getattr(config, "fish_reference_id", "")).strip()
        ),
        "fish_model": str(getattr(config, "fish_model", "")).strip(),
        "fish_reference_id": str(getattr(config, "fish_reference_id", "")).strip(),
        "openai_ready": bool(config.openai_api_key.strip()),
        "kokoro_available": _check_kokoro_available(),
        "mlx_whisper_available": _check_mlx_whisper_available(),
        "system_ready": bool(shutil.which("say")),
    }


def _synthesize_with_elevenlabs(
    config: AppConfig,
    text: str,
    requested_voice: str | None = None,
) -> AudioPayload:
    from elevenlabs.client import ElevenLabs
    from elevenlabs.core.request_options import RequestOptions

    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip() or config.elevenlabs_api_key.strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is missing.")
    voice = ElevenLabs(
        api_key=api_key,
        timeout=max(1.0, ELEVENLABS_TTS_TIMEOUT_SECONDS),
    )
    voice_id = _resolve_elevenlabs_voice_id(voice, requested_voice or config.elevenlabs_voice)
    audio = voice.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        optimize_streaming_latency=ELEVENLABS_STREAMING_LATENCY,
        output_format=ELEVENLABS_OUTPUT_FORMAT,
        request_options=RequestOptions(
            timeout_in_seconds=max(1, int(ELEVENLABS_TTS_TIMEOUT_SECONDS)),
            max_retries=0,
        ),
    )
    return AudioPayload(
        data=b"".join(audio),
        content_type="audio/mpeg",
        extension=".mp3",
        provider="elevenlabs",
    )


def _synthesize_with_fish_audio(
    config: AppConfig,
    text: str,
    requested_reference_id: str | None = None,
) -> AudioPayload:
    api_key = os.getenv("FISH_API_KEY", "").strip() or str(getattr(config, "fish_api_key", "")).strip()
    if not api_key:
        raise RuntimeError("FISH_API_KEY is missing.")

    reference_id = (requested_reference_id or str(getattr(config, "fish_reference_id", ""))).strip()
    if not reference_id:
        raise RuntimeError("FISH_REFERENCE_ID is missing.")

    payload = {
        "text": text,
        "reference_id": reference_id,
        "format": "mp3",
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        "https://api.fish.audio/v1/tts",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "model": str(getattr(config, "fish_model", "")).strip() or "s2.1-pro",
        },
    )
    try:
        with request.urlopen(req, timeout=FISH_TTS_TIMEOUT_SECONDS) as response:
            content_type = response.headers.get("Content-Type", "audio/mpeg").split(";", 1)[0].strip()
            data = response.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or f"Fish Audio HTTP {exc.code}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Fish Audio request failed: {exc.reason}") from exc

    return AudioPayload(
        data=data,
        content_type=content_type or "audio/mpeg",
        extension=".mp3",
        provider="fish",
    )


def _synthesize_with_piper(
    config: AppConfig,
    text: str,
    model_path_override: Path | None = None,
    speaker_override: str | None = None,
) -> AudioPayload:
    model_path = model_path_override or config.piper_model_path
    if not model_path:
        raise RuntimeError("PIPER_MODEL_PATH is not configured.")
    if not model_path.exists():
        raise RuntimeError(f"Piper model not found: {model_path}")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        output_path = Path(handle.name)

    cmd = [
        config.piper_binary,
        "--model",
        str(model_path),
        "--output_file",
        str(output_path),
    ]
    if speaker_override or config.piper_speaker:
        cmd.extend(["--speaker", speaker_override or config.piper_speaker])

    try:
        result = subprocess.run(
            cmd,
            input=text,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or "unknown Piper failure"
            raise RuntimeError(stderr)
        payload = output_path.read_bytes()
    finally:
        if output_path.exists():
            output_path.unlink()

    return AudioPayload(
        data=payload,
        content_type="audio/wav",
        extension=".wav",
        provider="piper",
    )


def _synthesize_with_localai(config: AppConfig, text: str) -> AudioPayload:
    requests = _load_requests()
    if not config.localai_base_url:
        raise RuntimeError("LOCALAI_BASE_URL is not configured.")

    response = requests.post(
        f"{config.localai_base_url.rstrip('/')}/tts",
        headers=_localai_headers(config),
        json={
            "backend": config.localai_tts_backend,
            "model": config.localai_tts_model,
            "input": text,
        },
        timeout=120,
    )
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "audio/wav").split(";", 1)[0].strip()
    extension = ".wav" if "wav" in content_type else ".mp3"
    return AudioPayload(
        data=response.content,
        content_type=content_type,
        extension=extension,
        provider="localai",
    )


def _synthesize_with_system(config: AppConfig, text: str) -> AudioPayload:
    say_binary = shutil.which("say")
    if not say_binary:
        raise RuntimeError("macOS say command is unavailable.")

    afconvert_binary = shutil.which("afconvert")
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as handle:
        aiff_path = Path(handle.name)
    wav_path = aiff_path.with_suffix(".wav")

    try:
        say_result = subprocess.run(
            [say_binary, "-o", str(aiff_path), text],
            capture_output=True,
            text=True,
            check=False,
        )
        if say_result.returncode != 0:
            stderr = say_result.stderr.strip() or say_result.stdout.strip() or "unknown say failure"
            raise RuntimeError(stderr)

        if afconvert_binary:
            convert_result = subprocess.run(
                [afconvert_binary, "-f", "WAVE", "-d", "LEI16", str(aiff_path), str(wav_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            if convert_result.returncode == 0 and wav_path.exists():
                return AudioPayload(
                    data=wav_path.read_bytes(),
                    content_type="audio/wav",
                    extension=".wav",
                    provider="system",
                )

        return AudioPayload(
            data=aiff_path.read_bytes(),
            content_type="audio/aiff",
            extension=".aiff",
            provider="system",
        )
    finally:
        if aiff_path.exists():
            aiff_path.unlink()
        if wav_path.exists():
            wav_path.unlink()


def _transcribe_with_openai(
    config: AppConfig,
    audio_file: BinaryIO,
    model: str,
    prompt: str = "",
) -> str:
    if not config.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    try:
        from openai import OpenAI
    except ModuleNotFoundError as exc:  # pragma: no cover - cold path
        raise RuntimeError("openai package is required for audio transcription.") from exc

    client = OpenAI(api_key=config.openai_api_key)
    transcription = client.audio.transcriptions.create(
        model=model,
        file=audio_file,
        prompt=prompt,
    )
    text = getattr(transcription, "text", None)
    if isinstance(text, str):
        return text
    return str(transcription)


def _transcribe_with_localai(
    config: AppConfig,
    audio_file: BinaryIO,
    prompt: str = "",
) -> str:
    requests = _load_requests()
    if not config.localai_base_url:
        raise RuntimeError("LOCALAI_BASE_URL is not configured.")

    filename = getattr(audio_file, "name", "speech.wav")
    files = {
        "file": (Path(filename).name, audio_file, "audio/wav"),
    }
    data = {
        "model": config.localai_stt_model,
    }
    if prompt:
        data["prompt"] = prompt

    response = requests.post(
        f"{config.localai_base_url.rstrip('/')}/v1/audio/transcriptions",
        headers=_localai_headers(config),
        data=data,
        files=files,
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json()
    text = payload.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    segments = payload.get("segments", [])
    if isinstance(segments, list):
        stitched = " ".join(
            str(item.get("text", "")).strip()
            for item in segments
            if isinstance(item, dict) and str(item.get("text", "")).strip()
        ).strip()
        if stitched:
            return stitched
    raise RuntimeError("LocalAI transcription response did not contain text.")


def _transcribe_with_mlx_whisper(
    config: AppConfig,
    audio_file: BinaryIO,
    prompt: str = "",
) -> str:
    """
    Transcribe audio using mlx-whisper on Apple Silicon Neural Engine.
    Significantly faster than cloud Whisper on M-series Macs.
    """
    try:
        import mlx_whisper
    except ImportError:
        raise RuntimeError(
            "mlx-whisper not installed. Run: pip install mlx-whisper"
        )

    import tempfile
    from pathlib import Path

    # Write audio to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_file.read())
        tmp_path = tmp.name

    try:
        model = getattr(config, "mlx_whisper_model", None) or \
                os.getenv("JARVIS_MLX_WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")
        result = mlx_whisper.transcribe(
            tmp_path,
            path_or_hf_repo=model,
            initial_prompt=prompt or None,
            verbose=False,
        )
        return (result.get("text") or "").strip()
    finally:
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass


def _synthesize_with_kokoro(
    config: AppConfig,
    text: str,
) -> AudioPayload:
    """
    Synthesize speech using Kokoro-82M on-device.
    Produces high-quality neural TTS audio.
    Voice: configurable via JARVIS_KOKORO_VOICE (default: 'af_heart' — warm American female)
    """
    try:
        from kokoro import KPipeline
        import soundfile as sf
        import numpy as np
        import io
    except ImportError:
        raise RuntimeError(
            "Kokoro not installed. Run: pip install kokoro soundfile"
        )

    voice = getattr(config, "kokoro_voice", None) or \
            os.getenv("JARVIS_KOKORO_VOICE", "af_heart")
    speed = float(os.getenv("JARVIS_KOKORO_SPEED", "1.0"))

    # KPipeline is stateful — cache it as a module-level singleton
    pipeline = _get_kokoro_pipeline()

    try:
        chunks = []
        for _, _, audio in pipeline(text, voice=voice, speed=speed):
            if audio is not None:
                chunks.append(audio)

        if not chunks:
            raise RuntimeError("Kokoro produced no audio chunks")

        audio_data = np.concatenate(chunks)
        sample_rate = 24000  # Kokoro output sample rate

        buf = io.BytesIO()
        sf.write(buf, audio_data, sample_rate, format="WAV", subtype="PCM_16")
        buf.seek(0)

        return AudioPayload(
            data=buf.read(),
            content_type="audio/wav",
            extension=".wav",
            provider="kokoro",
        )
    except Exception as e:
        raise RuntimeError(f"Kokoro synthesis failed: {e}")


# Module-level Kokoro pipeline cache
_kokoro_pipeline = None
_kokoro_pipeline_lock = threading.Lock()


def _get_kokoro_pipeline():
    """Return cached KPipeline instance (thread-safe, lazy init)."""
    global _kokoro_pipeline
    if _kokoro_pipeline is None:
        with _kokoro_pipeline_lock:
            if _kokoro_pipeline is None:
                from kokoro import KPipeline
                lang_code = os.getenv("JARVIS_KOKORO_LANG", "a")  # 'a' = American English
                _kokoro_pipeline = KPipeline(lang_code=lang_code)
    return _kokoro_pipeline


def _check_kokoro_available() -> bool:
    try:
        import kokoro  # noqa
        return True
    except ImportError:
        return False


def _check_mlx_whisper_available() -> bool:
    try:
        import mlx_whisper  # noqa
        return True
    except ImportError:
        return False


def _localai_headers(config: AppConfig) -> dict[str, str]:
    headers = {}
    if config.localai_api_key:
        headers["Authorization"] = f"Bearer {config.localai_api_key}"
    return headers


def _resolve_elevenlabs_voice_id(voice: object, requested: str) -> str:
    voices = voice.voices.get_all()
    fallback_voice_id = None
    for candidate in getattr(voices, "voices", []):
        candidate_name = getattr(candidate, "name", "")
        short_name = candidate_name.split(" - ", 1)[0].lower()
        if short_name == "george":
            fallback_voice_id = candidate.voice_id
        if getattr(candidate, "voice_id", "") == requested:
            return candidate.voice_id
        if short_name == requested.lower():
            return candidate.voice_id
    if fallback_voice_id:
        return fallback_voice_id
    return requested


def _with_audio_metadata(
    payload: AudioPayload,
    requested_provider: str,
    attempted_providers: list[str],
    errors: list[str],
) -> AudioPayload:
    return AudioPayload(
        data=payload.data,
        content_type=payload.content_type,
        extension=payload.extension,
        provider=payload.provider,
        requested_provider=requested_provider,
        attempted_providers=tuple(attempted_providers),
        provider_failures=tuple(errors),
    )


def load_voice_runtime_status(path: Path | None = None) -> dict[str, object]:
    status_path = path or VOICE_RUNTIME_STATUS_PATH
    if not status_path.exists():
        return {}
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def record_voice_runtime_status(audio: AudioPayload, path: Path | None = None) -> dict[str, object]:
    status_path = path or VOICE_RUNTIME_STATUS_PATH
    snapshot = load_voice_runtime_status(status_path)
    snapshot.setdefault("providers", {})
    providers = snapshot["providers"]
    if not isinstance(providers, dict):
        providers = {}
        snapshot["providers"] = providers

    now = datetime.now(timezone.utc).isoformat()
    requested_provider = str(audio.requested_provider or "").strip().lower()
    effective_provider = str(audio.provider or "").strip().lower()
    attempted_providers = [str(item).strip().lower() for item in audio.attempted_providers if str(item).strip()]
    provider_failures = [str(item).strip() for item in audio.provider_failures if str(item).strip()]

    snapshot["updated_at"] = now
    snapshot["last_requested_provider"] = requested_provider
    snapshot["last_effective_provider"] = effective_provider
    snapshot["last_attempted_providers"] = attempted_providers

    for failure in provider_failures:
        provider_name, failure_detail = _split_provider_failure(failure)
        providers[provider_name] = {
            "blocked": True,
            "state": _classify_voice_runtime_failure(failure_detail),
            "reason": failure_detail,
            "captured_at": now,
            "requested_provider": requested_provider,
            "effective_provider": effective_provider,
        }

    if effective_provider and (not requested_provider or effective_provider == requested_provider):
        providers[effective_provider] = {
            "blocked": False,
            "state": "live_success",
            "reason": "The last live synthesis succeeded through this provider.",
            "captured_at": now,
            "requested_provider": requested_provider,
            "effective_provider": effective_provider,
        }

    status_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(status_path, snapshot)
    return snapshot


def _build_tts_provider_statuses(
    config: AppConfig,
    *,
    tts_order: list[str],
    requested_provider: str,
    effective_piper_model: Path | None,
    piper_binary_ready: bool,
    localai_health: bool,
    runtime_diagnostics: dict[str, object],
) -> list[dict[str, object]]:
    statuses: list[dict[str, object]] = []
    provider_diagnostics = runtime_diagnostics.get("providers", {})
    if not isinstance(provider_diagnostics, dict):
        provider_diagnostics = {}
    for index, provider in enumerate(tts_order):
        status = _tts_provider_status(
            config,
            provider=provider,
            effective_piper_model=effective_piper_model,
            piper_binary_ready=piper_binary_ready,
            localai_health=localai_health,
            runtime_diagnostic=provider_diagnostics.get(provider),
        )
        status["selected"] = provider == requested_provider
        status["fallback_rank"] = index
        statuses.append(status)
    return statuses


def _selected_tts_provider_status(
    *,
    requested_provider: str,
    provider_statuses: list[dict[str, object]],
    effective_tts_status: dict[str, object] | None,
) -> dict[str, object]:
    if requested_provider == "auto":
        if effective_tts_status:
            return {
                "provider": "auto",
                "ready": True,
                "state": "ready",
                "reason": f"Auto mode will use {effective_tts_status['provider']} in the current runtime.",
            }
        return {
            "provider": "auto",
            "ready": False,
            "state": "unavailable",
            "reason": "Auto mode has no ready spoken-output provider in the current fallback order.",
        }
    for status in provider_statuses:
        if status["provider"] == requested_provider:
            return {
                "provider": status["provider"],
                "ready": status["ready"],
                "state": status["state"],
                "reason": status["reason"],
            }
    return {
        "provider": requested_provider,
        "ready": False,
        "state": "unavailable",
        "reason": f"{requested_provider} is not a recognized spoken-output provider.",
    }


def _selected_tts_live_status(
    *,
    requested_provider: str,
    provider_statuses: list[dict[str, object]],
    effective_tts_status: dict[str, object] | None,
) -> dict[str, object]:
    if requested_provider == "auto":
        if effective_tts_status:
            return {
                "live_ready": bool(effective_tts_status.get("live_ready", effective_tts_status.get("ready", False))),
                "live_state": str(effective_tts_status.get("live_state", effective_tts_status.get("state", "ready"))),
                "live_reason": f"Auto mode will currently rely on {effective_tts_status['provider']}.",
            }
        return {
            "live_ready": False,
            "live_state": "unavailable",
            "live_reason": "Auto mode has no currently usable spoken-output provider.",
        }
    for status in provider_statuses:
        if status["provider"] == requested_provider:
            return {
                "live_ready": bool(status.get("live_ready", status.get("ready", False))),
                "live_state": str(status.get("live_state", status.get("state", "ready"))),
                "live_reason": str(status.get("live_reason", status.get("reason", ""))),
            }
    return {
        "live_ready": False,
        "live_state": "unavailable",
        "live_reason": f"{requested_provider} is not a recognized spoken-output provider.",
    }


def _tts_fallback_note(
    selected_tts_status: dict[str, object],
    effective_tts_status: dict[str, object] | None,
    runtime_diagnostics: dict[str, object],
) -> str:
    live_reason = str(selected_tts_status.get("live_reason", "")).strip()
    live_state = str(selected_tts_status.get("live_state", "")).strip()
    last_live_effective_provider = str(runtime_diagnostics.get("last_effective_provider", "")).strip()
    if selected_tts_status["provider"] == "auto":
        return str(selected_tts_status["reason"])
    if selected_tts_status["ready"]:
        if live_reason and live_state and live_state != "ready":
            if last_live_effective_provider:
                return (
                    f"{selected_tts_status['provider']} is configured, but the last live request was {live_state}; "
                    f"the last live fallback reached {last_live_effective_provider}."
                )
            if effective_tts_status:
                return (
                    f"{selected_tts_status['provider']} is configured, but the last live request was {live_state}; "
                    f"fallback can use {effective_tts_status['provider']}."
                )
            return f"{selected_tts_status['provider']} is configured, but the last live request was {live_state}."
        return f"{selected_tts_status['provider']} is ready for spoken output in the current runtime."
    if effective_tts_status:
        return (
            f"{selected_tts_status['provider']} is {selected_tts_status['state']}; "
            f"fallback can use {effective_tts_status['provider']}."
        )
    return "No spoken-output provider is ready in the current fallback order."


def _tts_provider_status(
    config: AppConfig,
    *,
    provider: str,
    effective_piper_model: Path | None,
    piper_binary_ready: bool,
    localai_health: bool,
    runtime_diagnostic: object = None,
) -> dict[str, object]:
    runtime_state = _coerce_runtime_diagnostic(runtime_diagnostic)
    if provider == "kokoro":
        ready = _check_kokoro_available()
        status = {
            "provider": provider,
            "label": "Kokoro",
            "ready": ready,
            "state": "ready" if ready else "unavailable",
            "reason": (
                "Kokoro is installed for on-device spoken output."
                if ready
                else "Kokoro is not installed in this runtime."
            ),
        }
        return _attach_runtime_diagnostic(status, runtime_state)
    if provider == "piper":
        if piper_binary_ready and effective_piper_model and effective_piper_model.exists():
            status = {
                "provider": provider,
                "label": "Piper",
                "ready": True,
                "state": "ready",
                "reason": "Piper binary and model are present for local spoken output.",
            }
            return _attach_runtime_diagnostic(status, runtime_state)
        reasons: list[str] = []
        if not piper_binary_ready:
            reasons.append(f"{config.piper_binary} binary is unavailable.")
        if effective_piper_model:
            if not effective_piper_model.exists():
                reasons.append(f"Piper model path does not exist: {effective_piper_model}")
        else:
            reasons.append("Piper model path is not configured.")
        status = {
            "provider": provider,
            "label": "Piper",
            "ready": False,
            "state": "degraded" if piper_binary_ready or effective_piper_model is not None else "unavailable",
            "reason": " ".join(reasons),
        }
        return _attach_runtime_diagnostic(status, runtime_state)
    if provider == "localai":
        if localai_health:
            status = {
                "provider": provider,
                "label": "LocalAI",
                "ready": True,
                "state": "ready",
                "reason": "LocalAI is configured and its /readyz healthcheck succeeded.",
            }
            return _attach_runtime_diagnostic(status, runtime_state)
        if config.localai_base_url:
            status = {
                "provider": provider,
                "label": "LocalAI",
                "ready": False,
                "state": "degraded",
                "reason": "LocalAI is configured, but its /readyz healthcheck did not succeed.",
            }
            return _attach_runtime_diagnostic(status, runtime_state)
        status = {
            "provider": provider,
            "label": "LocalAI",
            "ready": False,
            "state": "unavailable",
            "reason": "LOCALAI_BASE_URL is not configured.",
        }
        return _attach_runtime_diagnostic(status, runtime_state)
    if provider == "elevenlabs":
        ready = bool(os.getenv("ELEVENLABS_API_KEY", "").strip() or config.elevenlabs_api_key.strip())
        status = {
            "provider": provider,
            "label": "ElevenLabs",
            "ready": ready,
            "state": "ready" if ready else "unavailable",
            "reason": (
                "ElevenLabs is credentialed for spoken output."
                if ready
                else "ELEVENLABS_API_KEY is missing."
            ),
        }
        return _attach_runtime_diagnostic(status, runtime_state)
    if provider == "fish":
        api_key = os.getenv("FISH_API_KEY", "").strip() or str(getattr(config, "fish_api_key", "")).strip()
        reference_id = str(getattr(config, "fish_reference_id", "")).strip()
        if api_key and reference_id:
            status = {
                "provider": provider,
                "label": "Fish Audio",
                "ready": True,
                "state": "ready",
                "reason": "Fish Audio has both an API key and a reference voice id.",
            }
            return _attach_runtime_diagnostic(status, runtime_state)
        reasons: list[str] = []
        if not api_key:
            reasons.append("FISH_API_KEY is missing.")
        if not reference_id:
            reasons.append("FISH_REFERENCE_ID is missing.")
        status = {
            "provider": provider,
            "label": "Fish Audio",
            "ready": False,
            "state": "degraded" if api_key or reference_id else "unavailable",
            "reason": " ".join(reasons),
        }
        return _attach_runtime_diagnostic(status, runtime_state)
    if provider == "system":
        ready = bool(shutil.which("say"))
        status = {
            "provider": provider,
            "label": "Browser/System Fallback",
            "ready": ready,
            "state": "ready" if ready else "unavailable",
            "reason": (
                "macOS say is available for local spoken-output fallback."
                if ready
                else "macOS say command is unavailable."
            ),
        }
        return _attach_runtime_diagnostic(status, runtime_state)
    status = {
        "provider": provider,
        "label": provider.title(),
        "ready": False,
        "state": "unavailable",
        "reason": f"{provider} is not a recognized spoken-output provider.",
    }
    return _attach_runtime_diagnostic(status, runtime_state)


def _coerce_runtime_diagnostic(runtime_diagnostic: object) -> dict[str, object]:
    if isinstance(runtime_diagnostic, dict):
        return dict(runtime_diagnostic)
    return {}


def _attach_runtime_diagnostic(status: dict[str, object], runtime_state: dict[str, object]) -> dict[str, object]:
    blocked = bool(runtime_state.get("blocked", False))
    state = str(runtime_state.get("state", "")).strip()
    reason = str(runtime_state.get("reason", "")).strip()
    captured_at = str(runtime_state.get("captured_at", "")).strip()
    status["live_ready"] = bool(status.get("ready", False)) and not blocked
    status["live_state"] = state or ("ready" if status["live_ready"] else str(status.get("state", "unavailable")))
    status["live_reason"] = reason or str(status.get("reason", ""))
    status["last_runtime_blocked"] = blocked
    status["last_runtime_state"] = state
    status["last_runtime_reason"] = reason
    status["last_runtime_at"] = captured_at
    return status


def _split_provider_failure(failure: str) -> tuple[str, str]:
    provider_name, separator, failure_detail = failure.partition(":")
    normalized_provider = provider_name.strip().lower() or "unknown"
    detail = failure_detail.strip() if separator else failure.strip()
    return normalized_provider, detail


def _classify_voice_runtime_failure(detail: str) -> str:
    lowered = detail.lower()
    if "certificate verify failed" in lowered or "certificat" in lowered and "ssl" in lowered:
        return "ssl_transport_blocked"
    if "timed out" in lowered or "timeout" in lowered:
        return "remote_timeout"
    if "request failed" in lowered or "http " in lowered:
        return "remote_request_blocked"
    return "runtime_blocked"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        normalized = item.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def _load_requests():
    try:
        import requests
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency path
        raise RuntimeError("requests is required for LocalAI speech providers.") from exc
    return requests


def _localai_healthcheck(base_url: str) -> bool:
    if not base_url:
        return False
    try:
        with request.urlopen(f"{base_url.rstrip('/')}/readyz", timeout=2) as response:
            return 200 <= response.status < 300
    except (error.URLError, TimeoutError, ValueError):
        return False


def _run_with_timeout(provider: str, operation, *, timeout_seconds: float) -> AudioPayload:
    import concurrent.futures

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(operation)
    try:
        return future.result(timeout=max(0.1, timeout_seconds))
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise RuntimeError(
            f"{provider} timed out after {timeout_seconds:.1f}s"
        ) from exc
    finally:
        if future.done():
            executor.shutdown(wait=True, cancel_futures=False)
