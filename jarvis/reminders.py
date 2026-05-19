"""
reminders.py — Persistent reminders for JARVIS.

Reminders survive restarts. Stored at ~/.jarvis/reminders.json.
Thread-safe via a module-level Lock.
"""
from __future__ import annotations
import json, os, time, threading
from pathlib import Path
from typing import Any

_REMINDERS_PATH = Path(os.path.expanduser("~/.jarvis/reminders.json"))
_lock = threading.Lock()


def _load() -> list[dict]:
    try:
        if _REMINDERS_PATH.exists():
            return json.loads(_REMINDERS_PATH.read_text())
    except Exception:
        pass
    return []


def _save(reminders: list[dict]) -> None:
    _REMINDERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REMINDERS_PATH.write_text(json.dumps(reminders, indent=2))


def list_reminders() -> list[dict]:
    with _lock:
        return _load()


def add_reminder(text: str, due_iso: str | None = None, priority: str = "normal") -> dict:
    """Add a reminder. Returns the new reminder dict."""
    reminder = {
        "id": str(int(time.time() * 1000)),
        "text": text.strip(),
        "due": due_iso,          # ISO 8601 or None
        "priority": priority,    # "high" | "normal" | "low"
        "done": False,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with _lock:
        reminders = _load()
        reminders.append(reminder)
        _save(reminders)
    return reminder


def complete_reminder(reminder_id: str) -> bool:
    """Mark a reminder done. Returns True if found."""
    with _lock:
        reminders = _load()
        for r in reminders:
            if r["id"] == reminder_id:
                r["done"] = True
                _save(reminders)
                return True
    return False


def delete_reminder(reminder_id: str) -> bool:
    """Hard-delete a reminder. Returns True if found."""
    with _lock:
        reminders = _load()
        new = [r for r in reminders if r["id"] != reminder_id]
        if len(new) < len(reminders):
            _save(new)
            return True
    return False


def snooze_reminder(reminder_id: str, new_due_iso: str) -> bool:
    """Update the due time (snooze). Returns True if found."""
    with _lock:
        reminders = _load()
        for r in reminders:
            if r["id"] == reminder_id:
                r["due"] = new_due_iso
                r["done"] = False
                _save(reminders)
                return True
    return False


def pending_reminders() -> list[dict]:
    """Return all non-done reminders, sorted by due (None last)."""
    with _lock:
        reminders = _load()
    active = [r for r in reminders if not r.get("done")]
    def sort_key(r):
        return r["due"] or "9999"
    return sorted(active, key=sort_key)
