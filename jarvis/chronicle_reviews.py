from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_STATUS_LABELS = {
    "study": "Study Next",
    "family": "Queue Family Handoff",
    "resolved": "Resolved",
}


def _normalize_review(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)
    normalized.setdefault("entry_id", "")
    normalized.setdefault("entry_title", "")
    normalized.setdefault("entry_type", "")
    normalized.setdefault("review_status", "")
    normalized.setdefault("review_status_label", "")
    normalized.setdefault("review_note", "")
    normalized.setdefault("reviewed_at", "")
    normalized.setdefault("actor_id", "chris")
    normalized.setdefault("route", "/chronicle-center")
    return normalized


class ChronicleReviewStore:
    def __init__(self, root: Path | None = None) -> None:
        base = root or (Path.cwd() / "data" / "system")
        self.root = base
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "chronicle_reviews.json"
        self.log_path = self.root / "chronicle_reviews_log.jsonl"
        self.state_log_path = self.root / "chronicle_reviews_state_log.jsonl"

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
        rows = [_normalize_review(dict(item)) for item in payload if isinstance(item, dict)]
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
                    latest = [_normalize_review(dict(item)) for item in records if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            return deepcopy(default)
        return latest or deepcopy(default)

    def _save(self, records: list[dict[str, Any]]) -> None:
        ordered = sorted(
            [_normalize_review(dict(item)) for item in records if isinstance(item, dict)],
            key=lambda item: str(item.get("reviewed_at", "")),
            reverse=True,
        )
        atomic_write_json(self.path, ordered)
        payload = {"saved_at": _now_iso(), "records": ordered}
        append_jsonl(self.log_path, payload)
        append_jsonl(self.state_log_path, payload)

    def list_reviews(self, actor_id: str = "chris", limit: int = 8) -> list[dict[str, Any]]:
        normalized_actor = str(actor_id).strip().lower() or "chris"
        rows = [
            dict(item)
            for item in self._load_json()
            if str(item.get("actor_id", "")).strip().lower() == normalized_actor
        ]
        return deepcopy(rows[: max(1, limit)])

    def review_summary(self, actor_id: str = "chris", limit: int = 6) -> dict[str, Any]:
        rows = self.list_reviews(actor_id, limit=100)
        counts = {
            "study": len([item for item in rows if str(item.get("review_status") or "") == "study"]),
            "family": len([item for item in rows if str(item.get("review_status") or "") == "family"]),
            "resolved": len([item for item in rows if str(item.get("review_status") or "") == "resolved"]),
        }
        return {
            "count": len(rows),
            "counts": counts,
            "items": deepcopy(rows[: max(1, limit)]),
        }

    def review_entry(
        self,
        *,
        entry_id: str,
        actor_id: str,
        title: str,
        entry_type: str,
        status: str,
        note: str = "",
        route: str = "/chronicle-center",
    ) -> dict[str, Any]:
        normalized_status = str(status).strip().lower()
        if normalized_status not in _STATUS_LABELS:
            raise ValueError("Invalid Chronicle review status.")
        normalized_entry_id = str(entry_id).strip()
        if not normalized_entry_id:
            raise ValueError("entry_id is required.")
        records = self._load_json()
        matched: dict[str, Any] | None = None
        for item in records:
            if str(item.get("entry_id") or "").strip() == normalized_entry_id:
                matched = item
                break
        if matched is None:
            matched = {"entry_id": normalized_entry_id}
            records.append(matched)
        matched.update(
            {
                "entry_id": normalized_entry_id,
                "entry_title": str(title).strip() or "Chronicle entry",
                "entry_type": str(entry_type).strip() or "reflection",
                "review_status": normalized_status,
                "review_status_label": _STATUS_LABELS[normalized_status],
                "review_note": str(note).strip(),
                "reviewed_at": _now_iso(),
                "actor_id": str(actor_id).strip().lower() or "chris",
                "route": str(route).strip() or "/chronicle-center",
            }
        )
        self._save(records)
        return deepcopy(matched)
