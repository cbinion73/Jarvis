from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


@dataclass(slots=True)
class WorkflowRunStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "workflow_runs.json"
        self.log_path = self.root / "workflow_runs_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"workflow_runs": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("workflow_runs", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Workflow run storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "record_count": len(payload.get("workflow_runs", {})),
                "history_count": len(payload.get("history", {})),
            },
        )

    def record_run(
        self,
        *,
        workflow_kind: str,
        actor: str,
        room: str,
        request: str,
        status: str,
        provider: str = "",
        model: str = "",
        run_id: str = "",
        graph_name: str = "",
        runtime_surface: str = "",
        active_nodes: list[str] | None = None,
        nodes_planned: list[str] | None = None,
        step_events: list[dict[str, Any]] | None = None,
        execution_trace: list[dict[str, Any]] | None = None,
        created_objects: list[dict[str, Any]] | None = None,
        plan_summary: dict[str, Any] | None = None,
        result_summary: dict[str, Any] | None = None,
        output_text: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        cleaned_workflow_kind = str(workflow_kind or "").strip()
        if not cleaned_workflow_kind:
            raise ValueError("workflow_kind is required")
        now = _now_iso()
        resolved_run_id = str(run_id or "").strip() or str(uuid.uuid4())
        record = {
            "run_id": resolved_run_id,
            "workflow_kind": cleaned_workflow_kind,
            "actor": str(actor or "").strip(),
            "room": str(room or "").strip(),
            "request": str(request or "").strip(),
            "status": str(status or "").strip() or "completed",
            "provider": str(provider or "").strip(),
            "model": str(model or "").strip(),
            "graph_name": str(graph_name or "").strip(),
            "runtime_surface": str(runtime_surface or "").strip(),
            "active_nodes": [_json_safe(item) for item in list(active_nodes or []) if str(item).strip()],
            "nodes_planned": [_json_safe(item) for item in list(nodes_planned or []) if str(item).strip()],
            "step_events": [_json_safe(item) for item in list(step_events or []) if isinstance(item, dict)],
            "execution_trace": [_json_safe(item) for item in list(execution_trace or []) if isinstance(item, dict)],
            "created_objects": [_json_safe(item) for item in list(created_objects or []) if isinstance(item, dict)],
            "plan_summary": _json_safe(dict(plan_summary or {})),
            "result_summary": _json_safe(dict(result_summary or {})),
            "output_text": str(output_text or "").strip(),
            "metadata": _json_safe(dict(metadata or {})),
            "started_at": now,
            "completed_at": now,
            "updated_at": now,
        }
        payload = self.load()
        records = dict(payload.get("workflow_runs") or {})
        history = [dict(item) for item in list(payload.get("history") or []) if isinstance(item, dict)]
        records[resolved_run_id] = record
        history.append(
            {
                "event": "workflow-run-recorded",
                "run_id": resolved_run_id,
                "workflow_kind": cleaned_workflow_kind,
                "status": record["status"],
                "provider": record["provider"],
                "recorded_at": now,
            }
        )
        payload["workflow_runs"] = records
        payload["history"] = history[-1000:]
        self.save(payload)
        append_jsonl(
            self.log_path,
            {
                "event": "workflow-run-recorded",
                "recorded_at": now,
                "run": record,
            },
        )
        return record

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        run_key = str(run_id or "").strip()
        if not run_key:
            return None
        payload = self.load()
        record = payload.get("workflow_runs", {}).get(run_key)
        return dict(record) if isinstance(record, dict) else None

    def list_runs(
        self,
        *,
        workflow_kind: str = "",
        status: str = "",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        workflow_key = str(workflow_kind or "").strip()
        status_key = str(status or "").strip()
        cleaned_limit = max(1, min(int(limit or 20), 100))
        payload = self.load()
        records = [
            dict(item)
            for item in payload.get("workflow_runs", {}).values()
            if isinstance(item, dict)
        ]
        records.sort(key=lambda item: str(item.get("completed_at", "")), reverse=True)
        filtered: list[dict[str, Any]] = []
        for item in records:
            if workflow_key and str(item.get("workflow_kind", "")).strip() != workflow_key:
                continue
            if status_key and str(item.get("status", "")).strip() != status_key:
                continue
            filtered.append(item)
            if len(filtered) >= cleaned_limit:
                break
        return filtered

    def summary(self, *, limit: int = 12) -> dict[str, Any]:
        records = self.list_runs(limit=max(1, min(int(limit or 12), 50)))
        payload = self.load()
        all_records = [
            dict(item)
            for item in payload.get("workflow_runs", {}).values()
            if isinstance(item, dict)
        ]
        counts_by_workflow: dict[str, int] = {}
        counts_by_status: dict[str, int] = {}
        for item in all_records:
            workflow_key = str(item.get("workflow_kind", "")).strip() or "unknown"
            status_key = str(item.get("status", "")).strip() or "unknown"
            counts_by_workflow[workflow_key] = counts_by_workflow.get(workflow_key, 0) + 1
            counts_by_status[status_key] = counts_by_status.get(status_key, 0) + 1
        return {
            "total_runs": len(all_records),
            "counts_by_workflow": counts_by_workflow,
            "counts_by_status": counts_by_status,
            "recent_runs": records,
        }
