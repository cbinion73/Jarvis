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


def _normalize_entry(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)
    normalized.setdefault("history_id", "")
    normalized.setdefault("actor_id", "chris")
    normalized.setdefault("event_type", "")
    normalized.setdefault("title", "")
    normalized.setdefault("detail", "")
    normalized.setdefault("status_label", "")
    normalized.setdefault("related_label", "")
    normalized.setdefault("project_id", "")
    normalized.setdefault("review_id", "")
    normalized.setdefault("step", "")
    normalized.setdefault("route", "/publish")
    normalized.setdefault("saved_at", "")
    return normalized


class PublishHistoryStore:
    def __init__(self, root: Path | None = None) -> None:
        base = root or (Path.cwd() / "data" / "system")
        self.root = base
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "publish_history.json"
        self.log_path = self.root / "publish_history_log.jsonl"
        self.state_log_path = self.root / "publish_history_state_log.jsonl"

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
        rows = [_normalize_entry(dict(item)) for item in payload if isinstance(item, dict)]
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
                    latest = [_normalize_entry(dict(item)) for item in records if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            return deepcopy(default)
        return latest or deepcopy(default)

    def _save(self, records: list[dict[str, Any]]) -> None:
        ordered = sorted(
            [_normalize_entry(dict(item)) for item in records if isinstance(item, dict)],
            key=lambda item: str(item.get("saved_at", "")),
            reverse=True,
        )
        atomic_write_json(self.path, ordered)
        payload = {"saved_at": _now_iso(), "records": ordered}
        append_jsonl(self.log_path, payload)
        append_jsonl(self.state_log_path, payload)

    def list_history(self, actor_id: str = "chris", limit: int = 8) -> list[dict[str, Any]]:
        normalized_actor = str(actor_id).strip().lower() or "chris"
        rows = [
            dict(item)
            for item in self._load_json()
            if str(item.get("actor_id", "")).strip().lower() == normalized_actor
        ]
        return deepcopy(rows[: max(1, limit)])

    def summary(self, actor_id: str = "chris", limit: int = 6) -> dict[str, Any]:
        rows = self.list_history(actor_id, limit=100)
        counts = {
            "approved": len([item for item in rows if str(item.get("event_type") or "") == "review-approved"]),
            "revision": len([item for item in rows if str(item.get("event_type") or "") == "review-revision"]),
            "completed": len([item for item in rows if str(item.get("event_type") or "") == "checklist-completed"]),
            "reopened": len([item for item in rows if str(item.get("event_type") or "") == "checklist-reopened"]),
            "drafted": len([item for item in rows if str(item.get("event_type") or "") == "project-created"]),
        }
        return {
            "count": len(rows),
            "counts": counts,
            "items": deepcopy(rows[: max(1, limit)]),
        }

    def record_event(
        self,
        *,
        actor_id: str,
        event_type: str,
        title: str,
        detail: str,
        status_label: str,
        route: str = "/publish",
        related_label: str = "",
        project_id: str = "",
        review_id: str = "",
        step: str = "",
    ) -> dict[str, Any]:
        normalized_event_type = str(event_type).strip().lower()
        if not normalized_event_type:
            raise ValueError("event_type is required.")
        records = self._load_json()
        entry = {
            "history_id": str(uuid.uuid4()),
            "actor_id": str(actor_id).strip().lower() or "chris",
            "event_type": normalized_event_type,
            "title": str(title).strip() or "Publish event",
            "detail": str(detail).strip(),
            "status_label": str(status_label).strip() or "Updated",
            "related_label": str(related_label).strip(),
            "project_id": str(project_id).strip(),
            "review_id": str(review_id).strip(),
            "step": str(step).strip(),
            "route": str(route).strip() or "/publish",
            "saved_at": _now_iso(),
        }
        records.append(entry)
        self._save(records)
        return deepcopy(entry)
