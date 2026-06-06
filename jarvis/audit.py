from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import ApprovalRequest, RequestPlan
from .persistence import append_jsonl, atomic_write_json, atomic_write_jsonl


class AuditLog:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.actions_path = self.root / "actions.jsonl"
        self.actions_state_log_path = self.root / "actions_state_log.jsonl"

    def _load_actions(self) -> list[dict]:
        if not self.actions_path.exists():
            return self._load_actions_from_state_log()
        try:
            lines = self.actions_path.read_text(encoding="utf-8").splitlines()
            records = [json.loads(line) for line in lines if line.strip()]
        except (OSError, json.JSONDecodeError):
            return self._load_actions_from_state_log()
        return [dict(item) for item in records if isinstance(item, dict)] or self._load_actions_from_state_log()

    def _load_actions_from_state_log(self) -> list[dict]:
        if not self.actions_state_log_path.exists():
            return []
        latest: list[dict] = []
        try:
            for line in self.actions_state_log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            return []
        return latest

    def _append_action(self, entry: dict) -> None:
        records = self._load_actions()
        records.append(dict(entry))
        atomic_write_jsonl(self.actions_path, records)
        append_jsonl(
            self.actions_state_log_path,
            {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "records": records,
            },
        )

    def log_plan(self, plan: RequestPlan) -> None:
        entry = asdict(plan)
        entry["entry_type"] = "plan"
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._append_action(entry)

    def log_response(
        self,
        plan: RequestPlan,
        provider: str,
        model: str,
        active_nodes: list[str],
        output_text: str,
    ) -> None:
        entry = asdict(plan)
        entry["entry_type"] = "response"
        entry["provider"] = provider
        entry["model"] = model
        entry["active_nodes"] = active_nodes
        entry["output_preview"] = output_text[:280]
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._append_action(entry)

    def log_assistant_action(
        self,
        *,
        actor: str,
        domain: str,
        item_id: str,
        action: str,
        detail: str,
        mode: str = "automatic",
        action_class: str = "",
        policy_basis: str = "",
        confidence: str = "",
        decision: str = "",
        cadence_phase: str = "",
        quiet_hours_active: bool | None = None,
        why_now: str = "",
        surface_key: str = "",
        result_summary: str = "",
        succeeded: bool | None = None,
        caused_friction: bool | None = None,
        friction_reason: str = "",
    ) -> None:
        entry = {
            "entry_type": "assistant-action",
            "actor": actor,
            "domain": domain,
            "item_id": item_id,
            "action": action,
            "action_class": action_class,
            "detail": detail,
            "mode": mode,
            "policy_basis": policy_basis,
            "confidence": confidence,
            "decision": decision,
            "cadence_phase": cadence_phase,
            "why_now": why_now,
            "surface_key": surface_key,
            "result_summary": result_summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if quiet_hours_active is not None:
            entry["quiet_hours_active"] = bool(quiet_hours_active)
        if succeeded is not None:
            entry["succeeded"] = bool(succeeded)
        if caused_friction is not None:
            entry["caused_friction"] = bool(caused_friction)
        if friction_reason.strip():
            entry["friction_reason"] = friction_reason.strip()
        self._append_action(entry)

    def log_event(self, entry_type: str, payload: dict) -> None:
        entry = {
            "entry_type": str(entry_type).strip() or "event",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        entry.update(dict(payload))
        self._append_action(entry)

    def list_recent(self, limit: int = 25, entry_type: str | None = None) -> list[dict]:
        records = self._load_actions()
        if entry_type:
            records = [item for item in records if item.get("entry_type") == entry_type]
        return list(reversed(records[-limit:]))


class ProgressSnapshotStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.current_path = self.root / "progress_snapshot.json"
        self.history_path = self.root / "progress_snapshot_log.jsonl"
        self.history_state_log_path = self.root / "progress_snapshot_state_log.jsonl"

    def _load_history(self) -> list[dict]:
        if not self.history_path.exists():
            return self._load_history_from_state_log()
        try:
            lines = self.history_path.read_text(encoding="utf-8").splitlines()
            records = [json.loads(line) for line in lines if line.strip()]
        except (OSError, json.JSONDecodeError):
            return self._load_history_from_state_log()
        return [dict(item) for item in records if isinstance(item, dict)] or self._load_history_from_state_log()

    def _load_history_from_state_log(self) -> list[dict]:
        if not self.history_state_log_path.exists():
            return []
        latest: list[dict] = []
        try:
            for line in self.history_state_log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            return []
        return latest

    def _load_current(self) -> dict:
        if not self.current_path.exists():
            history = self._load_history()
            return dict(history[-1]) if history else {}
        try:
            payload = json.loads(self.current_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            history = self._load_history()
            return dict(history[-1]) if history else {}
        return dict(payload) if isinstance(payload, dict) else {}

    def save_snapshot(
        self,
        *,
        progress_dashboard: dict,
        seam_tracker: dict,
        lane_progress: dict,
        next_focus: str,
    ) -> dict:
        history = self._load_history()
        snapshot = {
            "entry_type": "progress-snapshot",
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "branch": str(lane_progress.get("branch", "")).strip() or "unknown branch",
            "head": str(lane_progress.get("head", "")).strip() or "unknown head",
            "dirty_count": int(lane_progress.get("dirty_count", 0) or 0),
            "next_focus": str(next_focus).strip() or "No next focus recorded yet.",
            "progress_counts": dict(progress_dashboard.get("counts") or {}),
            "seam_counts": dict(seam_tracker.get("counts") or {}),
            "progress_items": [
                {
                    "module": str(item.get("module", "")).strip(),
                    "status": str(item.get("status", "")).strip(),
                    "status_label": str(item.get("status_label", "")).strip(),
                    "summary": str(item.get("summary", "")).strip(),
                    "evidence": str(item.get("evidence", "")).strip(),
                }
                for item in list(progress_dashboard.get("items") or [])
                if isinstance(item, dict)
            ][:8],
            "seam_items": [
                {
                    "name": str(item.get("name", "")).strip(),
                    "status": str(item.get("status", "")).strip(),
                    "module": str(item.get("module", "")).strip(),
                    "what_became_real": str(item.get("what_became_real", "")).strip(),
                    "remains_partial": str(item.get("remains_partial", "")).strip(),
                    "related_missions": [
                        {
                            "mission_id": str(mission.get("mission_id", "")).strip(),
                            "title": str(mission.get("title", "")).strip(),
                            "lane": str(mission.get("lane", "")).strip(),
                            "route": str(mission.get("route", "")).strip() or "/mission-board",
                        }
                        for mission in list(item.get("related_missions") or [])
                        if isinstance(mission, dict)
                    ][:3],
                }
                for item in list(seam_tracker.get("items") or [])
                if isinstance(item, dict)
            ][:8],
        }
        history.append(snapshot)
        history = history[-40:]
        atomic_write_json(self.current_path, snapshot)
        atomic_write_jsonl(self.history_path, history)
        append_jsonl(
            self.history_state_log_path,
            {
                "saved_at": snapshot["saved_at"],
                "records": history,
            },
        )
        return snapshot

    def summary(self, limit: int = 6) -> dict:
        history = self._load_history()
        current = self._load_current()
        recent = list(reversed(history[-max(1, limit):]))
        return {
            "latest": current,
            "history_count": len(history),
            "recent": recent,
            "proof_paths": {
                "current": str(self.current_path),
                "history": str(self.history_path),
            },
        }


class RecoveryActionStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.current_path = self.root / "recovery_actions.json"
        self.history_path = self.root / "recovery_actions_log.jsonl"
        self.history_state_log_path = self.root / "recovery_actions_state_log.jsonl"

    def _load_actions(self) -> list[dict]:
        if not self.current_path.exists():
            return self._load_actions_from_state_log()
        try:
            payload = json.loads(self.current_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._load_actions_from_state_log()
        if isinstance(payload, list):
            return [dict(item) for item in payload if isinstance(item, dict)]
        return self._load_actions_from_state_log()

    def _load_actions_from_state_log(self) -> list[dict]:
        if not self.history_state_log_path.exists():
            return []
        latest: list[dict] = []
        try:
            for line in self.history_state_log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            return []
        return latest

    def record_action(
        self,
        *,
        action_type: str,
        target_kind: str,
        target_label: str,
        detail: str,
        route: str = "/recovery-center",
        status: str = "queued",
    ) -> dict:
        records = self._load_actions()
        entry = {
            "entry_type": "recovery-action",
            "action_type": str(action_type).strip() or "review",
            "target_kind": str(target_kind).strip() or "recovery",
            "target_label": str(target_label).strip() or "Recovery item",
            "detail": str(detail).strip() or "Recovery action recorded.",
            "route": str(route).strip() or "/recovery-center",
            "status": str(status).strip() or "queued",
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        records.append(entry)
        records = records[-40:]
        atomic_write_json(self.current_path, records)
        atomic_write_jsonl(self.history_path, records)
        append_jsonl(
            self.history_state_log_path,
            {
                "saved_at": entry["saved_at"],
                "records": records,
            },
        )
        return entry

    def summary(self, limit: int = 8) -> dict:
        actions = self._load_actions()
        recent = list(reversed(actions[-max(1, limit):]))
        return {
            "count": len(actions),
            "recent": recent,
            "proof_paths": {
                "current": str(self.current_path),
                "history": str(self.history_path),
            },
        }


class ApprovalStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.pending_path = self.root / "pending.json"
        self.pending_log_path = self.root / "pending_log.jsonl"

    def _load(self) -> list[dict]:
        if not self.pending_path.exists():
            return self._load_from_log()
        try:
            return json.loads(self.pending_path.read_text())
        except Exception:
            return self._load_from_log()

    def _load_from_log(self) -> list[dict]:
        if not self.pending_log_path.exists():
            return []
        try:
            latest: list[dict] = []
            for line in self.pending_log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
            return latest
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        atomic_write_json(self.pending_path, records)
        append_jsonl(
            self.pending_log_path,
            {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "records": records,
            },
        )

    def add(self, approval: ApprovalRequest) -> None:
        records = self._load()
        records.append(asdict(approval))
        self._save(records)

    def list_pending(self) -> list[dict]:
        return [item for item in self._load() if item["status"] == "pending"]

    def update_status(self, request_id: str, status: str) -> dict | None:
        records = self._load()
        updated = None
        for item in records:
            if item["request_id"] == request_id:
                item["status"] = status
                updated = item
                break
        if updated is not None:
            self._save(records)
        return updated

    def list_all(self) -> list[dict]:
        return self._load()
