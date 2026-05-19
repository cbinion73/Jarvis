from __future__ import annotations

import argparse
import asyncio
import base64
import json
import logging
import os
import queue
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as write_wav
from websockets.asyncio.client import connect

from .models import InferredContext, VoiceContextProfile
from .runtime import JarvisRuntime
from .speech import synthesize_speech

logger = logging.getLogger("jarvis.voice")

TRANSCRIBE_PROMPT = (
    "This is a live household assistant conversation. Important names may include "
    "Chris, Rebekah, Caleb, Anna, JARVIS, Chronicle, Thermo Fisher, Scouts 95, "
    "Garden of Hope, and Realtime API."
)
DEFAULT_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")

try:
    import certifi
except ModuleNotFoundError:  # pragma: no cover - optional at runtime
    certifi = None


class WakeWordListener:
    """
    Continuously monitors the microphone for the JARVIS wake word.
    Runs in a daemon thread. Fires callback when wake word detected.

    Uses OpenWakeWord with the 'hey_jarvis' model or a custom model.
    Falls back gracefully if openwakeword is not installed.
    """

    CHUNK_SIZE = 1280     # 80ms at 16kHz
    SAMPLE_RATE = 16000
    DETECTION_THRESHOLD = 0.5

    def __init__(self, callback: callable, model_name: str = "hey_jarvis"):
        self._callback = callback
        self._model_name = model_name
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        """Start listening. Returns True if started, False if unavailable."""
        try:
            import openwakeword  # noqa
        except ImportError:
            logger.warning(
                "OpenWakeWord not installed — wake word detection unavailable. "
                "Run: pip install openwakeword"
            )
            return False

        self._running = True
        self._thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="wake-word-listener"
        )
        self._thread.start()
        logger.info(f"Wake word listener started (model: {self._model_name})")
        return True

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _listen_loop(self) -> None:
        try:
            import openwakeword  # noqa
            from openwakeword.model import Model as OWWModel
            import numpy as np

            # Load model — downloads on first use
            oww_model = OWWModel(
                wakeword_models=[self._model_name],
                inference_framework="onnx",
            )

            def audio_callback(indata, frames, time_info, status):
                if not self._running:
                    return
                audio_chunk = (indata[:, 0] * 32767).astype(np.int16)
                predictions = oww_model.predict(audio_chunk)
                for model_name, score in predictions.items():
                    if score > self.DETECTION_THRESHOLD:
                        logger.info(f"Wake word detected: {model_name} (score: {score:.2f})")
                        try:
                            self._callback(model_name, score)
                        except Exception as e:
                            logger.error(f"Wake word callback error: {e}")
                        # Reset to avoid re-triggering
                        oww_model.reset()
                        break

            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=self.CHUNK_SIZE,
                callback=audio_callback,
            ):
                while self._running:
                    time.sleep(0.1)

        except Exception as e:
            logger.error(f"Wake word listener crashed: {e}")
            self._running = False

    @property
    def is_running(self) -> bool:
        return self._running and bool(self._thread and self._thread.is_alive())


