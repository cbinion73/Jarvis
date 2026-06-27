from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .data_hygiene import filter_records
from .models import ApprovalRequest, RequestPlan
from .persistence import append_jsonl, atomic_write_json, atomic_write_jsonl
from .state_log_utils import read_jsonl_tail


class AuditLog:
    def __init__(self, root: Path, *, read_only: bool = False) -> None:
        self.root = root
        self.read_only = read_only
        if not self.read_only:
            self.root.mkdir(parents=True, exist_ok=True)
        self.actions_path = self.root / "actions.jsonl"
        self.actions_state_log_path = self.root / "actions_state_log.jsonl"
        self._session_actions: list[dict] = []

    def _load_actions(self) -> list[dict]:
        if self.read_only:
            records = self._load_actions_from_state_log() if not self.actions_path.exists() else []
            if self.actions_path.exists():
                try:
                    records = read_jsonl_tail(self.actions_path)
                except (OSError, json.JSONDecodeError):
                    records = self._load_actions_from_state_log()
            normalized = filter_records([dict(item) for item in records if isinstance(item, dict)])
            return [*normalized, *[dict(item) for item in self._session_actions]]
        if not self.actions_path.exists():
            return self._load_actions_from_state_log()
        try:
            records = read_jsonl_tail(self.actions_path)
        except (OSError, json.JSONDecodeError):
            return self._load_actions_from_state_log()
        return filter_records([dict(item) for item in records if isinstance(item, dict)]) or self._load_actions_from_state_log()

    def _load_actions_from_state_log(self) -> list[dict]:
        if not self.actions_state_log_path.exists():
            return []
        latest: list[dict] = []
        try:
            for payload in read_jsonl_tail(self.actions_state_log_path):
                records = payload.get("records")
                if isinstance(records, list):
                    latest = filter_records([dict(item) for item in records if isinstance(item, dict)])
        except (OSError, json.JSONDecodeError):
            return []
        return latest

    def _append_action(self, entry: dict) -> None:
        if self.read_only:
            self._session_actions.append(dict(entry))
            return
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
            records = read_jsonl_tail(self.history_path)
        except (OSError, json.JSONDecodeError):
            return self._load_history_from_state_log()
        return [dict(item) for item in records if isinstance(item, dict)] or self._load_history_from_state_log()

    def _load_history_from_state_log(self) -> list[dict]:
        if not self.history_state_log_path.exists():
            return []
        latest: list[dict] = []
        try:
            for payload in read_jsonl_tail(self.history_state_log_path):
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


class ProgressFocusStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.current_path = self.root / "progress_focus.json"
        self.history_path = self.root / "progress_focus_log.jsonl"
        self.history_state_log_path = self.root / "progress_focus_state_log.jsonl"

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

    def _load_history(self) -> list[dict]:
        if not self.history_path.exists():
            return self._load_history_from_state_log()
        try:
            records = read_jsonl_tail(self.history_path)
        except (OSError, json.JSONDecodeError):
            return self._load_history_from_state_log()
        return [dict(item) for item in records if isinstance(item, dict)] or self._load_history_from_state_log()

    def _load_history_from_state_log(self) -> list[dict]:
        if not self.history_state_log_path.exists():
            return []
        latest: list[dict] = []
        try:
            for payload in read_jsonl_tail(self.history_state_log_path):
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            return []
        return latest

    def save_focus(
        self,
        *,
        module: str,
        reason: str,
        route: str = "",
        actor: str = "Chris",
    ) -> dict:
        history = self._load_history()
        entry = {
            "entry_type": "progress-focus",
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "module": str(module).strip() or "Progress",
            "reason": str(reason).strip() or "No progress focus rationale recorded.",
            "route": str(route).strip() or "/progress-center",
            "actor": str(actor).strip() or "Chris",
        }
        history.append(entry)
        history = history[-40:]
        atomic_write_json(self.current_path, entry)
        atomic_write_jsonl(self.history_path, history)
        append_jsonl(
            self.history_state_log_path,
            {
                "saved_at": entry["saved_at"],
                "records": history,
            },
        )
        return entry

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


class SeamTrackerStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.current_path = self.root / "seam_tracker.json"
        self.history_path = self.root / "seam_tracker_log.jsonl"
        self.history_state_log_path = self.root / "seam_tracker_state_log.jsonl"

    def _load_history(self) -> list[dict]:
        if not self.history_path.exists():
            return self._load_history_from_state_log()
        try:
            records = read_jsonl_tail(self.history_path)
        except (OSError, json.JSONDecodeError):
            return self._load_history_from_state_log()
        return [dict(item) for item in records if isinstance(item, dict)] or self._load_history_from_state_log()

    def _load_history_from_state_log(self) -> list[dict]:
        if not self.history_state_log_path.exists():
            return []
        latest: list[dict] = []
        try:
            for payload in read_jsonl_tail(self.history_state_log_path):
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            return []
        return latest

    def _load_current_records(self) -> list[dict]:
        if self.current_path.exists():
            try:
                payload = json.loads(self.current_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {}
            records = payload.get("records") if isinstance(payload, dict) else None
            if isinstance(records, list):
                return [dict(item) for item in records if isinstance(item, dict)]
        latest_by_name: dict[str, dict] = {}
        for item in self._load_history():
            name = str(item.get("name", "")).strip()
            if name:
                latest_by_name[name] = dict(item)
        return list(latest_by_name.values())

    def _status_class(self, status: str) -> str:
        normalized = str(status).strip().lower()
        if normalized in {"useful", "durable", "compounding"}:
            return "accepted"
        return "steady"

    def save_seam_state(
        self,
        *,
        name: str,
        module: str,
        status: str,
        note: str,
        actor: str,
        route: str = "/progress-center",
        linked_mission: dict | None = None,
    ) -> dict:
        seam_name = str(name).strip() or "Unnamed Seam"
        normalized_status = str(status).strip().title() or "Wired"
        if normalized_status not in {"Wired", "Useful", "Durable", "Compounding"}:
            raise ValueError("Unsupported seam status.")

        history = self._load_history()
        records = self._load_current_records()
        now = datetime.now(timezone.utc).isoformat()
        mission = dict(linked_mission or {})
        entry = {
            "entry_type": "seam-state",
            "saved_at": now,
            "name": seam_name,
            "module": str(module).strip() or "Progress",
            "status": normalized_status,
            "status_class": self._status_class(normalized_status),
            "maturity": normalized_status,
            "operator_note": str(note).strip() or "No operator seam note recorded.",
            "actor": str(actor).strip() or "Chris",
            "route": str(route).strip() or "/progress-center",
            "linked_mission": {
                "mission_id": str(mission.get("mission_id", "")).strip(),
                "title": str(mission.get("title", "")).strip(),
                "lane": str(mission.get("lane", "")).strip(),
                "route": str(mission.get("route", "")).strip() or "/mission-board",
            } if mission else {},
        }

        updated_records = [dict(item) for item in records if str(item.get("name", "")).strip() != seam_name]
        updated_records.append(entry)
        updated_records.sort(key=lambda item: str(item.get("name", "")).lower())
        atomic_write_json(
            self.current_path,
            {
                "saved_at": now,
                "records": updated_records,
            },
        )

        history.append(entry)
        history = history[-80:]
        atomic_write_jsonl(self.history_path, history)
        append_jsonl(
            self.history_state_log_path,
            {
                "saved_at": now,
                "records": history,
            },
        )
        return entry

    def summary(self, limit: int = 6) -> dict:
        history = self._load_history()
        records = self._load_current_records()
        current_saved_at = str(records[-1].get("saved_at", "")) if records else ""
        recent = list(reversed(history[-max(1, limit):]))
        return {
            "latest": {
                "saved_at": current_saved_at,
                "records": records,
            },
            "records": records,
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
            for payload in read_jsonl_tail(self.history_state_log_path):
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
        target_id: str = "",
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
            "target_id": str(target_id).strip(),
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
            payload = json.loads(self.pending_path.read_text())
        except Exception:
            return self._load_from_log()
        return filter_records([dict(item) for item in payload if isinstance(item, dict)]) if isinstance(payload, list) else self._load_from_log()

    def _load_from_log(self) -> list[dict]:
        if not self.pending_log_path.exists():
            return []
        try:
            latest: list[dict] = []
            for payload in read_jsonl_tail(self.pending_log_path):
                records = payload.get("records")
                if isinstance(records, list):
                    latest = filter_records([dict(item) for item in records if isinstance(item, dict)])
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


class ActivityReviewStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.current_path = self.root / "activity_reviews.json"
        self.history_path = self.root / "activity_reviews_log.jsonl"
        self.history_state_log_path = self.root / "activity_reviews_state_log.jsonl"

    def _load_history(self) -> list[dict]:
        if not self.history_path.exists():
            return self._load_history_from_state_log()
        try:
            records = read_jsonl_tail(self.history_path)
        except (OSError, json.JSONDecodeError):
            return self._load_history_from_state_log()
        return [dict(item) for item in records if isinstance(item, dict)] or self._load_history_from_state_log()

    def _load_history_from_state_log(self) -> list[dict]:
        if not self.history_state_log_path.exists():
            return []
        latest: list[dict] = []
        try:
            for payload in read_jsonl_tail(self.history_state_log_path):
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            return []
        return latest

    def _load_current_records(self) -> list[dict]:
        if self.current_path.exists():
            try:
                payload = json.loads(self.current_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {}
            records = payload.get("records") if isinstance(payload, dict) else None
            if isinstance(records, list):
                return [dict(item) for item in records if isinstance(item, dict)]
        latest_by_id: dict[str, dict] = {}
        for item in self._load_history():
            review_id = str(item.get("review_id", "")).strip()
            if review_id:
                latest_by_id[review_id] = dict(item)
        return list(latest_by_id.values())

    def save_review(
        self,
        *,
        review_id: str,
        event_id: str,
        title: str,
        status: str,
        actor: str,
        detail: str,
        related_route: str,
        related_kind: str = "",
        route_label: str = "",
        target_module: str = "",
    ) -> dict:
        normalized_status = str(status).strip().lower() or "reviewing"
        if normalized_status not in {"reviewing", "resume-later", "resolved"}:
            raise ValueError("Unsupported activity review status.")
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "entry_type": "activity-review",
            "saved_at": now,
            "review_id": str(review_id).strip() or str(event_id).strip(),
            "event_id": str(event_id).strip(),
            "title": str(title).strip() or "Activity event",
            "status": normalized_status,
            "status_label": normalized_status.replace("-", " ").title(),
            "actor": str(actor).strip() or "Chris",
            "detail": str(detail).strip() or "No activity review detail recorded.",
            "related_route": str(related_route).strip() or "/activity-center",
            "related_kind": str(related_kind).strip(),
            "route_label": str(route_label).strip() or "Open Related Surface",
            "target_module": str(target_module).strip() or "",
        }

        records = [dict(item) for item in self._load_current_records() if str(item.get("review_id", "")).strip() != entry["review_id"]]
        records.append(entry)
        records.sort(key=lambda item: str(item.get("saved_at", "")), reverse=True)
        atomic_write_json(
            self.current_path,
            {
                "saved_at": now,
                "records": records,
            },
        )

        history = self._load_history()
        history.append(entry)
        history = history[-120:]
        atomic_write_jsonl(self.history_path, history)
        append_jsonl(
            self.history_state_log_path,
            {
                "saved_at": now,
                "records": history,
            },
        )
        return entry

    def summary(self, limit: int = 8) -> dict:
        history = self._load_history()
        records = self._load_current_records()
        current_saved_at = str(records[0].get("saved_at", "")) if records else ""
        recent = list(reversed(history[-max(1, limit):]))
        return {
            "latest": {
                "saved_at": current_saved_at,
                "records": records,
            },
            "records": records,
            "history_count": len(history),
            "recent": recent,
            "proof_paths": {
                "current": str(self.current_path),
                "history": str(self.history_path),
            },
        }
