from __future__ import annotations

from .config import AppConfig
from .speech import AudioPayload, synthesize_speech


def generate_tts_mp3(config: AppConfig, text: str, voice_settings: dict | None = None) -> bytes:
    audio = synthesize_speech(config, text, voice_settings=voice_settings)
    return audio.data


def generate_tts_audio(config: AppConfig, text: str, voice_settings: dict | None = None) -> AudioPayload:
    return synthesize_speech(config, text, voice_settings=voice_settings)
