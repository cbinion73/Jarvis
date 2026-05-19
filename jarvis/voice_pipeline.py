"""
voice_pipeline.py — Epic 7: Voice Shell
Unified voice pipeline layer for JARVIS/Friday TTS synthesis.

Architecture:
    text → FridayPersona.prepare_for_voice() → VoicePipeline.synthesize()
          → ElevenLabsTTSProvider | PiperTTSProvider | SilentTTSProvider
          → audio bytes → speaker

Provider cascade: ElevenLabs → Piper → Silent (text-only fallback).
Thread-safe. Caches up to 50 results (LRU-style).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import subprocess
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib import error, request

logger = logging.getLogger("jarvis.voice_pipeline")

# ---------------------------------------------------------------------------
# Voice persona rules — import and append to any voice-mode system prompt
# ---------------------------------------------------------------------------

VOICE_PERSONA_RULES = """
## Voice Mode Rules

1. You are speaking, not writing. No bullet points, no markdown, no numbered lists, no headers. Every response must be natural spoken English only.
2. Call tools silently and immediately. Never say "I'm going to call..." or "Let me check that tool." Just do it, then speak the result naturally.
3. Keep responses short — two to four sentences maximum unless asked for detail.
4. When something fails, respond in character: "That feed isn't responding right now — want me to try again?" Never say "Error:" or show technical details.
5. Use contractions and natural speech patterns. "What's" not "What is". "I've got" not "I have obtained".
6. Address Chris by name occasionally — not every sentence, just naturally.
"""

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class VoiceConfig:
    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel — warm, professional
    elevenlabs_model: str = "eleven_turbo_v2_5"
    elevenlabs_stability: float = 0.5
    elevenlabs_similarity: float = 0.8
    elevenlabs_style: float = 0.0
    elevenlabs_speaker_boost: bool = True

    # Piper (local fallback)
    piper_enabled: bool = True
    piper_model: str = "en_US-lessac-medium"
    piper_executable: str = "piper"

    # OpenAI Realtime (future)
    openai_realtime_enabled: bool = False
    openai_realtime_model: str = "gpt-realtime-1.5"

    # Behaviour
    max_response_chars: int = 800  # truncate TTS input if too long
    speaking_rate: float = 1.0
    auto_punctuate: bool = True  # add sentence-ending punctuation if missing


# ---------------------------------------------------------------------------
# Abstract TTS provider
# ---------------------------------------------------------------------------

class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, config: VoiceConfig) -> bytes:
        """Return raw audio bytes (MP3 or WAV)."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider can be used right now."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def format(self) -> str:
        """Audio format string: 'mp3' or 'wav'."""
        ...


# ---------------------------------------------------------------------------
# ElevenLabs provider
# ---------------------------------------------------------------------------

_ELEVENLABS_TTS_TIMEOUT = 10  # seconds


class ElevenLabsTTSProvider(TTSProvider):
    """Calls the ElevenLabs REST API directly via urllib (no SDK)."""

    def __init__(self) -> None:
        self._consecutive_failures = 0
        self._max_failures = 3
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return "elevenlabs"

    @property
    def format(self) -> str:
        return "mp3"

    def is_available(self) -> bool:
        # Provider is blocked after 3 consecutive failures until reset
        with self._lock:
            return self._consecutive_failures < self._max_failures

    def synthesize(self, text: str, config: VoiceConfig) -> bytes:
        api_key = config.elevenlabs_api_key.strip()
        if not api_key:
            raise RuntimeError("ElevenLabs API key is not configured.")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.elevenlabs_voice_id}"
        body = json.dumps({
            "text": text,
            "model_id": config.elevenlabs_model,
            "voice_settings": {
                "stability": config.elevenlabs_stability,
                "similarity_boost": config.elevenlabs_similarity,
                "style": config.elevenlabs_style,
                "use_speaker_boost": config.elevenlabs_speaker_boost,
            },
        }).encode("utf-8")

        req = request.Request(
            url,
            data=body,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=_ELEVENLABS_TTS_TIMEOUT) as resp:
                audio_bytes = resp.read()
            with self._lock:
                self._consecutive_failures = 0
            return audio_bytes
        except (error.URLError, error.HTTPError, TimeoutError, OSError) as exc:
            with self._lock:
                self._consecutive_failures += 1
            raise RuntimeError(f"ElevenLabs request failed: {exc}") from exc

    def reset_failures(self) -> None:
        """Reset the failure counter (e.g. after config change)."""
        with self._lock:
            self._consecutive_failures = 0


