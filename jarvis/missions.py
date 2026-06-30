from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agentic import AgentDefinition, AgentRegistry
from .audit import ApprovalStore, AuditLog
from .models import (
    AgentDecisionRecord,
    AgentDelegationRecord,
    AgentEscalationRecord,
    AgentHandoffRecord,
    AgentHypothesisRecord,
    AgentMessage,
    AgentTaskRef,
    AgentWorkState,
    DelegationReportRecord,
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
        objective = str(dossier.get("objective", "")).strip() or title
        next_step = str(dossier.get("next_step", "")).strip() or f"Advance {title.lower()}."
        why_this_matters = str(dossier.get("why_this_matters", "")).strip()
        success_definition = str(dossier.get("success_definition", "")).strip()
        progress_signal = str(dossier.get("progress_signal", "")).strip()
        recommendation = str(dossier.get("recommendation", "")).strip()
        primary_domain = str(dossier.get("primary_domain", "")).strip() or "general"
        next_actions = [dict(item) for item in list(dossier.get("next_actions") or []) if isinstance(item, dict)]
        milestones = [dict(item) for item in list(dossier.get("milestones") or []) if isinstance(item, dict)]
        mission_id = str(dossier.get("mission_id", "")).strip()
        selected = [str(agent_id).strip() for agent_id in list(dossier.get("selected_agents", [])) if str(agent_id).strip()]
        for index, agent_id in enumerate(selected):
            details = self._agent_display_payload(agent_id)
            role_name = str((details.get("mission_roles") or ["support"])[0]).strip() or "support"
            lead_task_title = str((next_actions[0] or {}).get("title", "")).strip() if next_actions else next_step
            lead_task_summary = (
                progress_signal
                or why_this_matters
                or f"Build visible momentum for {objective.lower()}."
            )
            support_review_title = str((milestones[0] or {}).get("title", "")).strip() if milestones else "Review mission success definition"
            support_review_summary = (
                success_definition
                or recommendation
                or f"Review how this {primary_domain} mission should contribute to the next move."
            )
            support_focus = recommendation or f"Support {objective.lower()}."
            default_task = self._task_ref(
                title=lead_task_title if index == 0 else f"Support {title}",
                status="active" if index == 0 else "queued",
                summary=lead_task_summary if index == 0 else support_review_summary,
                source="mission-bootstrap",
                updated_at=now,
            )
            default_review = self._task_ref(
                title=support_review_title,
                status="pending",
                summary=support_review_summary,
                source="mission-bootstrap",
                updated_at=now,
            )
            initial_message = self._message(
                kind="mission-brief",
                from_agent="jarvis-orchestrator",
                to_agent=agent_id,
                subject=title,
                summary=(
                    f"Objective: {objective}. "
                    f"{'Lead the next move.' if index == 0 else 'Support the mission with a clear contribution.'} "
                    f"Next step: {next_step}"
                ),
                created_at=now,
                status="delivered",
            )
            state = dict(work_states.get(agent_id) or {})
            if not state:
                work_states[agent_id] = self._new_workspace(
                    mission_id=mission_id,
                    agent_id=agent_id,
                    role=role_name,
                    ownership_mode="lead" if index == 0 else "supporting",
                    status="active" if index == 0 else "ready",
                    current_focus=next_step if index == 0 else support_focus,
                    inbox=[initial_message],
                    active_tasks=[default_task] if index == 0 else [],
                    pending_reviews=[] if index == 0 else [default_review],
                    decisions=[
                        self._decision(
                            summary="Mission accepted into workspace",
                            rationale=why_this_matters or "Mission dossier created and assigned.",
                            created_at=now,
                        )
                    ],
                    hypotheses=[
                        self._hypothesis(
                            summary=(
                                success_definition
                                or f"{title} likely needs {details.get('label', agent_id)} on {details.get('domain', 'general')} continuity."
                            ),
                            timestamp=now,
                        )
                    ],
                    updated_at=now,
                )
                continue
            state.setdefault("mission_id", mission_id)
            state.setdefault("agent_id", agent_id)
            state.setdefault("role", role_name)
            state.setdefault("status", "ready")
            state.setdefault("ownership_mode", "lead" if index == 0 else "supporting")
            state.setdefault("current_focus", next_step if index == 0 else support_focus)
            state["inbox"] = list(state.get("inbox") or []) or [initial_message]
            state["outbox"] = list(state.get("outbox") or [])
            state["active_tasks"] = list(state.get("active_tasks") or []) or ([default_task] if index == 0 else [])
            state["blocked_tasks"] = list(state.get("blocked_tasks") or [])
            state["pending_reviews"] = list(state.get("pending_reviews") or []) or ([] if index == 0 else [default_review])
            state["recent_decisions"] = self._trim_records(
                list(state.get("recent_decisions") or [])
                or [self._decision(summary="Mission accepted into workspace", rationale=why_this_matters or "Mission dossier created and assigned.", created_at=now)]
            )
            state["current_hypotheses"] = self._trim_records(
                list(state.get("current_hypotheses") or [])
                or [self._hypothesis(summary=success_definition or f"{title} needs a clear next move and continuity.", timestamp=now)]
            )
            state.setdefault("last_handoff_at", "")
            state["updated_at"] = str(state.get("updated_at", "")).strip() or now
            work_states[agent_id] = state
        dossier["agent_work_states"] = work_states
        dossier["handoffs"] = list(dossier.get("handoffs") or [])
        dossier["delegations"] = list(dossier.get("delegations") or [])
        dossier["delegation_reports"] = list(dossier.get("delegation_reports") or [])
        dossier["escalations"] = list(dossier.get("escalations") or [])
        dossier["ownership_transfers"] = list(dossier.get("ownership_transfers") or [])
        dossier["duplicate_suppressions"] = list(dossier.get("duplicate_suppressions") or [])
        dossier["background_prepared_outputs"] = [dict(item) for item in list(dossier.get("background_prepared_outputs") or []) if isinstance(item, dict)]
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
        result = self.save_mission(dossier)
        if resolved_status.lower() in {"completed", "blocked", "abandoned"}:
            try:
                audit_root = self.store.root.parent / "audit"
                AuditLog(audit_root).log_event(
                    "mission_lifecycle",
                    {
                        "mission_id": mission_id,
                        "title": str(dossier.get("title", "")).strip(),
                        "status": resolved_status,
                        "lessons_learned": str(dossier.get("lessons_learned", "")).strip(),
                        "note": note.strip(),
                        "selected_agents": list(dossier.get("selected_agents", [])),
                    },
                )
            except Exception:
                pass
        return result

    def update_mission_details(
        self,
        mission_id: str,
        *,
        title: str = "",
        brief: str = "",
        request: str = "",
        next_step: str = "",
        note: str = "",
    ) -> dict[str, Any]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        now = _now_iso()
        updated_fields: list[str] = []
        clean_title = title.strip()
        clean_brief = brief.strip()
        clean_request = request.strip()
        clean_next_step = next_step.strip()
        if clean_title and clean_title != str(dossier.get("title", "")).strip():
            dossier["title"] = clean_title
            updated_fields.append("title")
        if clean_brief and clean_brief != str(dossier.get("brief", "")).strip():
            dossier["brief"] = clean_brief
            updated_fields.append("brief")
        if clean_request and clean_request != str(dossier.get("request", "")).strip():
            dossier["request"] = clean_request
            updated_fields.append("request")
        if clean_next_step:
            subtasks = [dict(item or {}) for item in list(dossier.get("subtasks") or []) if isinstance(item, dict)]
            target_index = -1
            for index, item in enumerate(subtasks):
                if str(item.get("status", "")).strip().lower() == "active":
                    target_index = index
                    break
            if target_index < 0 and subtasks:
                target_index = 0
            if target_index >= 0:
                current_title = str(subtasks[target_index].get("title", "")).strip()
                if clean_next_step != current_title:
                    subtasks[target_index]["title"] = clean_next_step
                    subtasks[target_index]["updated_at"] = now
                    dossier["subtasks"] = subtasks
                    updated_fields.append("next_step")
        if note.strip() or updated_fields:
            evidence = list(dossier.get("evidence", []))
            summary_bits = updated_fields[:] or ["mission detail"]
            evidence.append(
                asdict(
                    MissionEvidence(
                        evidence_id=str(uuid.uuid4()),
                        source_agent="jarvis-orchestrator",
                        source_system="mission-control",
                        kind="detail-update",
                        title="Mission detail updated",
                        summary=f"Updated {', '.join(summary_bits)}.",
                        detail=note.strip() or f"Updated {', '.join(summary_bits)} from the mission board.",
                        timestamp=now,
                    )
                )
            )
            dossier["evidence"] = evidence
        dossier["updated_at"] = now
        return self.save_mission(dossier)

    def mission_work_state(self, mission_id: str) -> dict[str, Any]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        work_states = dict(dossier.get("agent_work_states") or {})
        handoffs = list(dossier.get("handoffs") or [])
        ownership_transfers = list(dossier.get("ownership_transfers") or [])
        delegation_reports = list(dossier.get("delegation_reports") or [])
        report_by_delegation = {
            str(item.get("delegation_id", "")).strip(): dict(item)
            for item in delegation_reports
            if str(item.get("delegation_id", "")).strip()
        }
        delegations: list[dict[str, Any]] = []
        for item in list(dossier.get("delegations") or []):
            delegation = dict(item or {})
            delegation_id = str(delegation.get("delegation_id", "")).strip()
            report = report_by_delegation.get(delegation_id)
            status_key = str(delegation.get("status", "")).strip().lower()
            if report:
                inspectable_output_status = "completed-with-output"
            elif status_key in {"rejected", "cancelled", "failed", "unavailable"}:
                inspectable_output_status = "unavailable"
            else:
                inspectable_output_status = "requested"
            delegation["inspectable_output_status"] = inspectable_output_status
            delegation["artifact_ref"] = str((report or {}).get("artifact_ref", "")).strip()
            delegation["output_id"] = str((report or {}).get("output_id", "")).strip()
            delegation["producer_agent"] = str((report or {}).get("producer_agent", "")).strip()
            delegation["report_id"] = str((report or {}).get("report_id", "")).strip()
            delegations.append(delegation)
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
                "delegations_requested": len([item for item in delegations if str(item.get("inspectable_output_status", "")).strip() == "requested"]),
                "delegations_completed_with_output": len(
                    [item for item in delegations if str(item.get("inspectable_output_status", "")).strip() == "completed-with-output"]
                ),
                "delegations_unavailable": len([item for item in delegations if str(item.get("inspectable_output_status", "")).strip() == "unavailable"]),
            },
            "agent_work_states": work_states,
            "handoffs": handoffs,
            "delegations": delegations,
            "delegation_reports": delegation_reports,
            "outputs": list(dossier.get("outputs") or []),
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

    def update_task_agent_assignment(
        self,
        agent_id: str,
        *,
        mission_id: str = "",
        mission_roles: list[str] | None = None,
        policy_assignment: str = "",
        purpose: str = "",
    ) -> dict[str, Any]:
        agent = self.get_task_agent(agent_id)
        if agent is None:
            raise KeyError(f"Unknown task agent: {agent_id}")
        now = _now_iso()
        prior_mission_id = str(agent.get("mission_id", "")).strip()
        next_mission_id = mission_id.strip() or prior_mission_id
        if next_mission_id:
            target_mission = self.get_mission(next_mission_id)
            if target_mission is None:
                raise KeyError(f"Unknown mission: {next_mission_id}")
        else:
            target_mission = None

        def detach_from_mission(detach_mission_id: str) -> None:
            if not detach_mission_id:
                return
            dossier = self.get_mission(detach_mission_id)
            if dossier is None:
                return
            selected_agents = [str(item).strip() for item in list(dossier.get("selected_agents") or []) if str(item).strip()]
            dossier["selected_agents"] = [item for item in selected_agents if item != agent_id]
            work_states = dict(dossier.get("agent_work_states") or {})
            work_states.pop(agent_id, None)
            dossier["agent_work_states"] = work_states
            dossier["updated_at"] = now
            self.save_mission(dossier)

        def attach_to_mission(dossier: dict[str, Any]) -> None:
            selected_agents = [str(item).strip() for item in list(dossier.get("selected_agents") or []) if str(item).strip()]
            if agent_id not in selected_agents:
                selected_agents.append(agent_id)
            dossier["selected_agents"] = selected_agents
            dossier["updated_at"] = now
            self.save_mission(dossier)

        if prior_mission_id and prior_mission_id != next_mission_id:
            detach_from_mission(prior_mission_id)
        if target_mission is not None:
            attach_to_mission(target_mission)

        if mission_roles is not None:
            cleaned_roles = [str(item).strip() for item in mission_roles if str(item).strip()]
            if cleaned_roles:
                agent["mission_roles"] = cleaned_roles
        if policy_assignment.strip():
            agent["policy_assignment"] = policy_assignment.strip()
        if purpose.strip():
            agent["purpose"] = purpose.strip()
        agent["mission_id"] = next_mission_id
        agent["updated_at"] = now
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
        objective = self._mission_objective(request)
        trust_zone = self._trust_zone_for_domain(primary_domain)
        title = self._mission_title(request, primary_domain)
        brief = self._mission_brief(request, primary_domain)
        mission_type = self._mission_type(request, primary_domain)
        why_this_matters = self._why_this_matters(primary_domain, request)
        success_definition = self._success_definition(primary_domain, request)
        time_horizon = self._time_horizon(request, primary_domain)
        momentum = self._initial_momentum(request, primary_domain)
        milestones = self._milestones_for_request(request, primary_domain)
        next_actions = self._next_actions_for_request(request, primary_domain)
        recommendation = self._recommendation_for_request(request, primary_domain)
        risks = self._risks_for_request(request, primary_domain)
        mission_open_loops = self._open_loops_for_request(request, primary_domain)
        accountability_cadence = self._accountability_cadence(primary_domain)
        progress_signal = self._initial_progress_signal(primary_domain, request)
        support_message = self._support_message(primary_domain, request)
        workspace_route = "/mission-board"
        truth_labels = self._truth_labels_for_mission()
        target_metrics = self._target_metrics_for_request(request, primary_domain)
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
        brief_summary = {
            "title": title,
            "why_it_matters": why_this_matters,
            "status": "pending-approval" if approval_ids else "active",
            "top_next_action": str((next_actions[0] if next_actions else {}).get("title", "")).strip(),
        }
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
            delegation_reports=[],
            escalations=[],
            ownership_transfers=[],
            duplicate_suppressions=[],
            memory_snapshot=dict(memory_snapshot or {}),
            family_impact=family_impact,
            created_at=now,
            updated_at=now,
            origin="conversation",
            objective=objective,
            mission_type=mission_type,
            why_this_matters=why_this_matters,
            success_definition=success_definition,
            time_horizon=time_horizon,
            momentum=momentum,
            milestones=milestones,
            next_actions=next_actions,
            next_step=str((next_actions[0] if next_actions else {}).get("title", "")).strip(),
            recommendation=recommendation,
            risks=risks,
            open_loops=mission_open_loops,
            accountability_cadence=accountability_cadence,
            progress_signal=progress_signal,
            support_message=support_message,
            workspace_route=workspace_route,
            brief_summary=brief_summary,
            truth_labels=truth_labels,
            target_metrics=target_metrics,
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

    def mission_delegation_reports(self, mission_id: str) -> list[dict[str, Any]]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            return []
        return list(dossier.get("delegation_reports", []))

    def mission_delegation_report(self, mission_id: str, report_id: str) -> dict[str, Any] | None:
        report_key = report_id.strip()
        if not report_key:
            return None
        for item in self.mission_delegation_reports(mission_id):
            if str(item.get("report_id", "")).strip() == report_key:
                return dict(item)
        return None

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
        existing_key = (
            str(payload.get("kind", "")).strip(),
            str(payload.get("title", "")).strip(),
            str(payload.get("status", "")).strip(),
        )
        if any(
            (
                str(item.get("kind", "")).strip(),
                str(item.get("title", "")).strip(),
                str(item.get("status", "")).strip(),
            ) == existing_key
            for item in outputs
        ):
            return dossier
        outputs.append(payload)
        dossier["outputs"] = outputs
        dossier["updated_at"] = _now_iso()
        return self.save_mission(dossier)

    def record_delegation_output(
        self,
        mission_id: str,
        delegation_id: str,
        *,
        producing_agent: str,
        title: str,
        summary: str,
        detail: str = "",
        key_output: str = "",
        next_step: str = "",
        evidence_note: str = "",
    ) -> dict[str, Any]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        delegation_key = delegation_id.strip()
        if not delegation_key:
            raise ValueError("delegation_id is required")
        delegations = [dict(item or {}) for item in list(dossier.get("delegations") or [])]
        target_delegation: dict[str, Any] | None = None
        for item in delegations:
            if str(item.get("delegation_id", "")).strip() == delegation_key:
                target_delegation = item
                break
        if target_delegation is None:
            raise KeyError(f"Unknown delegation: {delegation_id}")

        producer_key = producing_agent.strip()
        if not producer_key:
            raise ValueError("producing_agent is required")
        delegate_agent = str(target_delegation.get("delegate_agent", "")).strip()
        if delegate_agent and producer_key != delegate_agent:
            raise ValueError("Only the delegated agent may submit inspectable output for this delegation.")

        current_status = str(target_delegation.get("status", "")).strip().lower()
        if current_status in {"rejected", "cancelled", "failed", "unavailable"}:
            raise ValueError("This delegation is unavailable for inspectable output because it is no longer active.")
        if current_status == "pending-acceptance":
            raise ValueError("This delegation still needs acknowledgement before it can be marked complete with output.")

        existing_reports = [dict(item or {}) for item in list(dossier.get("delegation_reports") or [])]
        if any(str(item.get("delegation_id", "")).strip() == delegation_key for item in existing_reports):
            raise ValueError("This delegation already has inspectable output recorded.")

        cleaned_title = title.strip()
        cleaned_summary = summary.strip()
        cleaned_detail = detail.strip()
        cleaned_key_output = key_output.strip()
        cleaned_next_step = next_step.strip()
        cleaned_evidence_note = evidence_note.strip()
        if not cleaned_title:
            raise ValueError("title is required")
        if not cleaned_summary:
            raise ValueError("summary is required")
        if not any((cleaned_detail, cleaned_key_output, cleaned_next_step, cleaned_evidence_note)):
            raise ValueError(
                "Delegation reports need at least one useful supporting field: detail, key_output, next_step, or evidence_note."
            )

        now = _now_iso()
        report_id = str(uuid.uuid4())
        output_id = f"delegation-report-{delegation_key}"
        artifact_ref = f"/api/missions/{mission_id}/delegation-reports/{report_id}"
        report = asdict(
            DelegationReportRecord(
                report_id=report_id,
                mission_id=mission_id,
                delegation_id=delegation_key,
                producer_agent=producer_key,
                title=cleaned_title,
                summary=cleaned_summary,
                detail=cleaned_detail,
                key_output=cleaned_key_output,
                next_step=cleaned_next_step,
                evidence_note=cleaned_evidence_note,
                status="completed-with-output",
                handoff_id=str(target_delegation.get("handoff_id", "")).strip(),
                delegator_agent=str(target_delegation.get("delegator_agent", "")).strip(),
                delegate_agent=delegate_agent,
                created_at=now,
                output_id=output_id,
                artifact_ref=artifact_ref,
            )
        )

        target_delegation["status"] = "completed-with-output"
        target_delegation["resolved_at"] = now
        dossier["delegations"] = delegations
        dossier["delegation_reports"] = existing_reports + [report]

        updated_handoffs: list[dict[str, Any]] = []
        for item in list(dossier.get("handoffs") or []):
            handoff = dict(item or {})
            if str(handoff.get("handoff_id", "")).strip() == str(target_delegation.get("handoff_id", "")).strip():
                handoff["status"] = "completed-with-output"
                handoff["completed_at"] = now
            updated_handoffs.append(handoff)
        dossier["handoffs"] = updated_handoffs

        work_states = dict(dossier.get("agent_work_states") or {})
        producer_state = dict(work_states.get(producer_key) or {})
        if producer_state:
            producer_state["recent_decisions"] = self._trim_records(
                list(producer_state.get("recent_decisions") or [])
                + [
                    self._decision(
                        summary=report["title"],
                        rationale=report["summary"],
                        task_id=str(target_delegation.get("task_id", "")).strip(),
                        created_at=now,
                    )
                ]
            )
            producer_state["updated_at"] = now
            work_states[producer_key] = producer_state
            dossier["agent_work_states"] = work_states

        dossier["outputs"] = list(dossier.get("outputs") or []) + [
            asdict(
                MissionOutput(
                    output_id=output_id,
                    kind="delegation-report",
                    title=report["title"],
                    summary=report["summary"],
                    status="completed-with-output",
                    timestamp=now,
                    payload_ref=artifact_ref,
                )
            )
        ]
        dossier["updated_at"] = now
        return self.save_mission(dossier)

    def set_background_prepared_outputs(self, mission_id: str, outputs: list[dict[str, Any]]) -> dict[str, Any]:
        dossier = self.get_mission(mission_id)
        if dossier is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        normalized = [dict(item) for item in outputs if isinstance(item, dict)]
        if list(dossier.get("background_prepared_outputs") or []) == normalized:
            return dossier
        dossier["background_prepared_outputs"] = normalized
        dossier["updated_at"] = _now_iso()
        return self.save_mission(dossier)

    def _infer_primary_domain(self, request: str) -> str:
        lowered = request.lower()
        if any(token in lowered for token in ("weight", "workout", "exercise", "sleep", "nutrition", "blood pressure", "health", "fitness", "longevity")):
            return "health"
        if any(token in lowered for token in ("book sales", "book", "writing", "article", "publish", "publishing", "audience", "campaign", "content")):
            return "writing"
        if any(token in lowered for token in ("jarvis", "roadmap", "feature", "build slice", "implementation", "product rescope")):
            return "jarvis-development"
        if any(token in lowered for token in ("summer camp", "scout", "scouting", "troop", "camp", "advancement", "service project")):
            return "scouting"
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
            "health": "family-bmad.personal-local",
            "writing": "family-bmad.personal-local",
            "jarvis-development": "family-bmad.personal-local",
            "scouting": "family-bmad.family-ops",
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
        lowered = trimmed.lower()
        if "lose" in lowered and "pound" in lowered:
            return "Health mission: lose weight with a real plan"
        if "book sales" in lowered or ("increase" in lowered and "sales" in lowered):
            return "Writing mission: increase book sales"
        if "retirement" in lowered:
            return "Finance mission: prepare for retirement"
        if "summer camp" in lowered:
            return "Scouting mission: summer camp readiness"
        if trimmed:
            lead = trimmed.split(".")[0].split("?")[0].strip()
            if len(lead) > 72:
                lead = lead[:69].rstrip() + "..."
            if lead:
                return lead[0].upper() + lead[1:]
        labels = {
            "health": "Health mission",
            "writing": "Writing and publishing mission",
            "jarvis-development": "JARVIS development mission",
            "scouting": "Scouting and service mission",
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
            "health": "Turn the health objective into a practical plan with milestones, consistency, and accountability.",
            "writing": "Turn the publishing objective into a campaign with milestones, content actions, and momentum tracking.",
            "jarvis-development": "Turn the product objective into a focused build mission with visible progress and the next clean implementation step.",
            "scouting": "Turn the scouting objective into a readiness plan with missing items, logistics, and timing visibility.",
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
        if primary_domain == "health":
            selected.extend(["executive-watch", "memory-curator"])
        elif primary_domain == "writing":
            selected.extend(["catalyst-personal", "memory-curator", "executive-watch"])
        elif primary_domain == "jarvis-development":
            selected.extend(["system-steward", "executive-watch", "memory-curator"])
        elif primary_domain == "scouting":
            selected.extend(["family-logistics", "watchtower", "executive-watch"])
        elif primary_domain == "weather":
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
        if primary_domain in {"workshop", "weather", "finance", "health", "writing", "jarvis-development", "scouting"}:
            return "domain-specialist"
        return "planner"

    def _needs_task_agent(self, request: str, primary_domain: str, selected_agents: list[str]) -> bool:
        lowered = request.lower()
        if primary_domain in {"workshop", "finance", "health", "writing", "jarvis-development", "scouting"}:
            return True
        return any(token in lowered for token in ("together", "figure out", "build", "route", "trip", "project", "compare", "organize"))

    def _planned_actions_for_domain(self, domain: str, request: str) -> list[str]:
        lowered = request.lower()
        actions: list[str] = ["briefing-generation"]
        if domain == "health":
            actions.extend(["reminder"])
        elif domain == "writing":
            actions.extend(["email-draft", "reminder"])
        elif domain == "jarvis-development":
            actions.extend(["briefing-generation"])
        elif domain == "scouting":
            actions.extend(["family-alert", "reminder"])
        elif domain == "weather":
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
        if domain == "scouting":
            alerts.append("This mission affects readiness, logistics, and family planning around upcoming scouting events.")
        if domain == "weather":
            alerts.append("Weather timing could affect departures, events, or outdoor plans.")
        if any(token in request.lower() for token in ("kids", "school", "family", "home")):
            alerts.append("This mission touches shared family flow and should stay visible in Mission Control.")
        return alerts

    def _follow_ups(self, domain: str, request: str) -> list[str]:
        follow_ups = ["Capture the result and keep the next clean move visible."]
        if domain == "health":
            follow_ups.append("Review consistency before intensity when you check progress.")
        if domain == "writing":
            follow_ups.append("Use campaign feedback to refine the next publishing move.")
        if domain == "jarvis-development":
            follow_ups.append("Keep the next implementation slice visible in the mission workspace and the Daily Brief.")
        if domain == "scouting":
            follow_ups.append("Re-check readiness before the event window closes.")
        if domain == "weather":
            follow_ups.append("Re-check live weather before the relevant departure or event window.")
        if domain == "communications":
            follow_ups.append("Confirm timing, tone, and recipient before any external send.")
        if "project" in request.lower() or domain == "workshop":
            follow_ups.append("Break the mission into a sequenced execution path once evidence is gathered.")
        return follow_ups

    def _mission_objective(self, request: str) -> str:
        cleaned = request.strip()
        return cleaned[0].upper() + cleaned[1:] if cleaned else "Advance this mission with a practical plan."

    def _mission_type(self, request: str, primary_domain: str) -> str:
        lowered = request.lower()
        if primary_domain == "health":
            return "goal-pursuit"
        if primary_domain == "writing":
            return "campaign"
        if primary_domain == "scouting":
            return "readiness-check"
        if primary_domain == "jarvis-development":
            return "plan-build"
        if "ready" in lowered:
            return "readiness-check"
        return "goal-pursuit"

    def _why_this_matters(self, primary_domain: str, request: str) -> str:
        mapping = {
            "health": "Health progress compounds into better energy, clarity, and long-term stewardship.",
            "writing": "Publishing momentum grows audience, revenue, and creative leverage over time.",
            "jarvis-development": "A tighter build mission creates visible product progress instead of architecture drift.",
            "scouting": "Readiness reduces last-minute stress and protects the quality of the scouting experience.",
        }
        return mapping.get(primary_domain, f"This matters because it affects real stewardship, not just task completion. Request: {request.strip()}")

    def _success_definition(self, primary_domain: str, request: str) -> str:
        mapping = {
            "health": "Success means a realistic plan is active, progress is measurable, and consistency is easier to maintain.",
            "writing": "Success means a visible campaign is in motion with clear next actions and measurable momentum.",
            "jarvis-development": "Success means the next build slice is clearly defined, active, and reflected in the product surfaces.",
            "scouting": "Success means readiness gaps are visible, the plan is sequenced, and key logistics are under control.",
        }
        return mapping.get(primary_domain, f"Success means this request becomes a visible mission with next actions and follow-through: {request.strip()}")

    def _time_horizon(self, request: str, primary_domain: str) -> str:
        lowered = request.lower()
        if any(token in lowered for token in ("today", "tomorrow", "tonight")):
            return "today"
        if any(token in lowered for token in ("this week", "weekly", "summer camp", "camp")):
            return "this-week"
        if any(token in lowered for token in ("month", "30 days", "four weeks")):
            return "this-month"
        if any(token in lowered for token in ("quarter", "retirement")):
            return "this-quarter"
        return "ongoing" if primary_domain in {"health", "writing", "jarvis-development"} else "this-week"

    def _initial_momentum(self, request: str, primary_domain: str) -> str:
        lowered = request.lower()
        if any(token in lowered for token in ("stalled", "behind", "not moved")):
            return "slipping"
        if any(token in lowered for token in ("ready", "improve", "build", "increase", "prepare")):
            return "building"
        return "steady"

    def _milestones_for_request(self, request: str, primary_domain: str) -> list[dict[str, object]]:
        milestones_map = {
            "health": [
                "Establish target and current health baseline",
                "Create a realistic weekly consistency plan",
                "Track progress against the first milestone window",
            ],
            "writing": [
                "Define the campaign goal and offer focus",
                "Build the first content and promotion sequence",
                "Review momentum and adjust the next move",
            ],
            "jarvis-development": [
                "Frame the next product slice clearly",
                "Implement the smallest visible improvement",
                "Verify the slice in the real product surface",
            ],
            "scouting": [
                "Identify readiness gaps and missing items",
                "Sequence logistics and coordination steps",
                "Confirm readiness before the event window",
            ],
        }
        labels = milestones_map.get(primary_domain, [
            "Clarify the mission frame",
            "Create the first practical plan",
            "Advance the mission with a visible next step",
        ])
        results = []
        for idx, label in enumerate(labels[:5], start=1):
            results.append({"milestone_id": f"ms-{idx}", "title": label, "status": "pending"})
        return results

    def _next_actions_for_request(self, request: str, primary_domain: str) -> list[dict[str, object]]:
        actions_map = {
            "health": [
                "Log the current baseline and target for this plan",
                "Review the first week consistency plan",
            ],
            "writing": [
                "Review the first three campaign actions JARVIS prepared",
                "Choose the first content push to stage",
            ],
            "jarvis-development": [
                "Start the smallest visible product slice for this mission",
                "Verify the mission appears correctly in the product surface",
            ],
            "scouting": [
                "Confirm which readiness items are still missing",
                "Review the first logistics checklist JARVIS assembled",
            ],
        }
        labels = actions_map.get(primary_domain, ["Review the first plan and take the next clean step."])
        results = []
        for idx, label in enumerate(labels[:3], start=1):
            results.append({"action_id": f"act-{idx}", "title": label, "status": "pending"})
        return results

    def _recommendation_for_request(self, request: str, primary_domain: str) -> str:
        mapping = {
            "health": "Start with consistency, not intensity, for the first phase of this mission.",
            "writing": "Begin with one focused campaign sequence rather than scattering effort across channels.",
            "jarvis-development": "Build the smallest product slice that changes what Chris can feel immediately.",
            "scouting": "Solve readiness gaps before adding new optional work or purchases.",
        }
        return mapping.get(primary_domain, "Start with the clearest next move and keep the mission visible.")

    def _risks_for_request(self, request: str, primary_domain: str) -> list[str]:
        mapping = {
            "health": ["Inconsistency is a bigger risk than ambition right now."],
            "writing": ["Momentum may decay without a visible campaign cadence."],
            "jarvis-development": ["Architecture drift could outrun visible product progress."],
            "scouting": ["Last-minute logistics could create stress if readiness stays implicit."],
        }
        return mapping.get(primary_domain, ["This mission could drift without visible follow-through."])

    def _open_loops_for_request(self, request: str, primary_domain: str) -> list[str]:
        mapping = {
            "health": ["Baseline confirmation is still needed.", "The first accountability check-in is not yet complete."],
            "writing": ["The first promotion sequence needs review.", "Campaign success criteria should stay visible."],
            "jarvis-development": ["The next implementation slice must stay visible in the mission workspace."],
            "scouting": ["Readiness gaps still need confirmation.", "The final logistics pass is still open."],
        }
        return mapping.get(primary_domain, ["The next clean move should remain visible."])

    def _accountability_cadence(self, primary_domain: str) -> str:
        return {
            "health": "weekly",
            "writing": "weekly",
            "jarvis-development": "twice-weekly",
            "scouting": "event-countdown",
        }.get(primary_domain, "weekly")

    def _initial_progress_signal(self, primary_domain: str, request: str) -> str:
        return {
            "health": "A realistic health mission is now framed and ready to build momentum.",
            "writing": "The campaign now has a first structure instead of remaining a vague growth goal.",
            "jarvis-development": "This mission now has a concrete slice instead of staying at the idea level.",
            "scouting": "Readiness is now being made explicit so the remaining gaps can be closed.",
        }.get(primary_domain, "This mission now has a visible first structure.")

    def _support_message(self, primary_domain: str, request: str) -> str:
        return {
            "health": "Let’s recover or build momentum without overcorrecting.",
            "writing": "We do not need to solve the whole growth engine at once. We need the first useful push.",
            "jarvis-development": "Keep the slice small enough to ship and visible enough to feel.",
            "scouting": "You do not need to carry all of this mentally. We can track readiness step by step.",
        }.get(primary_domain, "JARVIS has the first pass framed. Now we keep it visible and moving.")

    def _truth_labels_for_mission(self) -> dict[str, str]:
        return {
            "objective": "confirmed",
            "primary_domain": "inferred",
            "success_definition": "inferred",
            "milestones": "inferred",
            "next_actions": "inferred",
            "progress_signal": "inferred",
        }

    def _target_metrics_for_request(self, request: str, primary_domain: str) -> list[str]:
        if primary_domain == "health":
            return ["Baseline captured", "Weekly consistency tracked"]
        if primary_domain == "writing":
            return ["Campaign launched", "Momentum reviewed"]
        if primary_domain == "jarvis-development":
            return ["Visible slice shipped", "Surface verified"]
        if primary_domain == "scouting":
            return ["Readiness gaps closed", "Logistics confirmed"]
        return []

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
