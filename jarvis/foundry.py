"""E5: Foundry — newborn agent creation and lifecycle management.

Implements: propose → approve → sandbox → evaluate → promote | retire
with durable persistence, governance audit trail, and honest state labels.

Every agent spec records: role, mission, zone, arena, memory_scope,
tool_scope, authority_stage, evaluation_criteria, and retirement policy.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_FOUNDRY_ROOT = Path("data/foundry")
_AGENTS_PATH = _FOUNDRY_ROOT / "agents.json"
_AGENTS_LOG_PATH = _FOUNDRY_ROOT / "agents_log.jsonl"
_AUDIT_PATH = _FOUNDRY_ROOT / "foundry_audit.jsonl"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --------------------------------------------------------------------------
# Agent lifecycle states
# --------------------------------------------------------------------------
AGENT_STATE_PROPOSED = "proposed"
AGENT_STATE_APPROVED = "approved"
AGENT_STATE_SANDBOXED = "sandboxed"
AGENT_STATE_EVALUATING = "evaluating"
AGENT_STATE_PROMOTED = "promoted"
AGENT_STATE_RETIRED = "retired"
AGENT_STATE_REJECTED = "rejected"

AGENT_STATES = frozenset({
    AGENT_STATE_PROPOSED, AGENT_STATE_APPROVED, AGENT_STATE_SANDBOXED,
    AGENT_STATE_EVALUATING, AGENT_STATE_PROMOTED, AGENT_STATE_RETIRED,
    AGENT_STATE_REJECTED,
})

TERMINAL_AGENT_STATES = frozenset({AGENT_STATE_PROMOTED, AGENT_STATE_RETIRED, AGENT_STATE_REJECTED})

# Valid forward transitions
_AGENT_TRANSITIONS: dict[str, frozenset[str]] = {
    AGENT_STATE_PROPOSED:   frozenset({AGENT_STATE_APPROVED, AGENT_STATE_REJECTED}),
    AGENT_STATE_APPROVED:   frozenset({AGENT_STATE_SANDBOXED, AGENT_STATE_REJECTED}),
    AGENT_STATE_SANDBOXED:  frozenset({AGENT_STATE_EVALUATING, AGENT_STATE_RETIRED}),
    AGENT_STATE_EVALUATING: frozenset({AGENT_STATE_PROMOTED, AGENT_STATE_RETIRED}),
    AGENT_STATE_PROMOTED:   frozenset(),
    AGENT_STATE_RETIRED:    frozenset(),
    AGENT_STATE_REJECTED:   frozenset(),
}

# --------------------------------------------------------------------------
# Authority stages (maps to trust zone stages)
# --------------------------------------------------------------------------
AUTHORITY_MONITOR = "monitor"
AUTHORITY_SUGGEST = "suggest"
AUTHORITY_SANDBOX = "sandbox"
AUTHORITY_SANDBOX_LIVE = "sandbox_live"
AUTHORITY_LIVE = "live"

AUTHORITY_STAGES = [AUTHORITY_MONITOR, AUTHORITY_SUGGEST, AUTHORITY_SANDBOX, AUTHORITY_SANDBOX_LIVE, AUTHORITY_LIVE]


@dataclass(slots=True)
class NewbornAgentSpec:
    """Full specification for a newborn JARVIS agent."""
    agent_id: str
    name: str
    role: str                           # short label: "research", "scheduler", "writer" etc.
    mission: str                        # one-sentence mission statement
    zone: str                           # trust zone this agent operates in
    arena: str                          # resource arena
    memory_scope: list[str]             # memory lanes this agent can read
    tool_scope: list[str]               # tool action_types this agent may invoke
    authority_stage: str                # starting authority stage
    evaluation_criteria: list[str]      # what constitutes success in evaluation
    retirement_policy: str              # condition under which agent is retired
    proposed_by: str                    # actor who proposed this agent
    state: str                          # lifecycle state
    created_at: str
    updated_at: str
    approved_at: str = ""
    approved_by: str = ""
    sandboxed_at: str = ""
    sandbox_run_count: int = 0
    sandbox_success_count: int = 0
    sandbox_failure_count: int = 0
    evaluation_notes: str = ""
    promoted_at: str = ""
    retired_at: str = ""
    retirement_reason: str = ""
    rejection_reason: str = ""
    labels: list[str] = field(default_factory=list)


class FoundryStore:
    """Durable store for newborn agent specs with JSONL audit trail."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _FOUNDRY_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.agents_path = self.root / "agents.json"
        self.log_path = self.root / "agents_log.jsonl"
        self.audit_path = self.root / "foundry_audit.jsonl"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> list[dict]:
        if not self.agents_path.exists():
            return []
        try:
            data = json.loads(self.agents_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        self.agents_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.agents_path, records)

    def _audit(self, event: str, agent_id: str, actor: str, extra: dict | None = None) -> None:
        record: dict[str, Any] = {
            "ts": _ts(),
            "event": event,
            "agent_id": agent_id,
            "actor": actor,
        }
        if extra:
            record.update(extra)
        try:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            append_jsonl(self.audit_path, record)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Agent operations
    # ------------------------------------------------------------------

    def propose(self, spec: NewbornAgentSpec) -> dict:
        """Submit a new agent proposal. Returns the stored record."""
        records = self._load()
        payload = asdict(spec)
        records.append(payload)
        self._save(records)
        self._audit("proposed", spec.agent_id, spec.proposed_by)
        return payload

    def get(self, agent_id: str) -> dict | None:
        for r in self._load():
            if r.get("agent_id") == agent_id:
                return r
        return None

    def list_all(self, state: str | None = None) -> list[dict]:
        records = self._load()
        if state:
            records = [r for r in records if r.get("state") == state]
        return records

    def _transition(self, agent_id: str, new_state: str, actor: str, updates: dict | None = None) -> dict | None:
        records = self._load()
        updated = None
        for r in records:
            if r.get("agent_id") == agent_id:
                current = r.get("state", "")
                allowed = _AGENT_TRANSITIONS.get(current, frozenset())
                if new_state not in allowed:
                    raise ValueError(
                        f"Invalid transition {current!r} → {new_state!r} "
                        f"for agent {agent_id}. Allowed: {sorted(allowed)}"
                    )
                r["state"] = new_state
                r["updated_at"] = _ts()
                if updates:
                    r.update(updates)
                updated = r
                break
        if updated is None:
            raise KeyError(f"Agent not found: {agent_id}")
        self._save(records)
        return updated

    def approve(self, agent_id: str, actor: str) -> dict:
        updates = {"approved_at": _ts(), "approved_by": actor}
        result = self._transition(agent_id, AGENT_STATE_APPROVED, actor, updates)
        self._audit("approved", agent_id, actor)
        return result

    def reject(self, agent_id: str, actor: str, reason: str = "") -> dict:
        updates = {"rejection_reason": reason}
        result = self._transition(agent_id, AGENT_STATE_REJECTED, actor, updates)
        self._audit("rejected", agent_id, actor, {"reason": reason})
        return result

    def sandbox(self, agent_id: str, actor: str) -> dict:
        updates = {"sandboxed_at": _ts()}
        result = self._transition(agent_id, AGENT_STATE_SANDBOXED, actor, updates)
        self._audit("sandboxed", agent_id, actor)
        return result

    def capture_sandbox_snapshot(self, agent_id: str) -> dict | None:
        """K5: Capture a pre-execution snapshot of agent state for rollback.

        Stores a timestamped snapshot under agent['sandbox_snapshots'].
        Returns the snapshot dict, or None if agent not found.
        """
        records = self._load()
        snapshot = None
        for r in records:
            if r.get("agent_id") == agent_id:
                snap = {
                    "snapshot_id": str(uuid.uuid4()),
                    "captured_at": _ts(),
                    "state": r.get("state"),
                    "authority_stage": r.get("authority_stage"),
                    "sandbox_run_count": r.get("sandbox_run_count", 0),
                    "sandbox_success_count": r.get("sandbox_success_count", 0),
                    "sandbox_failure_count": r.get("sandbox_failure_count", 0),
                    "evaluation_notes": r.get("evaluation_notes", ""),
                }
                snaps = list(r.get("sandbox_snapshots") or [])
                snaps.append(snap)
                r["sandbox_snapshots"] = snaps[-10:]  # keep last 10
                r["updated_at"] = _ts()
                snapshot = snap
                break
        if snapshot:
            self._save(records)
            self._audit("sandbox_snapshot", agent_id, "system", {"snapshot_id": snapshot["snapshot_id"]})
        return snapshot

    def rollback_to_snapshot(self, agent_id: str, snapshot_id: str, actor: str) -> dict | None:
        """K5: Roll an agent back to a captured sandbox snapshot.

        Restores state, authority_stage, and counter fields from the snapshot.
        The rollback itself is audited.  Returns the updated agent or None.
        """
        records = self._load()
        updated = None
        for r in records:
            if r.get("agent_id") == agent_id:
                snaps = r.get("sandbox_snapshots") or []
                target = next((s for s in snaps if s.get("snapshot_id") == snapshot_id), None)
                if not target:
                    return None
                r["state"] = target["state"]
                r["authority_stage"] = target["authority_stage"]
                r["sandbox_run_count"] = target["sandbox_run_count"]
                r["sandbox_success_count"] = target["sandbox_success_count"]
                r["sandbox_failure_count"] = target["sandbox_failure_count"]
                r["evaluation_notes"] = target["evaluation_notes"]
                r["rolled_back_at"] = _ts()
                r["rolled_back_to_snapshot"] = snapshot_id
                r["updated_at"] = _ts()
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("rollback", agent_id, actor, {"snapshot_id": snapshot_id})
        return updated

    def record_sandbox_run(self, agent_id: str, success: bool, notes: str = "") -> dict | None:
        records = self._load()
        updated = None
        for r in records:
            if r.get("agent_id") == agent_id:
                r["sandbox_run_count"] = int(r.get("sandbox_run_count") or 0) + 1
                if success:
                    r["sandbox_success_count"] = int(r.get("sandbox_success_count") or 0) + 1
                else:
                    r["sandbox_failure_count"] = int(r.get("sandbox_failure_count") or 0) + 1
                if notes:
                    r["evaluation_notes"] = notes
                r["updated_at"] = _ts()
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("sandbox_run", agent_id, "system", {"success": success})
        return updated

    def begin_evaluation(self, agent_id: str, actor: str) -> dict:
        result = self._transition(agent_id, AGENT_STATE_EVALUATING, actor)
        self._audit("evaluation_started", agent_id, actor)
        return result

    def promote(self, agent_id: str, actor: str, new_authority: str | None = None) -> dict:
        updates: dict[str, Any] = {"promoted_at": _ts()}
        if new_authority and new_authority in AUTHORITY_STAGES:
            updates["authority_stage"] = new_authority
        result = self._transition(agent_id, AGENT_STATE_PROMOTED, actor, updates)
        self._audit("promoted", agent_id, actor, {"new_authority": new_authority})
        return result

    def retire(self, agent_id: str, actor: str, reason: str = "") -> dict:
        updates = {"retired_at": _ts(), "retirement_reason": reason}
        result = self._transition(agent_id, AGENT_STATE_RETIRED, actor, updates)
        self._audit("retired", agent_id, actor, {"reason": reason})
        return result

    def evaluation_summary(self, agent_id: str) -> dict:
        agent = self.get(agent_id)
        if not agent:
            return {"error": "agent not found", "agent_id": agent_id}
        runs = int(agent.get("sandbox_run_count") or 0)
        successes = int(agent.get("sandbox_success_count") or 0)
        failures = int(agent.get("sandbox_failure_count") or 0)
        success_rate = round(successes / runs, 3) if runs > 0 else 0.0
        criteria = agent.get("evaluation_criteria") or []
        return {
            "agent_id": agent_id,
            "name": agent.get("name"),
            "state": agent.get("state"),
            "sandbox_run_count": runs,
            "sandbox_success_count": successes,
            "sandbox_failure_count": failures,
            "success_rate": success_rate,
            "evaluation_criteria": criteria,
            "evaluation_notes": agent.get("evaluation_notes", ""),
            "authority_stage": agent.get("authority_stage"),
            "recommended_action": (
                "promote" if success_rate >= 0.8 and runs >= 3 else
                "retire" if failures >= 3 else
                "continue_evaluation"
            ),
        }


