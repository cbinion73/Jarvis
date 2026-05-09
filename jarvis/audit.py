from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import ApprovalRequest, RequestPlan


class AuditLog:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.actions_path = self.root / "actions.jsonl"

    def log_plan(self, plan: RequestPlan) -> None:
        entry = asdict(plan)
        entry["entry_type"] = "plan"
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        with self.actions_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

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
        with self.actions_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def list_recent(self, limit: int = 25, entry_type: str | None = None) -> list[dict]:
        if not self.actions_path.exists():
            return []
        lines = self.actions_path.read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
        if entry_type:
            records = [item for item in records if item.get("entry_type") == entry_type]
        return list(reversed(records[-limit:]))


class ApprovalStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.pending_path = self.root / "pending.json"

    def _load(self) -> list[dict]:
        if not self.pending_path.exists():
            return []
        return json.loads(self.pending_path.read_text())

    def _save(self, records: list[dict]) -> None:
        self.pending_path.write_text(json.dumps(records, indent=2) + "\n")

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
