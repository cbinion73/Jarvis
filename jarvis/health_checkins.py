from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_checkin(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)
    normalized.setdefault("review_status", "")
    normalized.setdefault("review_status_label", "")
    normalized.setdefault("review_note", "")
    normalized.setdefault("reviewed_at", "")
    return normalized


class HealthCheckInStore:
    def __init__(self, root: Path | None = None) -> None:
        base = root or (Path.cwd() / "data" / "system")
        self.root = base
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "health_checkins.json"
        self.log_path = self.root / "health_checkins_log.jsonl"
        self.state_log_path = self.root / "health_checkins_state_log.jsonl"

    def _load_json(self) -> list[dict[str, Any]]:
        default: list[dict[str, Any]] = []
        if not self.path.exists():
            return self._load_from_state_log(default)
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._load_from_state_log(default)
        if not isinstance(payload, list):
            return self._load_from_state_log(default)
        rows = [_normalize_checkin(dict(item)) for item in payload if isinstance(item, dict)]
        return rows or self._load_from_state_log(default)

    def _load_from_state_log(self, default: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.state_log_path.exists():
            return deepcopy(default)
        latest: list[dict[str, Any]] = []
        try:
            for line in self.state_log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [_normalize_checkin(dict(item)) for item in records if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            return deepcopy(default)
        return latest or deepcopy(default)

    def _save(self, records: list[dict[str, Any]]) -> None:
        ordered = sorted(
            [_normalize_checkin(dict(item)) for item in records if isinstance(item, dict)],
            key=lambda item: str(item.get("saved_at", "")),
            reverse=True,
        )
        atomic_write_json(self.path, ordered)
        payload = {"saved_at": _now_iso(), "records": ordered}
        append_jsonl(self.log_path, payload)
        append_jsonl(self.state_log_path, payload)

    def list_checkins(self, actor_id: str = "chris", limit: int = 8) -> list[dict[str, Any]]:
        normalized_actor = str(actor_id).strip().lower() or "chris"
        rows = [
            dict(item)
            for item in self._load_json()
            if str(item.get("actor_id", "")).strip().lower() == normalized_actor
        ]
        return deepcopy(rows[: max(1, limit)])

    def review_summary(self, actor_id: str = "chris", limit: int = 6) -> dict[str, Any]:
        rows = self.list_checkins(actor_id, limit=100)
        reviewed = [dict(item) for item in rows if str(item.get("review_status") or "").strip()]
        counts = {
            "watch": len([item for item in reviewed if str(item.get("review_status") or "") == "watch"]),
            "adjust": len([item for item in reviewed if str(item.get("review_status") or "") == "adjust"]),
            "resolved": len([item for item in reviewed if str(item.get("review_status") or "") == "resolved"]),
        }
        return {
            "count": len(reviewed),
            "counts": counts,
            "items": deepcopy(reviewed[: max(1, limit)]),
        }

    def save_checkin(
        self,
        *,
        actor_id: str,
        symptoms: str = "",
        note: str = "",
        energy_level: int | None = None,
        sleep_hours: float | None = None,
        stress_level: int | None = None,
        source: str = "manual",
    ) -> dict[str, Any]:
        records = self._load_json()
        entry = {
            "checkin_id": str(uuid.uuid4()),
            "actor_id": str(actor_id).strip().lower() or "chris",
            "symptoms": str(symptoms).strip(),
            "note": str(note).strip(),
            "energy_level": int(energy_level) if isinstance(energy_level, (int, float)) else None,
            "sleep_hours": float(sleep_hours) if isinstance(sleep_hours, (int, float)) else None,
            "stress_level": int(stress_level) if isinstance(stress_level, (int, float)) else None,
            "source": str(source).strip() or "manual",
            "saved_at": _now_iso(),
            "review_status": "",
            "review_status_label": "",
            "review_note": "",
            "reviewed_at": "",
        }
        records.append(entry)
        self._save(records)
        return deepcopy(entry)

    def review_checkin(
        self,
        *,
        checkin_id: str,
        status: str,
        note: str = "",
    ) -> dict[str, Any]:
        normalized_status = str(status).strip().lower()
        labels = {
            "watch": "Watch",
            "adjust": "Adjust Protocol",
            "resolved": "Resolved",
        }
        if normalized_status not in labels:
            raise ValueError("Invalid health review status.")
        records = self._load_json()
        for item in records:
            if str(item.get("checkin_id") or "").strip() != str(checkin_id).strip():
                continue
            item["review_status"] = normalized_status
            item["review_status_label"] = labels[normalized_status]
            item["review_note"] = str(note).strip()
            item["reviewed_at"] = _now_iso()
            self._save(records)
            return deepcopy(item)
        raise KeyError(f"Unknown check-in '{checkin_id}'.")
