"""D5: Voice session state machine — no audio I/O dependency.

Extracted here so tests and lightweight callers can import VoiceSession
without pulling in numpy / sounddevice.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger("jarvis.voice_session")

VOICE_SESSION_IDLE = "idle"
VOICE_SESSION_LISTENING = "listening"
VOICE_SESSION_PROCESSING = "processing"
VOICE_SESSION_SPEAKING = "speaking"
VOICE_SESSION_ERROR = "error"

_VOICE_SESSION_TRANSITIONS: dict[str, frozenset[str]] = {
    VOICE_SESSION_IDLE: frozenset({VOICE_SESSION_LISTENING}),
    VOICE_SESSION_LISTENING: frozenset({VOICE_SESSION_PROCESSING, VOICE_SESSION_IDLE, VOICE_SESSION_ERROR}),
    VOICE_SESSION_PROCESSING: frozenset({VOICE_SESSION_SPEAKING, VOICE_SESSION_IDLE, VOICE_SESSION_ERROR}),
    VOICE_SESSION_SPEAKING: frozenset({VOICE_SESSION_IDLE, VOICE_SESSION_ERROR}),
    VOICE_SESSION_ERROR: frozenset({VOICE_SESSION_IDLE}),
}


class VoiceSession:
    """Lightweight voice session state machine.

    Does NOT handle audio I/O — that is JarvisVoiceShell's responsibility.
    Manages state, tracks transitions, and provides honest unavailable state
    when the wake word model is absent.
    """

    def __init__(self, session_id: str = "") -> None:
        self.session_id = session_id or str(id(self))
        self._state: str = VOICE_SESSION_IDLE
        self._error_reason: str = ""
        self._wake_word_available: bool | None = None
        self._transitions: list[dict] = []

    def _record(self, from_state: str, to_state: str, reason: str = "") -> None:
        self._transitions.append({
            "from": from_state,
            "to": to_state,
            "reason": reason,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        if len(self._transitions) > 50:
            self._transitions = self._transitions[-50:]

    def transition(self, new_state: str, reason: str = "") -> bool:
        """Attempt a state transition. Returns True on success, False if invalid."""
        allowed = _VOICE_SESSION_TRANSITIONS.get(self._state, frozenset())
        if new_state not in allowed:
            logger.warning(
                "VoiceSession invalid transition %s → %s (allowed: %s)",
                self._state, new_state, sorted(allowed),
            )
            return False
        old = self._state
        self._state = new_state
        if new_state == VOICE_SESSION_ERROR:
            self._error_reason = reason
        elif new_state == VOICE_SESSION_IDLE:
            self._error_reason = ""
        self._record(old, new_state, reason)
        return True

    def reset_to_idle(self) -> None:
        """Force-reset to idle (e.g. after timeout or fatal error)."""
        old = self._state
        self._state = VOICE_SESSION_IDLE
        self._error_reason = ""
        self._record(old, VOICE_SESSION_IDLE, "reset")

    def check_wake_word_available(self) -> bool:
        """Check if the wake word model is importable. Caches result."""
        if self._wake_word_available is None:
            try:
                import openwakeword  # noqa: F401
                self._wake_word_available = True
            except ImportError:
                self._wake_word_available = False
        return bool(self._wake_word_available)

    @property
    def state(self) -> str:
        return self._state

    @property
    def error_reason(self) -> str:
        return self._error_reason

    def status(self) -> dict:
        wake_ok = self.check_wake_word_available()
        return {
            "session_id": self.session_id,
            "state": self._state,
            "error_reason": self._error_reason,
            "source": "live" if wake_ok else "unavailable",
            "wake_word_available": wake_ok,
            "recent_transitions": self._transitions[-5:],
        }