class JarvisVoiceShell:
    def __init__(self, runtime: JarvisRuntime) -> None:
        self.runtime = runtime
        self.voice_context = runtime.config.load_voice_context()
        self._playback_lock = threading.Lock()
        self._playback_process: subprocess.Popen[str] | None = None
        self._wake_word_listener: WakeWordListener | None = None
        self._wake_word_queue: queue.Queue = queue.Queue()

    def list_input_devices(self) -> int:
        devices = sd.query_devices()
        default_input = sd.default.device[0]
        for idx, device in enumerate(devices):
            if device["max_input_channels"] > 0:
                marker = " (default)" if idx == default_input else ""
                print(
                    f"{idx}: {device['name']} | input_channels={device['max_input_channels']} | "
                    f"default_samplerate={device['default_samplerate']}{marker}"
                )
        return 0

    def infer_context(
        self,
        raw_text: str,
        explicit_actor: str | None = None,
        explicit_room: str | None = None,
        device_name: str = "",
        require_wake_word: bool = True,
    ) -> InferredContext:
        wake_word, cleaned = self._strip_wake_word(raw_text)
        quiet_mode, whisper_mode, cleaned = self._extract_voice_mode(cleaned)
        actor, speaker_confidence = self._infer_actor(cleaned, device_name)
        actor = explicit_actor or actor
        room = explicit_room or self._infer_room(cleaned, device_name)
        return InferredContext(
            actor=actor,
            room=room,
            wake_word_detected=wake_word,
            cleaned_request=cleaned.strip(),
            source_device=device_name,
            quiet_mode=quiet_mode,
            whisper_mode=whisper_mode,
            speaker_confidence=speaker_confidence,
        )

    def handle_text_turn(
        self,
        raw_text: str,
        explicit_actor: str | None = None,
        explicit_room: str | None = None,
        device_name: str = "",
        require_wake_word: bool = True,
        force_quiet: bool = False,
        force_whisper: bool = False,
    ) -> tuple[InferredContext, str] | None:
        inferred = self.infer_context(
            raw_text=raw_text,
            explicit_actor=explicit_actor,
            explicit_room=explicit_room,
            device_name=device_name,
            require_wake_word=require_wake_word,
        )
        if force_whisper:
            inferred.whisper_mode = True
            inferred.quiet_mode = True
        elif force_quiet:
            inferred.quiet_mode = True
        if require_wake_word and not inferred.wake_word_detected:
            return None
        if not inferred.cleaned_request:
            return None
        result = self.runtime.respond(inferred.actor, inferred.room, inferred.cleaned_request)
        return inferred, result.output_text

    def run_text_loop(
        self,
        actor: str | None,
        room: str | None,
        silent: bool,
        require_wake_word: bool,
        force_quiet: bool = False,
        force_whisper: bool = False,
    ) -> int:
        print("JARVIS text loop is live. Type /quit to exit.")
        while True:
            try:
                user_text = input("You: ").strip()
            except EOFError:
                print()
                return 0
            if not user_text:
                continue
            if user_text.lower() in {"/quit", "quit", "exit"}:
                return 0
            try:
                handled = self.handle_text_turn(
                    raw_text=user_text,
                    explicit_actor=actor,
                    explicit_room=room,
                    require_wake_word=require_wake_word,
                    force_quiet=force_quiet,
                    force_whisper=force_whisper,
                )
                if not handled:
                    print("JARVIS is listening for the wake word.")
                    continue
                inferred, reply = handled
                print(f"{inferred.actor} @ {inferred.room}")
                print(f"JARVIS: {reply}")
                if not silent:
                    self.speak(reply, quiet=inferred.quiet_mode, whisper=inferred.whisper_mode)
            except Exception as exc:  # pragma: no cover - interactive path
                print(f"Loop error: {exc}", file=sys.stderr)
        return 0

    def run_push_to_talk_loop(
        self,
        duration: float,
        actor: str | None,
        room: str | None,
        input_device: str | None,
        silent: bool,
        require_wake_word: bool,
        force_quiet: bool = False,
        force_whisper: bool = False,
    ) -> int:
        print("JARVIS push-to-talk loop is live.")
        print("Press Enter to record a turn, or type q and press Enter to exit.")
        while True:
            try:
                command = input("> ").strip().lower()
            except EOFError:
                print()
                return 0
            if command in {"q", "quit", "exit"}:
                return 0

            audio_path: Path | None = None
            try:
                audio_path = self.record_audio(duration=duration, input_device=input_device)
                transcript = self.transcribe_audio(audio_path)
                print(f"Heard: {transcript}")
                handled = self.handle_text_turn(
                    raw_text=transcript,
                    explicit_actor=actor,
                    explicit_room=room,
                    device_name=self._resolve_device_name(input_device),
                    require_wake_word=require_wake_word,
                    force_quiet=force_quiet,
                    force_whisper=force_whisper,
                )
                if not handled:
                    print("JARVIS is listening for the wake word.")
                    continue
                inferred, reply = handled
                print(f"{inferred.actor} @ {inferred.room}")
                print(f"JARVIS: {reply}")
                if not silent:
                    self.speak(reply, quiet=inferred.quiet_mode, whisper=inferred.whisper_mode)
            except KeyboardInterrupt:  # pragma: no cover - interactive path
                print("\nStopping.", file=sys.stderr)
                return 130
            except Exception as exc:  # pragma: no cover - interactive path
                print(f"Voice loop error: {exc}", file=sys.stderr)
            finally:
                if audio_path and audio_path.exists():
                    audio_path.unlink()
        return 0

    async def run_realtime_transcription_loop(
        self,
        actor: str | None,
        room: str | None,
        input_device: str | None,
        silent: bool,
        require_wake_word: bool,
        samplerate: int,
        force_quiet: bool = False,
        force_whisper: bool = False,
    ) -> int:
        api_key = self._require_env("OPENAI_API_KEY")
        device_name = self._resolve_device_name(input_device)
        print("JARVIS realtime voice session is live. Press Ctrl+C to stop.")
        print("Speak naturally. Completed speech turns will be transcribed and answered.")

        audio_queue: queue.Queue[bytes | None] = queue.Queue()
        stop_event = asyncio.Event()

        def callback(indata: np.ndarray, frames: int, time: object, status: object) -> None:
            if status:
                print(f"Audio status: {status}", file=sys.stderr)
            audio_queue.put(bytes(indata))

        async with connect(
            "wss://api.openai.com/v1/realtime?intent=transcription",
            additional_headers={
                "Authorization": f"Bearer {api_key}",
                "OpenAI-Beta": "realtime=v1",
            },
            max_size=2**22,
            ssl=self._build_ssl_context(),
        ) as websocket:
            await websocket.send(
                json.dumps(
                    {
                        "type": "transcription_session.update",
                        "input_audio_format": "pcm16",
                        "input_audio_transcription": {
                            "model": DEFAULT_TRANSCRIBE_MODEL,
                            "prompt": TRANSCRIBE_PROMPT,
                            "language": "en",
                        },
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 600,
                        },
                        "input_audio_noise_reduction": {"type": "near_field"},
                    }
                )
            )

            async def sender() -> None:
                while not stop_event.is_set():
                    chunk = await asyncio.to_thread(audio_queue.get)
                    if chunk is None:
                        return
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "input_audio_buffer.append",
                                "audio": base64.b64encode(chunk).decode("ascii"),
                            }
                        )
                    )

            async def receiver() -> None:
                while not stop_event.is_set():
                    message = await websocket.recv()
                    payload = json.loads(message)
                    event_type = payload.get("type", "")
                    if event_type == "conversation.item.input_audio_transcription.completed":
                        transcript = payload.get("transcript", "").strip()
                        if not transcript:
                            continue
                        print(f"Heard: {transcript}")
                        handled = self.handle_text_turn(
                            raw_text=transcript,
                            explicit_actor=actor,
                            explicit_room=room,
                            device_name=device_name,
                            require_wake_word=require_wake_word,
                            force_quiet=force_quiet,
                            force_whisper=force_whisper,
                        )
                        if not handled:
                            print("JARVIS is listening for the wake word.")
                            continue
                        inferred, reply = handled
                        print(f"{inferred.actor} @ {inferred.room}")
                        print(f"JARVIS: {reply}")
                        if not silent:
                            self.speak(
                                reply,
                                quiet=inferred.quiet_mode,
                                whisper=inferred.whisper_mode,
                                interrupt=True,
                                block=False,
                            )

            input_index = self._resolve_input_device(input_device)
            stream = sd.RawInputStream(
                samplerate=samplerate,
                blocksize=int(samplerate * 0.2),
                device=input_index,
                dtype="int16",
                channels=1,
                callback=callback,
            )

            sender_task = asyncio.create_task(sender())
            receiver_task = asyncio.create_task(receiver())

            try:
                with stream:
                    await receiver_task
            except KeyboardInterrupt:  # pragma: no cover - interactive path
                stop_event.set()
            finally:
                stop_event.set()
                audio_queue.put(None)
                sender_task.cancel()
                if not receiver_task.done():
                    receiver_task.cancel()
                await asyncio.gather(sender_task, receiver_task, return_exceptions=True)

        return 0

    def start_wake_word_listener(self) -> bool:
        """
        Start continuous wake word monitoring.
        When wake word detected, queues a signal for the main voice loop.
        """
        model = os.getenv("JARVIS_WAKE_WORD_MODEL", "hey_jarvis")

        def on_wake_word(model_name: str, score: float):
            self._wake_word_queue.put({"model": model_name, "score": score, "ts": time.time()})

        self._wake_word_listener = WakeWordListener(callback=on_wake_word, model_name=model)
        return self._wake_word_listener.start()

    def stop_wake_word_listener(self) -> None:
        if self._wake_word_listener:
            self._wake_word_listener.stop()

    def run_continuous_listen_loop(
        self,
        actor: str | None,
        room: str | None,
        record_duration: float = 4.0,
        input_device: str | None = None,
        silent: bool = False,
    ) -> int:
        """
        Continuous listening loop with wake word detection.
        Waits for wake word -> records -> transcribes -> responds -> speaks -> repeat.

        This is the production voice mode for the Mac Mini.
        """
        print("JARVIS continuous listening mode. Say 'Hey JARVIS' to activate.")
        started = self.start_wake_word_listener()
        if not started:
            print("Wake word unavailable — falling back to push-to-talk.")
            return self.run_push_to_talk_loop(
                duration=record_duration,
                actor=actor,
                room=room,
                input_device=input_device,
                silent=silent,
                require_wake_word=False,
            )

        try:
            while True:
                try:
                    # Wait for wake word (blocks until detected)
                    wake_event = self._wake_word_queue.get(timeout=60.0)
                    print(f"\n[Wake word detected — listening...]")

                    # Record after wake word
                    audio_path = self.record_audio(
                        duration=record_duration,
                        input_device=input_device,
                    )
                    transcript = self.transcribe_audio(audio_path)
                    print(f"Heard: {transcript}")

                    if not transcript.strip():
                        continue

                    handled = self.handle_text_turn(
                        raw_text=transcript,
                        explicit_actor=actor,
                        explicit_room=room,
                        require_wake_word=False,  # already detected
                    )
                    if not handled:
                        continue
                    inferred, reply = handled
                    print(f"JARVIS: {reply}")
                    if not silent:
                        self.speak(reply, quiet=inferred.quiet_mode, whisper=inferred.whisper_mode)

                except queue.Empty:
                    continue  # No wake word — keep listening
                except KeyboardInterrupt:
                    print("\nStopping.", file=sys.stderr)
                    return 130
                except Exception as exc:
                    logger.error(f"Continuous loop error: {exc}")
        finally:
            self.stop_wake_word_listener()

        return 0

    def record_audio(
        self,
        duration: float,
        samplerate: int = 16000,
        input_device: str | None = None,
    ) -> Path:
        frames = max(1, int(duration * samplerate))
        print(f"Listening for {duration:.1f} seconds...", flush=True)
        device_index = self._resolve_input_device(input_device)
        audio = sd.rec(
            frames,
            samplerate=samplerate,
            channels=1,
            dtype="int16",
            device=device_index,
        )
        sd.wait()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
            wav_path = Path(handle.name)

        mono_audio = np.squeeze(audio)
        write_wav(wav_path, samplerate, mono_audio)
        return wav_path

    def transcribe_audio(self, audio_path: Path) -> str:
        with audio_path.open("rb") as audio_file:
            transcription = self.runtime.openai_client.transcribe_audio(
                audio_file,
                model=DEFAULT_TRANSCRIBE_MODEL,
                prompt=TRANSCRIBE_PROMPT,
            )
        return transcription.strip()

    def speak(
        self,
        text: str,
        quiet: bool = False,
        whisper: bool = False,
        interrupt: bool = True,
        block: bool = True,
    ) -> None:
        if interrupt:
            self.stop_speaking()

        try:
            audio = synthesize_speech(self.runtime.config, text)
            with tempfile.NamedTemporaryFile(suffix=audio.extension, delete=False) as handle:
                audio_path = handle.name
                handle.write(audio.data)
            volume = "0.20" if whisper else ("0.35" if quiet else "1.0")
            self._play_with_process(
                ["afplay", "-v", volume, audio_path],
                cleanup_path=audio_path,
                block=block,
            )
            return
        except Exception:
            pass

        self._local_fallback_tts(text, quiet=quiet, whisper=whisper, block=block)

    def stop_speaking(self) -> None:
        with self._playback_lock:
            if self._playback_process is None:
                return
            if self._playback_process.poll() is None:
                self._playback_process.terminate()
                try:
                    self._playback_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._playback_process.kill()
            self._playback_process = None

    def _strip_wake_word(self, raw_text: str) -> tuple[bool, str]:
        text = raw_text.strip()
        lowered = text.lower()
        for wake_word in self.voice_context.wake_words:
            lowered_wake = wake_word.lower()
            if lowered.startswith(lowered_wake):
                cleaned = text[len(wake_word):].lstrip(" ,:.-")
                return True, cleaned
        return False, text

    def _extract_voice_mode(self, text: str) -> tuple[bool, bool, str]:
        lowered = text.lower().strip()
        cleaned = text.strip()
        quiet_mode = False
        whisper_mode = False
        whisper_prefixes = ("whisper mode", "whisper", "in a whisper")
        quiet_prefixes = ("quiet mode", "quietly", "keep it quiet", "softly")

        for prefix in whisper_prefixes:
            if lowered.startswith(prefix):
                whisper_mode = True
                quiet_mode = True
                cleaned = cleaned[len(prefix):].lstrip(" ,:.-")
                return quiet_mode, whisper_mode, cleaned

        for prefix in quiet_prefixes:
            if lowered.startswith(prefix):
                quiet_mode = True
                cleaned = cleaned[len(prefix):].lstrip(" ,:.-")
                break

        return quiet_mode, whisper_mode, cleaned

    def _infer_actor(self, cleaned: str, device_name: str) -> tuple[str, str]:
        lowered = cleaned.lower()
        for user in self.runtime.household.users.values():
            if user.display_name.lower() in lowered:
                return user.display_name, "direct-name"
        for member in self.runtime.identity_overview().get("members", []):
            display_name = str(member.get("display_name", "")).strip()
            aliases = [str(item).strip().lower() for item in member.get("voice_aliases", []) if str(item).strip()]
            if any(alias in lowered for alias in aliases):
                return display_name or str(member.get("user_id", "")).title(), "profile-alias"
        speaker_markers = {
            "my homework": "Caleb",
            "my quiz": "Caleb",
            "my project": "Anna",
            "troop meeting": "Rebekah",
            "grocery pickup": "Rebekah",
            "manuscript": "Chris",
            "thermo": "Chris",
        }
        for phrase, actor in speaker_markers.items():
            if phrase in lowered:
                return actor, "context-phrase"
        normalized_device = device_name.strip().lower()
        if normalized_device:
            for device in self.runtime.identity_overview().get("devices", []):
                label = str(device.get("label", "")).strip().lower()
                device_id = str(device.get("device_id", "")).strip().lower()
                if normalized_device in {label, device_id}:
                    candidate = (
                        str(device.get("default_actor_id", "")).strip()
                        or str(device.get("owner_user_id", "")).strip()
                        or str(device.get("last_actor_id", "")).strip()
                    )
                    if candidate:
                        try:
                            return self.runtime.get_actor(candidate).display_name, "identity-device"
                        except KeyError:
                            pass
        satellite = self._match_satellite(device_name)
        if satellite and satellite.default_speaker:
            return satellite.default_speaker, "device-map"
        return "Chris", "default"

    def _infer_room(self, cleaned: str, device_name: str) -> str:
        lowered = cleaned.lower()
        for room in self.runtime.household.rooms.values():
            if room.room_id in lowered or room.room_id.replace("-", " ") in lowered:
                return room.room_id
        satellite = self._match_satellite(device_name)
        if satellite:
            return satellite.room
        return "office"

    def _match_satellite(self, device_name: str):
        lowered_device = device_name.lower()
        for satellite in self.voice_context.satellites:
            if satellite.device_name.lower() == lowered_device:
                return satellite
        return None

    def _resolve_input_device(self, requested: str | None) -> int | None:
        if requested is None or requested == "":
            default_input = sd.default.device[0]
            return default_input if default_input != -1 else None
        if requested.isdigit():
            return int(requested)
        devices = sd.query_devices()
        lowered = requested.lower()
        for idx, device in enumerate(devices):
            if device["max_input_channels"] <= 0:
                continue
            if lowered in device["name"].lower():
                return idx
        raise ValueError(f"Unknown input device: {requested}")

    def _resolve_device_name(self, requested: str | None) -> str:
        try:
            index = self._resolve_input_device(requested)
        except ValueError:
            return requested or ""
        if index is None:
            return ""
        devices = sd.query_devices()
        return str(devices[index]["name"])

    def _local_fallback_tts(self, text: str, quiet: bool, whisper: bool, block: bool) -> None:
        rate = "145" if whisper else ("165" if quiet else "185")
        self._play_with_process(["say", "-v", "Alex", "-r", rate, text], block=block)

    def _play_with_process(self, cmd: list[str], cleanup_path: str | None = None, block: bool = True) -> None:
        with self._playback_lock:
            self._playback_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            process = self._playback_process
        if block:
            self._wait_for_process(process, cleanup_path=cleanup_path)
            return
        threading.Thread(
            target=self._wait_for_process,
            args=(process,),
            kwargs={"cleanup_path": cleanup_path},
            daemon=True,
        ).start()

    def _wait_for_process(self, process: subprocess.Popen[str], cleanup_path: str | None = None) -> None:
        process.wait()
        if cleanup_path and os.path.exists(cleanup_path):
            os.unlink(cleanup_path)
        with self._playback_lock:
            if self._playback_process is process:
                self._playback_process = None

    def _require_env(self, name: str) -> str:
        value = os.getenv(name, "")
        if not value:
            raise RuntimeError(f"Missing {name}. Add it to .env and run again.")
        return value

    def _build_ssl_context(self) -> ssl.SSLContext:
        if certifi is not None:
            return ssl.create_default_context(cafile=certifi.where())
        return ssl.create_default_context()


def build_voice_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("voice", help="Run JARVIS voice and text conversation surfaces")
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--loop", action="store_true", help="Run a push-to-talk microphone loop.")
    parser.add_argument("--text-loop", action="store_true", help="Run a typed conversation loop.")
    parser.add_argument("--realtime", action="store_true", help="Run Realtime API transcription loop.")
    parser.add_argument("--text", help="Handle one text turn and exit.")
    parser.add_argument("--actor")
    parser.add_argument("--room")
    parser.add_argument("--input-device")
    parser.add_argument("--duration", type=float, default=6.0)
    parser.add_argument("--samplerate", type=int, default=16000)
    parser.add_argument("--silent", action="store_true")
    parser.add_argument("--quiet", action="store_true", help="Request quieter reply playback and quieter response phrasing.")
    parser.add_argument("--whisper", action="store_true", help="Request whisper-style playback and shorter hush-mode replies.")
    parser.add_argument("--no-wake-word", action="store_true")
