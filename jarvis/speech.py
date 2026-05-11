from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import BinaryIO
from urllib import error, request

from .config import AppConfig


@dataclass(slots=True)
class AudioPayload:
    data: bytes
    content_type: str
    extension: str
    provider: str


ELEVENLABS_TTS_TIMEOUT_SECONDS = float(os.getenv("JARVIS_ELEVENLABS_TTS_TIMEOUT_SECONDS", "3.5"))
ELEVENLABS_STREAMING_LATENCY = int(os.getenv("JARVIS_ELEVENLABS_STREAMING_LATENCY", "3"))
ELEVENLABS_OUTPUT_FORMAT = os.getenv("JARVIS_ELEVENLABS_OUTPUT_FORMAT", "mp3_22050_32").strip() or "mp3_22050_32"


def resolve_tts_providers(config: AppConfig, preferred_provider: str | None = None) -> list[str]:
    provider = (preferred_provider or config.tts_provider).strip().lower()
    if provider == "auto":
        base = ["piper", "localai", "elevenlabs", "system"]
    else:
        base = [provider]
    return _dedupe(base + list(config.tts_fallbacks))


def resolve_stt_providers(config: AppConfig) -> list[str]:
    if config.stt_provider == "auto":
        base = ["localai", "openai"]
    else:
        base = [config.stt_provider]
    return _dedupe(base + list(config.stt_fallbacks))


def synthesize_speech(config: AppConfig, text: str, voice_settings: dict | None = None) -> AudioPayload:
    errors: list[str] = []
    selected_provider = str((voice_settings or {}).get("tts_provider", "")).strip().lower()
    selected_elevenlabs_voice = str((voice_settings or {}).get("elevenlabs_voice", "")).strip()
    selected_piper_model = str((voice_settings or {}).get("piper_model_path", "")).strip()
    selected_piper_speaker = str((voice_settings or {}).get("piper_speaker", "")).strip()

    for provider in resolve_tts_providers(config, preferred_provider=selected_provider):
        try:
            if provider == "piper":
                override_model = Path(selected_piper_model) if selected_piper_model else None
                return _synthesize_with_piper(
                    config,
                    text,
                    model_path_override=override_model,
                    speaker_override=selected_piper_speaker or None,
                )
            if provider == "localai":
                return _synthesize_with_localai(config, text)
            if provider == "elevenlabs":
                return _run_with_timeout(
                    "elevenlabs",
                    partial(
                        _synthesize_with_elevenlabs,
                        config,
                        text,
                        requested_voice=selected_elevenlabs_voice or None,
                    ),
                    timeout_seconds=ELEVENLABS_TTS_TIMEOUT_SECONDS,
                )
            if provider == "system":
                return _synthesize_with_system(config, text)
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
    localai_health = _localai_healthcheck(config.localai_base_url)
    effective_piper_model = Path(selected_piper_model) if selected_piper_model else config.piper_model_path
    return {
        "tts_provider": config.tts_provider,
        "selected_tts_provider": selected_provider or config.tts_provider,
        "tts_fallbacks": list(config.tts_fallbacks),
        "tts_order": resolve_tts_providers(config, preferred_provider=selected_provider),
        "stt_provider": config.stt_provider,
        "stt_fallbacks": list(config.stt_fallbacks),
        "stt_order": resolve_stt_providers(config),
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
        "openai_ready": bool(config.openai_api_key.strip()),
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
