import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from elevenlabs import save
from elevenlabs.client import ElevenLabs
from openai import OpenAI
from scipy.io.wavfile import write as write_wav


load_dotenv()

YOUR_NAME = os.getenv("YOUR_NAME", "Chris")
OPENAI_MODEL = os.getenv("OPENAI_TEXT_MODEL") or os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")
ELEVENLABS_VOICE = os.getenv("ELEVENLABS_VOICE", "Adam")
SYSTEM_PROMPT = (
    "You are JARVIS, a concise British-inspired household associate. "
    "Be direct, capable, dryly witty, and warm. "
    "Keep spoken responses short unless the user asks for more detail. "
    "Prefer one to three sentences."
)
TRANSCRIBE_PROMPT = (
    "This is a live household assistant conversation. "
    "Important names may include Chris, Rebekah, Caleb, Anna, JARVIS, Chronicle, "
    "Thermo Fisher, Scouts 95, and Garden of Hope."
)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name}. Add it to .env and run again.")
    return value


def build_openai_client() -> OpenAI:
    require_env("OPENAI_API_KEY")
    return OpenAI()


def build_elevenlabs_client() -> ElevenLabs:
    api_key = require_env("ELEVENLABS_API_KEY")
    return ElevenLabs(api_key=api_key)


def resolve_voice_id(voice: ElevenLabs, requested: str) -> str:
    voice_id = requested
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
    return voice_id


def speak(text: str) -> None:
    voice = build_elevenlabs_client()
    voice_id = resolve_voice_id(voice, ELEVENLABS_VOICE)
    audio = voice.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        output_format="mp3_44100_128",
    )
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as handle:
        audio_path = handle.name

    try:
        save(audio, audio_path)
        subprocess.run(["afplay", audio_path], check=True)
    finally:
        if os.path.exists(audio_path):
            os.unlink(audio_path)


def ask_brain(name: str) -> str:
    brain = build_openai_client()
    response = brain.responses.create(
        model=OPENAI_MODEL,
        max_output_tokens=80,
        input=f"Say a short greeting to {name}. Be direct. Sound like JARVIS from Iron Man, but keep it brief.",
    )
    return response.output_text.strip()


def respond_to_user(user_text: str) -> str:
    brain = build_openai_client()
    response = brain.responses.create(
        model=OPENAI_MODEL,
        max_output_tokens=120,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
    )
    return response.output_text.strip()


def record_audio(duration: float, samplerate: int = 16000) -> Path:
    frames = max(1, int(duration * samplerate))
    print(f"Listening for {duration:.1f} seconds...", flush=True)
    audio = sd.rec(frames, samplerate=samplerate, channels=1, dtype="int16")
    sd.wait()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        wav_path = Path(handle.name)

    mono_audio = np.squeeze(audio)
    write_wav(wav_path, samplerate, mono_audio)
    return wav_path


def transcribe_audio(audio_path: Path) -> str:
    brain = build_openai_client()
    with audio_path.open("rb") as audio_file:
        transcription = brain.audio.transcriptions.create(
            model=OPENAI_TRANSCRIBE_MODEL,
            file=audio_file,
            prompt=TRANSCRIBE_PROMPT,
        )
    text = getattr(transcription, "text", None)
    if isinstance(text, str):
        return text.strip()
    return str(transcription).strip()


def list_input_devices() -> int:
    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        if device["max_input_channels"] > 0:
            print(
                f"{idx}: {device['name']} | input_channels={device['max_input_channels']} | "
                f"default_samplerate={device['default_samplerate']}"
            )
    return 0


def run_once_greeting(silent: bool) -> int:
    try:
        text = ask_brain(YOUR_NAME)
    except Exception as exc:
        print(f"OpenAI error: {exc}", file=sys.stderr)
        return 1

    print(f"JARVIS: {text}")

    try:
        if not silent:
            speak(text)
    except Exception as exc:
        print(f"ElevenLabs audio error: {exc}", file=sys.stderr)
        print("The OpenAI brain path worked; fix voice settings and run again.", file=sys.stderr)
        return 2

    return 0


def run_text_loop(silent: bool) -> int:
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
            reply = respond_to_user(user_text)
            print(f"JARVIS: {reply}")
            if not silent:
                speak(reply)
        except Exception as exc:
            print(f"Loop error: {exc}", file=sys.stderr)
    return 0


def run_voice_loop(duration: float, silent: bool) -> int:
    print("JARVIS voice loop is live.")
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
            audio_path = record_audio(duration)
            transcript = transcribe_audio(audio_path)
            if not transcript:
                print("JARVIS: I did not catch that.")
                continue
            print(f"You said: {transcript}")
            reply = respond_to_user(transcript)
            print(f"JARVIS: {reply}")
            if not silent:
                speak(reply)
        except KeyboardInterrupt:
            print("\nStopping.", file=sys.stderr)
            return 130
        except Exception as exc:
            print(f"Voice loop error: {exc}", file=sys.stderr)
        finally:
            if audio_path and audio_path.exists():
                audio_path.unlink()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="APEX/JARVIS OpenAI and ElevenLabs starter")
    parser.add_argument("--loop", action="store_true", help="Run an interactive conversation loop.")
    parser.add_argument("--text-input", action="store_true", help="Use typed input instead of microphone capture.")
    parser.add_argument("--duration", type=float, default=6.0, help="Seconds to record for each mic turn.")
    parser.add_argument("--list-devices", action="store_true", help="List available input devices and exit.")
    parser.add_argument("--silent", action="store_true", help="Skip speech playback and print text only.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.list_devices:
        return list_input_devices()
    if args.loop and args.text_input:
        return run_text_loop(args.silent)
    if args.loop:
        return run_voice_loop(args.duration, args.silent)
    return run_once_greeting(args.silent)


if __name__ == "__main__":
    raise SystemExit(main())
