"""E8: Catalyst/executive workflow contracts.

Models bounded domains for: strategy, writing, pipeline, publishing, growth.
Each workflow has:
- A contract (scope, owner, success criteria, handoff targets)
- Run history (start/end timestamps, outcome, actor)
- Approval gates (which steps require explicit sign-off)
- Handoff records (what was passed to next stage / next actor)
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_EWF_ROOT = Path("data/catalyst/executive_workflows")
_CONTRACTS_PATH = _EWF_ROOT / "contracts.json"
_RUNS_PATH = _EWF_ROOT / "runs.json"
_AUDIT_PATH = _EWF_ROOT / "workflow_audit.jsonl"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


WORKFLOW_DOMAINS = frozenset({"strategy", "writing", "pipeline", "publishing", "growth", "research", "review"})

RUN_STATES = frozenset({"created", "in_progress", "awaiting_approval", "approved", "completed", "failed", "cancelled"})
TERMINAL_RUN_STATES = frozenset({"completed", "failed", "cancelled"})


@dataclass(slots=True)
class WorkflowContract:
    contract_id: str
    name: str
    domain: str                  # strategy/writing/pipeline/publishing/growth
    owner: str                   # actor responsible
    scope: str                   # what this workflow covers
    success_criteria: list[str]
    approval_gates: list[str]    # which steps need explicit sign-off
    handoff_targets: list[str]   # downstream domains/actors
    created_at: str
    updated_at: str
    active: bool = True
    labels: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkflowRun:
    run_id: str
    contract_id: str
    actor: str
    state: str
    created_at: str
    started_at: str = ""
    completed_at: str = ""
    outcome: str = ""            # success/partial/failure
    outcome_summary: str = ""
    approved_by: str = ""
    approved_at: str = ""
    handoff_note: str = ""       # what was passed to the next domain
    handoff_target: str = ""
    failure_reason: str = ""
    source: str = "live"


class ExecutiveWorkflowStore:
    """Manages executive workflow contracts and run histories."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _EWF_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.contracts_path = self.root / "contracts.json"
        self.runs_path = self.root / "runs.json"
        self.audit_path = self.root / "workflow_audit.jsonl"

    def _load(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, path: Path, records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, records)

    def _audit(self, event: str, entity_id: str, actor: str, extra: dict | None = None) -> None:
        record: dict[str, Any] = {
            "ts": _ts(), "event": event, "entity_id": entity_id, "actor": actor,
        }
        if extra:
            record.update(extra)
        try:
            append_jsonl(self.audit_path, record)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Contracts
    # ------------------------------------------------------------------

    def create_contract(
        self,
        *,
        name: str,
        domain: str,
        owner: str,
        scope: str,
        success_criteria: list[str] | None = None,
        approval_gates: list[str] | None = None,
        handoff_targets: list[str] | None = None,
        labels: list[str] | None = None,
    ) -> WorkflowContract:
        if not name.strip():
            raise ValueError("name is required")
        if domain not in WORKFLOW_DOMAINS:
            raise ValueError(f"domain must be one of {sorted(WORKFLOW_DOMAINS)}")
        contract = WorkflowContract(
            contract_id=str(uuid.uuid4()),
            name=name.strip(),
            domain=domain,
            owner=owner,
            scope=scope,
            success_criteria=success_criteria or [],
            approval_gates=approval_gates or [],
            handoff_targets=handoff_targets or [],
            created_at=_ts(),
            updated_at=_ts(),
            labels=labels or [],
        )
        records = self._load(self.contracts_path)
        records.append(asdict(contract))
        self._save(self.contracts_path, records)
        self._audit("contract_created", contract.contract_id, owner, {"name": name, "domain": domain})
        return contract

    def get_contract(self, contract_id: str) -> dict | None:
        for r in self._load(self.contracts_path):
            if r.get("contract_id") == contract_id:
                return r
        return None

    def list_contracts(self, domain: str | None = None, active_only: bool = True) -> list[dict]:
        records = self._load(self.contracts_path)
        if active_only:
            records = [r for r in records if r.get("active", True)]
        if domain:
            records = [r for r in records if r.get("domain") == domain]
        return records

    # ------------------------------------------------------------------
    # Runs
    # ------------------------------------------------------------------

    def start_run(self, contract_id: str, actor: str) -> WorkflowRun:
        contract = self.get_contract(contract_id)
        if not contract:
            raise KeyError(f"Contract not found: {contract_id}")
        if not contract.get("active", True):
            raise ValueError(f"Contract {contract_id} is inactive")
        run = WorkflowRun(
            run_id=str(uuid.uuid4()),
            contract_id=contract_id,
            actor=actor,
            state="in_progress",
            created_at=_ts(),
            started_at=_ts(),
        )
        records = self._load(self.runs_path)
        records.append(asdict(run))
        self._save(self.runs_path, records)
        self._audit("run_started", run.run_id, actor, {"contract_id": contract_id})
        return run

    def complete_run(
        self,
        run_id: str,
        actor: str,
        outcome: str,
        outcome_summary: str = "",
        handoff_note: str = "",
        handoff_target: str = "",
    ) -> dict | None:
        if outcome not in ("success", "partial", "failure"):
            raise ValueError("outcome must be success/partial/failure")
        records = self._load(self.runs_path)
        updated = None
        for r in records:
            if r.get("run_id") == run_id:
                if r.get("state") in TERMINAL_RUN_STATES:
                    raise ValueError(f"Run {run_id} is already in terminal state {r.get('state')}")
                r["state"] = "completed"
                r["completed_at"] = _ts()
                r["outcome"] = outcome
                r["outcome_summary"] = outcome_summary
                r["handoff_note"] = handoff_note
                r["handoff_target"] = handoff_target
                updated = r
                break
        if updated:
            self._save(self.runs_path, records)
            self._audit("run_completed", run_id, actor, {"outcome": outcome})
        return updated

    def approve_run(self, run_id: str, actor: str) -> dict | None:
        records = self._load(self.runs_path)
        updated = None
        for r in records:
            if r.get("run_id") == run_id:
                r["state"] = "approved"
                r["approved_by"] = actor
                r["approved_at"] = _ts()
                updated = r
                break
        if updated:
            self._save(self.runs_path, records)
            self._audit("run_approved", run_id, actor)
        return updated

    def cancel_run(self, run_id: str, actor: str, reason: str = "") -> dict | None:
        records = self._load(self.runs_path)
        updated = None
        for r in records:
            if r.get("run_id") == run_id:
                if r.get("state") in TERMINAL_RUN_STATES:
                    raise ValueError(f"Run {run_id} is already terminal")
                r["state"] = "cancelled"
                r["failure_reason"] = reason
                updated = r
                break
        if updated:
            self._save(self.runs_path, records)
            self._audit("run_cancelled", run_id, actor, {"reason": reason})
        return updated

    def list_runs(self, contract_id: str | None = None) -> list[dict]:
        records = self._load(self.runs_path)
        if contract_id:
            records = [r for r in records if r.get("contract_id") == contract_id]
        return records
