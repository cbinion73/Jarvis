from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

ALLOWED_AUTONOMY_STATE_STATUSES = {
    "queued",
    "in_progress",
    "blocked",
    "completed",
}

ALLOWED_AUTONOMY_APPROVAL_STATES = {
    "not_requested",
    "required",
    "approved",
    "not_required",
}

ALLOWED_AUTONOMY_PLAN_ACTION_STATUSES = {
    "proposed_not_run",
}

ALLOWED_AUTONOMY_CONTROL_ACTIONS = {
    "pause",
    "resume",
    "abort",
}

ALLOWED_AUTONOMY_CONTROL_POSTURES = {
    "recorded_active",
    "paused",
    "aborted",
}

ALLOWED_AUTONOMY_READINESS_STATES = {
    "not_ready",
    "ready_pending_approval",
    "ready_within_boundary",
}

ALLOWED_AUTONOMY_FOLLOW_THROUGH_STATUSES = {
    "not_triggered",
    "local_proof_created",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class AutonomyStateStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)
    follow_through_root: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "autonomy_states.json"
        self.log_path = self.root / "autonomy_states_log.jsonl"
        self.follow_through_root = self.root / "follow_through"

    def load(self) -> dict[str, Any]:
        default = {"autonomy_states": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("autonomy_states", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Autonomy-state storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_state(
        self,
        *,
        actor: str,
        title: str,
        objective: str,
        status: str = "queued",
        current_focus: str = "",
        next_step: str = "",
        requested_scope: str = "",
        initiation_reason: str = "",
        approval_state: str = "required",
        approval_required: bool = True,
        allowed_action_boundary: str = "",
        blocked_reason: str = "",
    ) -> dict[str, Any]:
        cleaned_title = str(title or "").strip()
        cleaned_objective = str(objective or "").strip()
        cleaned_status = str(status or "").strip().lower() or "queued"
        cleaned_focus = str(current_focus or "").strip()
        cleaned_next_step = str(next_step or "").strip()
        cleaned_requested_scope = str(requested_scope or "").strip()
        cleaned_initiation_reason = str(initiation_reason or "").strip()
        cleaned_approval_state = str(approval_state or "").strip().lower() or "required"
        cleaned_allowed_action_boundary = str(allowed_action_boundary or "").strip() or "record_visibility_only"
        cleaned_blocked_reason = str(blocked_reason or "").strip()
        if not cleaned_title:
            raise ValueError("title is required")
        if not cleaned_objective:
            raise ValueError("objective is required")
        if cleaned_status not in ALLOWED_AUTONOMY_STATE_STATUSES:
            raise ValueError("status must be one of: queued, in_progress, blocked, completed")
        if not cleaned_requested_scope:
            raise ValueError("requested_scope is required")
        if not cleaned_initiation_reason:
            raise ValueError("initiation_reason is required")
        if cleaned_approval_state not in ALLOWED_AUTONOMY_APPROVAL_STATES:
            raise ValueError("approval_state must be one of: approved, not_requested, not_required, required")
        approval_required_flag = bool(approval_required)
        if cleaned_approval_state == "not_required":
            approval_required_flag = False
        if not cleaned_blocked_reason and cleaned_approval_state != "approved":
            cleaned_blocked_reason = "autonomy execution is not enabled in this slice"
        now = _now_iso()
        autonomy_id = str(uuid.uuid4())
        record = {
            "autonomy_id": autonomy_id,
            "object_kind": "autonomy_state",
            "initiated_by": str(actor or "").strip() or "Chris",
            "title": cleaned_title,
            "objective": cleaned_objective,
            "status": cleaned_status,
            "current_focus": cleaned_focus,
            "next_step": cleaned_next_step,
            "requested_scope": cleaned_requested_scope,
            "initiation_reason": cleaned_initiation_reason,
            "approval_required": approval_required_flag,
            "approval_state": cleaned_approval_state,
            "allowed_action_boundary": cleaned_allowed_action_boundary,
            "blocked_reason": cleaned_blocked_reason,
            "created_at": now,
            "updated_at": now,
            "visibility_mode": "recorded_state_only",
            "autonomous_execution_recorded": False,
            "background_execution_claimed": False,
            "progress_summary": "",
            "planning_note": "",
            "proposed_actions": [],
            "planned_action_count": 0,
            "has_proposed_plan": False,
            "current_control_posture": "recorded_active",
            "last_control_action": "",
            "last_control_reason": "",
            "last_control_changed_by": "",
            "last_control_changed_at": "",
            "control_history": [],
            "readiness_state": "not_ready",
            "readiness_reason": "",
            "approval_gate_status": "approval_not_satisfied",
            "last_readiness_changed_by": "",
            "last_readiness_changed_at": "",
            "readiness_history": [],
            "local_follow_through_status": "not_triggered",
            "last_follow_through_effect": "",
            "last_follow_through_triggered_by": "",
            "last_follow_through_triggered_at": "",
            "last_follow_through_artifact_path": "",
            "follow_through_history": [],
        }
        payload = self.load()
        states = dict(payload.get("autonomy_states", {}))
        history = [dict(item) for item in list(payload.get("history") or []) if isinstance(item, dict)]
        states[autonomy_id] = record
        history.append(
            {
                "event": "autonomy-state-created",
                "autonomy_id": autonomy_id,
                "title": cleaned_title,
                "status": cleaned_status,
                "initiated_by": record["initiated_by"],
                "approval_state": cleaned_approval_state,
                "created_at": now,
            }
        )
        payload["autonomy_states"] = states
        payload["history"] = history[-300:]
        self.save(payload)
        return record

    def _write_follow_through_packet(
        self,
        *,
        autonomy_id: str,
        title: str,
        objective: str,
        requested_scope: str,
        readiness_state: str,
        approval_gate_status: str,
        actor: str,
        triggered_at: str,
        trigger_note: str,
        proposed_actions: list[dict[str, Any]],
    ) -> Path:
        safe_title = title or "Autonomy state"
        action_lines = "".join(
            f"- {str(item.get('title', '')).strip() or 'Untitled proposed action'}"
            f" [{str(item.get('execution_status', '')).strip() or 'proposed_not_run'}]\n"
            for item in proposed_actions
        ) or "- No proposed actions were stored on this autonomy record.\n"
        note_line = trigger_note if trigger_note else "No extra trigger note was recorded."
        body = (
            "# Autonomy Local Follow-Through Proof\n\n"
            f"Autonomy ID: {autonomy_id}\n"
            f"Title: {safe_title}\n"
            f"Triggered by: {actor}\n"
            f"Triggered at: {triggered_at}\n"
            "Local effect: wrote this bounded local proof packet.\n\n"
            "What ran:\n"
            "- A local markdown proof packet was written to disk for this autonomy record.\n"
            "- Stored autonomy fields were copied into this packet for later inspection.\n\n"
            "What did not run:\n"
            "- No invisible or background execution started.\n"
            "- No network retrieval or external tool action occurred.\n"
            "- No multi-agent or workforce orchestration occurred.\n"
            "- No approval state was auto-changed.\n\n"
            f"Objective:\n{objective or 'No objective recorded.'}\n\n"
            f"Requested scope:\n{requested_scope or 'No requested scope recorded.'}\n\n"
            f"Readiness state: {readiness_state}\n"
            f"Approval gate status: {approval_gate_status}\n"
            f"Trigger note: {note_line}\n\n"
            "Proposed actions snapshot:\n"
            f"{action_lines}"
        )
        slug = autonomy_id.replace("/", "-").replace(" ", "-")
        target = self.follow_through_root / f"{slug}-local-follow-through.md"
        self.follow_through_root.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        return target

    def trigger_local_follow_through(
        self,
        autonomy_id: str,
        *,
        actor: str,
        trigger_note: str = "",
    ) -> dict[str, Any]:
        cleaned_autonomy_id = str(autonomy_id or "").strip()
        if not cleaned_autonomy_id:
            raise ValueError("autonomy_id is required")
        cleaned_actor = str(actor or "").strip() or "Chris"
        cleaned_trigger_note = str(trigger_note or "").strip()

        payload = self.load()
        states = dict(payload.get("autonomy_states", {}))
        history = [dict(item) for item in list(payload.get("history") or []) if isinstance(item, dict)]
        record = states.get(cleaned_autonomy_id)
        if not isinstance(record, dict):
            raise KeyError(f"Unknown autonomy state: {cleaned_autonomy_id}")

        readiness_state = str(record.get("readiness_state", "not_ready") or "not_ready").strip()
        if readiness_state != "ready_within_boundary":
            raise ValueError("local follow-through trigger requires readiness_state=ready_within_boundary")
        control_posture = str(record.get("current_control_posture", "recorded_active") or "recorded_active").strip()
        if control_posture != "recorded_active":
            raise ValueError("local follow-through trigger requires current_control_posture=recorded_active")

        now = _now_iso()
        artifact_path = self._write_follow_through_packet(
            autonomy_id=cleaned_autonomy_id,
            title=str(record.get("title", "")).strip(),
            objective=str(record.get("objective", "")).strip(),
            requested_scope=str(record.get("requested_scope", "")).strip(),
            readiness_state=readiness_state,
            approval_gate_status=str(record.get("approval_gate_status", "approval_not_satisfied")).strip() or "approval_not_satisfied",
            actor=cleaned_actor,
            triggered_at=now,
            trigger_note=cleaned_trigger_note,
            proposed_actions=[dict(item) for item in list(record.get("proposed_actions") or []) if isinstance(item, dict)],
        )

        updated_record = dict(record)
        follow_entry = {
            "status": "local_proof_created",
            "effect": "local_status_packet_written",
            "artifact_path": str(artifact_path),
            "trigger_note": cleaned_trigger_note,
            "triggered_by": cleaned_actor,
            "triggered_at": now,
        }
        follow_history = [dict(item) for item in list(updated_record.get("follow_through_history") or []) if isinstance(item, dict)]
        follow_history.append(follow_entry)
        updated_record["local_follow_through_status"] = "local_proof_created"
        updated_record["last_follow_through_effect"] = "local_status_packet_written"
        updated_record["last_follow_through_triggered_by"] = cleaned_actor
        updated_record["last_follow_through_triggered_at"] = now
        updated_record["last_follow_through_artifact_path"] = str(artifact_path)
        updated_record["follow_through_history"] = follow_history[-20:]
        updated_record["updated_at"] = now

        states[cleaned_autonomy_id] = updated_record
        history.append(
            {
                "event": "autonomy-local-follow-through-triggered",
                "autonomy_id": cleaned_autonomy_id,
                "effect": "local_status_packet_written",
                "artifact_path": str(artifact_path),
                "changed_by": cleaned_actor,
                "created_at": now,
            }
        )
        payload["autonomy_states"] = states
        payload["history"] = history[-300:]
        self.save(payload)
        return updated_record

    def apply_readiness_state(
        self,
        autonomy_id: str,
        *,
        actor: str,
        readiness_state: str,
        readiness_reason: str = "",
    ) -> dict[str, Any]:
        cleaned_autonomy_id = str(autonomy_id or "").strip()
        if not cleaned_autonomy_id:
            raise ValueError("autonomy_id is required")
        cleaned_actor = str(actor or "").strip() or "Chris"
        cleaned_readiness_state = str(readiness_state or "").strip().lower()
        cleaned_readiness_reason = str(readiness_reason or "").strip()
        if cleaned_readiness_state not in ALLOWED_AUTONOMY_READINESS_STATES:
            raise ValueError("readiness_state must be one of: not_ready, ready_pending_approval, ready_within_boundary")
        if not cleaned_readiness_reason:
            raise ValueError("readiness_reason is required")

        payload = self.load()
        states = dict(payload.get("autonomy_states", {}))
        history = [dict(item) for item in list(payload.get("history") or []) if isinstance(item, dict)]
        record = states.get(cleaned_autonomy_id)
        if not isinstance(record, dict):
            raise KeyError(f"Unknown autonomy state: {cleaned_autonomy_id}")

        control_posture = str(record.get("current_control_posture", "recorded_active") or "recorded_active").strip()
        if control_posture == "aborted" and cleaned_readiness_state != "not_ready":
            raise ValueError("aborted autonomy state cannot be marked ready")

        approval_state = str(record.get("approval_state", "required") or "required").strip().lower()
        approval_required = bool(record.get("approval_required", False))
        if cleaned_readiness_state == "ready_within_boundary":
            if approval_required and approval_state not in {"approved", "not_required"}:
                raise ValueError("ready_within_boundary requires approval to be satisfied or not required")
            approval_gate_status = "within_boundary"
        elif cleaned_readiness_state == "ready_pending_approval":
            if not approval_required or approval_state in {"approved", "not_required"}:
                raise ValueError("ready_pending_approval requires an unsatisfied approval gate")
            approval_gate_status = "approval_pending"
        else:
            approval_gate_status = "approval_not_satisfied"

        now = _now_iso()
        updated_record = dict(record)
        readiness_entry = {
            "readiness_state": cleaned_readiness_state,
            "readiness_reason": cleaned_readiness_reason,
            "approval_gate_status": approval_gate_status,
            "changed_by": cleaned_actor,
            "changed_at": now,
        }
        readiness_history = [dict(item) for item in list(updated_record.get("readiness_history") or []) if isinstance(item, dict)]
        readiness_history.append(readiness_entry)
        updated_record["readiness_state"] = cleaned_readiness_state
        updated_record["readiness_reason"] = cleaned_readiness_reason
        updated_record["approval_gate_status"] = approval_gate_status
        updated_record["last_readiness_changed_by"] = cleaned_actor
        updated_record["last_readiness_changed_at"] = now
        updated_record["readiness_history"] = readiness_history[-50:]
        updated_record["updated_at"] = now

        states[cleaned_autonomy_id] = updated_record
        history.append(
            {
                "event": "autonomy-readiness-recorded",
                "autonomy_id": cleaned_autonomy_id,
                "readiness_state": cleaned_readiness_state,
                "approval_gate_status": approval_gate_status,
                "changed_by": cleaned_actor,
                "created_at": now,
            }
        )
        payload["autonomy_states"] = states
        payload["history"] = history[-300:]
        self.save(payload)
        return updated_record

    def apply_control_action(
        self,
        autonomy_id: str,
        *,
        actor: str,
        action: str,
        reason: str = "",
    ) -> dict[str, Any]:
        cleaned_autonomy_id = str(autonomy_id or "").strip()
        if not cleaned_autonomy_id:
            raise ValueError("autonomy_id is required")
        cleaned_actor = str(actor or "").strip() or "Chris"
        cleaned_action = str(action or "").strip().lower()
        cleaned_reason = str(reason or "").strip()
        if cleaned_action not in ALLOWED_AUTONOMY_CONTROL_ACTIONS:
            raise ValueError("action must be one of: abort, pause, resume")
        if not cleaned_reason:
            raise ValueError("control_reason is required")

        payload = self.load()
        states = dict(payload.get("autonomy_states", {}))
        history = [dict(item) for item in list(payload.get("history") or []) if isinstance(item, dict)]
        record = states.get(cleaned_autonomy_id)
        if not isinstance(record, dict):
            raise KeyError(f"Unknown autonomy state: {cleaned_autonomy_id}")

        current_posture = str(record.get("current_control_posture", "recorded_active") or "recorded_active").strip()
        if current_posture not in ALLOWED_AUTONOMY_CONTROL_POSTURES:
            current_posture = "recorded_active"

        if cleaned_action == "pause":
            if current_posture == "aborted":
                raise ValueError("aborted autonomy state cannot be paused")
            new_posture = "paused"
        elif cleaned_action == "resume":
            if current_posture == "aborted":
                raise ValueError("aborted autonomy state cannot be resumed")
            new_posture = "recorded_active"
        else:
            new_posture = "aborted"

        now = _now_iso()
        updated_record = dict(record)
        control_entry = {
            "action": cleaned_action,
            "reason": cleaned_reason,
            "changed_by": cleaned_actor,
            "changed_at": now,
            "resulting_posture": new_posture,
        }
        control_history = [dict(item) for item in list(updated_record.get("control_history") or []) if isinstance(item, dict)]
        control_history.append(control_entry)
        updated_record["current_control_posture"] = new_posture
        updated_record["last_control_action"] = cleaned_action
        updated_record["last_control_reason"] = cleaned_reason
        updated_record["last_control_changed_by"] = cleaned_actor
        updated_record["last_control_changed_at"] = now
        updated_record["control_history"] = control_history[-50:]
        updated_record["updated_at"] = now

        states[cleaned_autonomy_id] = updated_record
        history.append(
            {
                "event": "autonomy-control-recorded",
                "autonomy_id": cleaned_autonomy_id,
                "action": cleaned_action,
                "resulting_posture": new_posture,
                "changed_by": cleaned_actor,
                "created_at": now,
            }
        )
        payload["autonomy_states"] = states
        payload["history"] = history[-300:]
        self.save(payload)
        return updated_record

    def add_action_plan(
        self,
        autonomy_id: str,
        *,
        planning_note: str = "",
        proposed_actions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        cleaned_autonomy_id = str(autonomy_id or "").strip()
        if not cleaned_autonomy_id:
            raise ValueError("autonomy_id is required")

        raw_actions = list(proposed_actions or [])
        if not raw_actions:
            raise ValueError("at least one proposed action is required")

        cleaned_planning_note = str(planning_note or "").strip()
        normalized_actions: list[dict[str, Any]] = []
        now = _now_iso()

        for index, item in enumerate(raw_actions, start=1):
            if not isinstance(item, dict):
                raise ValueError("proposed actions must be objects")
            cleaned_title = str(
                item.get("title")
                or item.get("action")
                or item.get("label")
                or ""
            ).strip()
            if not cleaned_title:
                raise ValueError("each proposed action requires a title")
            approval_needed = bool(item.get("approval_needed", item.get("approval_required", True)))
            cleaned_approval_state = str(item.get("approval_state", "required") or "").strip().lower() or "required"
            if not approval_needed and cleaned_approval_state == "required":
                cleaned_approval_state = "not_required"
            if cleaned_approval_state not in ALLOWED_AUTONOMY_APPROVAL_STATES:
                raise ValueError("approval_state must be one of: approved, not_requested, not_required, required")
            cleaned_execution_status = str(item.get("execution_status", "proposed_not_run") or "").strip().lower() or "proposed_not_run"
            if cleaned_execution_status not in ALLOWED_AUTONOMY_PLAN_ACTION_STATUSES:
                raise ValueError("execution_status must be one of: proposed_not_run")
            cleaned_rationale = str(item.get("rationale", "") or "").strip()
            normalized_actions.append(
                {
                    "action_id": str(uuid.uuid4()),
                    "title": cleaned_title,
                    "rationale": cleaned_rationale,
                    "approval_needed": approval_needed,
                    "approval_state": cleaned_approval_state,
                    "execution_status": cleaned_execution_status,
                    "sequence": index,
                    "planned_at": now,
                }
            )

        payload = self.load()
        states = dict(payload.get("autonomy_states", {}))
        history = [dict(item) for item in list(payload.get("history") or []) if isinstance(item, dict)]
        record = states.get(cleaned_autonomy_id)
        if not isinstance(record, dict):
            raise KeyError(f"Unknown autonomy state: {cleaned_autonomy_id}")

        updated_record = dict(record)
        updated_record["planning_note"] = cleaned_planning_note
        updated_record["proposed_actions"] = normalized_actions
        updated_record["planned_action_count"] = len(normalized_actions)
        updated_record["has_proposed_plan"] = True
        updated_record["updated_at"] = now

        states[cleaned_autonomy_id] = updated_record
        history.append(
            {
                "event": "autonomy-plan-recorded",
                "autonomy_id": cleaned_autonomy_id,
                "planned_action_count": len(normalized_actions),
                "created_at": now,
            }
        )
        payload["autonomy_states"] = states
        payload["history"] = history[-300:]
        self.save(payload)
        return updated_record

    def get_state(self, autonomy_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("autonomy_states", {}).get(str(autonomy_id or "").strip())
        return dict(record) if isinstance(record, dict) else None

    def list_states(self) -> list[dict[str, Any]]:
        payload = self.load()
        records = payload.get("autonomy_states", {})
        if not isinstance(records, dict):
            return []
        items = [dict(item) for item in records.values() if isinstance(item, dict)]
        items.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
        return items
