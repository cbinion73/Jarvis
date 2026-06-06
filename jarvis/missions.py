from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agentic import AgentDefinition, AgentRegistry
from .audit import ApprovalStore
from .models import (
    AgentDecisionRecord,
    AgentDelegationRecord,
    AgentEscalationRecord,
    AgentHandoffRecord,
    AgentHypothesisRecord,
    AgentMessage,
    AgentTaskRef,
    AgentWorkState,
    DuplicateWorkSuppressionRecord,
    ApprovalRequest,
    MissionActionDecision,
    MissionDossier,
    MissionEvidence,
    MissionOutput,
    MissionSubtask,
    OwnershipTransferRecord,
    TaskAgentProfile,
    TrustZone,
)
from .persistence import atomic_write_json
from .trust import TrustSupport


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    lowered = "".join(ch if ch.isalnum() else "-" for ch in value.strip().lower())
    cleaned = "-".join(part for part in lowered.split("-") if part)
    return cleaned or "agent"


def _deep_copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value))


class MissionStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.dossiers_path = self.root / "dossiers.json"
        self.task_agents_path = self.root / "task_agents.json"

    def _load_records(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return payload if isinstance(payload, list) else []

    def _save_records(self, path: Path, records: list[dict[str, Any]]) -> None:
        atomic_write_json(path, records)

    def list_dossiers(self) -> list[dict[str, Any]]:
        return self._load_records(self.dossiers_path)

    def save_dossiers(self, records: list[dict[str, Any]]) -> None:
        self._save_records(self.dossiers_path, records)

    def list_task_agents(self) -> list[dict[str, Any]]:
        return self._load_records(self.task_agents_path)

    def save_task_agents(self, records: list[dict[str, Any]]) -> None:
        self._save_records(self.task_agents_path, records)


class MissionSupport:
    LOW_RISK_ACTIONS = {
        "calendar-triage",
        "email-draft",
        "reminder",
        "family-alert",
        "route-weather-check",
        "briefing-generation",
    }
    STAGED_ACTIONS = {
        "send-approved-contact-email",
        "external-commitment",
        "book-travel",
        "purchase",
        "finance-move",
    }
    BLOCKED_ACTIONS = {
        "payment-submission",
        "trade-execution",
        "medical-action",
    }
    TEMPLATE_LIBRARY: dict[str, dict[str, Any]] = {
        "researcher": {
            "label": "Mission Researcher",
            "mission_roles": ["evidence-gathering", "comparison"],
            "allowed_tools": ["research", "briefings", "weather", "calendar"],
            "success_metrics": ["Useful evidence", "Clear comparisons", "Lower ambiguity"],
        },
        "planner": {
            "label": "Mission Planner",
            "mission_roles": ["sequencing", "next-actions"],
            "allowed_tools": ["planning", "calendar", "route-weather", "briefings"],
            "success_metrics": ["Clean plan", "Good sequencing", "Fewer dropped steps"],
        },
        "triager": {
            "label": "Mission Triager",
            "mission_roles": ["sorting", "prioritization"],
            "allowed_tools": ["triage", "calendar", "gmail", "briefings"],
            "success_metrics": ["Cleaner queue", "Better priority order", "Less noise"],
        },
        "communicator": {
            "label": "Mission Communicator",
            "mission_roles": ["drafting", "handoffs"],
            "allowed_tools": ["drafts", "gmail", "briefings"],
            "success_metrics": ["Cleaner drafts", "Better tone", "Faster outbound prep"],
        },
        "analyst": {
            "label": "Mission Analyst",
            "mission_roles": ["assessment", "recommendation"],
            "allowed_tools": ["analysis", "comparisons", "briefings"],
            "success_metrics": ["Sharper recommendations", "Clearer tradeoffs", "Lower confusion"],
        },
        "domain-specialist": {
            "label": "Mission Specialist",
            "mission_roles": ["specialist-support"],
            "allowed_tools": ["briefings", "planning", "analysis"],
            "success_metrics": ["Domain fit", "Useful specialist output", "Reduced manual work"],
        },
    }
    TRUST_ZONE_DEFAULTS = [
        TrustZone(
            zone_id="family-bmad.personal-local",
            name="Personal Local",
            zone_type="local",
            resource_scope={"systems": ["jarvis"], "data_classes": ["personal_context", "local_notes"]},
            allowed_actions=["observe", "classify", "draft", "brief", "reminder"],
            authority_stage="draft",
            approval_mode="bounded-autonomy",
            audit_mode="standard",
            promotion_rules={"eligible_next_stages": ["sandbox_live"], "minimum_success_rate": 0.97, "minimum_review_count": 15},
            demotion_rules={"triggers": ["boundary_violation", "manual_override"], "fallback_stage": "draft"},
            status="active",
            description="Local personal operations that can usually execute quietly.",
            reporting_cadence="on_change",
        ),
        TrustZone(
            zone_id="family-bmad.family-ops",
            name="Family Ops",
            zone_type="household",
            resource_scope={"systems": ["jarvis", "weather", "calendar"], "data_classes": ["household", "weather", "family_schedule"]},
            allowed_actions=["observe", "classify", "draft", "brief", "alert", "route-check", "reminder"],
            authority_stage="draft",
            approval_mode="bounded-autonomy",
            audit_mode="standard",
            promotion_rules={"eligible_next_stages": ["sandbox_live"], "minimum_success_rate": 0.98, "minimum_review_count": 20},
            demotion_rules={"triggers": ["boundary_violation", "manual_override"], "fallback_stage": "stage_alert"},
            status="active",
            description="Family coordination, alerts, and calm-operating work.",
            reporting_cadence="event_driven",
        ),
        TrustZone(
            zone_id="family-bmad.communications",
            name="Communications",
            zone_type="communications",
            resource_scope={"systems": ["gmail", "calendar"], "data_classes": ["messages", "meeting_context"]},
            allowed_actions=["observe", "classify", "draft", "stage", "alert", "send-approved-contact-email"],
            authority_stage="stage_alert",
            approval_mode="stage_and_alert",
            audit_mode="detailed",
            promotion_rules={"eligible_next_stages": ["stage_alert"], "minimum_success_rate": 0.99, "minimum_review_count": 30},
            demotion_rules={"triggers": ["hidden_action", "manual_override"], "fallback_stage": "draft"},
            status="active",
            description="Communications should be staged cleanly and only auto-send within tight policy.",
            reporting_cadence="per_action",
        ),
        TrustZone(
            zone_id="family-bmad.finances",
            name="Finances",
            zone_type="finance",
            resource_scope={"systems": ["finance"], "data_classes": ["financial", "household_budget"]},
            allowed_actions=["observe", "classify", "draft", "brief"],
            authority_stage="draft",
            approval_mode="explicit-approval",
            audit_mode="detailed",
            promotion_rules={"eligible_next_stages": ["draft"], "minimum_success_rate": 1.0, "minimum_review_count": 50},
            demotion_rules={"triggers": ["manual_override"], "fallback_stage": "draft"},
            status="active",
            description="Financial work stays staged unless explicitly approved.",
            reporting_cadence="per_action",
        ),
        TrustZone(
            zone_id="family-bmad.external-commitments",
            name="External Commitments",
            zone_type="external",
            resource_scope={"systems": ["gmail", "calendar", "travel"], "data_classes": ["external_commitments", "public_commitments"]},
            allowed_actions=["observe", "classify", "draft", "stage", "alert"],
            authority_stage="stage_alert",
            approval_mode="stage_and_alert",
            audit_mode="detailed",
            promotion_rules={"eligible_next_stages": ["stage_alert"], "minimum_success_rate": 0.99, "minimum_review_count": 40},
            demotion_rules={"triggers": ["manual_override", "hidden_action"], "fallback_stage": "draft"},
            status="active",
            description="Commitments that affect others or spend reputation get staged first.",
            reporting_cadence="per_action",
        ),
    ]

    def __init__(
        self,
        store: MissionStore,
        *,
        trust_support: TrustSupport,
        approval_store: ApprovalStore,
        agent_registry: AgentRegistry,
    ) -> None:
        self.store = store
        self.trust_support = trust_support
        self.approval_store = approval_store
        self.agent_registry = agent_registry
        self._bootstrap_trust_zones()

    def _bootstrap_trust_zones(self) -> None:
        now = _now_iso()
        for zone in self.TRUST_ZONE_DEFAULTS:
            existing = self.trust_support.get_trust_zone(zone.zone_id)
            payload = asdict(zone)
            payload["created_at"] = str((existing or {}).get("created_at", "")).strip() or now
            payload["updated_at"] = now
            self.trust_support.upsert_trust_zone(TrustZone(**payload))

    def _agent_display_payload(self, agent_id: str) -> dict[str, Any]:
        task_agent = self.get_task_agent(agent_id)
        if task_agent is not None:
            return {
                "agent_id": str(task_agent.get("agent_id", "")).strip(),
                "label": str(task_agent.get("label", agent_id)).strip() or agent_id,
                "class_type": str(task_agent.get("class_type", "task-agent")).strip() or "task-agent",
                "domain": str(task_agent.get("domain", "general")).strip() or "general",
                "trust_zone": str(task_agent.get("trust_zone", "family-bmad.personal-local")).strip() or "family-bmad.personal-local",
                "promotion_status": str(task_agent.get("promotion_status", "ephemeral")).strip() or "ephemeral",
                "mission_roles": list(task_agent.get("mission_roles", [])),
                "allowed_tools": list(task_agent.get("allowed_tools", [])),
                "autonomy_posture": str(task_agent.get("autonomy_level", "bounded-autonomy")).strip() or "bounded-autonomy",
                "purpose": str(task_agent.get("purpose", "")).strip(),
            }
        core_agent = self.agent_registry.by_id().get(agent_id)
        if core_agent is None:
            return {
                "agent_id": agent_id,
                "label": agent_id,
                "class_type": "unknown-agent",
                "domain": "general",
                "trust_zone": "family-bmad.personal-local",
                "promotion_status": "unknown",
                "mission_roles": [],
                "allowed_tools": [],
                "autonomy_posture": "bounded-autonomy",
                "purpose": "",
            }
        return {
            "agent_id": core_agent.agent_id,
            "label": core_agent.label,
            "class_type": core_agent.agent_class,
            "domain": core_agent.primary_domain,
            "trust_zone": core_agent.trust_zone,
            "promotion_status": core_agent.promotion_status,
            "mission_roles": list(core_agent.mission_roles),
            "allowed_tools": list(core_agent.allowed_tools),
            "autonomy_posture": core_agent.autonomy_posture,
            "purpose": core_agent.purpose,
        }

    def _trim_records(self, items: list[Any], limit: int = 8) -> list[Any]:
        return items[-max(1, int(limit)) :]

    def _message(
        self,
        *,
        kind: str,
        from_agent: str,
        to_agent: str,
        subject: str,
        summary: str,
        task_id: str = "",
        status: str = "pending",
        created_at: str = "",
    ) -> dict[str, Any]:
        return asdict(
            AgentMessage(
                entry_id=str(uuid.uuid4()),
                kind=kind,
                status=status,
                from_agent=from_agent,
                to_agent=to_agent,
                subject=subject,
                summary=summary,
                task_id=task_id,
                created_at=created_at or _now_iso(),
            )
        )

    def _task_ref(
        self,
        *,
        title: str,
        status: str,
        summary: str,
        source: str,
        updated_at: str,
        task_id: str = "",
        dependencies: list[str] | None = None,
        handoff_id: str = "",
    ) -> dict[str, Any]:
        return asdict(
            AgentTaskRef(
                task_id=task_id or f"task-{uuid.uuid4().hex[:10]}",
                title=title,
                status=status,
                summary=summary,
                source=source,
                updated_at=updated_at,
                dependencies=list(dependencies or []),
                handoff_id=handoff_id,
            )
        )

    def _decision(self, *, summary: str, rationale: str, task_id: str = "", created_at: str = "") -> dict[str, Any]:
        return asdict(
            AgentDecisionRecord(
                decision_id=str(uuid.uuid4()),
                summary=summary,
                rationale=rationale,
                task_id=task_id,
                created_at=created_at or _now_iso(),
            )
        )

    def _hypothesis(
        self,
        *,
        summary: str,
        task_id: str = "",
        confidence: str = "working",
        status: str = "active",
        timestamp: str = "",
    ) -> dict[str, Any]:
        when = timestamp or _now_iso()
        return asdict(
            AgentHypothesisRecord(
                hypothesis_id=str(uuid.uuid4()),
                summary=summary,
                confidence=confidence,
                status=status,
                task_id=task_id,
                created_at=when,
                updated_at=when,
            )
        )

    def _new_workspace(
        self,
        *,
        mission_id: str,
        agent_id: str,
        role: str,
        ownership_mode: str,
        status: str,
        current_focus: str,
        inbox: list[dict[str, Any]] | None = None,
        active_tasks: list[dict[str, Any]] | None = None,
        pending_reviews: list[dict[str, Any]] | None = None,
        decisions: list[dict[str, Any]] | None = None,
        hypotheses: list[dict[str, Any]] | None = None,
        updated_at: str = "",
    ) -> dict[str, Any]:
        return asdict(
            AgentWorkState(
                agent_id=agent_id,
                mission_id=mission_id,
                role=role,
                status=status,
                ownership_mode=ownership_mode,
                current_focus=current_focus,
                inbox=list(inbox or []),
                active_tasks=list(active_tasks or []),
                pending_reviews=list(pending_reviews or []),
                recent_decisions=list(decisions or []),
                current_hypotheses=list(hypotheses or []),
                updated_at=updated_at or _now_iso(),
            )
        )

    def _normalize_work_states(self, dossier: dict[str, Any]) -> dict[str, Any]:
        now = str(dossier.get("updated_at", "")).strip() or _now_iso()
        work_states = dict(dossier.get("agent_work_states") or {})
        title = str(dossier.get("title", "Mission")).strip() or "Mission"
        mission_id = str(dossier.get("mission_id", "")).strip()
        selected = [str(agent_id).strip() for agent_id in list(dossier.get("selected_agents", [])) if str(agent_id).strip()]
        for index, agent_id in enumerate(selected):
            details = self._agent_display_payload(agent_id)
            default_task = self._task_ref(
                title="Support mission continuity",
                status="active" if index == 0 else "queued",
                summary=f"Advance {title.lower()} without losing partial work or ownership clarity.",
                source="mission-bootstrap",
                updated_at=now,
            )
            default_review = self._task_ref(
                title="Review mission brief",
                status="pending",
                summary="Inspect the mission frame, constraints, and current evidence.",
                source="mission-bootstrap",
                updated_at=now,
            )
            initial_message = self._message(
                kind="mission-brief",
                from_agent="jarvis-orchestrator",
                to_agent=agent_id,
                subject=title,
                summary=f"You are attached to {title}. Keep continuity, ownership, and review posture explicit.",
                created_at=now,
                status="delivered",
            )
            state = dict(work_states.get(agent_id) or {})
            if not state:
                work_states[agent_id] = self._new_workspace(
                    mission_id=mission_id,
                    agent_id=agent_id,
                    role=str((details.get("mission_roles") or ["support"])[0]),
                    ownership_mode="lead" if index == 0 else "supporting",
                    status="active" if index == 0 else "ready",
                    current_focus=title,
                    inbox=[initial_message],
                    active_tasks=[default_task] if index == 0 else [],
                    pending_reviews=[] if index == 0 else [default_review],
                    decisions=[self._decision(summary="Mission accepted into workspace", rationale="Mission dossier created and assigned.", created_at=now)],
                    hypotheses=[self._hypothesis(summary=f"{title} likely needs {details.get('label', agent_id)} on {details.get('domain', 'general')} continuity.", timestamp=now)],
                    updated_at=now,
                )
                continue
            state.setdefault("mission_id", mission_id)
            state.setdefault("agent_id", agent_id)
            state.setdefault("role", str((details.get("mission_roles") or ["support"])[0]))
            state.setdefault("status", "ready")
            state.setdefault("ownership_mode", "lead" if index == 0 else "supporting")
            state.setdefault("current_focus", title)
            state["inbox"] = list(state.get("inbox") or []) or [initial_message]
            state["outbox"] = list(state.get("outbox") or [])
            state["active_tasks"] = list(state.get("active_tasks") or [])
            state["blocked_tasks"] = list(state.get("blocked_tasks") or [])
            state["pending_reviews"] = list(state.get("pending_reviews") or [])
            state["recent_decisions"] = self._trim_records(list(state.get("recent_decisions") or []))
            state["current_hypotheses"] = self._trim_records(list(state.get("current_hypotheses") or []))
            state.setdefault("last_handoff_at", "")
            state["updated_at"] = str(state.get("updated_at", "")).strip() or now
            work_states[agent_id] = state
        dossier["agent_work_states"] = work_states
        dossier["handoffs"] = list(dossier.get("handoffs") or [])
        dossier["delegations"] = list(dossier.get("delegations") or [])
        dossier["escalations"] = list(dossier.get("escalations") or [])
        dossier["ownership_transfers"] = list(dossier.get("ownership_transfers") or [])
        dossier["duplicate_suppressions"] = list(dossier.get("duplicate_suppressions") or [])
        return dossier

    def _load_mission(self, mission_id: str) -> dict[str, Any] | None:
        mission_key = mission_id.strip()
        if not mission_key:
            return None
        records = self.store.list_dossiers()
        for index, item in enumerate(records):
            if str(item.get("mission_id", "")).strip() != mission_key:
                continue
            normalized = self._normalize_work_states(dict(item))
            if normalized != item:
                records[index] = normalized
                self.store.save_dossiers(records)
            return normalized
        return None

    def list_missions(self, *, actor: str = "", include_completed: bool = True, limit: int = 20) -> list[dict[str, Any]]:
        records = [self._normalize_work_states(dict(item)) for item in self.store.list_dossiers() if isinstance(item, dict)]
        actor_key = actor.strip().lower()
        if actor_key:
            records = [item for item in records if str(item.get("actor", "")).strip().lower() == actor_key]
        if not include_completed:
            records = [item for item in records if str(item.get("status", "")).strip().lower() not in {"completed", "archived", "retired"}]
        records.sort(key=lambda item: str(item.get("updated_at", "")).strip(), reverse=True)
        return records[:limit]

    def get_mission(self, mission_id: str) -> dict[str, Any] | None:
        return self._load_mission(mission_id)

    def save_mission(self, payload: dict[str, Any]) -> dict[str, Any]:
        records = self.store.list_dossiers()
        payload = self._normalize_work_states(dict(payload))
        mission_id = str(payload.get("mission_id", "")).strip()
        if not mission_id:
            raise ValueError("mission_id is required")
        replaced = False
        for index, item in enumerate(records):
            if str(item.get("mission_id", "")).strip() == mission_id:
                records[index] = payload
                replaced = True
                break
        if not replaced:
            records.append(payload)
        self.store.save_dossiers(records)
        return payload

    def update_mission_status(self, mission_id: str, status: str, *, note: str = "") -> dict[str, Any]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        resolved_status = status.strip() or dossier.get("status", "active")
        dossier["status"] = resolved_status
        dossier["updated_at"] = _now_iso()
        if note.strip():
            evidence = list(dossier.get("evidence", []))
            evidence.append(
                asdict(
                    MissionEvidence(
                        evidence_id=str(uuid.uuid4()),
                        source_agent="jarvis-orchestrator",
                        source_system="mission-control",
                        kind="status-update",
                        title="Mission status updated",
                        summary=note.strip(),
                        detail=note.strip(),
                        timestamp=dossier["updated_at"],
                    )
                )
            )
            dossier["evidence"] = evidence
        work_states = dict(dossier.get("agent_work_states") or {})
        for agent_id, state in work_states.items():
            state = dict(state or {})
            state["updated_at"] = dossier["updated_at"]
            if resolved_status.lower() == "completed":
                state["status"] = "completed"
                state["pending_reviews"] = []
            elif resolved_status.lower() in {"blocked", "abandoned"} and str(state.get("status", "")).strip().lower() != "completed":
                state["status"] = "blocked"
            work_states[agent_id] = state
        dossier["agent_work_states"] = work_states
        task_agents = {item["agent_id"]: item for item in self.list_task_agents(limit=200)}
        if resolved_status.lower() == "completed":
            for agent_id in list(dossier.get("selected_agents", [])):
                if agent_id in task_agents:
                    self.record_task_agent_outcome(agent_id, succeeded=True)
        elif resolved_status.lower() in {"blocked", "abandoned"}:
            for agent_id in list(dossier.get("selected_agents", [])):
                if agent_id in task_agents:
                    self.record_task_agent_outcome(agent_id, succeeded=False)
        return self.save_mission(dossier)

    def mission_work_state(self, mission_id: str) -> dict[str, Any]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        work_states = dict(dossier.get("agent_work_states") or {})
        handoffs = list(dossier.get("handoffs") or [])
        ownership_transfers = list(dossier.get("ownership_transfers") or [])
        pending_handoffs = [
            item
            for item in handoffs
            if str(item.get("status", "")).strip().lower() in {"pending", "pending-acceptance", "accepted"}
        ]
        pending_transfers = [
            item
            for item in ownership_transfers
            if str(item.get("status", "")).strip().lower() in {"pending", "pending-acceptance"}
        ]
        return {
            "mission_id": str(dossier.get("mission_id", "")).strip(),
            "title": str(dossier.get("title", "")).strip(),
            "status": str(dossier.get("status", "")).strip(),
            "generated_at": _now_iso(),
            "summary": {
                "agents": len(work_states),
                "active_tasks": sum(len(list((state or {}).get("active_tasks") or [])) for state in work_states.values()),
                "blocked_tasks": sum(len(list((state or {}).get("blocked_tasks") or [])) for state in work_states.values()),
                "pending_reviews": sum(len(list((state or {}).get("pending_reviews") or [])) for state in work_states.values()),
                "pending_handoffs": len(pending_handoffs),
                "pending_transfers": len(pending_transfers),
                "escalations": len([item for item in list(dossier.get("escalations") or []) if str(item.get("status", "")).strip().lower() == "open"]),
                "duplicate_suppressions": len(list(dossier.get("duplicate_suppressions") or [])),
            },
            "agent_work_states": work_states,
            "handoffs": handoffs,
            "delegations": list(dossier.get("delegations") or []),
            "escalations": list(dossier.get("escalations") or []),
            "ownership_transfers": ownership_transfers,
            "duplicate_suppressions": list(dossier.get("duplicate_suppressions") or []),
        }

    def update_agent_work_state(
        self,
        mission_id: str,
        agent_id: str,
        *,
        status: str = "",
        current_focus: str = "",
        ownership_mode: str = "",
        note: str = "",
        decision: str = "",
        rationale: str = "",
        hypothesis: str = "",
    ) -> dict[str, Any]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        work_states = dict(dossier.get("agent_work_states") or {})
        if agent_id not in work_states:
            raise KeyError(f"Unknown mission agent: {agent_id}")
        state = dict(work_states.get(agent_id) or {})
        now = _now_iso()
        if status.strip():
            state["status"] = status.strip()
        if current_focus.strip():
            state["current_focus"] = current_focus.strip()
        if ownership_mode.strip():
            state["ownership_mode"] = ownership_mode.strip()
        if note.strip():
            state["inbox"] = self._trim_records(
                list(state.get("inbox") or [])
                + [
                    self._message(
                        kind="mission-note",
                        from_agent="jarvis-orchestrator",
                        to_agent=agent_id,
                        subject=str(dossier.get("title", "Mission")).strip() or "Mission",
                        summary=note.strip(),
                        created_at=now,
                        status="delivered",
                    )
                ]
            )
        if decision.strip():
            state["recent_decisions"] = self._trim_records(
                list(state.get("recent_decisions") or [])
                + [self._decision(summary=decision.strip(), rationale=rationale.strip() or decision.strip(), created_at=now)]
            )
        if hypothesis.strip():
            state["current_hypotheses"] = self._trim_records(
                list(state.get("current_hypotheses") or [])
                + [self._hypothesis(summary=hypothesis.strip(), timestamp=now)]
            )
        state["updated_at"] = now
        work_states[agent_id] = state
        dossier["agent_work_states"] = work_states
        dossier["updated_at"] = now
        return self.save_mission(dossier)

    def create_agent_handoff(
        self,
        mission_id: str,
        *,
        from_agent: str,
        to_agent: str,
        task_title: str,
        summary: str,
        context: str = "",
        partial_work: str = "",
        delegation_reason: str = "",
        expected_result: str = "",
        transfer_ownership: bool = False,
        duplicate_key: str = "",
    ) -> dict[str, Any]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        work_states = dict(dossier.get("agent_work_states") or {})
        if from_agent not in work_states or to_agent not in work_states:
            raise KeyError("Both from_agent and to_agent must be attached to the mission.")
        now = _now_iso()
        from_state = dict(work_states[from_agent] or {})
        to_state = dict(work_states[to_agent] or {})
        task = self._task_ref(
            title=task_title.strip() or "Delegated task",
            status="handoff-pending" if transfer_ownership else "delegated",
            summary=summary.strip() or "Continue the delegated task carefully.",
            source=from_agent,
            updated_at=now,
        )
        handoff = asdict(
            AgentHandoffRecord(
                handoff_id=str(uuid.uuid4()),
                mission_id=mission_id,
                from_agent=from_agent,
                to_agent=to_agent,
                task_id=str(task.get("task_id", "")).strip(),
                handoff_kind="ownership-transfer" if transfer_ownership else "delegation",
                status="pending-acceptance" if transfer_ownership else "pending",
                summary=summary.strip() or "Continue the delegated task carefully.",
                context=context.strip(),
                partial_work=partial_work.strip(),
                duplicate_key=duplicate_key.strip(),
                requires_acceptance=transfer_ownership,
                created_at=now,
            )
        )
        delegation = asdict(
            AgentDelegationRecord(
                delegation_id=str(uuid.uuid4()),
                mission_id=mission_id,
                delegator_agent=from_agent,
                delegate_agent=to_agent,
                task_id=str(task.get("task_id", "")).strip(),
                scope=task_title.strip() or "Delegated task",
                rationale=delegation_reason.strip() or summary.strip() or "Shift this work to the better-positioned agent.",
                expected_result=expected_result.strip() or "Return clean progress without duplicating work.",
                status="pending-acceptance" if transfer_ownership else "active",
                handoff_id=str(handoff.get("handoff_id", "")).strip(),
                created_at=now,
            )
        )
        dossier["handoffs"] = list(dossier.get("handoffs") or []) + [handoff]
        dossier["delegations"] = list(dossier.get("delegations") or []) + [delegation]
        from_state["outbox"] = self._trim_records(
            list(from_state.get("outbox") or [])
            + [
                self._message(
                    kind="handoff-outbound",
                    from_agent=from_agent,
                    to_agent=to_agent,
                    subject=task_title.strip() or "Delegated task",
                    summary=summary.strip() or "Delegated task sent.",
                    task_id=str(task.get("task_id", "")).strip(),
                    created_at=now,
                    status="sent",
                )
            ]
        )
        to_state["inbox"] = self._trim_records(
            list(to_state.get("inbox") or [])
            + [
                self._message(
                    kind="handoff-inbound",
                    from_agent=from_agent,
                    to_agent=to_agent,
                    subject=task_title.strip() or "Delegated task",
                    summary=summary.strip() or "New delegated task waiting.",
                    task_id=str(task.get("task_id", "")).strip(),
                    created_at=now,
                    status="pending-acceptance" if transfer_ownership else "delivered",
                )
            ]
        )
        to_state["pending_reviews"] = self._trim_records(list(to_state.get("pending_reviews") or []) + [task])
        if transfer_ownership:
            transfer = asdict(
                OwnershipTransferRecord(
                    transfer_id=str(uuid.uuid4()),
                    mission_id=mission_id,
                    task_id=str(task.get("task_id", "")).strip(),
                    from_agent=from_agent,
                    to_agent=to_agent,
                    reason=delegation_reason.strip() or summary.strip() or "Ownership moved to the better-positioned agent.",
                    status="pending-acceptance",
                    continuity_notes=partial_work.strip() or context.strip(),
                    created_at=now,
                )
            )
            dossier["ownership_transfers"] = list(dossier.get("ownership_transfers") or []) + [transfer]
            from_state["blocked_tasks"] = self._trim_records(
                list(from_state.get("blocked_tasks") or [])
                + [
                    self._task_ref(
                        title=task_title.strip() or "Delegated task",
                        status="awaiting-transfer-acceptance",
                        summary="Ownership is not released until the receiving agent acknowledges the handoff.",
                        source=to_agent,
                        updated_at=now,
                        task_id=str(task.get("task_id", "")).strip(),
                        handoff_id=str(handoff.get("handoff_id", "")).strip(),
                    )
                ]
            )
        else:
            from_state["active_tasks"] = self._trim_records(list(from_state.get("active_tasks") or []) + [task])
        from_state["last_handoff_at"] = now
        to_state["last_handoff_at"] = now
        from_state["updated_at"] = now
        to_state["updated_at"] = now
        work_states[from_agent] = from_state
        work_states[to_agent] = to_state
        dossier["agent_work_states"] = work_states
        dossier["updated_at"] = now
        return self.save_mission(dossier)

    def acknowledge_agent_handoff(
        self,
        mission_id: str,
        handoff_id: str,
        *,
        receiving_agent: str,
        accepted: bool = True,
        note: str = "",
    ) -> dict[str, Any]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        work_states = dict(dossier.get("agent_work_states") or {})
        if receiving_agent not in work_states:
            raise KeyError(f"Unknown mission agent: {receiving_agent}")
        now = _now_iso()
        target_handoff: dict[str, Any] | None = None
        handoffs: list[dict[str, Any]] = []
        for item in list(dossier.get("handoffs") or []):
            record = dict(item or {})
            if str(record.get("handoff_id", "")).strip() == handoff_id.strip():
                target_handoff = record
            handoffs.append(record)
        if target_handoff is None:
            raise KeyError(f"Unknown handoff: {handoff_id}")
        if str(target_handoff.get("to_agent", "")).strip() != receiving_agent:
            raise ValueError("Only the receiving agent may acknowledge this handoff.")
        target_handoff["status"] = "accepted" if accepted else "rejected"
        target_handoff["acknowledged_at"] = now
        if accepted:
            target_handoff["completed_at"] = now
        for index, item in enumerate(handoffs):
            if str(item.get("handoff_id", "")).strip() == handoff_id.strip():
                handoffs[index] = target_handoff
                break
        dossier["handoffs"] = handoffs
        to_state = dict(work_states[receiving_agent] or {})
        from_agent = str(target_handoff.get("from_agent", "")).strip()
        from_state = dict(work_states.get(from_agent) or {})
        task_id = str(target_handoff.get("task_id", "")).strip()
        if accepted:
            accepted_task = self._task_ref(
                title=str(target_handoff.get("summary", "Accepted handoff")).strip(),
                status="active",
                summary=note.strip() or str(target_handoff.get("partial_work", "")).strip() or str(target_handoff.get("context", "")).strip(),
                source=from_agent,
                updated_at=now,
                task_id=task_id,
                handoff_id=handoff_id.strip(),
            )
            to_state["active_tasks"] = self._trim_records(list(to_state.get("active_tasks") or []) + [accepted_task])
            to_state["pending_reviews"] = [
                item for item in list(to_state.get("pending_reviews") or []) if str((item or {}).get("task_id", "")).strip() != task_id
            ]
            to_state["recent_decisions"] = self._trim_records(
                list(to_state.get("recent_decisions") or [])
                + [self._decision(summary="Accepted handoff", rationale=note.strip() or "Receiving agent accepted delegated partial work.", task_id=task_id, created_at=now)]
            )
            for transfer in list(dossier.get("ownership_transfers") or []):
                if str(transfer.get("task_id", "")).strip() != task_id or str(transfer.get("to_agent", "")).strip() != receiving_agent:
                    continue
                transfer["status"] = "accepted"
                transfer["safe_to_release"] = True
                transfer["accepted_at"] = now
                from_state["blocked_tasks"] = [
                    item for item in list(from_state.get("blocked_tasks") or []) if str((item or {}).get("task_id", "")).strip() != task_id
                ]
                from_state["ownership_mode"] = "supporting"
                to_state["ownership_mode"] = "lead"
            for delegation in list(dossier.get("delegations") or []):
                if str(delegation.get("handoff_id", "")).strip() == handoff_id.strip():
                    delegation["status"] = "accepted"
                    delegation["resolved_at"] = now
        else:
            to_state["pending_reviews"] = [
                item for item in list(to_state.get("pending_reviews") or []) if str((item or {}).get("task_id", "")).strip() != task_id
            ]
            from_state["recent_decisions"] = self._trim_records(
                list(from_state.get("recent_decisions") or [])
                + [self._decision(summary="Handoff rejected", rationale=note.strip() or "Receiving agent rejected the proposed handoff.", task_id=task_id, created_at=now)]
            )
            for transfer in list(dossier.get("ownership_transfers") or []):
                if str(transfer.get("task_id", "")).strip() == task_id and str(transfer.get("to_agent", "")).strip() == receiving_agent:
                    transfer["status"] = "rejected"
            for delegation in list(dossier.get("delegations") or []):
                if str(delegation.get("handoff_id", "")).strip() == handoff_id.strip():
                    delegation["status"] = "rejected"
                    delegation["resolved_at"] = now
        to_state["updated_at"] = now
        from_state["updated_at"] = now
        work_states[receiving_agent] = to_state
        if from_agent:
            work_states[from_agent] = from_state
        dossier["agent_work_states"] = work_states
        dossier["updated_at"] = now
        return self.save_mission(dossier)

    def record_agent_escalation(
        self,
        mission_id: str,
        *,
        from_agent: str,
        to_agent: str,
        severity: str,
        rationale: str,
        requested_action: str,
        task_id: str = "",
    ) -> dict[str, Any]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        work_states = dict(dossier.get("agent_work_states") or {})
        if from_agent not in work_states or to_agent not in work_states:
            raise KeyError("Both escalation agents must be attached to the mission.")
        now = _now_iso()
        escalation = asdict(
            AgentEscalationRecord(
                escalation_id=str(uuid.uuid4()),
                mission_id=mission_id,
                from_agent=from_agent,
                to_agent=to_agent,
                task_id=task_id.strip(),
                severity=severity.strip() or "moderate",
                rationale=rationale.strip(),
                requested_action=requested_action.strip(),
                created_at=now,
            )
        )
        dossier["escalations"] = list(dossier.get("escalations") or []) + [escalation]
        to_state = dict(work_states[to_agent] or {})
        to_state["inbox"] = self._trim_records(
            list(to_state.get("inbox") or [])
            + [
                self._message(
                    kind="escalation",
                    from_agent=from_agent,
                    to_agent=to_agent,
                    subject=requested_action.strip() or "Escalation",
                    summary=rationale.strip() or "Escalation requested.",
                    task_id=task_id.strip(),
                    created_at=now,
                    status="delivered",
                )
            ]
        )
        to_state["pending_reviews"] = self._trim_records(
            list(to_state.get("pending_reviews") or [])
            + [
                self._task_ref(
                    title=requested_action.strip() or "Review escalation",
                    status="pending",
                    summary=rationale.strip() or "Escalation requested.",
                    source=from_agent,
                    updated_at=now,
                    task_id=task_id.strip(),
                )
            ]
        )
        to_state["updated_at"] = now
        work_states[to_agent] = to_state
        dossier["agent_work_states"] = work_states
        dossier["updated_at"] = now
        return self.save_mission(dossier)

    def suppress_duplicate_work(
        self,
        mission_id: str,
        *,
        duplicate_key: str,
        winning_agent: str,
        suppressed_agent: str,
        rationale: str,
        task_title: str = "",
        task_id: str = "",
    ) -> dict[str, Any]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        work_states = dict(dossier.get("agent_work_states") or {})
        if winning_agent not in work_states or suppressed_agent not in work_states:
            raise KeyError("Both winning_agent and suppressed_agent must be attached to the mission.")
        now = _now_iso()
        suppression = asdict(
            DuplicateWorkSuppressionRecord(
                suppression_id=str(uuid.uuid4()),
                mission_id=mission_id,
                duplicate_key=duplicate_key.strip() or f"dup-{uuid.uuid4().hex[:8]}",
                task_id=task_id.strip(),
                winning_agent=winning_agent,
                suppressed_agent=suppressed_agent,
                rationale=rationale.strip(),
                created_at=now,
            )
        )
        dossier["duplicate_suppressions"] = list(dossier.get("duplicate_suppressions") or []) + [suppression]
        suppressed_state = dict(work_states[suppressed_agent] or {})
        suppressed_state["blocked_tasks"] = self._trim_records(
            list(suppressed_state.get("blocked_tasks") or [])
            + [
                self._task_ref(
                    title=task_title.strip() or "Duplicate work suppressed",
                    status="suppressed-duplicate",
                    summary=rationale.strip() or "This work was suppressed to avoid duplicate effort.",
                    source=winning_agent,
                    updated_at=now,
                    task_id=task_id.strip(),
                )
            ]
        )
        suppressed_state["current_hypotheses"] = self._trim_records(
            list(suppressed_state.get("current_hypotheses") or [])
            + [self._hypothesis(summary="Stand down and wait for the owning agent's next artifact before resuming.", task_id=task_id.strip(), timestamp=now)]
        )
        suppressed_state["updated_at"] = now
        work_states[suppressed_agent] = suppressed_state
        dossier["agent_work_states"] = work_states
        dossier["updated_at"] = now
        return self.save_mission(dossier)

    def list_task_agents(self, *, status: str = "", limit: int = 50) -> list[dict[str, Any]]:
        records = self.store.list_task_agents()
        status_key = status.strip().lower()
        if status_key:
            records = [item for item in records if str(item.get("status", "")).strip().lower() == status_key]
        records.sort(key=lambda item: str(item.get("updated_at", "")).strip(), reverse=True)
        return records[:limit]

    def get_task_agent(self, agent_id: str) -> dict[str, Any] | None:
        agent_key = agent_id.strip()
        if not agent_key:
            return None
        for item in self.store.list_task_agents():
            if str(item.get("agent_id", "")).strip() == agent_key:
                return item
        return None

    def save_task_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        records = self.store.list_task_agents()
        agent_id = str(payload.get("agent_id", "")).strip()
        if not agent_id:
            raise ValueError("agent_id is required")
        replaced = False
        for index, item in enumerate(records):
            if str(item.get("agent_id", "")).strip() == agent_id:
                records[index] = payload
                replaced = True
                break
        if not replaced:
            records.append(payload)
        self.store.save_task_agents(records)
        return payload

    def record_task_agent_outcome(self, agent_id: str, *, succeeded: bool) -> dict[str, Any]:
        agent = self.get_task_agent(agent_id)
        if agent is None:
            raise KeyError(f"Unknown task agent: {agent_id}")
        agent["usage_count"] = int(agent.get("usage_count", 0) or 0) + 1
        if succeeded:
            agent["success_count"] = int(agent.get("success_count", 0) or 0) + 1
        agent["last_used_at"] = _now_iso()
        agent["updated_at"] = agent["last_used_at"]
        if self._eligible_for_promotion(agent):
            agent["promotion_candidate"] = True
        return self.save_task_agent(agent)

    def _eligible_for_promotion(self, agent: dict[str, Any]) -> bool:
        return int(agent.get("usage_count", 0) or 0) >= 3 and int(agent.get("success_count", 0) or 0) >= 2

    def promote_task_agent(self, agent_id: str, *, role_name: str = "", policy_assignment: str = "", memory_boundary: str = "", force: bool = False) -> dict[str, Any]:
        agent = self.get_task_agent(agent_id)
        if agent is None:
            raise KeyError(f"Unknown task agent: {agent_id}")
        if not force and not self._eligible_for_promotion(agent):
            raise ValueError("Agent is not yet eligible for promotion.")
        agent["promotion_status"] = "promoted"
        agent["class_type"] = "promoted-family-agent"
        agent["status"] = "active"
        agent["updated_at"] = _now_iso()
        agent["promoted_at"] = agent["updated_at"]
        if role_name.strip():
            agent["label"] = role_name.strip()
        if policy_assignment.strip():
            agent["policy_assignment"] = policy_assignment.strip()
        if memory_boundary.strip():
            agent["memory_boundary"] = memory_boundary.strip()
        return self.save_task_agent(agent)

    def retire_task_agent(self, agent_id: str) -> dict[str, Any]:
        agent = self.get_task_agent(agent_id)
        if agent is None:
            raise KeyError(f"Unknown task agent: {agent_id}")
        agent["status"] = "retired"
        agent["updated_at"] = _now_iso()
        return self.save_task_agent(agent)

    def spawn_task_agent(
        self,
        *,
        mission_id: str,
        domain: str,
        trust_zone: str,
        template_id: str,
        purpose: str,
        mission_roles: list[str] | None = None,
    ) -> dict[str, Any]:
        template = dict(self.TEMPLATE_LIBRARY.get(template_id) or self.TEMPLATE_LIBRARY["domain-specialist"])
        now = _now_iso()
        label = str(template.get("label", "Mission Specialist")).strip()
        agent = TaskAgentProfile(
            agent_id=f"task-{_slugify(domain)}-{uuid.uuid4().hex[:8]}",
            label=label,
            class_type="task-agent",
            origin="mission-synthesis",
            mission_id=mission_id,
            template_id=template_id,
            domain=domain,
            trust_zone=trust_zone,
            autonomy_level="bounded-autonomy",
            promotion_status="ephemeral",
            purpose=purpose.strip() or f"Support the {domain} mission cleanly.",
            mission_roles=list(mission_roles or template.get("mission_roles", ["specialist-support"])),
            allowed_tools=list(template.get("allowed_tools", [])),
            approval_triggers=["external commitments", "payments", "protected communications"],
            success_metrics=list(template.get("success_metrics", [])),
            usage_count=1,
            last_used_at=now,
            memory_boundary=f"mission:{mission_id}",
            created_at=now,
            updated_at=now,
        )
        payload = asdict(agent)
        self.save_task_agent(payload)
        return payload

    def create_mission(
        self,
        *,
        actor: str,
        room: str,
        request: str,
        memory_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _now_iso()
        primary_domain = self._infer_primary_domain(request)
        trust_zone = self._trust_zone_for_domain(primary_domain)
        title = self._mission_title(request, primary_domain)
        brief = self._mission_brief(request, primary_domain)
        mission_id = f"mission-{uuid.uuid4().hex[:10]}"
        selected_agents = self._select_core_agents(request, primary_domain)
        task_template = self._template_for_request(request, primary_domain)
        if self._needs_task_agent(request, primary_domain, selected_agents):
            task_agent = self.spawn_task_agent(
                mission_id=mission_id,
                domain=primary_domain,
                trust_zone=trust_zone,
                template_id=task_template,
                purpose=f"Support {title} with {task_template.replace('-', ' ')} work.",
                mission_roles=["support", "specialist"],
            )
            selected_agents.append(str(task_agent.get("agent_id", "")).strip())
        action_types = self._planned_actions_for_domain(primary_domain, request)
        action_decisions = []
        approval_ids: list[str] = []
        family_impact = self._family_impact(primary_domain, request)
        for action_type in action_types:
            decision = self._resolve_action(actor=actor, room=room, mission_id=mission_id, request=request, action_type=action_type, trust_zone=trust_zone, owner_agent=selected_agents[0] if selected_agents else "jarvis-orchestrator")
            action_decisions.append(MissionActionDecision(**decision))
            if decision.get("approval_request_id"):
                approval_ids.append(str(decision["approval_request_id"]))
        subtasks = [
            MissionSubtask(
                subtask_id=f"sub-{uuid.uuid4().hex[:8]}",
                title="Frame the mission",
                description="Clarify the household objective, constraints, and likely family impact.",
                status="completed",
                owner_agent="jarvis-orchestrator",
                domain=primary_domain,
                trust_zone=trust_zone,
                action_type="mission-framing",
                resolution="auto-execute",
            ),
            MissionSubtask(
                subtask_id=f"sub-{uuid.uuid4().hex[:8]}",
                title="Collect live evidence",
                description="Pull live signals from the selected domain agents before recommending or acting.",
                status="active",
                owner_agent=selected_agents[0] if selected_agents else "jarvis-orchestrator",
                domain=primary_domain,
                trust_zone=trust_zone,
                action_type="collect-evidence",
                resolution="auto-execute",
            ),
            MissionSubtask(
                subtask_id=f"sub-{uuid.uuid4().hex[:8]}",
                title="Stage the next move",
                description="Surface the completed work, blocked work, approvals, and the next clean step.",
                status="pending-approval" if approval_ids else "active",
                owner_agent="jarvis-orchestrator",
                domain=primary_domain,
                trust_zone=trust_zone,
                action_type="stage-next-move",
                resolution="stage-for-approval" if approval_ids else "auto-execute",
                dependencies=[subtask.subtask_id for subtask in []],
            ),
        ]
        evidence = [
            MissionEvidence(
                evidence_id=str(uuid.uuid4()),
                source_agent="jarvis-orchestrator",
                source_system="mission-engine",
                kind="mission-brief",
                title="Mission brief created",
                summary=brief,
                detail=f"Primary domain: {primary_domain}. Trust zone: {trust_zone}.",
                timestamp=now,
            ),
        ]
        dossier = MissionDossier(
            mission_id=mission_id,
            actor=actor,
            room=room,
            request=request.strip(),
            title=title,
            brief=brief,
            status="pending-approval" if approval_ids else "active",
            primary_domain=primary_domain,
            trust_zone=trust_zone,
            autonomy_posture="bounded-autonomy",
            owner_agent="jarvis-orchestrator",
            selected_agents=selected_agents,
            subtasks=subtasks,
            action_decisions=action_decisions,
            evidence=evidence,
            approvals=approval_ids,
            outputs=[],
            follow_ups=self._follow_ups(primary_domain, request),
            agent_work_states={},
            handoffs=[],
            delegations=[],
            escalations=[],
            ownership_transfers=[],
            duplicate_suppressions=[],
            memory_snapshot=dict(memory_snapshot or {}),
            family_impact=family_impact,
            created_at=now,
            updated_at=now,
        )
        payload = self._normalize_work_states(asdict(dossier))
        self.save_mission(payload)
        return payload

    def mission_approvals(self, mission_id: str) -> list[dict[str, Any]]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            return []
        approval_ids = {str(item).strip() for item in list(dossier.get("approvals", [])) if str(item).strip()}
        records = []
        for item in self.approval_store.list_all():
            if str(item.get("request_id", "")).strip() in approval_ids:
                records.append(item)
        return records

    def mission_outputs(self, mission_id: str) -> list[dict[str, Any]]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            return []
        return list(dossier.get("outputs", []))

    def mission_agents(self, mission_id: str) -> list[dict[str, Any]]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            return []
        work_states = dict(dossier.get("agent_work_states") or {})
        result: list[dict[str, Any]] = []
        for agent_id in list(dossier.get("selected_agents", [])):
            profile = self._agent_display_payload(str(agent_id).strip())
            workspace = dict(work_states.get(str(agent_id).strip()) or {})
            profile["workspace_summary"] = {
                "status": str(workspace.get("status", "")).strip(),
                "ownership_mode": str(workspace.get("ownership_mode", "")).strip(),
                "active_tasks": len(list(workspace.get("active_tasks") or [])),
                "blocked_tasks": len(list(workspace.get("blocked_tasks") or [])),
                "pending_reviews": len(list(workspace.get("pending_reviews") or [])),
            }
            result.append(profile)
        return result

    def mission_control_summary(self, *, actor: str = "", limit: int = 12) -> dict[str, Any]:
        missions = self.list_missions(actor=actor, limit=limit)
        active = [item for item in missions if str(item.get("status", "")).strip().lower() not in {"completed", "archived", "retired"}]
        approvals = []
        family_alerts: list[str] = []
        for mission in active:
            approvals.extend(self.mission_approvals(str(mission.get("mission_id", ""))))
            family_alerts.extend(list(mission.get("family_impact", [])))
        workspaces = [dict(state or {}) for mission in active for state in dict(mission.get("agent_work_states") or {}).values()]
        ownership_conflicts = [
            state
            for state in workspaces
            if str(state.get("ownership_mode", "")).strip().lower() == "lead"
        ]
        pending_handoffs = [
            item
            for mission in active
            for item in list(mission.get("handoffs") or [])
            if str(item.get("status", "")).strip().lower() in {"pending", "pending-acceptance", "accepted"}
        ]
        return {
            "generated_at": _now_iso(),
            "summary": {
                "active_missions": len(active),
                "pending_approvals": len([item for item in approvals if str(item.get("status", "")).strip() == "pending"]),
                "task_agents": len([item for item in self.list_task_agents(limit=200) if str(item.get("status", "")).strip().lower() == "active"]),
                "promoted_agents": len([item for item in self.list_task_agents(limit=200) if str(item.get("promotion_status", "")).strip().lower() == "promoted"]),
                "blocked_tasks": sum(len(list(state.get("blocked_tasks") or [])) for state in workspaces),
                "pending_reviews": sum(len(list(state.get("pending_reviews") or [])) for state in workspaces),
                "pending_handoffs": len(pending_handoffs),
                "ownership_conflicts": max(0, len(ownership_conflicts) - len(active)),
            },
            "active_missions": active,
            "pending_approvals": approvals[:10],
            "family_alerts": family_alerts[:10],
            "agent_society": self._agent_society_summary(active),
        }

    def _agent_society_summary(self, active_missions: list[dict[str, Any]]) -> dict[str, Any]:
        registry = self.agent_registry.by_id()
        agents: dict[str, dict[str, Any]] = {}
        lanes: dict[str, dict[str, Any]] = {}

        for mission in active_missions:
            mission_id = str(mission.get("mission_id", "")).strip()
            mission_title = str(mission.get("title", "")).strip() or "Mission"
            work_states = dict(mission.get("agent_work_states") or {})
            for agent_id, workspace in work_states.items():
                state = dict(workspace or {})
                agent_key = str(agent_id).strip()
                if not agent_key:
                    continue
                details = registry.get(agent_key)
                domain = str(getattr(details, "primary_domain", "") or state.get("role") or "general").strip() or "general"
                row = agents.setdefault(
                    agent_key,
                    {
                        "agent_id": agent_key,
                        "label": str(getattr(details, "label", "") or agent_key),
                        "primary_domain": domain,
                        "mission_ids": [],
                        "mission_titles": [],
                        "roles": [],
                        "statuses": [],
                        "ownership_modes": [],
                        "current_focuses": [],
                        "active_tasks": 0,
                        "blocked_tasks": 0,
                        "pending_reviews": 0,
                        "inbox_items": 0,
                        "outbox_items": 0,
                        "hypotheses": 0,
                        "recent_decisions": 0,
                        "lead_missions": 0,
                        "last_updated_at": "",
                    },
                )
                row["mission_ids"].append(mission_id)
                row["mission_titles"].append(mission_title)
                row["roles"] = self._trim_records(list(row.get("roles") or []) + [str(state.get("role", "")).strip()], limit=6)
                row["statuses"] = self._trim_records(list(row.get("statuses") or []) + [str(state.get("status", "")).strip()], limit=6)
                ownership_mode = str(state.get("ownership_mode", "")).strip() or "supporting"
                row["ownership_modes"] = self._trim_records(list(row.get("ownership_modes") or []) + [ownership_mode], limit=6)
                current_focus = str(state.get("current_focus", "")).strip()
                if current_focus:
                    row["current_focuses"] = self._trim_records(list(row.get("current_focuses") or []) + [current_focus], limit=4)
                row["active_tasks"] += len(list(state.get("active_tasks") or []))
                row["blocked_tasks"] += len(list(state.get("blocked_tasks") or []))
                row["pending_reviews"] += len(list(state.get("pending_reviews") or []))
                row["inbox_items"] += len(list(state.get("inbox") or []))
                row["outbox_items"] += len(list(state.get("outbox") or []))
                row["hypotheses"] += len(list(state.get("current_hypotheses") or []))
                row["recent_decisions"] += len(list(state.get("recent_decisions") or []))
                if ownership_mode == "lead":
                    row["lead_missions"] += 1
                updated_at = str(state.get("updated_at", "")).strip()
                if updated_at and updated_at > str(row.get("last_updated_at", "")):
                    row["last_updated_at"] = updated_at

                lane = lanes.setdefault(
                    domain,
                    {
                        "lane_id": domain,
                        "name": domain.replace("-", " ").title(),
                        "total_agents": 0,
                        "lead_agents": 0,
                        "active_tasks": 0,
                        "blocked_tasks": 0,
                        "pending_reviews": 0,
                        "hypotheses": 0,
                        "missions": [],
                    },
                )
                lane["active_tasks"] += len(list(state.get("active_tasks") or []))
                lane["blocked_tasks"] += len(list(state.get("blocked_tasks") or []))
                lane["pending_reviews"] += len(list(state.get("pending_reviews") or []))
                lane["hypotheses"] += len(list(state.get("current_hypotheses") or []))
                if mission_id and mission_id not in lane["missions"]:
                    lane["missions"].append(mission_id)

        for row in agents.values():
            domain = str(row.get("primary_domain") or "general")
            lane = lanes.setdefault(
                domain,
                {
                    "lane_id": domain,
                    "name": domain.replace("-", " ").title(),
                    "total_agents": 0,
                    "lead_agents": 0,
                    "active_tasks": 0,
                    "blocked_tasks": 0,
                    "pending_reviews": 0,
                    "hypotheses": 0,
                    "missions": [],
                },
            )
            lane["total_agents"] += 1
            if int(row.get("lead_missions", 0) or 0) > 0:
                lane["lead_agents"] += 1

        agent_rows = sorted(
            agents.values(),
            key=lambda item: (
                -int(item.get("blocked_tasks", 0) or 0),
                -int(item.get("pending_reviews", 0) or 0),
                -int(item.get("active_tasks", 0) or 0),
                str(item.get("label") or item.get("agent_id") or ""),
            ),
        )
        lane_rows = sorted(
            lanes.values(),
            key=lambda item: (
                -int(item.get("blocked_tasks", 0) or 0),
                -int(item.get("pending_reviews", 0) or 0),
                -int(item.get("active_tasks", 0) or 0),
                str(item.get("name") or item.get("lane_id") or ""),
            ),
        )
        return {
            "summary": {
                "active_agents": len(agent_rows),
                "lead_agents": len([item for item in agent_rows if int(item.get("lead_missions", 0) or 0) > 0]),
                "blocked_agents": len([item for item in agent_rows if int(item.get("blocked_tasks", 0) or 0) > 0]),
                "pending_review_agents": len([item for item in agent_rows if int(item.get("pending_reviews", 0) or 0) > 0]),
                "inbox_items": sum(int(item.get("inbox_items", 0) or 0) for item in agent_rows),
                "outbox_items": sum(int(item.get("outbox_items", 0) or 0) for item in agent_rows),
                "hypotheses": sum(int(item.get("hypotheses", 0) or 0) for item in agent_rows),
            },
            "agents": agent_rows,
            "lanes": lane_rows,
        }

    def add_mission_evidence(self, mission_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        evidence = list(dossier.get("evidence", []))
        existing_key = (
            str(payload.get("source_agent", "")).strip(),
            str(payload.get("kind", "")).strip(),
            str(payload.get("title", "")).strip(),
        )
        if any(
            (
                str(item.get("source_agent", "")).strip(),
                str(item.get("kind", "")).strip(),
                str(item.get("title", "")).strip(),
            ) == existing_key
            for item in evidence
        ):
            return dossier
        evidence.append(payload)
        dossier["evidence"] = evidence
        dossier["updated_at"] = _now_iso()
        return self.save_mission(dossier)

    def add_mission_output(self, mission_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        outputs = list(dossier.get("outputs", []))
        outputs.append(payload)
        dossier["outputs"] = outputs
        dossier["updated_at"] = _now_iso()
        return self.save_mission(dossier)

    def _infer_primary_domain(self, request: str) -> str:
        lowered = request.lower()
        if any(token in lowered for token in ("weather", "storm", "travel", "route", "campout", "outing", "forecast")):
            return "weather"
        if any(token in lowered for token in ("calendar", "meeting", "email", "task", "project", "inbox")):
            return "communications"
        if any(token in lowered for token in ("family", "kids", "school", "meal", "home", "household")):
            return "family"
        if any(token in lowered for token in ("build", "print", "forge", "workshop", "design", "photo", "vision", "model")):
            return "workshop"
        if any(token in lowered for token in ("journal", "reflect", "scripture", "chronicle", "devotional", "prayer")):
            return "formation"
        if any(token in lowered for token in ("budget", "finance", "money", "invest", "wealth")):
            return "finance"
        return "general"

    def _trust_zone_for_domain(self, domain: str) -> str:
        mapping = {
            "weather": "family-bmad.family-ops",
            "family": "family-bmad.family-ops",
            "communications": "family-bmad.communications",
            "finance": "family-bmad.finances",
            "workshop": "family-bmad.personal-local",
            "formation": "family-bmad.personal-local",
            "general": "family-bmad.personal-local",
        }
        return mapping.get(domain, "family-bmad.personal-local")

    def _mission_title(self, request: str, primary_domain: str) -> str:
        trimmed = request.strip()
        if trimmed:
            lead = trimmed.split(".")[0].split("?")[0].strip()
            if len(lead) > 72:
                lead = lead[:69].rstrip() + "..."
            if lead:
                return lead[0].upper() + lead[1:]
        labels = {
            "weather": "Weather and route mission",
            "communications": "Communications and calendar mission",
            "family": "Family operations mission",
            "workshop": "Workshop and creation mission",
            "formation": "Formation mission",
            "finance": "Finance mission",
        }
        return labels.get(primary_domain, "Family chief-of-staff mission")

    def _mission_brief(self, request: str, primary_domain: str) -> str:
        summaries = {
            "weather": "Translate live weather into practical guidance, route timing, and family-safe next actions.",
            "communications": "Triage communications, schedule pressure, and next drafts without losing tone or timing.",
            "family": "Reduce household friction and sequence the next clean family moves.",
            "workshop": "Turn creative or workshop intent into an actionable, reviewable build path.",
            "formation": "Support reflection and formation continuity without losing the practical next step.",
            "finance": "Stage finance work conservatively, with visibility and explicit approval posture.",
            "general": "Break the request into a bounded family-safe mission with clear evidence, actions, and follow-through.",
        }
        brief = summaries.get(primary_domain, summaries["general"])
        if request.strip():
            brief += f" Request: {request.strip()}"
        return brief

    def _select_core_agents(self, request: str, primary_domain: str) -> list[str]:
        lowered = request.lower()
        selected = ["ambient-router"]
        if primary_domain == "weather":
            selected.extend(["storm", "watchtower", "family-logistics"])
        elif primary_domain == "communications":
            selected.extend(["catalyst-personal", "executive-watch", "memory-curator"])
        elif primary_domain == "family":
            selected.extend(["family-logistics", "home-ops", "watchtower"])
        elif primary_domain == "workshop":
            selected.extend(["workshop-watch", "system-steward"])
        elif primary_domain == "formation":
            selected.extend(["chronicle-curator", "memory-curator"])
        elif primary_domain == "finance":
            selected.extend(["executive-watch", "memory-curator"])
        else:
            selected.extend(["executive-watch", "memory-curator"])
        return list(dict.fromkeys(selected))

    def _template_for_request(self, request: str, primary_domain: str) -> str:
        lowered = request.lower()
        if any(token in lowered for token in ("compare", "research", "look into", "investigate")):
            return "researcher"
        if any(token in lowered for token in ("plan", "sequence", "figure out")):
            return "planner"
        if any(token in lowered for token in ("triage", "sort", "rank")):
            return "triager"
        if any(token in lowered for token in ("draft", "message", "send", "reply")):
            return "communicator"
        if any(token in lowered for token in ("analyze", "assess", "decide")):
            return "analyst"
        if primary_domain in {"workshop", "weather", "finance"}:
            return "domain-specialist"
        return "planner"

    def _needs_task_agent(self, request: str, primary_domain: str, selected_agents: list[str]) -> bool:
        lowered = request.lower()
        if primary_domain in {"workshop", "finance"}:
            return True
        return any(token in lowered for token in ("together", "figure out", "build", "route", "trip", "project", "compare", "organize"))

    def _planned_actions_for_domain(self, domain: str, request: str) -> list[str]:
        lowered = request.lower()
        actions: list[str] = ["briefing-generation"]
        if domain == "weather":
            actions.append("route-weather-check")
            if any(token in lowered for token in ("warn", "alert", "family")):
                actions.append("family-alert")
        elif domain == "communications":
            actions.extend(["calendar-triage", "email-draft"])
            if any(token in lowered for token in ("send", "reply")):
                actions.append("send-approved-contact-email")
        elif domain == "family":
            actions.extend(["reminder", "family-alert"])
        elif domain == "finance":
            actions.extend(["finance-move"])
        elif domain == "workshop":
            actions.extend(["briefing-generation"])
        return list(dict.fromkeys(actions))

    def _family_impact(self, domain: str, request: str) -> list[str]:
        alerts = []
        if domain == "weather":
            alerts.append("Weather timing could affect departures, events, or outdoor plans.")
        if any(token in request.lower() for token in ("kids", "school", "family", "home")):
            alerts.append("This mission touches shared family flow and should stay visible in Mission Control.")
        return alerts

    def _follow_ups(self, domain: str, request: str) -> list[str]:
        follow_ups = ["Capture the result and keep the next clean move visible."]
        if domain == "weather":
            follow_ups.append("Re-check live weather before the relevant departure or event window.")
        if domain == "communications":
            follow_ups.append("Confirm timing, tone, and recipient before any external send.")
        if "project" in request.lower() or domain == "workshop":
            follow_ups.append("Break the mission into a sequenced execution path once evidence is gathered.")
        return follow_ups

    def _resolve_action(
        self,
        *,
        actor: str,
        room: str,
        mission_id: str,
        request: str,
        action_type: str,
        trust_zone: str,
        owner_agent: str,
    ) -> dict[str, Any]:
        approval_request_id = ""
        if action_type in self.BLOCKED_ACTIONS:
            resolution = "blocked"
            rationale = "This action crosses a trust boundary that stays blocked or fully staged in the first release."
            approval_required = False
        elif trust_zone == "family-bmad.finances":
            resolution = "stage-for-approval"
            rationale = "Financial moves stay reviewable and require explicit approval posture in the first release."
            approval_required = True
        elif action_type in self.STAGED_ACTIONS or trust_zone in {"family-bmad.external-commitments"}:
            resolution = "stage-for-approval"
            rationale = "This action affects external commitments or communications and should be staged for explicit approval."
            approval_required = True
        elif action_type in self.LOW_RISK_ACTIONS:
            resolution = "auto-execute"
            rationale = "This action fits the low-risk bounded autonomy lane."
            approval_required = False
        else:
            resolution = "stage-for-approval"
            rationale = "Unknown actions default to staged review until the household promotes them into a safer lane."
            approval_required = True
        if approval_required:
            approval = ApprovalRequest(
                request_id=str(uuid.uuid4()),
                actor=actor,
                room=room,
                request=f"Mission approval: {action_type} for {request.strip()[:96]}",
                action_class="EXECUTE_MEDIUM_RISK",
                second_factor_required=False,
                status="pending",
                rationale=rationale,
                domain=trust_zone,
                lane="mission-control",
                owner_agent=owner_agent,
                lifecycle_work_id=mission_id,
            )
            self.approval_store.add(approval)
            approval_request_id = approval.request_id
        return {
            "action_type": action_type,
            "trust_zone": trust_zone,
            "resolution": resolution,
            "rationale": rationale,
            "approval_required": approval_required,
            "approval_request_id": approval_request_id,
        }
