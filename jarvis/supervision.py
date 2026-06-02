from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import AuditLog
from .doctrine import SharedDoctrineStore
from .trust import TrustSupport


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class StewardshipLaneContract:
    lane_id: str
    name: str
    mission: str
    primary_burden: str
    primary_agents: list[str]
    trust_zone_ids: list[str]
    report_cadence: str
    output_types: list[str]
    escalation_target: str
    autonomy_posture: str
    sandbox_default: str
    doctrine_threshold: dict[str, int | float]
    notes: str = ""
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class AgentSupervisionContract:
    agent_id: str
    label: str
    lane_id: str
    mission: str
    stewardship_role: str
    trust_zone_id: str
    authority_stage: str
    sandbox_class: str
    approval_mode: str
    allowed_without_approval: list[str]
    must_stage_actions: list[str]
    must_sandbox_actions: list[str]
    must_escalate_actions: list[str]
    forbidden_actions: list[str]
    reversible_actions: list[str]
    doctrine_scope: dict[str, int | float]
    supervision_cadence: str
    escalation_target: str
    quiet_hours_behavior: str = "defer-non-urgent"
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class SupervisionDecision:
    decision_id: str
    agent_id: str
    lane_id: str
    trust_zone_id: str
    action_type: str
    requested_outcome: str
    resolution: str
    approval_required: bool
    sandbox_required: bool
    escalation_required: bool
    rollback_posture: str
    authority_stage: str
    doctrine_rules_applied: list[str]
    reasons: list[str]
    trace: dict[str, Any]
    created_at: str


class SupervisionStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.lanes_path = self.root / "stewardship_lanes.json"
        self.contracts_path = self.root / "agent_supervision_contracts.json"
        self.reviews_path = self.root / "decision_reviews.json"
        self.traces_path = self.root / "decision_traces.jsonl"

    def _load_json(self, path: Path, *, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        return payload

    def _save_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def list_lanes(self) -> list[dict[str, Any]]:
        payload = self._load_json(self.lanes_path, default=[])
        return [dict(item) for item in payload if isinstance(item, dict)]

    def save_lanes(self, records: list[dict[str, Any]]) -> None:
        self._save_json(self.lanes_path, records)

    def list_contracts(self) -> list[dict[str, Any]]:
        payload = self._load_json(self.contracts_path, default=[])
        return [dict(item) for item in payload if isinstance(item, dict)]

    def save_contracts(self, records: list[dict[str, Any]]) -> None:
        self._save_json(self.contracts_path, records)

    def list_reviews(self) -> list[dict[str, Any]]:
        payload = self._load_json(self.reviews_path, default=[])
        return [dict(item) for item in payload if isinstance(item, dict)]

    def save_reviews(self, records: list[dict[str, Any]]) -> None:
        self._save_json(self.reviews_path, records[-800:])

    def append_trace(self, record: dict[str, Any]) -> None:
        with self.traces_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def list_traces(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.traces_path.exists():
            return []
        try:
            records = [
                json.loads(line)
                for line in self.traces_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, json.JSONDecodeError):
            return []
        return list(reversed(records[-limit:]))


class SupervisionSupport:
    def __init__(
        self,
        store: SupervisionStore,
        *,
        trust_support: TrustSupport,
        doctrine_store: SharedDoctrineStore,
        audit_log: AuditLog,
    ) -> None:
        self.store = store
        self.trust_support = trust_support
        self.doctrine_store = doctrine_store
        self.audit_log = audit_log
        self.bootstrap_defaults()

    def bootstrap_defaults(self) -> None:
        if not self.store.list_lanes():
            now = _now_iso()
            lanes = [
                StewardshipLaneContract(
                    lane_id="family-stewardship",
                    name="Family Stewardship",
                    mission="Protect household peace, rhythm, and logistics through governed preparation and escalation.",
                    primary_burden="Household drift and social friction.",
                    primary_agents=["pepper", "family-steward", "family-chief"],
                    trust_zone_ids=["shared-email.stage", "household_schedule", "household_home", "household_tasks"],
                    report_cadence="event_driven",
                    output_types=["briefing_item", "decision_needed", "drift_signal", "blocked_work"],
                    escalation_target="chris",
                    autonomy_posture="prepare-and-stage",
                    sandbox_default="household.workflow",
                    doctrine_threshold={"min_reviewed_successes": 3, "max_reversals": 0, "min_success_rate": 0.95},
                    created_at=now,
                    updated_at=now,
                ),
                StewardshipLaneContract(
                    lane_id="executive-calendar",
                    name="Executive and Calendar",
                    mission="Reduce work friction through staged prep, scheduling hygiene, and bounded routing actions.",
                    primary_burden="Calendar collisions and underprepared decisions.",
                    primary_agents=["herald", "executive-counsel", "kang"],
                    trust_zone_ids=["household_schedule", "shared-email.stage", "household_attention"],
                    report_cadence="event_driven",
                    output_types=["prepared_work", "decision_needed", "quiet_completion"],
                    escalation_target="chris",
                    autonomy_posture="stage-before-send",
                    sandbox_default="calendar-routing",
                    doctrine_threshold={"min_reviewed_successes": 4, "max_reversals": 0, "min_success_rate": 0.97},
                    created_at=now,
                    updated_at=now,
                ),
                StewardshipLaneContract(
                    lane_id="watcher-continuity",
                    name="Watcher and Continuity",
                    mission="Preserve continuity, detect repeat friction, and strengthen doctrine from reviewed success.",
                    primary_burden="Loss of context and repeated unlearned mistakes.",
                    primary_agents=["watcher", "memory-curator"],
                    trust_zone_ids=["household_attention", "household_huddle"],
                    report_cadence="hourly",
                    output_types=["drift_signal", "prepared_work", "quiet_completion"],
                    escalation_target="system-steward",
                    autonomy_posture="observe-synthesize-escalate",
                    sandbox_default="memory-review",
                    doctrine_threshold={"min_reviewed_successes": 5, "max_reversals": 1, "min_success_rate": 0.98},
                    created_at=now,
                    updated_at=now,
                ),
                StewardshipLaneContract(
                    lane_id="wealth-opportunity",
                    name="Wealth and Opportunity",
                    mission="Prepare diligence and bounded simulations without letting enthusiasm outrun approval.",
                    primary_burden="Financial risk and premature commitment.",
                    primary_agents=["black-panther", "opportunity-scout"],
                    trust_zone_ids=["publication_review", "shared-email.stage"],
                    report_cadence="daily",
                    output_types=["prepared_work", "decision_needed", "blocked_work"],
                    escalation_target="chris",
                    autonomy_posture="sandbox-and-stage",
                    sandbox_default="diligence-sandbox",
                    doctrine_threshold={"min_reviewed_successes": 4, "max_reversals": 0, "min_success_rate": 0.99},
                    created_at=now,
                    updated_at=now,
                ),
                StewardshipLaneContract(
                    lane_id="chamber-operations",
                    name="Chamber Operations",
                    mission="Keep the agent society healthy, quiet, and reversible while extending autonomy only through review.",
                    primary_burden="Runtime drift, noisy automation, and unsafe self-change.",
                    primary_agents=["system-steward", "autoforge"],
                    trust_zone_ids=["household_huddle", "household_focus", "household_attention"],
                    report_cadence="hourly",
                    output_types=["quiet_completion", "blocked_work", "drift_signal"],
                    escalation_target="chris",
                    autonomy_posture="supervised-background",
                    sandbox_default="ops-sandbox",
                    doctrine_threshold={"min_reviewed_successes": 5, "max_reversals": 0, "min_success_rate": 0.99},
                    created_at=now,
                    updated_at=now,
                ),
            ]
            self.store.save_lanes([asdict(item) for item in lanes])
        if not self.store.list_contracts():
            now = _now_iso()
            contracts = [
                AgentSupervisionContract(
                    agent_id="pepper",
                    label="Pepper",
                    lane_id="family-stewardship",
                    mission="Prepare and stage household coordination work.",
                    stewardship_role="lane-anchor",
                    trust_zone_id="household_schedule",
                    authority_stage="sandbox_live",
                    sandbox_class="household.workflow",
                    approval_mode="stage_and_alert",
                    allowed_without_approval=["observe", "classify"],
                    must_stage_actions=["draft", "stage", "calendar_route", "alert"],
                    must_sandbox_actions=["calendar_route"],
                    must_escalate_actions=["home_control"],
                    forbidden_actions=["spawn_agent_in_zone", "retire_agent_in_zone"],
                    reversible_actions=["calendar_route", "draft", "stage", "alert"],
                    doctrine_scope={"min_reviewed_successes": 3, "max_reversals": 0, "min_success_rate": 0.95},
                    supervision_cadence="event_driven",
                    escalation_target="chris",
                    created_at=now,
                    updated_at=now,
                ),
                AgentSupervisionContract(
                    agent_id="herald",
                    label="Herald",
                    lane_id="executive-calendar",
                    mission="Prepare executive decision context and route bounded schedule actions.",
                    stewardship_role="lane-anchor",
                    trust_zone_id="household_schedule",
                    authority_stage="sandbox_live",
                    sandbox_class="calendar-routing",
                    approval_mode="stage_and_alert",
                    allowed_without_approval=["observe", "classify", "recommend"],
                    must_stage_actions=["draft", "stage", "alert"],
                    must_sandbox_actions=["calendar_route"],
                    must_escalate_actions=["send", "deploy", "publish"],
                    forbidden_actions=["home_control"],
                    reversible_actions=["calendar_route", "draft", "stage", "alert"],
                    doctrine_scope={"min_reviewed_successes": 4, "max_reversals": 0, "min_success_rate": 0.97},
                    supervision_cadence="event_driven",
                    escalation_target="chris",
                    created_at=now,
                    updated_at=now,
                ),
                AgentSupervisionContract(
                    agent_id="watcher",
                    label="Watcher",
                    lane_id="watcher-continuity",
                    mission="Synthesize background patterns and queue doctrine candidates.",
                    stewardship_role="observer",
                    trust_zone_id="household_attention",
                    authority_stage="stage_alert",
                    sandbox_class="memory-review",
                    approval_mode="boundary_escalation_only",
                    allowed_without_approval=["observe", "classify", "infer", "recommend"],
                    must_stage_actions=["alert", "notification_workflow"],
                    must_sandbox_actions=[],
                    must_escalate_actions=["spawn_agent_in_zone"],
                    forbidden_actions=["home_control", "calendar_route"],
                    reversible_actions=["alert", "notification_workflow"],
                    doctrine_scope={"min_reviewed_successes": 5, "max_reversals": 1, "min_success_rate": 0.98},
                    supervision_cadence="hourly",
                    escalation_target="system-steward",
                    created_at=now,
                    updated_at=now,
                ),
                AgentSupervisionContract(
                    agent_id="black-panther",
                    label="Black Panther",
                    lane_id="wealth-opportunity",
                    mission="Stage diligence and reversible opportunity work only.",
                    stewardship_role="diligence-lead",
                    trust_zone_id="publication_review",
                    authority_stage="stage_alert",
                    sandbox_class="diligence-sandbox",
                    approval_mode="stage_and_alert",
                    allowed_without_approval=["observe", "classify", "recommend"],
                    must_stage_actions=["draft", "stage", "publishing_review", "alert"],
                    must_sandbox_actions=["simulate", "execute_in_zone"],
                    must_escalate_actions=["purchase", "send_message", "deploy"],
                    forbidden_actions=["home_control"],
                    reversible_actions=["draft", "stage", "alert", "simulate"],
                    doctrine_scope={"min_reviewed_successes": 4, "max_reversals": 0, "min_success_rate": 0.99},
                    supervision_cadence="daily",
                    escalation_target="chris",
                    created_at=now,
                    updated_at=now,
                ),
                AgentSupervisionContract(
                    agent_id="system-steward",
                    label="System Steward",
                    lane_id="chamber-operations",
                    mission="Supervise runtime health and bounded orchestration posture.",
                    stewardship_role="supervisor",
                    trust_zone_id="household_huddle",
                    authority_stage="stage_alert",
                    sandbox_class="ops-sandbox",
                    approval_mode="boundary_escalation_only",
                    allowed_without_approval=["observe", "classify", "infer", "recommend"],
                    must_stage_actions=["huddle_workflow", "alert"],
                    must_sandbox_actions=["simulate", "execute_in_zone", "spawn_agent_in_zone"],
                    must_escalate_actions=["retire_agent_in_zone", "deploy"],
                    forbidden_actions=["home_control", "calendar_route"],
                    reversible_actions=["simulate", "alert", "huddle_workflow"],
                    doctrine_scope={"min_reviewed_successes": 5, "max_reversals": 0, "min_success_rate": 0.99},
                    supervision_cadence="hourly",
                    escalation_target="chris",
                    created_at=now,
                    updated_at=now,
                ),
            ]
            self.store.save_contracts([asdict(item) for item in contracts])

    def list_stewardship_lanes(self) -> list[dict[str, Any]]:
        return self.store.list_lanes()

    def list_agent_contracts(self) -> list[dict[str, Any]]:
        return self.store.list_contracts()

    def list_reviews(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(reversed(self.store.list_reviews()[-limit:]))

    def list_traces(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.store.list_traces(limit=limit)

    def get_contract(self, agent_id: str) -> dict[str, Any] | None:
        agent_key = str(agent_id).strip().lower()
        for item in self.store.list_contracts():
            if str(item.get("agent_id", "")).strip().lower() == agent_key:
                return dict(item)
        return None

    def evaluate_action(
        self,
        *,
        agent_id: str,
        action_type: str,
        requested_outcome: str,
        trust_zone_id: str = "",
        lane_id: str = "",
        arena_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = dict(context or {})
        contract = self.get_contract(agent_id)
        decision_id = f"sup-{uuid.uuid4().hex[:12]}"
        created_at = _now_iso()
        if contract is None:
            payload = {
                "decision_id": decision_id,
                "agent_id": agent_id,
                "lane_id": lane_id,
                "trust_zone_id": trust_zone_id,
                "action_type": action_type,
                "requested_outcome": requested_outcome,
                "resolution": "escalate",
                "approval_required": True,
                "sandbox_required": False,
                "escalation_required": True,
                "rollback_posture": "manual-only",
                "authority_stage": "unknown",
                "doctrine_rules_applied": [],
                "reasons": [f"No supervision contract exists for agent '{agent_id}'."],
                "trace": {"arena_id": arena_id, "context": context},
                "created_at": created_at,
            }
            self._record_decision(payload)
            return payload

        lane_id = str(lane_id or contract.get("lane_id", "")).strip()
        trust_zone_id = str(trust_zone_id or contract.get("trust_zone_id", "")).strip()
        zone = self.trust_support.get_trust_zone(trust_zone_id) if trust_zone_id else None
        stage = self.trust_support.get_authority_stage(str(contract.get("authority_stage", "")).strip() or str((zone or {}).get("authority_stage", "")))
        doctrine_rules = self.doctrine_store.rules_for(agent_id=agent_id, domain=lane_id, active_only=True)
        doctrine_rule_ids = [str(item.get("rule_id", "")).strip() for item in doctrine_rules if str(item.get("rule_id", "")).strip()]
        reasons: list[str] = []
        resolution = "autonomous"
        approval_required = False
        sandbox_required = False
        escalation_required = False
        rollback_posture = "full"
        action_key = str(action_type).strip()
        zone_allowed_actions = [str(item).strip() for item in list((zone or {}).get("allowed_actions", [])) if str(item).strip()]

        if str(contract.get("status", "active")).strip().lower() != "active":
            resolution = "forbidden"
            escalation_required = True
            approval_required = True
            rollback_posture = "manual-only"
            reasons.append(f"Agent contract '{agent_id}' is not active.")
        if zone is None:
            resolution = "forbidden"
            escalation_required = True
            approval_required = True
            rollback_posture = "manual-only"
            reasons.append(f"Trust zone '{trust_zone_id}' is unknown.")
        elif str(zone.get("status", "active")).strip().lower() != "active":
            resolution = "forbidden"
            escalation_required = True
            approval_required = True
            rollback_posture = "manual-only"
            reasons.append(f"Trust zone '{trust_zone_id}' is not active.")
        elif action_key not in zone_allowed_actions:
            resolution = "escalate"
            escalation_required = True
            approval_required = True
            rollback_posture = "manual-only"
            reasons.append(f"Action '{action_key}' is outside trust zone '{trust_zone_id}'.")

        if action_key in set(contract.get("forbidden_actions", [])):
            resolution = "forbidden"
            escalation_required = True
            approval_required = True
            rollback_posture = "manual-only"
            reasons.append(f"Action '{action_key}' is forbidden for agent '{agent_id}'.")

        if context.get("cross_zone"):
            resolution = "escalate"
            escalation_required = True
            approval_required = True
            rollback_posture = "manual-only"
            reasons.append("Cross-zone actions require human escalation.")

        if context.get("touches_external_state") and not context.get("reversible", True):
            rollback_posture = "none-known"
            reasons.append("Requested action touches external state without a declared reversal path.")
            if resolution == "autonomous":
                resolution = "stage"
                approval_required = True

        if action_key in set(contract.get("must_escalate_actions", [])):
            resolution = "escalate"
            escalation_required = True
            approval_required = True
            rollback_posture = "manual-only"
            reasons.append(f"Action '{action_key}' is always escalated for this agent.")
        elif not escalation_required and action_key in set(contract.get("must_sandbox_actions", [])):
            resolution = "sandbox"
            sandbox_required = True
            reasons.append(f"Action '{action_key}' must run inside sandbox '{contract.get('sandbox_class', '')}'.")
        elif not escalation_required and action_key in set(contract.get("must_stage_actions", [])):
            resolution = "stage"
            approval_required = True
            reasons.append(f"Action '{action_key}' must be staged before execution.")
        elif not escalation_required and action_key not in set(contract.get("allowed_without_approval", [])):
            approval_required = True
            resolution = "stage" if resolution == "autonomous" else resolution
            reasons.append(f"Action '{action_key}' is not in the standing autonomous allowance set.")

        stage_id = str((stage or {}).get("stage_id", contract.get("authority_stage", "observe"))).strip() or "observe"
        if stage_id in {"observe", "draft"} and resolution in {"autonomous", "sandbox"}:
            resolution = "stage"
            approval_required = True
            sandbox_required = False
            reasons.append(f"Authority stage '{stage_id}' does not permit live mutation.")

        if stage_id == "stage_alert" and resolution == "autonomous":
            resolution = "stage"
            approval_required = True
            reasons.append("Stage-and-alert posture requires human review before completion.")

        if stage_id in {"sandbox_live", "mature_live"} and resolution == "sandbox":
            sandbox_required = True
        elif resolution == "sandbox":
            resolution = "stage"
            sandbox_required = False
            approval_required = True
            reasons.append(f"Authority stage '{stage_id}' is not yet sandbox-live.")

        doctrine_effects = self._apply_doctrine_effects(doctrine_rules, action_key, reasons)
        if doctrine_effects.get("force_stage"):
            resolution = "stage"
            approval_required = True
        if doctrine_effects.get("force_escalate"):
            resolution = "escalate"
            approval_required = True
            escalation_required = True
            sandbox_required = False
            rollback_posture = "manual-only"

        if action_key in set(contract.get("reversible_actions", [])) and rollback_posture == "full":
            rollback_posture = "reversible"

        payload = asdict(
            SupervisionDecision(
                decision_id=decision_id,
                agent_id=agent_id,
                lane_id=lane_id,
                trust_zone_id=trust_zone_id,
                action_type=action_key,
                requested_outcome=requested_outcome,
                resolution=resolution,
                approval_required=approval_required,
                sandbox_required=sandbox_required,
                escalation_required=escalation_required,
                rollback_posture=rollback_posture,
                authority_stage=stage_id,
                doctrine_rules_applied=doctrine_rule_ids,
                reasons=reasons or ["Action fits current supervision contract."],
                trace={
                    "arena_id": arena_id,
                    "context": context,
                    "zone_approval_mode": str((zone or {}).get("approval_mode", "")).strip(),
                    "zone_allowed_actions": zone_allowed_actions,
                    "contract": {
                        "approval_mode": str(contract.get("approval_mode", "")).strip(),
                        "sandbox_class": str(contract.get("sandbox_class", "")).strip(),
                        "escalation_target": str(contract.get("escalation_target", "")).strip(),
                    },
                },
                created_at=created_at,
            )
        )
        self._record_decision(payload)
        return payload

    def record_review(
        self,
        *,
        decision_id: str,
        reviewer: str,
        outcome: str,
        notes: str = "",
        rollback_executed: bool = False,
        doctrine_ready: bool | None = None,
    ) -> dict[str, Any]:
        traces = self.store.list_traces(limit=400)
        trace = next((item for item in traces if str(item.get("decision_id", "")).strip() == decision_id.strip()), None)
        if trace is None:
            raise KeyError(f"Unknown supervision decision '{decision_id}'.")
        review = {
            "review_id": f"rev-{uuid.uuid4().hex[:12]}",
            "decision_id": decision_id.strip(),
            "reviewer": reviewer.strip(),
            "outcome": outcome.strip().lower(),
            "notes": notes.strip(),
            "rollback_executed": bool(rollback_executed),
            "doctrine_ready": bool(doctrine_ready) if doctrine_ready is not None else outcome.strip().lower() == "approved",
            "agent_id": str(trace.get("agent_id", "")).strip(),
            "lane_id": str(trace.get("lane_id", "")).strip(),
            "trust_zone_id": str(trace.get("trust_zone_id", "")).strip(),
            "action_type": str(trace.get("action_type", "")).strip(),
            "resolution": str(trace.get("resolution", "")).strip(),
            "created_at": _now_iso(),
        }
        reviews = self.store.list_reviews()
        reviews.append(review)
        self.store.save_reviews(reviews)
        self.audit_log.log_event("supervision-review", review)
        return review

    def refresh_doctrine_candidates(self, *, synthesized_by: str = "system-steward") -> dict[str, Any]:
        contracts = {
            str(item.get("agent_id", "")).strip(): item
            for item in self.store.list_contracts()
            if isinstance(item, dict)
        }
        grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}
        for item in self.store.list_reviews():
            key = (
                str(item.get("agent_id", "")).strip(),
                str(item.get("lane_id", "")).strip(),
                str(item.get("trust_zone_id", "")).strip(),
                str(item.get("action_type", "")).strip(),
                str(item.get("resolution", "")).strip(),
            )
            grouped.setdefault(key, []).append(item)

        candidates: list[dict[str, Any]] = []
        for (agent_id, lane_id, trust_zone_id, action_type, resolution), reviews in grouped.items():
            contract = contracts.get(agent_id, {})
            thresholds = dict(contract.get("doctrine_scope", {}))
            min_reviewed_successes = int(thresholds.get("min_reviewed_successes", 3) or 3)
            max_reversals = int(thresholds.get("max_reversals", 0) or 0)
            min_success_rate = float(thresholds.get("min_success_rate", 0.95) or 0.95)
            approved = [item for item in reviews if str(item.get("outcome", "")).strip().lower() == "approved"]
            doctrine_ready = [item for item in approved if bool(item.get("doctrine_ready"))]
            reversals = [item for item in reviews if bool(item.get("rollback_executed"))]
            success_rate = (len(approved) / len(reviews)) if reviews else 0.0
            if len(doctrine_ready) < min_reviewed_successes:
                continue
            if len(reversals) > max_reversals:
                continue
            if success_rate < min_success_rate:
                continue
            candidate_id = f"supervision-{agent_id}-{lane_id}-{trust_zone_id}-{action_type}-{resolution}".replace("_", "-")
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "rule_id": candidate_id,
                    "title": f"{agent_id} {action_type} {resolution} doctrine",
                    "summary": (
                        f"{agent_id} may handle '{action_type}' as '{resolution}' in lane '{lane_id}' "
                        f"inside trust zone '{trust_zone_id}' because reviewed success repeated without unsafe reversals."
                    ),
                    "kind": "bounded-autonomy",
                    "status": "candidate",
                    "source": "supervision",
                    "domains": [lane_id],
                    "agent_ids": [agent_id],
                    "actors": [],
                    "policy_effects": {
                        "action_type": action_type,
                        "resolution": resolution,
                        "trust_zone_id": trust_zone_id,
                        "requires_review_sampling": True,
                    },
                    "evidence": {
                        "review_count": len(reviews),
                        "approved_count": len(approved),
                        "success_rate": round(success_rate, 4),
                        "rollback_count": len(reversals),
                    },
                    "promotion_reason": "repeated reviewed success",
                }
            )

        state = self.doctrine_store.merge_candidates(
            candidates,
            synthesis_meta={
                "source": "supervision",
                "generated_by": synthesized_by,
                "candidate_count": len(candidates),
            },
            source="supervision",
        )
        self.audit_log.log_event(
            "supervision-doctrine-refresh",
            {
                "generated_by": synthesized_by,
                "candidate_count": len(candidates),
                "generated_at": state.get("generated_at", ""),
            },
        )
        return {
            "generated_at": state.get("generated_at", ""),
            "candidate_count": len(candidates),
            "candidates": candidates,
        }

    def _apply_doctrine_effects(
        self,
        rules: list[dict[str, Any]],
        action_type: str,
        reasons: list[str],
    ) -> dict[str, bool]:
        effects = {"force_stage": False, "force_escalate": False}
        for item in rules:
            policy_effects = dict(item.get("policy_effects", {}))
            if str(policy_effects.get("action_type", "")).strip() not in {"", action_type}:
                continue
            resolution = str(policy_effects.get("resolution", "")).strip().lower()
            if resolution == "stage":
                effects["force_stage"] = True
                reasons.append(f"Doctrine rule '{item.get('rule_id', '')}' keeps this action staged.")
            if resolution == "escalate":
                effects["force_escalate"] = True
                reasons.append(f"Doctrine rule '{item.get('rule_id', '')}' forces escalation.")
        return effects

    def _record_decision(self, payload: dict[str, Any]) -> None:
        self.store.append_trace(payload)
        self.audit_log.log_event("supervision-decision", payload)
