from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ADAPTATION_PATH = Path.cwd() / "data" / "settings" / "adaptation_profiles.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AdaptationStore:
    def __init__(self, path: Path = ADAPTATION_PATH) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        default = {"profiles": {}, "history": []}
        if not self.path.exists():
            return default
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("profiles", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def profile(self, user_id: str) -> dict[str, Any] | None:
        return self.load().get("profiles", {}).get(user_id)

    def record_profile(self, user_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        payload = self.load()
        profiles = dict(payload.get("profiles", {}))
        history = list(payload.get("history", []))
        profiles[user_id] = snapshot
        history.append(
            {
                "user_id": user_id,
                "generated_at": snapshot.get("generated_at", _now_iso()),
                "summary": snapshot.get("digital_twin", {}).get("headline", ""),
                "signals": snapshot.get("signal_counts", {}),
            }
        )
        payload["profiles"] = profiles
        payload["history"] = history[-80:]
        self.save(payload)
        return snapshot
