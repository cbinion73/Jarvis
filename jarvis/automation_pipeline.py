"""E7: Real automation pipeline — research → synthesis → draft → review → approval → publish.

Models a governed automation workflow where each stage must complete before
the next begins, every stage is audited, and the whole pipeline can be rolled
back or halted at any point.

No external services are called here — this is the governance contract.
Actual LLM calls, publishing actions, etc. are handled by callers.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_PIPELINE_ROOT = Path("data/automation/pipelines")
_PIPELINES_PATH = _PIPELINE_ROOT / "pipelines.json"
_PIPELINE_LOG = _PIPELINE_ROOT / "pipelines_log.jsonl"
_PIPELINE_AUDIT = _PIPELINE_ROOT / "pipeline_audit.jsonl"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Pipeline stages (ordered)
# ---------------------------------------------------------------------------
PIPELINE_STAGES = [
    "research",
    "synthesis",
    "draft",
    "review",
    "approval",
    "publish",
]

STAGE_STATES = frozenset({"pending", "in_progress", "completed", "failed", "skipped"})

# Pipeline-level states
PIPELINE_CREATED = "created"
PIPELINE_RUNNING = "running"
PIPELINE_PAUSED = "paused"
PIPELINE_COMPLETED = "completed"
PIPELINE_FAILED = "failed"
PIPELINE_CANCELLED = "cancelled"
PIPELINE_ROLLED_BACK = "rolled_back"

PIPELINE_STATES = frozenset({
    PIPELINE_CREATED, PIPELINE_RUNNING, PIPELINE_PAUSED,
    PIPELINE_COMPLETED, PIPELINE_FAILED, PIPELINE_CANCELLED, PIPELINE_ROLLED_BACK,
})

TERMINAL_PIPELINE_STATES = frozenset({PIPELINE_COMPLETED, PIPELINE_FAILED, PIPELINE_CANCELLED, PIPELINE_ROLLED_BACK})


@dataclass(slots=True)
class PipelineStageRecord:
    stage: str
    state: str                   # pending/in_progress/completed/failed/skipped
    started_at: str = ""
    completed_at: str = ""
    result_summary: str = ""     # brief description of what was produced
    evidence: str = ""           # URL, file path, or content hash
    failure_reason: str = ""
    requires_approval: bool = False
    approved_by: str = ""
    approved_at: str = ""


@dataclass(slots=True)
class AutomationPipeline:
    pipeline_id: str
    title: str
    description: str
    actor: str
    pipeline_state: str
    stages: list[dict]           # list of PipelineStageRecord dicts
    created_at: str
    started_at: str = ""
    completed_at: str = ""
    cancelled_at: str = ""
    cancelled_by: str = ""
    cancel_reason: str = ""
    rollback_packet_id: str = ""
    rollback_executed_at: str = ""
    rollback_executed_by: str = ""
    labels: list[str] = field(default_factory=list)
    source: str = "live"


class AutomationPipelineStore:
    """Manages automation pipelines with governance audit trail."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _PIPELINE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.pipelines_path = self.root / "pipelines.json"
        self.log_path = self.root / "pipelines_log.jsonl"
        self.audit_path = self.root / "pipeline_audit.jsonl"

    def _load(self) -> list[dict]:
        if not self.pipelines_path.exists():
            return []
        try:
            data = json.loads(self.pipelines_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        self.pipelines_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.pipelines_path, records)

    def _audit(self, event: str, pipeline_id: str, actor: str, extra: dict | None = None) -> None:
        record: dict[str, Any] = {
            "ts": _ts(), "event": event, "pipeline_id": pipeline_id, "actor": actor,
        }
        if extra:
            record.update(extra)
        try:
            append_jsonl(self.audit_path, record)
        except Exception:
            pass

    def create(
        self,
        *,
        title: str,
        description: str,
        actor: str,
        labels: list[str] | None = None,
    ) -> AutomationPipeline:
        if not title.strip():
            raise ValueError("title is required")
        stages = [
            asdict(PipelineStageRecord(
                stage=s,
                state="pending",
                requires_approval=(s == "approval"),
            ))
            for s in PIPELINE_STAGES
        ]
        pipeline = AutomationPipeline(
            pipeline_id=str(uuid.uuid4()),
            title=title.strip(),
            description=description,
            actor=actor,
            pipeline_state=PIPELINE_CREATED,
            stages=stages,
            created_at=_ts(),
            labels=labels or [],
        )
        records = self._load()
        records.append(asdict(pipeline))
        self._save(records)
        self._audit("created", pipeline.pipeline_id, actor, {"title": title})
        return pipeline

    def get(self, pipeline_id: str) -> dict | None:
        for r in self._load():
            if r.get("pipeline_id") == pipeline_id:
                return r
        return None

    def list_all(self, state: str | None = None) -> list[dict]:
        records = self._load()
        if state:
            records = [r for r in records if r.get("pipeline_state") == state]
        return records

    def start_stage(self, pipeline_id: str, stage: str, actor: str) -> dict | None:
        """Mark a stage as in-progress."""
        if stage not in PIPELINE_STAGES:
            raise ValueError(f"Unknown stage: {stage}")
        records = self._load()
        updated = None
        for r in records:
            if r.get("pipeline_id") != pipeline_id:
                continue
            for s in r.get("stages", []):
                if s.get("stage") == stage:
                    if s.get("state") not in ("pending", "failed"):
                        raise ValueError(f"Stage {stage} is already {s.get('state')}")
                    s["state"] = "in_progress"
                    s["started_at"] = _ts()
                    break
            r["pipeline_state"] = PIPELINE_RUNNING
            if not r.get("started_at"):
                r["started_at"] = _ts()
            updated = r
            break
        if updated:
            self._save(records)
            self._audit("stage_started", pipeline_id, actor, {"stage": stage})
        return updated

    def complete_stage(
        self,
        pipeline_id: str,
        stage: str,
        actor: str,
        result_summary: str = "",
        evidence: str = "",
    ) -> dict | None:
        """Mark a stage as completed."""
        records = self._load()
        updated = None
        for r in records:
            if r.get("pipeline_id") != pipeline_id:
                continue
            for s in r.get("stages", []):
                if s.get("stage") == stage:
                    s["state"] = "completed"
                    s["completed_at"] = _ts()
                    s["result_summary"] = result_summary
                    s["evidence"] = evidence
                    break
            # Check if all non-approval stages are done
            all_done = all(
                s.get("state") in ("completed", "skipped")
                for s in r.get("stages", [])
            )
            if all_done:
                r["pipeline_state"] = PIPELINE_COMPLETED
                r["completed_at"] = _ts()
            updated = r
            break
        if updated:
            self._save(records)
            self._audit("stage_completed", pipeline_id, actor, {"stage": stage, "evidence": evidence})
        return updated

    def approve_stage(self, pipeline_id: str, stage: str, actor: str) -> dict | None:
        """Approve a stage that requires approval."""
        records = self._load()
        updated = None
        for r in records:
            if r.get("pipeline_id") != pipeline_id:
                continue
            for s in r.get("stages", []):
                if s.get("stage") == stage:
                    if not s.get("requires_approval"):
                        raise ValueError(f"Stage {stage} does not require approval")
                    s["approved_by"] = actor
                    s["approved_at"] = _ts()
                    break
            updated = r
            break
        if updated:
            self._save(records)
            self._audit("stage_approved", pipeline_id, actor, {"stage": stage})
        return updated

    def fail_stage(self, pipeline_id: str, stage: str, actor: str, reason: str = "") -> dict | None:
        records = self._load()
        updated = None
        for r in records:
            if r.get("pipeline_id") != pipeline_id:
                continue
            for s in r.get("stages", []):
                if s.get("stage") == stage:
                    s["state"] = "failed"
                    s["failure_reason"] = reason
                    break
            r["pipeline_state"] = PIPELINE_FAILED
            updated = r
            break
        if updated:
            self._save(records)
            self._audit("stage_failed", pipeline_id, actor, {"stage": stage, "reason": reason})
        return updated

    def cancel(self, pipeline_id: str, actor: str, reason: str = "") -> dict | None:
        records = self._load()
        updated = None
        for r in records:
            if r.get("pipeline_id") == pipeline_id:
                if r.get("pipeline_state") in TERMINAL_PIPELINE_STATES:
                    raise ValueError(f"Pipeline {pipeline_id} is already in terminal state {r.get('pipeline_state')}")
                r["pipeline_state"] = PIPELINE_CANCELLED
                r["cancelled_at"] = _ts()
                r["cancelled_by"] = actor
                r["cancel_reason"] = reason
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("cancelled", pipeline_id, actor, {"reason": reason})
        return updated

    def rollback(self, pipeline_id: str, actor: str, rollback_packet_id: str = "") -> dict | None:
        records = self._load()
        updated = None
        for r in records:
            if r.get("pipeline_id") == pipeline_id:
                r["pipeline_state"] = PIPELINE_ROLLED_BACK
                r["rollback_executed_at"] = _ts()
                r["rollback_executed_by"] = actor
                if rollback_packet_id:
                    r["rollback_packet_id"] = rollback_packet_id
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("rolled_back", pipeline_id, actor, {"rollback_packet_id": rollback_packet_id})
        return updated

    def pipeline_summary(self, pipeline_id: str) -> dict:
        p = self.get(pipeline_id)
        if not p:
            return {"error": "pipeline not found", "pipeline_id": pipeline_id}
        stages = p.get("stages", [])
        completed = [s for s in stages if s.get("state") == "completed"]
        pending = [s for s in stages if s.get("state") == "pending"]
        failed = [s for s in stages if s.get("state") == "failed"]
        return {
            "pipeline_id": pipeline_id,
            "title": p.get("title"),
            "pipeline_state": p.get("pipeline_state"),
            "stages_total": len(stages),
            "stages_completed": len(completed),
            "stages_pending": len(pending),
            "stages_failed": len(failed),
            "evidence": [
                {"stage": s["stage"], "evidence": s.get("evidence")}
                for s in completed if s.get("evidence")
            ],
        }
