from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

ALLOWED_ARTIFACT_OUTCOMES = {
    "used",
    "completed",
    "helpful",
    "not_used",
    "needs_revision",
    "abandoned",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ArtifactOutcomeStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "artifact_outcomes.json"
        self.log_path = self.root / "artifact_outcomes_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"outcomes": [], "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("outcomes", [])
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Artifact outcome storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def record_outcome(
        self,
        *,
        recorded_by: str,
        target_kind: str,
        target_id: str,
        outcome: str,
        note: str = "",
        mission_id: str = "",
        target_category: str = "",
        target_label: str = "",
        artifact_ref: str = "",
        storage_mode: str = "",
        backing_store_files: list[str] | None = None,
    ) -> dict[str, Any]:
        cleaned_outcome = str(outcome or "").strip().lower()
        if cleaned_outcome not in ALLOWED_ARTIFACT_OUTCOMES:
            raise ValueError(
                "outcome must be one of: used, completed, helpful, not_used, needs_revision, abandoned"
            )
        now = _now_iso()
        record = {
            "outcome_id": str(uuid.uuid4()),
            "recorded_at": now,
            "recorded_by": str(recorded_by or "").strip() or "Chris",
            "target_kind": str(target_kind or "").strip(),
            "target_id": str(target_id or "").strip(),
            "mission_id": str(mission_id or "").strip(),
            "target_category": str(target_category or "").strip(),
            "target_label": str(target_label or "").strip(),
            "artifact_ref": str(artifact_ref or "").strip(),
            "storage_mode": str(storage_mode or "").strip(),
            "backing_store_files": [str(item).strip() for item in list(backing_store_files or []) if str(item).strip()],
            "outcome": cleaned_outcome,
            "note": str(note or "").strip(),
        }
        payload = self.load()
        outcomes = [dict(item) for item in list(payload.get("outcomes") or []) if isinstance(item, dict)]
        history = [dict(item) for item in list(payload.get("history") or []) if isinstance(item, dict)]
        outcomes.append(record)
        history.append(
            {
                "event": "artifact-outcome-recorded",
                "outcome_id": record["outcome_id"],
                "target_kind": record["target_kind"],
                "target_id": record["target_id"],
                "mission_id": record["mission_id"],
                "outcome": record["outcome"],
                "recorded_by": record["recorded_by"],
                "recorded_at": now,
            }
        )
        payload["outcomes"] = outcomes[-500:]
        payload["history"] = history[-500:]
        self.save(payload)
        return record

    def list_outcomes(
        self,
        *,
        target_kind: str,
        target_id: str,
        mission_id: str = "",
    ) -> list[dict[str, Any]]:
        kind_key = str(target_kind or "").strip()
        target_key = str(target_id or "").strip()
        mission_key = str(mission_id or "").strip()
        if not kind_key or not target_key:
            return []
        payload = self.load()
        records = [dict(item) for item in list(payload.get("outcomes") or []) if isinstance(item, dict)]
        filtered = [
            item
            for item in records
            if str(item.get("target_kind", "")).strip() == kind_key
            and str(item.get("target_id", "")).strip() == target_key
            and (not mission_key or str(item.get("mission_id", "")).strip() == mission_key)
        ]
        return filtered

    def all_outcomes(self, *, mission_id: str = "") -> list[dict[str, Any]]:
        mission_key = str(mission_id or "").strip()
        payload = self.load()
        records = [dict(item) for item in list(payload.get("outcomes") or []) if isinstance(item, dict)]
        if not mission_key:
            return records
        return [item for item in records if str(item.get("mission_id", "")).strip() == mission_key]

    def summary(self, *, mission_id: str = "", limit: int = 12) -> dict[str, Any]:
        records = self.all_outcomes(mission_id=mission_id)
        cleaned_limit = max(1, min(int(limit or 12), 50))
        counts_by_outcome: dict[str, int] = {}
        counts_by_target_kind: dict[str, int] = {}
        counts_by_mission: dict[str, int] = {}
        for item in records:
            outcome_key = str(item.get("outcome", "")).strip() or "unknown"
            target_key = str(item.get("target_kind", "")).strip() or "unknown"
            mission_key = str(item.get("mission_id", "")).strip() or "unscoped"
            counts_by_outcome[outcome_key] = counts_by_outcome.get(outcome_key, 0) + 1
            counts_by_target_kind[target_key] = counts_by_target_kind.get(target_key, 0) + 1
            counts_by_mission[mission_key] = counts_by_mission.get(mission_key, 0) + 1
        recent_records = [dict(item) for item in reversed(records[-cleaned_limit:])]
        return {
            "mission_id": str(mission_id or "").strip(),
            "total_records": len(records),
            "counts_by_outcome": counts_by_outcome,
            "counts_by_target_kind": counts_by_target_kind,
            "counts_by_mission": counts_by_mission,
            "recent_outcomes": recent_records,
            "learning_effect": "none",
        }
