"""E12: Perception/security config contract.

Honest unavailable state for camera/sensor feeds that are not yet wired.
Privacy governance: no raw video archive in cloud, no cameras in private spaces.

Covers:
- Camera feed config validation
- Privacy governance rules (hard constraints)
- Honest unavailable when camera/sensor not configured
- Perception event routing policy
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .persistence import append_jsonl

_PERCEPTION_AUDIT_PATH = Path("data/perception/config_audit.jsonl")


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Hard constraints — never overridden
# ---------------------------------------------------------------------------
PRIVATE_SPACES = frozenset({"bedroom", "bathroom", "restroom", "toilet", "changing_room"})

PRIVACY_HARD_CONSTRAINTS = [
    "No cameras in bedrooms or bathrooms — ever.",
    "No raw video archived to cloud storage.",
    "No audio recording without explicit per-session consent.",
    "Facial recognition output must not be sent to external APIs without approval.",
    "Perception events are not logged to JARVIS public memory.",
]

# ---------------------------------------------------------------------------
# Known perception feed definitions
# ---------------------------------------------------------------------------
KNOWN_FEEDS = {
    "porch": {
        "display_name": "Front Porch",
        "space": "exterior",
        "privacy_concern": False,
        "env_var": "CAMERA_PORCH_URL",
        "description": "Package/visitor detection at front door",
    },
    "garage": {
        "display_name": "Garage",
        "space": "garage",
        "privacy_concern": False,
        "env_var": "CAMERA_GARAGE_URL",
        "description": "Vehicle/person presence in garage",
    },
    "living_room": {
        "display_name": "Living Room",
        "space": "common_area",
        "privacy_concern": False,
        "env_var": "CAMERA_LIVING_ROOM_URL",
        "description": "Room presence detection",
    },
    "bedroom": {
        "display_name": "Bedroom",
        "space": "bedroom",
        "privacy_concern": True,
        "env_var": None,
        "description": "BLOCKED — bedroom cameras are never permitted.",
    },
    "bathroom": {
        "display_name": "Bathroom",
        "space": "bathroom",
        "privacy_concern": True,
        "env_var": None,
        "description": "BLOCKED — bathroom cameras are never permitted.",
    },
}


def _audit_privacy_block(feed_id: str, reason: str) -> None:
    record: dict[str, Any] = {
        "ts": _ts(),
        "event": "privacy_block",
        "feed_id": feed_id,
        "reason": reason,
    }
    try:
        _PERCEPTION_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        append_jsonl(_PERCEPTION_AUDIT_PATH, record)
    except Exception:
        pass


def check_feed_config(feed_id: str, env_vars: dict[str, str] | None = None) -> dict[str, Any]:
    """Return honest configuration and availability state for a perception feed.

    Hard constraint: private-space feeds are always blocked.
    """
    env_vars = env_vars or {}
    feed = KNOWN_FEEDS.get(feed_id)

    # Unknown feed
    if feed is None:
        return {
            "feed_id": feed_id,
            "available": False,
            "source": "unavailable",
            "reason": f"Feed '{feed_id}' is not in the known-feeds registry.",
            "action_required": "Add feed definition to KNOWN_FEEDS before attempting to configure.",
        }

    # Hard constraint: private spaces are always blocked
    if feed.get("privacy_concern") or feed.get("space") in PRIVATE_SPACES:
        _audit_privacy_block(feed_id, PRIVACY_HARD_CONSTRAINTS[0])
        return {
            "feed_id": feed_id,
            "available": False,
            "source": "blocked",
            "hard_boundary": True,
            "reason": f"Feed '{feed_id}' is in a private space — permanently blocked by privacy policy.",
            "policy": PRIVACY_HARD_CONSTRAINTS[0],
        }

    # Check env var
    env_var = feed.get("env_var")
    if env_var and not env_vars.get(env_var):
        return {
            "feed_id": feed_id,
            "display_name": feed["display_name"],
            "available": False,
            "source": "unavailable",
            "reason": f"Environment variable {env_var} is not set.",
            "action_required": f"Set {env_var} in .env to enable this feed.",
            "space": feed["space"],
        }

    return {
        "feed_id": feed_id,
        "display_name": feed["display_name"],
        "available": True,
        "source": "config",
        "space": feed["space"],
        "env_var": env_var,
        "description": feed["description"],
    }


def privacy_governance_summary() -> dict[str, Any]:
    """Return the full privacy governance policy for UI display."""
    blocked = [
        fid for fid, f in KNOWN_FEEDS.items()
        if f.get("privacy_concern") or f.get("space") in PRIVATE_SPACES
    ]
    return {
        "hard_constraints": PRIVACY_HARD_CONSTRAINTS,
        "permanently_blocked_feeds": blocked,
        "private_space_categories": sorted(PRIVATE_SPACES),
        "cloud_video_archive": False,
        "facial_recognition_external_api": False,
        "source": "policy",
    }
