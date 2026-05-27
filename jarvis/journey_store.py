"""
journey_store.py — Per-user event log for JARVIS Journey Tracking (Phase 5).

Appends structured events to per-user JSONL files and provides query helpers.
Zero external dependencies. Never raises — all errors are swallowed silently.
"""

from __future__ import annotations

from pathlib import Path
import json
import threading
import time
from datetime import datetime, timezone

JOURNEY_DIR = Path("data/journey")
_lock = threading.Lock()

EVENT_TYPES = {
    "task_created", "task_completed", "task_deleted",
    "reminder_created", "reminder_completed",
    "approval_actioned",
    "brief_received",
    "chronicle_entry",
    "agent_run",
    "kdp_sync",
    "idea_captured",
    "login",            # logged when /api/identity/me is called
}


def log_event(user_id: str, event_type: str, payload: dict = None) -> None:
    """Append a journey event for a user. Never raises."""
    try:
        JOURNEY_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "payload": payload or {},
        }
        path = JOURNEY_DIR / f"{user_id}.jsonl"
        with _lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def get_journey(user_id: str, days: int = 30, limit: int = 200) -> list[dict]:
    """Return recent events, newest first."""
    try:
        path = JOURNEY_DIR / f"{user_id}.jsonl"
        if not path.exists():
            return []
        cutoff = time.time() - days * 86400
        events = []
        with _lock:
            lines = path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            ev = json.loads(line)
            ts = datetime.fromisoformat(ev["ts"]).timestamp()
            if ts < cutoff:
                break
            events.append(ev)
            if len(events) >= limit:
                break
        return events
    except Exception:
        return []


def get_stats(user_id: str, days: int = 30) -> dict:
    """Aggregate event counts per type for the last N days."""
    events = get_journey(user_id, days=days, limit=10000)
    counts = {}
    for ev in events:
        counts[ev["type"]] = counts.get(ev["type"], 0) + 1
    return {"days": days, "total": len(events), "by_type": counts}


def get_all_users_stats(days: int = 7) -> dict:
    """Stats for all users (admin view)."""
    result = {}
    try:
        for path in JOURNEY_DIR.glob("*.jsonl"):
            uid = path.stem
            result[uid] = get_stats(uid, days=days)
    except Exception:
        pass
    return result


def get_last_login_ts(user_id: str) -> float:
    """Return the unix timestamp of the most recent 'login' event, or 0."""
    try:
        path = JOURNEY_DIR / f"{user_id}.jsonl"
        if not path.exists():
            return 0.0
        with _lock:
            lines = path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            ev = json.loads(line)
            if ev.get("type") == "login":
                return datetime.fromisoformat(ev["ts"]).timestamp()
    except Exception:
        pass
    return 0.0
