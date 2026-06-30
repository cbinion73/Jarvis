"""
Per-user settings profiles.
Each user gets data/settings/profile_{user_id}.json
"""
from pathlib import Path
import json, threading
from datetime import datetime, timezone

from .persistence import append_jsonl, atomic_write_json
from .state_log_utils import read_jsonl_tail

PROFILES_DIR = Path("data/settings/profiles")
_lock = threading.Lock()

DEFAULT_PROFILE = {
    "theme": "glass",
    "voice_provider": "fish",
    "voice_id": "",
    "language": "en",
    "timezone": "America/New_York",
    "greeting_name": "",          # e.g. "Chris" — overrides display_name
    "brief_enabled": True,
    "brief_time": "07:00",
    "notifications": {
        "approvals": True,
        "health_alerts": True,
        "calendar_reminders": True,
        "agent_updates": False,
    },
    "dashboard": {
        "show_health": True,
        "show_finance": False,
        "show_dining": True,
        "show_chronicle": True,
        "show_publishing": False,
    },
    "privacy": {
        "share_health_with_family": False,
        "share_calendar_with_family": True,
        "private_chronicle": True,
    },
    "updated_at": None,
}

def _profile_path(user_id: str) -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    safe = user_id.replace("/", "_").replace("..", "_")
    return PROFILES_DIR / f"{safe}.json"

def _profile_log_path(user_id: str) -> Path:
    path = _profile_path(user_id)
    return path.with_name(f"{path.stem}_log.jsonl")

def _profile_state_log_path(user_id: str) -> Path:
    path = _profile_path(user_id)
    return path.with_name(f"{path.stem}_state_log.jsonl")

def load_profile(user_id: str) -> dict:
    """Load profile for user, merging with defaults for missing keys."""
    path = _profile_path(user_id)
    with _lock:
        if not path.exists():
            return _load_profile_from_state_log(user_id)
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(saved, dict) and saved:
                return _merge_profile(saved, user_id)
            return _load_profile_from_state_log(user_id)
        except Exception:
            return _load_profile_from_state_log(user_id)

def _merge_profile(saved: dict, user_id: str) -> dict:
    merged = {**DEFAULT_PROFILE, **saved, "user_id": user_id}
    for key in ("notifications", "dashboard", "privacy"):
        merged[key] = {**DEFAULT_PROFILE.get(key, {}), **saved.get(key, {})}
    return merged

def _load_profile_from_state_log(user_id: str) -> dict:
    path = _profile_state_log_path(user_id)
    default = {**DEFAULT_PROFILE, "user_id": user_id}
    if not path.exists():
        return _load_profile_from_log(user_id)
    try:
        latest: dict = {}
        for payload in read_jsonl_tail(path):
            records = payload.get("records")
            if isinstance(records, dict):
                latest = dict(records)
        if latest:
            return _merge_profile(latest, user_id)
        return _load_profile_from_log(user_id)
    except Exception:
        return _load_profile_from_log(user_id)

def _load_profile_from_log(user_id: str) -> dict:
    path = _profile_log_path(user_id)
    default = {**DEFAULT_PROFILE, "user_id": user_id}
    if not path.exists():
        return default
    try:
        latest: dict = {}
        for payload in read_jsonl_tail(path):
            records = payload.get("records")
            if isinstance(records, dict):
                latest = dict(records)
        if latest:
            return _merge_profile(latest, user_id)
        return default
    except Exception:
        return default

def save_profile(user_id: str, updates: dict) -> dict:
    """Merge updates into existing profile and save."""
    current = load_profile(user_id)
    # Merge top-level keys
    for key, val in updates.items():
        if key in ("notifications", "dashboard", "privacy") and isinstance(val, dict):
            current[key] = {**current.get(key, {}), **val}
        elif key not in ("user_id",):  # protect user_id
            current[key] = val
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    current["user_id"] = user_id
    path = _profile_path(user_id)
    log_path = _profile_log_path(user_id)
    state_log_path = _profile_state_log_path(user_id)
    with _lock:
        atomic_write_json(path, current, ensure_ascii=False)
        append_jsonl(
            log_path,
            {
                "saved_at": current["updated_at"],
                "records": current,
            },
            ensure_ascii=False,
        )
        append_jsonl(
            state_log_path,
            {
                "saved_at": current["updated_at"],
                "records": current,
            },
            ensure_ascii=False,
        )
    return current

def get_all_profiles() -> dict[str, dict]:
    """Load all existing profiles keyed by user_id."""
    result = {}
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    for p in PROFILES_DIR.glob("*.json"):
        user_id = p.stem
        result[user_id] = load_profile(user_id)
    return result

def seed_default_profiles() -> None:
    """Create default profiles for all known family members if they don't exist."""
    defaults = {
        "chris":    {"theme": "glass",   "greeting_name": "Chris",   "timezone": "America/New_York", "dashboard": {**DEFAULT_PROFILE["dashboard"], "show_finance": True, "show_publishing": True}},
        "rebekah":  {"theme": "glass",   "greeting_name": "Rebekah", "timezone": "America/New_York"},
        "caleb":    {"theme": "classic", "greeting_name": "Caleb",   "timezone": "America/New_York", "dashboard": {**DEFAULT_PROFILE["dashboard"], "show_finance": False, "show_publishing": False}},
        "anna":     {"theme": "glass",   "greeting_name": "Anna",    "timezone": "America/New_York", "dashboard": {**DEFAULT_PROFILE["dashboard"], "show_finance": False, "show_publishing": False}},
    }
    for user_id, overrides in defaults.items():
        path = _profile_path(user_id)
        if not path.exists():
            save_profile(user_id, overrides)
