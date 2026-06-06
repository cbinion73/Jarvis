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


class RecoveryCaseStore:
    def __init__(self, root: Path | None = None) -> None:
        base = root or (Path.cwd() / "data" / "system")
        self.root = base
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "recovery_cases.json"
        self.log_path = self.root / "recovery_cases_log.jsonl"
        self.state_log_path = self.root / "recovery_cases_state_log.jsonl"

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
        rows = [dict(item) for item in payload if isinstance(item, dict)]
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
                    latest = [dict(item) for item in records if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            return deepcopy(default)
        return latest or deepcopy(default)

    def _save(self, records: list[dict[str, Any]]) -> None:
        ordered = sorted(
            [dict(item) for item in records if isinstance(item, dict)],
            key=lambda item: str(item.get("updated_at", "")),
            reverse=True,
        )
        atomic_write_json(self.path, ordered)
        payload = {"saved_at": _now_iso(), "records": ordered}
        append_jsonl(self.log_path, payload)
        append_jsonl(self.state_log_path, payload)

    def list_cases(self) -> list[dict[str, Any]]:
        return deepcopy(self._load_json())

    def upsert_case(
        self,
        *,
        source_kind: str,
        title: str,
        detail: str,
        related_route: str,
        related_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_key = related_key.strip()
        now = _now_iso()
        records = self._load_json()
        existing = None
        for item in records:
            if (
                str(item.get("related_key", "")).strip() == normalized_key
                and str(item.get("source_kind", "")).strip() == source_kind.strip()
            ):
                existing = item
                break
        if existing is None:
            record = {
                "case_id": str(uuid.uuid4()),
                "source_kind": source_kind.strip() or "recovery",
                "title": title.strip() or "Recovery case",
                "detail": detail.strip() or "Recovery case opened.",
                "status": "open",
                "status_label": "Open",
                "related_route": related_route.strip() or "/recovery-center",
                "related_key": normalized_key or str(uuid.uuid4()),
                "metadata": dict(metadata or {}),
                "created_at": now,
                "updated_at": now,
                "last_action_at": now,
                "last_action": "opened",
                "history": [
                    {
                        "timestamp": now,
                        "action": "opened",
                        "status": "open",
                        "detail": detail.strip() or "Recovery case opened.",
                    }
                ],
            }
            records.append(record)
            self._save(records)
            return deepcopy(record)

        existing["title"] = title.strip() or str(existing.get("title", "")).strip() or "Recovery case"
        existing["detail"] = detail.strip() or str(existing.get("detail", "")).strip() or "Recovery case needs review."
        existing["related_route"] = related_route.strip() or str(existing.get("related_route", "")).strip() or "/recovery-center"
        existing["metadata"] = {**dict(existing.get("metadata") or {}), **dict(metadata or {})}
        existing["updated_at"] = now
        self._save(records)
        return deepcopy(existing)

    def update_status(self, case_id: str, *, status: str, actor: str, note: str = "") -> dict[str, Any]:
        normalized_status = status.strip().lower()
        if normalized_status not in {"investigating", "watch", "resolved"}:
            raise ValueError("Unsupported recovery case status.")
        records = self._load_json()
        target = None
        for item in records:
            if str(item.get("case_id", "")).strip() == case_id.strip():
                target = item
                break
        if target is None:
            raise KeyError("Recovery case not found.")
        now = _now_iso()
        target["status"] = normalized_status
        target["status_label"] = {
            "investigating": "Investigating",
            "watch": "Watch",
            "resolved": "Resolved",
        }[normalized_status]
        target["updated_at"] = now
        target["last_action_at"] = now
        target["last_action"] = normalized_status
        history = list(target.get("history") or [])
        history.append(
            {
                "timestamp": now,
                "action": normalized_status,
                "status": normalized_status,
                "actor": actor.strip() or "Chris",
                "detail": note.strip() or f"Recovery case moved to {normalized_status}.",
            }
        )
        target["history"] = history[-12:]
        self._save(records)
        return deepcopy(target)

    def record_execution(
        self,
        case_id: str,
        *,
        actor: str,
        action_type: str,
        note: str = "",
    ) -> dict[str, Any]:
        normalized_action = action_type.strip().lower()
        if normalized_action not in {"retry", "stabilize"}:
            raise ValueError("Unsupported recovery case execution action.")
        records = self._load_json()
        target = None
        for item in records:
            if str(item.get("case_id", "")).strip() == case_id.strip():
                target = item
                break
        if target is None:
            raise KeyError("Recovery case not found.")

        now = _now_iso()
        execution_count = int(target.get("execution_count", 0) or 0) + 1
        transition_status = "investigating" if normalized_action == "retry" else "watch"
        transition_label = {
            "investigating": "Investigating",
            "watch": "Watch",
        }[transition_status]

        target["status"] = transition_status
        target["status_label"] = transition_label
        target["execution_count"] = execution_count
        target["last_execution_at"] = now
        target["last_execution_action"] = normalized_action
        target["last_execution_status"] = "executed" if normalized_action == "retry" else "stabilized"
        target["updated_at"] = now
        target["last_action_at"] = now
        target["last_action"] = normalized_action

        history = list(target.get("history") or [])
        history.append(
            {
                "timestamp": now,
                "action": normalized_action,
                "status": transition_status,
                "actor": actor.strip() or "Chris",
                "detail": note.strip()
                or (
                    "Recovery retry execution loop started."
                    if normalized_action == "retry"
                    else "Recovery case moved into watch stabilization."
                ),
            }
        )
        target["history"] = history[-16:]
        self._save(records)
        return deepcopy(target)