class FoundryBuilder:
    """Validates and constructs NewbornAgentSpec objects."""

    REQUIRED_FIELDS = {"name", "role", "mission", "zone", "arena", "evaluation_criteria"}

    def build(
        self,
        *,
        name: str,
        role: str,
        mission: str,
        zone: str,
        arena: str,
        memory_scope: list[str] | None = None,
        tool_scope: list[str] | None = None,
        authority_stage: str = AUTHORITY_MONITOR,
        evaluation_criteria: list[str] | None = None,
        retirement_policy: str = "retire after 3 consecutive failures or on manual review",
        proposed_by: str = "chris",
        labels: list[str] | None = None,
    ) -> NewbornAgentSpec:
        if not name.strip():
            raise ValueError("name is required")
        if not mission.strip():
            raise ValueError("mission is required")
        if authority_stage not in AUTHORITY_STAGES:
            raise ValueError(f"authority_stage must be one of {AUTHORITY_STAGES}")
        if not evaluation_criteria:
            raise ValueError("evaluation_criteria must have at least one criterion")
        return NewbornAgentSpec(
            agent_id=str(uuid.uuid4()),
            name=name.strip(),
            role=role.strip(),
            mission=mission.strip(),
            zone=zone.strip(),
            arena=arena.strip(),
            memory_scope=memory_scope or [],
            tool_scope=tool_scope or [],
            authority_stage=authority_stage,
            evaluation_criteria=evaluation_criteria,
            retirement_policy=retirement_policy,
            proposed_by=proposed_by,
            state=AGENT_STATE_PROPOSED,
            created_at=_ts(),
            updated_at=_ts(),
            labels=labels or [],
        )
