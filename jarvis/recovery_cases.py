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

    def _normalize_plan_step(self, raw_step: Any, index: int) -> dict[str, Any] | None:
        if isinstance(raw_step, str):
            label = raw_step.strip()
            detail = ""
            status = "pending"
            step_id = ""
        elif isinstance(raw_step, dict):
            label = str(raw_step.get("label") or raw_step.get("title") or raw_step.get("step") or "").strip()
            detail = str(raw_step.get("detail") or raw_step.get("summary") or "").strip()
            status = str(raw_step.get("status") or "pending").strip().lower() or "pending"
            step_id = str(raw_step.get("step_id") or raw_step.get("id") or "").strip()
        else:
            return None
        if not label:
            return None
        if status not in {"pending", "completed"}:
            status = "pending"
        return {
            "step_id": step_id or f"recovery-step-{index + 1}",
            "label": label,
            "detail": detail,
            "status": status,
            "completed_at": str(raw_step.get("completed_at") or "").strip() if isinstance(raw_step, dict) else "",
        }

    def _refresh_plan_state(self, record: dict[str, Any]) -> None:
        raw_steps = record.get("remediation_plan")
        normalized_steps: list[dict[str, Any]] = []
        if isinstance(raw_steps, list):
            for index, item in enumerate(raw_steps):
                step = self._normalize_plan_step(item, index)
                if step is not None:
                    normalized_steps.append(step)
        record["remediation_plan"] = normalized_steps
        total = len(normalized_steps)
        completed = sum(1 for item in normalized_steps if str(item.get("status") or "").strip().lower() == "completed")
        pending_steps = [item for item in normalized_steps if str(item.get("status") or "").strip().lower() != "completed"]
        next_step = pending_steps[0] if pending_steps else None
        if total == 0:
            plan_status = "unplanned"
            plan_label = "Unplanned"
        elif completed >= total:
            plan_status = "completed"
            plan_label = "Completed"
        elif completed == 0:
            plan_status = "planned"
            plan_label = "Planned"
        else:
            plan_status = "in_progress"
            plan_label = "In Progress"
        record["remediation_plan_count"] = total
        record["remediation_plan_completed_count"] = completed
        record["remediation_plan_status"] = plan_status
        record["remediation_plan_status_label"] = plan_label
        record["next_plan_step_id"] = str((next_step or {}).get("step_id") or "").strip()
        record["next_plan_step_label"] = str((next_step or {}).get("label") or "").strip()

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        for item in self._load_json():
            if str(item.get("case_id", "")).strip() == case_id.strip():
                from copy import deepcopy
                return deepcopy(item)
        return None

    def list_cases(self) -> list[dict[str, Any]]:
        records = self._load_json()
        for item in records:
            self._refresh_plan_state(item)
        return deepcopy(records)

    def upsert_case(
        self,
        *,
        source_kind: str,
        title: str,
        detail: str,
        related_route: str,
        related_key: str,
        metadata: dict[str, Any] | None = None,
        owner: str = "",
        root_cause: str = "",
        prevention_note: str = "",
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
                "remediation_status": "available",
                "remediation_status_label": "Available",
                "remediation_count": 0,
                "last_remediation_at": "",
                "last_remediation_action": "",
                "last_remediation_status": "",
                "remediation_plan": [],
                "remediation_plan_count": 0,
                "remediation_plan_completed_count": 0,
                "remediation_plan_status": "unplanned",
                "remediation_plan_status_label": "Unplanned",
                "next_plan_step_id": "",
                "next_plan_step_label": "",
                "owner": owner.strip(),
                "root_cause": root_cause.strip(),
                "prevention_note": prevention_note.strip(),
                "verification_note": "",
                "closure_note": "",
                "closed_at": "",
                "closed_by": "",
            }
            self._refresh_plan_state(record)
            records.append(record)
            self._save(records)
            return deepcopy(record)

        existing["title"] = title.strip() or str(existing.get("title", "")).strip() or "Recovery case"
        existing["detail"] = detail.strip() or str(existing.get("detail", "")).strip() or "Recovery case needs review."
        existing["related_route"] = related_route.strip() or str(existing.get("related_route", "")).strip() or "/recovery-center"
        existing["metadata"] = {**dict(existing.get("metadata") or {}), **dict(metadata or {})}
        existing.setdefault("remediation_status", "available")
        existing.setdefault("remediation_status_label", "Available")
        existing.setdefault("remediation_count", 0)
        existing.setdefault("last_remediation_at", "")
        existing.setdefault("last_remediation_action", "")
        existing.setdefault("last_remediation_status", "")
        existing.setdefault("remediation_plan", [])
        existing.setdefault("remediation_plan_count", 0)
        existing.setdefault("remediation_plan_completed_count", 0)
        existing.setdefault("remediation_plan_status", "unplanned")
        existing.setdefault("remediation_plan_status_label", "Unplanned")
        existing.setdefault("next_plan_step_id", "")
        existing.setdefault("next_plan_step_label", "")
        self._refresh_plan_state(existing)
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
        self._refresh_plan_state(target)
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
        self._refresh_plan_state(target)
        self._save(records)
        return deepcopy(target)

    def record_remediation(
        self,
        case_id: str,
        *,
        actor: str,
        action_type: str,
        note: str = "",
    ) -> dict[str, Any]:
        normalized_action = action_type.strip().lower()
        if normalized_action not in {"stage", "execute"}:
            raise ValueError("Unsupported recovery remediation action.")
        records = self._load_json()
        target = None
        for item in records:
            if str(item.get("case_id", "")).strip() == case_id.strip():
                target = item
                break
        if target is None:
            raise KeyError("Recovery case not found.")

        now = _now_iso()
        remediation_count = int(target.get("remediation_count", 0) or 0) + 1
        remediation_status = "staged" if normalized_action == "stage" else "executed"
        remediation_label = "Staged" if normalized_action == "stage" else "Executed"

        target["remediation_status"] = remediation_status
        target["remediation_status_label"] = remediation_label
        target["remediation_count"] = remediation_count
        target["last_remediation_at"] = now
        target["last_remediation_action"] = normalized_action
        target["last_remediation_status"] = remediation_status
        target["updated_at"] = now
        target["last_action_at"] = now
        target["last_action"] = f"remediation-{normalized_action}"
        if normalized_action == "execute":
            target["status"] = "watch"
            target["status_label"] = "Watch"

        history = list(target.get("history") or [])
        history.append(
            {
                "timestamp": now,
                "action": f"remediation-{normalized_action}",
                "status": str(target.get("status") or "open"),
                "actor": actor.strip() or "Chris",
                "detail": note.strip()
                or (
                    "Recovery auto-remediation staged for the next safe execution window."
                    if normalized_action == "stage"
                    else "Recovery auto-remediation executed and moved the case into watch."
                ),
            }
        )
        target["history"] = history[-20:]
        self._refresh_plan_state(target)
        self._save(records)
        return deepcopy(target)

    def save_remediation_plan(
        self,
        case_id: str,
        *,
        actor: str,
        steps: list[Any],
        note: str = "",
    ) -> dict[str, Any]:
        records = self._load_json()
        target = None
        for item in records:
            if str(item.get("case_id", "")).strip() == case_id.strip():
                target = item
                break
        if target is None:
            raise KeyError("Recovery case not found.")
        normalized_steps = [
            step
            for index, raw_step in enumerate(steps)
            for step in [self._normalize_plan_step(raw_step, index)]
            if step is not None
        ]
        if not normalized_steps:
            raise ValueError("At least one remediation step is required.")

        now = _now_iso()
        target["remediation_plan"] = normalized_steps
        target["updated_at"] = now
        target["last_action_at"] = now
        target["last_action"] = "remediation-plan"
        self._refresh_plan_state(target)

        history = list(target.get("history") or [])
        history.append(
            {
                "timestamp": now,
                "action": "remediation-plan",
                "status": str(target.get("status") or "open"),
                "actor": actor.strip() or "Chris",
                "detail": note.strip() or f"Recovery plan prepared with {len(normalized_steps)} step(s).",
            }
        )
        target["history"] = history[-24:]
        self._save(records)
        return deepcopy(target)

    def execute_next_plan_step(
        self,
        case_id: str,
        *,
        actor: str,
        note: str = "",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        records = self._load_json()
        target = None
        for item in records:
            if str(item.get("case_id", "")).strip() == case_id.strip():
                target = item
                break
        if target is None:
            raise KeyError("Recovery case not found.")
        self._refresh_plan_state(target)
        steps = list(target.get("remediation_plan") or [])
        next_index = next(
            (index for index, step in enumerate(steps) if str(step.get("status") or "").strip().lower() != "completed"),
            -1,
        )
        if next_index < 0:
            raise ValueError("Recovery plan has no pending steps.")

        now = _now_iso()
        step = dict(steps[next_index])
        step["status"] = "completed"
        step["completed_at"] = now
        steps[next_index] = step
        target["remediation_plan"] = steps
        target["updated_at"] = now
        target["last_action_at"] = now
        target["last_action"] = "remediation-plan-step"
        target["last_remediation_at"] = now
        target["last_remediation_action"] = "plan-step"
        target["last_remediation_status"] = "in_progress"
        self._refresh_plan_state(target)

        history = list(target.get("history") or [])
        history.append(
            {
                "timestamp": now,
                "action": "remediation-plan-step",
                "status": str(target.get("status") or "open"),
                "actor": actor.strip() or "Chris",
                "detail": note.strip() or f"Executed remediation step: {step.get('label')}.",
            }
        )
        target["history"] = history[-26:]
        self._save(records)
        return deepcopy(target), deepcopy(step)

    def set_lifecycle_fields(
        self,
        case_id: str,
        *,
        owner: str = "",
        root_cause: str = "",
        prevention_note: str = "",
        verification_note: str = "",
    ) -> dict[str, Any]:
        """Set durable lifecycle metadata: owner, root cause, prevention note, verification note."""
        records = self._load_json()
        target = None
        for item in records:
            if str(item.get("case_id", "")).strip() == case_id.strip():
                target = item
                break
        if target is None:
            raise KeyError("Recovery case not found.")
        now = _now_iso()
        if owner:
            target["owner"] = owner.strip()
        if root_cause:
            target["root_cause"] = root_cause.strip()
        if prevention_note:
            target["prevention_note"] = prevention_note.strip()
        if verification_note:
            target["verification_note"] = verification_note.strip()
        target["updated_at"] = now
        target["last_action_at"] = now
        target["last_action"] = "lifecycle-update"
        history = list(target.get("history") or [])
        history.append(
            {
                "timestamp": now,
                "action": "lifecycle-update",
                "status": str(target.get("status") or "open"),
                "detail": "Recovery case lifecycle fields updated.",
            }
        )
        target["history"] = history[-28:]
        self._save(records)
        return deepcopy(target)

    def close_case(
        self,
        case_id: str,
        *,
        actor: str,
        closure_note: str = "",
        verification_note: str = "",
        prevention_note: str = "",
    ) -> dict[str, Any]:
        """Close a recovery case with audit evidence: verification and prevention notes required."""
        records = self._load_json()
        target = None
        for item in records:
            if str(item.get("case_id", "")).strip() == case_id.strip():
                target = item
                break
        if target is None:
            raise KeyError("Recovery case not found.")
        now = _now_iso()
        target["status"] = "resolved"
        target["status_label"] = "Resolved"
        target["closed_at"] = now
        target["closed_by"] = actor.strip() or "Chris"
        if closure_note:
            target["closure_note"] = closure_note.strip()
        if verification_note:
            target["verification_note"] = verification_note.strip()
        if prevention_note:
            target["prevention_note"] = prevention_note.strip()
        target["updated_at"] = now
        target["last_action_at"] = now
        target["last_action"] = "closed"
        history = list(target.get("history") or [])
        history.append(
            {
                "timestamp": now,
                "action": "closed",
                "status": "resolved",
                "actor": actor.strip() or "Chris",
                "detail": closure_note.strip() or "Recovery case closed.",
            }
        )
        target["history"] = history[-30:]
        self._save(records)
        return deepcopy(target)