# ---------------------------------------------------------------------------
# Piper provider
# ---------------------------------------------------------------------------

class PiperTTSProvider(TTSProvider):
    """Calls the Piper CLI to synthesise WAV audio locally."""

    @property
    def name(self) -> str:
        return "piper"

    @property
    def format(self) -> str:
        return "wav"

    def is_available(self) -> bool:
        return shutil.which("piper") is not None

    def synthesize(self, text: str, config: VoiceConfig) -> bytes:
        piper_bin = shutil.which(config.piper_executable) or shutil.which("piper")
        if not piper_bin:
            raise RuntimeError("Piper binary not found on PATH.")

        cmd = [piper_bin, "--model", config.piper_model, "--output_raw"]
        try:
            result = subprocess.run(
                cmd,
                input=text,
                capture_output=True,
                text=False,
                timeout=30,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(f"Piper binary not executable: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Piper synthesis timed out after 30 s") from exc

        if result.returncode != 0:
            stderr = (result.stderr or b"").decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Piper returned non-zero exit code {result.returncode}: {stderr}")

        return result.stdout  # raw PCM — callers treat it as WAV


# ---------------------------------------------------------------------------
# Silent fallback provider
# ---------------------------------------------------------------------------

class SilentTTSProvider(TTSProvider):
    """No-op provider for text-only mode. Always available."""

    @property
    def name(self) -> str:
        return "silent"

    @property
    def format(self) -> str:
        return "wav"

    def is_available(self) -> bool:
        return True

    def synthesize(self, text: str, config: VoiceConfig) -> bytes:
        logger.warning(
            "SilentTTSProvider: no TTS provider available — returning empty audio. "
            "Configure ELEVENLABS_API_KEY or install Piper to enable voice output."
        )
        return b""


# ---------------------------------------------------------------------------
# Voice pipeline
# ---------------------------------------------------------------------------

_CACHE_MAX_SIZE = 50
_VALID_STATES = {"idle", "listening", "thinking", "speaking"}


class VoicePipeline:
    """
    Manages TTS provider selection, caching, and voice state.
    Thread-safe singleton usage encouraged via init_voice() / get_pipeline().
    """

    def __init__(self, config: VoiceConfig) -> None:
        self._config = config
        self._providers: list[TTSProvider] = []
        self._active_provider: TTSProvider | None = None
        self._state: str = "idle"
        self._tts_cache: dict[str, tuple[bytes, str]] = {}  # hash → (bytes, format)
        self._cache_order: list[str] = []  # LRU tracking (oldest first)
        self._lock = threading.Lock()
        self._setup_providers()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def synthesize(self, text: str) -> tuple[bytes, str]:
        """
        Convert text to audio. Returns (audio_bytes, format_str).
        Uses provider cascade: ElevenLabs → Piper → Silent.
        Short texts are cached (up to 50 entries) for common phrases.
        """
        if not text:
            return b"", "wav"

        cache_key = hashlib.md5(text.encode("utf-8")).hexdigest()
        with self._lock:
            if cache_key in self._tts_cache:
                # Move to end (most recently used)
                self._cache_order.remove(cache_key)
                self._cache_order.append(cache_key)
                return self._tts_cache[cache_key]

        # Synthesise outside the lock so we don't block other reads
        audio_bytes, fmt = self._cascade_synthesize(text)

        # Cache if non-empty
        if audio_bytes:
            with self._lock:
                if cache_key not in self._tts_cache:
                    if len(self._tts_cache) >= _CACHE_MAX_SIZE:
                        # Evict oldest
                        oldest = self._cache_order.pop(0)
                        self._tts_cache.pop(oldest, None)
                    self._tts_cache[cache_key] = (audio_bytes, fmt)
                    self._cache_order.append(cache_key)

        return audio_bytes, fmt

    def get_state(self) -> str:
        with self._lock:
            return self._state

    def set_state(self, state: str) -> None:
        if state not in _VALID_STATES:
            raise ValueError(f"Invalid voice state: {state!r}. Must be one of {_VALID_STATES}")
        with self._lock:
            self._state = state

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            active_name = self._active_provider.name if self._active_provider else "none"
            providers_snapshot = [
                {"name": p.name, "available": p.is_available()} for p in self._providers
            ]
            state = self._state
            cache_size = len(self._tts_cache)
        return {
            "active_provider": active_name,
            "providers": providers_snapshot,
            "state": state,
            "cache_size": cache_size,
        }

    def update_config(self, config: VoiceConfig) -> None:
        """Swap in a new config and re-build the provider list."""
        with self._lock:
            self._config = config
            self._tts_cache.clear()
            self._cache_order.clear()
        self._setup_providers()

    def synthesize_streaming(
        self,
        text: str,
        on_sentence: callable,
    ) -> int:
        """
        Split text into sentences, synthesize each one as soon as it's ready,
        and call on_sentence(audio_bytes, sentence_text) for each.

        Returns total number of sentences processed.
        Inspired by Friday's producer/consumer streaming TTS pattern.
        """
        sentences = _split_sentences(text)
        count = 0
        for sentence in sentences:
            audio_bytes, _fmt = self.synthesize(sentence)
            on_sentence(audio_bytes, sentence)
            count += 1
        return count

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _setup_providers(self) -> None:
        """Configure ordered provider cascade based on current config."""
        providers: list[TTSProvider] = []
        if self._config.elevenlabs_api_key.strip():
            providers.append(ElevenLabsTTSProvider())
        if self._config.piper_enabled:
            providers.append(PiperTTSProvider())
        providers.append(SilentTTSProvider())

        with self._lock:
            self._providers = providers
            self._active_provider = providers[0] if providers else None

    def _cascade_synthesize(self, text: str) -> tuple[bytes, str]:
        """Try each provider in order; log and fall back on failure."""
        with self._lock:
            providers = list(self._providers)
            config = self._config

        previous_provider: str | None = None
        for provider in providers:
            if not provider.is_available():
                continue
            try:
                audio_bytes = provider.synthesize(text, config)
                if previous_provider:
                    logger.info(
                        "Voice synthesis: now using %s (previously attempted %s)",
                        provider.name,
                        previous_provider,
                    )
                with self._lock:
                    self._active_provider = provider
                return audio_bytes, provider.format
            except Exception as exc:
                next_provider = self._next_available_name(providers, provider)
                logger.warning(
                    "Falling back from %s to %s: %s",
                    provider.name,
                    next_provider or "none",
                    exc,
                )
                previous_provider = provider.name

        # All providers failed — SilentTTSProvider should never raise, but guard anyway
        logger.error("All TTS providers failed for text of length %d", len(text))
        return b"", "wav"

    @staticmethod
    def _next_available_name(providers: list[TTSProvider], current: TTSProvider) -> str | None:
        found = False
        for p in providers:
            if found and p.is_available():
                return p.name
            if p is current:
                found = True
        return None


# ---------------------------------------------------------------------------
# Sentence-streaming helpers
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """Split on sentence boundaries: . ! ? followed by space or end."""
    # Split on .!? followed by whitespace or end, preserve sentence-ending punct
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    # Filter empty, merge very short fragments (< 8 chars) with next sentence
    result: list[str] = []
    carry = ""
    for part in parts:
        combined = (carry + " " + part).strip() if carry else part
        if len(combined) < 8 and combined:
            carry = combined
        else:
            result.append(combined)
            carry = ""
    if carry:
        if result:
            result[-1] = result[-1] + " " + carry
        else:
            result.append(carry)
    return [s for s in result if s.strip()]


def stream_speak(text: str, pipeline: "VoicePipeline") -> list[bytes]:
    """
    Synthesize text sentence by sentence. Returns list of audio chunks in order.
    Each chunk is available as soon as that sentence is done — callers can
    stream chunks to the client progressively.
    """
    chunks: list[bytes] = []
    pipeline.synthesize_streaming(text, on_sentence=lambda audio, _: chunks.append(audio))
    return chunks


# ---------------------------------------------------------------------------
# Time-aware greeting
# ---------------------------------------------------------------------------

def get_time_aware_greeting(name: str = "boss") -> str:
    """
    Returns a JARVIS-persona greeting appropriate to the time of day.
    Mirrors Friday's on_enter() pattern.
    """
    hour = datetime.now(timezone.utc).hour  # UTC; adjust below for US Central
    # Approximate US Central Time (UTC-5/6) — good enough for greetings
    local_hour = (hour - 5) % 24

    if local_hour < 5:
        return f"You're up late, {name}. What do you need?"
    elif local_hour < 12:
        return f"Good morning, {name}. What are we working on today?"
    elif local_hour < 17:
        return f"Good afternoon, {name}. What's on your mind?"
    elif local_hour < 21:
        return f"Good evening, {name}. What do you need?"
    else:
        return f"Still at it, {name}? What can I do for you?"


# ---------------------------------------------------------------------------
# Friday Persona
# ---------------------------------------------------------------------------

class FridayPersona:
    """
    Friday is JARVIS's Voice Director.
    She shapes voice responses to be appropriate for audio:
      - Shorter sentences
      - No markdown, lists, or headers
      - Conversational rhythm
      - Natural speech patterns
    """

    # Patterns applied in order during prepare_for_voice()
    _STRIP_PATTERNS: list[tuple[re.Pattern, str]] = [
        (re.compile(r'\*\*(.+?)\*\*', re.DOTALL), r'\1'),   # bold → plain
        (re.compile(r'\*(.+?)\*', re.DOTALL), r'\1'),        # italic → plain
        (re.compile(r'#{1,6}\s+'), ''),                       # headers
        (re.compile(r'\[(.+?)\]\(.*?\)'), r'\1'),             # links → link text
        (re.compile(r'`{3}.*?`{3}', re.DOTALL), ''),         # fenced code blocks
        (re.compile(r'`(.+?)`'), r'\1'),                      # inline code → plain
    ]

    # Bullet/numbered list items — replaced with spoken transitions
    _BULLET_PATTERN = re.compile(r'^\s*[-•*]\s+', re.MULTILINE)
    _NUMBERED_PATTERN = re.compile(r'^\s*\d+\.\s+', re.MULTILINE)

    # Abbreviation expansions
    _ABBREVIATIONS: list[tuple[re.Pattern, str]] = [
        (re.compile(r'\bDr\.', re.IGNORECASE), 'Doctor'),
        (re.compile(r'\bMr\.', re.IGNORECASE), 'Mister'),
        (re.compile(r'\bMrs\.', re.IGNORECASE), 'Missus'),
        (re.compile(r'\bMs\.', re.IGNORECASE), 'Miss'),
        (re.compile(r'\bvs\.'), 'versus'),
        (re.compile(r'\betc\.'), 'et cetera'),
        (re.compile(r'\be\.g\.'), 'for example'),
        (re.compile(r'\bi\.e\.'), 'that is'),
        (re.compile(r'\bapprox\.'), 'approximately'),
        (re.compile(r'\bst\.', re.IGNORECASE), 'street'),
        (re.compile(r'\bave\.', re.IGNORECASE), 'avenue'),
    ]

    # Spoken list transitions
    _LIST_TRANSITIONS = ["First,", "Second,", "Third,", "Fourth,", "Fifth,", "Also,", "And finally,"]

    def prepare_for_voice(self, text: str, max_chars: int = 800) -> str:
        """
        Clean an LLM response for TTS:
        1. Strip markdown
        2. Convert bullet lists to natural speech transitions
        3. Expand abbreviations
        4. Truncate if over max_chars
        5. Ensure ends with punctuation
        """
        if not text:
            return text

        # 1. Strip markdown
        result = text
        for pattern, replacement in self._STRIP_PATTERNS:
            result = pattern.sub(replacement, result)

        # 2. Convert bullet/numbered lists
        result = self._convert_lists(result)

        # 3. Expand abbreviations
        for pattern, expansion in self._ABBREVIATIONS:
            result = pattern.sub(expansion, result)

        # 4. Collapse excess whitespace
        result = re.sub(r'\n{3,}', '\n\n', result)
        result = re.sub(r'[ \t]+', ' ', result)
        result = result.strip()

        # 5. Truncate
        if len(result) > max_chars:
            # Break at a sentence boundary near the limit
            truncated = result[:max_chars]
            last_period = max(
                truncated.rfind('. '),
                truncated.rfind('! '),
                truncated.rfind('? '),
            )
            if last_period > max_chars // 2:
                result = truncated[: last_period + 1]
            else:
                result = truncated.rstrip() + "…"

        # 6. Ensure ends with terminal punctuation
        result = result.strip()
        if result and result[-1] not in {'.', '!', '?', '…'}:
            result += '.'

        return result

    def _convert_lists(self, text: str) -> str:
        """Replace bullet/numbered list items with spoken transitions."""
        lines = text.split('\n')
        result_lines: list[str] = []
        transition_idx = 0

        for line in lines:
            if self._BULLET_PATTERN.match(line):
                content = self._BULLET_PATTERN.sub('', line).strip()
                if content:
                    transition = self._LIST_TRANSITIONS[
                        min(transition_idx, len(self._LIST_TRANSITIONS) - 1)
                    ]
                    result_lines.append(f"{transition} {content}")
                    transition_idx += 1
            elif self._NUMBERED_PATTERN.match(line):
                content = self._NUMBERED_PATTERN.sub('', line).strip()
                if content:
                    transition = self._LIST_TRANSITIONS[
                        min(transition_idx, len(self._LIST_TRANSITIONS) - 1)
                    ]
                    result_lines.append(f"{transition} {content}")
                    transition_idx += 1
            else:
                # Reset transition counter on blank lines (new list section)
                if not line.strip():
                    transition_idx = 0
                result_lines.append(line)

        return '\n'.join(result_lines)

    def should_speak(self, text: str, context: dict | None = None) -> bool:
        """
        Return False for responses that should not be spoken:
          - Pure JSON or code responses
          - Very long technical outputs (over 3000 chars)
          - Responses tagged as text-only in context
        """
        if not text or not text.strip():
            return False

        if context and context.get("text_only"):
            return False

        stripped = text.strip()

        # Pure JSON check
        if stripped.startswith(('{', '[')) and stripped.endswith(('}', ']')):
            try:
                json.loads(stripped)
                return False
            except (json.JSONDecodeError, ValueError):
                pass

        # Fenced code block — almost certainly not speakable
        if stripped.startswith('```'):
            return False

        # Very long technical output
        if len(stripped) > 3000:
            return False

        return True

    def get_greeting(self, hour: int | None = None) -> str:
        """Time-appropriate greeting for voice start."""
        if hour is None:
            hour = datetime.now().hour
        if 5 <= hour < 12:
            return "Good morning, Sir."
        elif 12 <= hour < 17:
            return "Good afternoon."
        elif 17 <= hour < 21:
            return "Good evening, Sir."
        else:
            return "Still at it. What do you need?"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_pipeline: VoicePipeline | None = None
_friday: FridayPersona | None = None
_pipeline_lock = threading.Lock()


def init_voice(config: Any) -> VoicePipeline:
    """
    Initialise the voice pipeline. Called at server startup.
    `config` is an AppConfig (or any object with elevenlabs_api_key /
    elevenlabs_voice / piper_binary / piper_model_path attributes).
    """
    global _pipeline, _friday

    voice_cfg = VoiceConfig()

    # Pull from AppConfig if available
    if hasattr(config, "elevenlabs_api_key"):
        import os
        api_key = (
            os.getenv("ELEVENLABS_API_KEY", "").strip()
            or getattr(config, "elevenlabs_api_key", "").strip()
        )
        voice_cfg.elevenlabs_api_key = api_key
    if hasattr(config, "elevenlabs_voice"):
        voice_id = getattr(config, "elevenlabs_voice", "").strip()
        if voice_id:
            voice_cfg.elevenlabs_voice_id = voice_id
    if hasattr(config, "piper_binary"):
        piper_bin = getattr(config, "piper_binary", "piper").strip()
        if piper_bin:
            voice_cfg.piper_executable = piper_bin
    if hasattr(config, "piper_model_path"):
        piper_path = getattr(config, "piper_model_path", None)
        if piper_path:
            voice_cfg.piper_model = str(piper_path)

    with _pipeline_lock:
        _pipeline = VoicePipeline(voice_cfg)
        _friday = FridayPersona()

    logger.info(
        "Voice pipeline initialised. Provider status: %s",
        [{"name": p["name"], "available": p["available"]} for p in _pipeline.get_status()["providers"]],
    )
    return _pipeline


def get_pipeline() -> VoicePipeline | None:
    return _pipeline


def get_friday() -> FridayPersona:
    if _friday is None:
        return FridayPersona()
    return _friday
