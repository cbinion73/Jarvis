from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .data_hygiene import filter_records


FIRST_LIGHT_PATH = Path.cwd() / "data" / "settings" / "first_light.json"


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class FirstLightStore:
    path: Path = FIRST_LIGHT_PATH

    def load(self) -> dict[str, Any]:
        default = {"users": {}, "history": []}
        if not self.path.exists():
            return default
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("users", {})
        payload.setdefault("history", [])
        history = payload.get("history", [])
        payload["history"] = filter_records(history if isinstance(history, list) else [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def local_now(self, timezone_name: str) -> datetime:
        try:
            zone = ZoneInfo(timezone_name)
        except Exception:
            zone = ZoneInfo("America/New_York")
        return _now_utc().astimezone(zone)

    def status(self, user_id: str, timezone_name: str, *, after_hour: int = 6) -> dict[str, Any]:
        state = self.load()
        local_now = self.local_now(timezone_name)
        local_date = local_now.date().isoformat()
        user_state = dict(state.get("users", {}).get(user_id, {}))
        last_presented = str(user_state.get("last_presented_local_date", "")).strip()
        eligible = local_now.hour >= after_hour and last_presented != local_date
        latest_packet = self.latest_packet(user_id)
        return {
            "user_id": user_id,
            "local_date": local_date,
            "local_time": local_now.isoformat(),
            "after_hour": after_hour,
            "eligible": eligible,
            "already_presented_today": last_presented == local_date,
            "latest_packet": latest_packet,
        }

    def latest_packet(self, user_id: str) -> dict[str, Any] | None:
        history = self.load().get("history", [])
        for item in reversed(history if isinstance(history, list) else []):
            if isinstance(item, dict) and str(item.get("user_id", "")).strip().lower() == user_id.strip().lower():
                return item
        return None

    def mark_presented(self, user_id: str, packet: dict[str, Any], timezone_name: str) -> dict[str, Any]:
        state = self.load()
        local_now = self.local_now(timezone_name)
        local_date = local_now.date().isoformat()
        users = dict(state.get("users", {}))
        user_state = dict(users.get(user_id, {}))
        user_state["last_presented_local_date"] = local_date
        user_state["last_presented_at"] = _now_utc().isoformat()
        user_state["last_packet_id"] = str(packet.get("packet_id", "")).strip()
        users[user_id] = user_state
        history = list(state.get("history", []))
        history.append(packet)
        state["users"] = users
        state["history"] = history[-40:]
        self.save(state)
        return user_state
