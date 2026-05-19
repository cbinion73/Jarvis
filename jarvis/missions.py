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
    ApprovalRequest,
    MissionActionDecision,
    MissionDossier,
    MissionEvidence,
    MissionOutput,
    MissionSubtask,
    TaskAgentProfile,
    TrustZone,
)
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
        path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

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

    def list_missions(self, *, actor: str = "", include_completed: bool = True, limit: int = 20) -> list[dict[str, Any]]:
        records = self.store.list_dossiers()
        actor_key = actor.strip().lower()
        if actor_key:
            records = [item for item in records if str(item.get("actor", "")).strip().lower() == actor_key]
        if not include_completed:
            records = [item for item in records if str(item.get("status", "")).strip().lower() not in {"completed", "archived", "retired"}]
        records.sort(key=lambda item: str(item.get("updated_at", "")).strip(), reverse=True)
        return records[:limit]

    def get_mission(self, mission_id: str) -> dict[str, Any] | None:
        mission_key = mission_id.strip()
        if not mission_key:
            return None
        for item in self.store.list_dossiers():
            if str(item.get("mission_id", "")).strip() == mission_key:
                return item
        return None

    def save_mission(self, payload: dict[str, Any]) -> dict[str, Any]:
        records = self.store.list_dossiers()
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
        dossier["status"] = status.strip() or dossier.get("status", "active")
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
        task_agents = {item["agent_id"]: item for item in self.list_task_agents(limit=200)}
        if str(status).strip().lower() == "completed":
            for agent_id in list(dossier.get("selected_agents", [])):
                if agent_id in task_agents:
                    self.record_task_agent_outcome(agent_id, succeeded=True)
        elif str(status).strip().lower() in {"blocked", "abandoned"}:
            for agent_id in list(dossier.get("selected_agents", [])):
                if agent_id in task_agents:
                    self.record_task_agent_outcome(agent_id, succeeded=False)
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
            memory_snapshot=dict(memory_snapshot or {}),
            family_impact=family_impact,
            created_at=now,
            updated_at=now,
        )
        payload = asdict(dossier)
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
        task_agents = {item["agent_id"]: item for item in self.store.list_task_agents() if isinstance(item, dict) and str(item.get("agent_id", "")).strip()}
        core_agents = {agent.agent_id: agent for agent in self.agent_registry.list()}
        result: list[dict[str, Any]] = []
        for agent_id in list(dossier.get("selected_agents", [])):
            if agent_id in task_agents:
                result.append(task_agents[agent_id])
                continue
            agent = core_agents.get(agent_id)
            if agent is None:
                continue
            result.append(
                {
                    "agent_id": agent.agent_id,
                    "label": agent.label,
                    "class_type": agent.agent_class,
                    "domain": agent.primary_domain,
                    "trust_zone": agent.trust_zone,
                    "promotion_status": agent.promotion_status,
                    "mission_roles": list(agent.mission_roles),
                    "allowed_tools": list(agent.allowed_tools),
                    "autonomy_posture": agent.autonomy_posture,
                    "purpose": agent.purpose,
                }
            )
        return result

    def mission_control_summary(self, *, actor: str = "", limit: int = 12) -> dict[str, Any]:
        missions = self.list_missions(actor=actor, limit=limit)
        active = [item for item in missions if str(item.get("status", "")).strip().lower() not in {"completed", "archived", "retired"}]
        approvals = []
        family_alerts: list[str] = []
        for mission in active:
            approvals.extend(self.mission_approvals(str(mission.get("mission_id", ""))))
            family_alerts.extend(list(mission.get("family_impact", [])))
        return {
            "generated_at": _now_iso(),
            "summary": {
                "active_missions": len(active),
                "pending_approvals": len([item for item in approvals if str(item.get("status", "")).strip() == "pending"]),
                "task_agents": len([item for item in self.list_task_agents(limit=200) if str(item.get("status", "")).strip().lower() == "active"]),
                "promoted_agents": len([item for item in self.list_task_agents(limit=200) if str(item.get("promotion_status", "")).strip().lower() == "promoted"]),
            },
            "active_missions": active,
            "pending_approvals": approvals[:10],
            "family_alerts": family_alerts[:10],
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
