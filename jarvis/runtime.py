from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import uuid

from .accounts import AccountRegistry
from .agentic import AgentRegistry, BackgroundStateStore, BackgroundTaskScheduler, LifeAgentStudioStore, MemoryCurator
from .audit import ApprovalStore, AuditLog
from .briefing import build_morning_brief
from .catalyst import CatalystStore, CatalystSupport
from .chronicle import ChronicleStore, ChronicleSupport
from .config import AppConfig
from .executive import ExecutiveSupport
from .family import FamilyStore, FamilySupport
from .google_workspace import GoogleWorkspaceSupport
from .home import HomeStore, HomeSupport
from .memory import MemoryStore, MemorySupport
from .models import ApprovalRequest, HouseholdProfile, RequestPlan, UserProfile
from .models import HouseholdSnapshot
from .openai_tasks import JarvisOpenAIClient, OpenAIResult
from .orchestrator import JarvisOrchestrator
from .perception import PerceptionStore, PerceptionSupport
from .permissions import PermissionEngine
from .security import SecurityStore, SecuritySupport
from .status import collect_status
from .tutoring import TutoringStore, TutoringSupport
from .workshop import WorkshopStore, WorkshopSupport


@dataclass(slots=True)
class JarvisRuntime:
    config: AppConfig
    household: HouseholdProfile
    snapshot: HouseholdSnapshot
    orchestrator: JarvisOrchestrator
    audit_log: AuditLog
    approval_store: ApprovalStore
    openai_client: JarvisOpenAIClient
    executive_support: ExecutiveSupport
    chronicle_support: ChronicleSupport
    family_support: FamilySupport
    tutoring_support: TutoringSupport
    workshop_support: WorkshopSupport
    security_support: SecuritySupport
    home_support: HomeSupport
    perception_support: PerceptionSupport
    memory_support: MemorySupport
    catalyst_support: CatalystSupport
    google_workspace: GoogleWorkspaceSupport
    account_registry: AccountRegistry
    agent_registry: AgentRegistry
    life_agent_store: LifeAgentStudioStore
    background_scheduler: BackgroundTaskScheduler
    memory_curator: MemoryCurator

    @classmethod
    def from_env(cls) -> "JarvisRuntime":
        config = AppConfig.from_env()
        household = config.load_household()
        permissions = PermissionEngine()
        orchestrator = JarvisOrchestrator(config, permissions)
        data_root = Path("data")
        openai_client = JarvisOpenAIClient(config)
        account_registry = AccountRegistry(household)
        family_support = FamilySupport(config, openai_client, FamilyStore(data_root / "family"))
        tutoring_support = TutoringSupport(config, openai_client, TutoringStore(data_root / "tutoring"))
        workshop_support = WorkshopSupport(config, openai_client, WorkshopStore(data_root / "workshop"))
        security_support = SecuritySupport(config, openai_client, SecurityStore(data_root / "security"))
        home_support = HomeSupport(config, HomeStore(data_root / "home"))
        perception_support = PerceptionSupport(config, PerceptionStore(data_root / "perception"))
        memory_support = MemorySupport(config, MemoryStore(data_root / "memory"))
        catalyst_support = CatalystSupport(config, openai_client, CatalystStore(data_root / "catalyst"))
        google_workspace = GoogleWorkspaceSupport(config)
        agent_registry = AgentRegistry()
        life_agent_store = LifeAgentStudioStore(data_root / "agents")
        background_scheduler = BackgroundTaskScheduler(
            BackgroundStateStore(data_root / "agents"),
            agent_registry,
        )
        return cls(
            config=config,
            household=household,
            snapshot=config.load_snapshot(),
            orchestrator=orchestrator,
            audit_log=AuditLog(data_root / "logs"),
            approval_store=ApprovalStore(data_root / "approvals"),
            openai_client=openai_client,
            executive_support=ExecutiveSupport(config, openai_client),
            chronicle_support=ChronicleSupport(
                config,
                openai_client,
                ChronicleStore(data_root / "chronicle"),
            ),
            family_support=family_support,
            tutoring_support=tutoring_support,
            workshop_support=workshop_support,
            security_support=security_support,
            home_support=home_support,
            perception_support=perception_support,
            memory_support=memory_support,
            catalyst_support=catalyst_support,
            google_workspace=google_workspace,
            account_registry=account_registry,
            agent_registry=agent_registry,
            life_agent_store=life_agent_store,
            background_scheduler=background_scheduler,
            memory_curator=MemoryCurator(),
        )

    def get_actor(self, actor_name: str) -> UserProfile:
        actor_key = actor_name.strip().lower()
        if actor_key in self.household.users:
            return self.household.users[actor_key]
        for profile in self.household.users.values():
            if profile.display_name.lower() == actor_key:
                return profile
        raise KeyError(f"Unknown actor: {actor_name}")

    def morning_brief(self, actor_name: str) -> str:
        actor = self.get_actor(actor_name)
        return build_morning_brief(self.household, actor)

    def plan_request(self, actor_name: str, room: str, request: str) -> RequestPlan:
        actor = self.get_actor(actor_name)
        plan = self.orchestrator.route(actor, room, request)
        plan = self.tutoring_support.apply_child_boundaries(actor, plan)
        self.audit_log.log_plan(plan)
        if plan.needs_approval and plan.allowed:
            self.approval_store.add(
                ApprovalRequest(
                    request_id=plan.request_id,
                    actor=plan.actor,
                    room=plan.room,
                    request=plan.request,
                    action_class=plan.action_class.name,
                    second_factor_required=plan.second_factor_required,
                    status="pending",
                    rationale=plan.rationale,
                )
            )
        return plan

    def list_pending_approvals(self) -> list[dict]:
        return self.approval_store.list_pending()

    def approval_history(self) -> list[dict]:
        return self.approval_store.list_all()

    def status(self) -> list[dict]:
        return [
            {"name": item.name, "ok": item.ok, "detail": item.detail}
            for item in collect_status(self.config)
        ]

    def recent_activity(self, limit: int = 25) -> list[dict]:
        responses = self.audit_log.list_recent(limit=limit, entry_type="response")
        if responses:
            return responses
        return self.audit_log.list_recent(limit=limit, entry_type="plan")

    def explainability_snapshot(self) -> dict:
        activity = self.audit_log.list_recent(limit=12, entry_type="plan")
        approvals = self.approval_history()
        status_items = self.status()
        blocked_integrations = [item for item in status_items if not item["ok"]]
        module_counts: dict[str, int] = {}
        for item in activity:
            module = item.get("module", "unknown")
            module_counts[module] = module_counts.get(module, 0) + 1
        latest_reasons = [
            {
                "actor": item.get("actor", ""),
                "request": item.get("request", ""),
                "module": item.get("module", ""),
                "action_class": item.get("action_class", ""),
                "needs_approval": item.get("needs_approval", False),
                "second_factor_required": item.get("second_factor_required", False),
                "rationale": item.get("rationale", ""),
                "timestamp": item.get("timestamp", ""),
            }
            for item in activity[:8]
        ]
        return {
            "blocked_integrations": blocked_integrations,
            "approval_history": approvals[-12:],
            "module_counts": module_counts,
            "latest_reasons": latest_reasons,
        }

    def update_approval(self, request_id: str, status: str) -> dict | None:
        return self.approval_store.update_status(request_id, status)

    def respond(self, actor_name: str, room: str, request: str) -> OpenAIResult:
        plan = self.plan_request(actor_name, room, request)
        actor = self.get_actor(actor_name)
        if not plan.allowed:
            result = OpenAIResult(
                provider="policy",
                model="policy",
                output_text=self.tutoring_support.denial_response(actor, request, plan.rationale),
            )
            self.audit_log.log_response(
                plan,
                provider=result.provider,
                model=result.model,
                active_nodes=self._active_nodes_for(plan, result.provider),
                output_text=result.output_text,
            )
            return result
        result = self.openai_client.respond(plan)
        self.audit_log.log_response(
            plan,
            provider=result.provider,
            model=result.model,
            active_nodes=self._active_nodes_for(plan, result.provider),
            output_text=result.output_text,
        )
        return result

    def brain_graph_snapshot(self) -> dict:
        second_brain = self.openai_client.second_brain_status()
        recent = self.audit_log.list_recent(limit=1, entry_type="response")
        latest = recent[0] if recent else {}
        active_nodes = latest.get("active_nodes", []) if isinstance(latest, dict) else []
        return {
            "active_provider": latest.get("provider", "standby") if isinstance(latest, dict) else "standby",
            "active_model": latest.get("model", "") if isinstance(latest, dict) else "",
            "last_module": latest.get("module", "") if isinstance(latest, dict) else "",
            "last_timestamp": latest.get("timestamp", "") if isinstance(latest, dict) else "",
            "active_nodes": active_nodes,
            "secondary_brain": second_brain,
            "nodes": [
                {"id": "router", "label": "Router", "status": "ready"},
                {"id": "primary-brain", "label": "Primary", "status": "ready" if self.config.openai_api_key else "offline"},
                {
                    "id": "second-brain",
                    "label": "Second",
                    "status": "ready" if second_brain.get("model_available") else ("configured" if second_brain.get("healthy") or second_brain.get("enabled") else "disabled"),
                },
                {"id": "memory-core", "label": "Memory", "status": "ready"},
                {"id": "catalyst-personal", "label": "Catalyst", "status": "ready"},
                {"id": "household-associate", "label": "Ambient", "status": "ready"},
                {"id": "family-logistics", "label": "Family", "status": "ready"},
                {"id": "executive-work", "label": "Work", "status": "ready"},
                {"id": "faith-and-formation", "label": "Chronicle", "status": "ready"},
                {"id": "workshop-copilot", "label": "Workshop", "status": "ready"},
            ],
        }

    def agent_registry_snapshot(self) -> dict:
        return {
            "agents": [
                {
                    "agent_id": agent.agent_id,
                    "label": agent.label,
                    "purpose": agent.purpose,
                    "cadence_minutes": agent.cadence_minutes,
                    "triggers": list(agent.triggers),
                    "dependencies": list(agent.dependencies),
                    "memory_scope": list(agent.memory_scope),
                    "owns": list(agent.owns),
                    "quiet_hours_behavior": agent.quiet_hours_behavior,
                }
                for agent in self.agent_registry.list()
            ]
        }

    def background_agent_status(
        self,
        *,
        recent_activity: list[dict] | None = None,
        integration_status: list[dict] | None = None,
    ) -> dict:
        active_mode = self.family_support.active_mode().mode
        activity = recent_activity if recent_activity is not None else self.recent_activity(limit=20)
        status_items = integration_status if integration_status is not None else self.status()
        return self.background_scheduler.tick(
            active_mode=active_mode,
            integration_status=status_items,
            recent_activity=activity,
            quiet_hours=(self.household.quiet_start, self.household.quiet_end),
        )

    def memory_curator_snapshot(self, *, recent_activity: list[dict] | None = None) -> dict:
        activity = recent_activity if recent_activity is not None else self.recent_activity(limit=20)
        return self.memory_curator.rules_snapshot(activity)

    def life_agent_snapshot(self) -> dict:
        agents = [agent.to_dict() for agent in self.life_agent_store.load()]
        tiers = {
            "orchestrator": [agent for agent in agents if agent["tier"] == "orchestrator"],
            "strategic": [agent for agent in agents if agent["tier"] == "strategic"],
            "execution": [agent for agent in agents if agent["tier"] == "execution"],
        }
        return {"agents": agents, "tiers": tiers}

    def save_life_agent(self, payload: dict) -> dict:
        agent = self.life_agent_store.upsert(payload)
        return {"ok": True, "agent": agent.to_dict(), "snapshot": self.life_agent_snapshot()}

    def delete_life_agent(self, agent_id: str) -> dict:
        deleted = self.life_agent_store.delete(agent_id)
        return {"ok": deleted, "snapshot": self.life_agent_snapshot()}

    def life_party_mode(self, actor_name: str, room: str, prompt: str, selected_agent_ids: list[str]) -> dict:
        actor = self.get_actor(actor_name)
        agents = {agent.agent_id: agent for agent in self.life_agent_store.load() if agent.enabled}
        selected = [agents[agent_id] for agent_id in selected_agent_ids if agent_id in agents]
        if not selected:
            selected = list(agents.values())[:4]

        participants: list[dict] = []
        for agent in selected[:8]:
            system_prompt = (
                f"You are {agent.label}, a specialist agent inside Chris's personal JARVIS mesh. "
                f"Role: {agent.role} "
                f"Personality: {agent.personality} "
                f"Instructions: {agent.instructions} "
                f"Specific information: {agent.knowledge} "
                f"Logic: {agent.logic} "
                "Respond in 2-4 concise sentences. Give your perspective, your main concern, and your recommended next move. "
                "Stay in character, but be practical."
            )
            output_text = self.openai_client.prompt_text(system_prompt, prompt, max_output_tokens=220).strip()
            participants.append(
                {
                    "agent_id": agent.agent_id,
                    "label": agent.label,
                    "tier": agent.tier,
                    "response": output_text,
                }
            )

        synthesis_prompt = (
            f"Actor: {actor.display_name}. Room: {room}. "
            "You are JARVIS synthesizing a roundtable of specialist life agents into one coherent answer. "
            "Keep the voice formal, calm, and concise. "
            "State the recommendation, the tradeoff, and the next step."
        )
        synthesis_context = json.dumps(
            {
                "request": prompt,
                "participants": participants,
            },
            indent=2,
        )
        synthesis = self.openai_client.prompt_text(
            synthesis_prompt,
            synthesis_context,
            max_output_tokens=320,
        ).strip()
        return {
            "ok": True,
            "actor": actor.display_name,
            "room": room,
            "request": prompt,
            "participants": participants,
            "synthesis": synthesis,
        }

    def _active_nodes_for(self, plan: RequestPlan, provider: str) -> list[str]:
        provider_node = {
            "openai": "primary-brain",
            "ollama": "second-brain",
            "policy": "primary-brain",
            "fallback": "primary-brain",
        }.get(provider, "primary-brain")
        return ["router", provider_node, "memory-core", plan.module]

    def meeting_brief(self, actor_name: str, context: str) -> str:
        actor = self.get_actor(actor_name)
        return self.executive_support.meeting_brief(actor.display_name, context)

    def meeting_followup(self, actor_name: str, transcript: str) -> str:
        actor = self.get_actor(actor_name)
        return self.executive_support.meeting_followup(actor.display_name, transcript)

    def decision_framework(self, actor_name: str, context: str) -> str:
        actor = self.get_actor(actor_name)
        return self.executive_support.decision_framework(actor.display_name, context)

    def research_summary(self, actor_name: str, topic: str, notes: str) -> str:
        actor = self.get_actor(actor_name)
        return self.executive_support.research_summary(actor.display_name, topic, notes)

    def confidentiality_review(self, text: str) -> dict:
        return self.executive_support.confidentiality_review(text)

    def manuscript_review(self, actor_name: str, excerpt: str) -> str:
        actor = self.get_actor(actor_name)
        return self.executive_support.manuscript_review(actor.display_name, excerpt)

    def iron_clad_editor(self, actor_name: str, excerpt: str) -> str:
        actor = self.get_actor(actor_name)
        return self.executive_support.iron_clad_editor(actor.display_name, excerpt)

    def venture_brief(self, actor_name: str, topic: str, notes: str) -> str:
        actor = self.get_actor(actor_name)
        return self.executive_support.venture_brief(actor.display_name, topic, notes)

    def devotional_pause(self, actor_name: str, theme: str, mode: str = "scripture") -> str:
        actor = self.get_actor(actor_name)
        return self.chronicle_support.devotional_pause(actor.display_name, theme, mode)

    def family_devotional_prep(self, actor_name: str, theme: str, context: str = "") -> str:
        actor = self.get_actor(actor_name)
        return self.chronicle_support.family_devotional_prep(actor.display_name, theme, context)

    def chronicle_capture(self, actor_name: str, theme: str, note: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.chronicle_support.chronicle_capture(actor.display_name, theme, note)

    def chronicle_timeline(self, limit: int = 10) -> list[dict]:
        return self.chronicle_support.prayer_timeline(limit=limit)

    def chronicle_theme_summary(self, limit: int = 25) -> dict:
        return self.chronicle_support.prayer_theme_summary(limit=limit)

    def catalyst_overview(self) -> dict:
        overview = self.catalyst_support.overview()
        accounts = self.list_personal_accounts()
        google_accounts = [item for item in accounts if item["provider"] == "google"]
        google_summary = {
            "accounts": [
                self.google_account_snapshot(item["account_id"])
                for item in google_accounts
            ],
            "count": len(google_accounts),
        }
        connectors: list[dict] = []
        for item in overview.get("connectors", []):
            connector = dict(item)
            if connector.get("id") == "gmail":
                connector["status"] = "ready" if any(entry["status"].get("gmail_ready") for entry in google_summary["accounts"]) else "planned"
                connector["notes"] = "One or more personal Google mail accounts can live here. Add them in Settings."
            elif connector.get("id") == "google_calendar":
                connector["status"] = "ready" if any(entry["status"].get("calendar_ready") for entry in google_summary["accounts"]) else "planned"
                connector["notes"] = "One or more personal Google calendar accounts can live here. Add them in Settings."
            connectors.append(connector)
        overview["connectors"] = connectors
        overview["google_workspace"] = google_summary
        overview["personal_accounts"] = accounts
        return overview

    def google_workspace_status(self) -> dict:
        return {
            "default": self.google_workspace.status().to_dict(),
            "accounts": [self.google_account_snapshot(item["account_id"]) for item in self.list_personal_accounts() if item["provider"] == "google"],
        }

    def google_workspace_summary(self) -> dict:
        return {
            "client_secret": self.google_workspace.client_secret_summary(),
            "accounts": [self.google_account_snapshot(item["account_id"]) for item in self.list_personal_accounts() if item["provider"] == "google"],
        }

    def google_connect_url(self, account_id: str, base_url: str) -> dict:
        account = self.account_registry.get(account_id)
        if not account:
            return {"ok": False, "detail": "Account not found."}
        if account.provider != "google":
            return {"ok": False, "detail": f"{account.provider.title()} login is not wired yet."}
        return self.google_workspace.build_connect_url(account, base_url)

    def google_handle_callback(self, base_url: str, code: str, state: str) -> dict:
        result = self.google_workspace.handle_callback(base_url, code, state)
        account_id = str(result.get("account_id", "")).strip()
        if result.get("ok") and account_id:
            self.account_registry.update_status(account_id, "connected", "Google login complete.")
        return result

    def google_disconnect(self) -> dict:
        return self.google_workspace.disconnect()

    def google_save_client_secret(self, raw_json: str) -> dict:
        return self.google_workspace.save_client_secret_json(raw_json)

    def google_disconnect_account(self, account_id: str) -> dict:
        account = self.account_registry.get(account_id)
        if not account:
            return {"ok": False, "message": "Account not found."}
        if account.provider != "google":
            return {"ok": False, "message": f"{account.provider.title()} disconnect is not wired yet."}
        result = self.google_workspace.disconnect(account)
        self.account_registry.update_status(account_id, "planned", "Disconnected from Google.")
        result["account"] = account.to_dict()
        return result

    def list_personal_accounts(self) -> list[dict]:
        return [item.to_dict() for item in self.account_registry.list_accounts()]

    def account_registry_snapshot(self) -> dict:
        snapshot = self.account_registry.describe()
        accounts = []
        for item in snapshot["accounts"]:
            enriched = dict(item)
            if enriched.get("provider") == "google":
                enriched["connection"] = self.google_account_snapshot(enriched["account_id"])["status"]
            accounts.append(enriched)
        snapshot["accounts"] = accounts
        return snapshot

    def save_personal_account(self, payload: dict) -> dict:
        account = self.account_registry.save_account(payload)
        return {
            "message": f"Saved account '{account.label}'.",
            "account": account.to_dict(),
            "registry": self.account_registry_snapshot(),
        }

    def google_account_snapshot(self, account_id: str) -> dict:
        account = self.account_registry.get(account_id)
        if not account:
            return {"account_id": account_id, "status": self.google_workspace.status().to_dict(), "emails": [], "calendar_events": []}
        summary = self.google_workspace.summary(account)
        summary["account"] = account.to_dict()
        return summary

    def catalyst_capture_signal(
        self,
        actor_name: str,
        source: str,
        title: str,
        content: str,
        *,
        sender: str = "",
        tags: list[str] | None = None,
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.catalyst_support.capture_signal(
            actor.display_name,
            source,
            title,
            content,
            sender=sender,
            tags=tags,
        )

    def catalyst_email_triage(self, actor_name: str, subject: str, body: str, sender: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.catalyst_support.email_triage(actor.display_name, subject, body, sender)

    def catalyst_meeting_prep(
        self,
        actor_name: str,
        meeting_title: str,
        open_commitments: list[str],
        recent_signals: list[str],
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.catalyst_support.meeting_prep(actor.display_name, meeting_title, open_commitments, recent_signals)

    def catalyst_meeting_extraction(self, actor_name: str, transcript: str, context: str = "") -> dict:
        actor = self.get_actor(actor_name)
        return self.catalyst_support.meeting_extraction(actor.display_name, transcript, context)

    def catalyst_briefing(self, actor_name: str, user_context: str = "") -> dict:
        actor = self.get_actor(actor_name)
        return self.catalyst_support.briefing_generation(actor.display_name, user_context)

    def catalyst_draft(
        self,
        actor_name: str,
        intent: str,
        context: str,
        recipient: str,
        tone: str = "professional",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.catalyst_support.draft_composition(actor.display_name, intent, context, recipient, tone)

    def catalyst_project_brief(
        self,
        actor_name: str,
        project_name: str,
        problem: str,
        desired_outcome: str,
        constraints: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.catalyst_support.project_brief(actor.display_name, project_name, problem, desired_outcome, constraints)

    def catalyst_implementation_plan(
        self,
        actor_name: str,
        project_name: str,
        brief: str,
        constraints: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.catalyst_support.implementation_plan(actor.display_name, project_name, brief, constraints)

    def catalyst_proactive_surfacing(self, actor_name: str, horizon: str = "today", context: str = "") -> dict:
        actor = self.get_actor(actor_name)
        return self.catalyst_support.proactive_surfacing(actor.display_name, horizon, context)

    def _design_review_path(self) -> Path:
        root = Path("data") / "design-review"
        root.mkdir(parents=True, exist_ok=True)
        return root / "holo-review.json"

    def design_review_state(self) -> dict:
        path = self._design_review_path()
        if not path.exists():
            return {
                "active_page": "shell",
                "page_settings": {"shell": {"enabled": True}},
                "pages": {"shell": {"removed": [], "notes": {}, "overrides": {}}},
            }
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {
                "active_page": "shell",
                "page_settings": {"shell": {"enabled": True}},
                "pages": {"shell": {"removed": [], "notes": {}, "overrides": {}}},
            }
        if "pages" in raw:
            return {
                "active_page": str(raw.get("active_page", "shell") or "shell"),
                "page_settings": dict(raw.get("page_settings", {"shell": {"enabled": True}})),
                "pages": dict(raw.get("pages", {})),
            }
        return {
            "active_page": "shell",
            "page_settings": {"shell": {"enabled": True}},
            "pages": {
                "shell": {
                    "removed": list(raw.get("removed", [])),
                    "notes": dict(raw.get("notes", {})),
                    "overrides": dict(raw.get("overrides", {})),
                }
            },
        }

    def save_design_review_state(self, payload: dict) -> dict:
        if "pages" in payload:
            state = {
                "active_page": str(payload.get("active_page", "shell") or "shell"),
                "page_settings": dict(payload.get("page_settings", {"shell": {"enabled": True}})),
                "pages": dict(payload.get("pages", {})),
            }
        else:
            state = {
                "active_page": "shell",
                "page_settings": {"shell": {"enabled": True}},
                "pages": {
                    "shell": {
                        "removed": list(payload.get("removed", [])),
                        "notes": dict(payload.get("notes", {})),
                        "overrides": dict(payload.get("overrides", {})),
                    }
                },
            }
        path = self._design_review_path()
        path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "message": "Design review state saved.", "state": state, "path": str(path)}

    def dashboard_snapshot(self) -> dict:
        active_mode = self.family_support.active_mode()
        adult_names = [profile.display_name for profile in self.household.users.values() if profile.permissions == "adult"]
        parent_viewer = "Rebekah" if "Rebekah" in adult_names else (adult_names[0] if adult_names else "Chris")
        recent_activity = self.recent_activity(limit=20)
        integration_status = self.status()
        background_agents = self.background_agent_status(
            recent_activity=recent_activity,
            integration_status=integration_status,
        )
        memory_curator = self.memory_curator_snapshot(recent_activity=recent_activity)

        def card_payload(card) -> dict:
            return {
                "title": card.title,
                "status": card.status,
                "summary": card.summary,
                "details": list(card.details),
            }

        def event_payload(event) -> dict:
            return {
                "time": event.time,
                "owner": event.owner,
                "title": event.title,
                "note": event.note,
            }

        return {
            "day_label": self.snapshot.day_label,
            "location": self.household.location_label,
            "weather": self.snapshot.weather,
            "house_note": self.snapshot.house_note,
            "active_mode": {
                "mode": active_mode.mode,
                "status": active_mode.status,
                "reason": active_mode.reason,
                "actor": active_mode.actor,
                "timestamp": active_mode.timestamp,
            },
            "cards": {
                "body": card_payload(self.snapshot.body),
                "home": card_payload(self.snapshot.home),
                "mission": card_payload(self.snapshot.mission),
            },
            "body_home_mission": [
                card_payload(self.snapshot.body),
                card_payload(self.snapshot.home),
                card_payload(self.snapshot.mission),
            ],
            "events": [event_payload(event) for event in self.snapshot.events],
            "family_focus": self.snapshot.family_focus,
            "watch_items": self.snapshot.watch_items,
            "mode_brief": self.family_mode_brief(active_mode.mode),
            "departure_checklist": self.family_support.departure_checklist(),
            "departure_runs": self.list_departure_runs(limit=5),
            "message_drafts": self.family_support.list_drafts(limit=5),
            "anomalies": self.family_support.anomaly_watch(
                self.snapshot.home.details,
                self.snapshot.watch_items,
            ),
            "meal_plans": self.list_meal_plans(limit=5),
            "vehicle_plans": self.list_vehicle_plans(limit=5),
            "weather_plans": self.list_weather_plans(limit=5),
            "child_boundaries": self.child_boundaries(),
            "tutoring_summaries": self.tutoring_summaries(parent_viewer, limit=6),
            "printer_status": self.printer_status(),
            "workshop_inspections": self.list_workshop_inspections(limit=5),
            "vendor_preps": self.list_vendor_preps(limit=5),
            "cad_packages": self.list_cad_packages(limit=5),
            "print_preps": self.list_print_preps(limit=5),
            "material_recommendations": self.list_material_recommendations(limit=5),
            "safety_checks": self.list_safety_checks(limit=5),
            "inventory_summary": self.inventory_summary(),
            "voice_note_tasks": self.list_voice_note_tasks(limit=5),
            "home_overview": self.home_overview(),
            "home_actions": self.list_home_actions(limit=8),
            "climate_status": self.climate_status(),
            "access_overview": self.access_overview(),
            "garage_status": self.garage_status(),
            "leak_monitor": self.leak_monitor(),
            "cold_storage_monitor": self.cold_storage_monitor(),
            "outage_readiness": self.outage_readiness(),
            "perception_overview": self.perception_overview(),
            "memory_overview": self.memory_overview("Chris"),
            "catalyst_overview": self.catalyst_overview(),
            "google_workspace": self.google_workspace_summary(),
            "chronicle_timeline": self.chronicle_timeline(limit=5),
            "chronicle_theme_summary": self.chronicle_theme_summary(limit=20),
            "device_boundaries": self.list_device_boundaries(limit=6),
            "security_incidents": self.list_security_incidents(limit=8),
            "weather_advisories": self.list_weather_advisories(limit=5),
            "arrival_events": self.list_arrival_events(limit=5),
            "unlock_assessments": self.list_unlock_assessments(limit=5),
            "overnight_review": self.overnight_review(),
            "explainability": self.explainability_snapshot(),
            "brain_graph": self.brain_graph_snapshot(),
            "background_agents": background_agents,
            "agent_registry": self.agent_registry_snapshot(),
            "memory_curator": memory_curator,
        }

    def home_overview(self) -> dict:
        return self.home_support.home_overview()

    def list_home_actions(self, limit: int = 20) -> list[dict]:
        return self.home_support.store.list_actions(limit=limit)

    def room_scene(self, actor_name: str, room: str, scene_name: str, intent: str = "") -> dict:
        actor = self.get_actor(actor_name)
        return self.home_support.room_scene(actor.display_name, room, scene_name, intent=intent)

    def climate_status(self) -> list[dict]:
        return self.home_support.climate_status()

    def climate_control(
        self,
        actor_name: str,
        zone: str,
        hvac_mode: str,
        target_temperature: float | None = None,
        context: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.home_support.climate_control(
            actor.display_name,
            zone,
            hvac_mode,
            target_temperature=target_temperature,
            context=context,
        )

    def access_overview(self) -> dict:
        return self.home_support.access_overview()

    def access_control(self, actor_name: str, target: str, desired_state: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.home_support.access_control(actor.display_name, target, desired_state)

    def garage_status(self) -> list[dict]:
        return self.home_support.garage_status()

    def garage_safe_close(self, actor_name: str, target: str = "") -> dict:
        actor = self.get_actor(actor_name)
        return self.home_support.garage_safe_close(actor.display_name, target)

    def leak_monitor(self) -> dict:
        return self.home_support.leak_monitor()

    def cold_storage_monitor(self) -> dict:
        return self.home_support.cold_storage_monitor()

    def energy_window(self, appliance: str, request_text: str = "") -> dict:
        return self.home_support.energy_window(appliance, request_text=request_text)

    def outage_readiness(self) -> dict:
        return self.home_support.outage_readiness()

    def perception_overview(self) -> dict:
        return self.perception_support.perception_overview()

    def microphone_ingress(
        self,
        microphone: str,
        transcript: str,
        wake_word_detected: bool = False,
        actor_hint: str = "",
    ) -> dict:
        return self.perception_support.far_field_microphone_ingress(
            microphone,
            transcript,
            wake_word_detected=wake_word_detected,
            actor_hint=actor_hint,
        )

    def presence_update(self, sensor: str, room: str, occupied: bool, detail: str = "") -> dict:
        return self.perception_support.presence_sensor_update(sensor, room, occupied, detail=detail)

    def phone_presence_update(
        self,
        actor_name: str,
        device: str,
        state: str,
        zone: str = "",
        detail: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.perception_support.phone_presence_update(
            actor.display_name,
            device,
            state,
            zone=zone,
            detail=detail,
        )

    def camera_event(
        self,
        camera: str,
        event_type: str,
        detail: str,
        detected_object: str = "",
        confidence: str = "medium",
    ) -> dict:
        return self.perception_support.camera_event(
            camera,
            event_type,
            detail,
            detected_object=detected_object,
            confidence=confidence,
        )

    def package_rule(
        self,
        zone: str,
        preferred_drop: str,
        rain_sensitive: bool,
        note: str = "",
    ) -> dict:
        return self.perception_support.update_package_rule(zone, preferred_drop, rain_sensitive, note=note)

    def object_recognition(
        self,
        source: str,
        room: str,
        observed_object: str,
        detail: str = "",
        confidence: str = "medium",
    ) -> dict:
        return self.perception_support.object_recognition(
            source,
            room,
            observed_object,
            detail=detail,
            confidence=confidence,
        )

    def environmental_anomaly(
        self,
        category: str,
        source: str,
        reading: str,
        baseline: str,
        severity: str = "watch",
        detail: str = "",
    ) -> dict:
        return self.perception_support.environmental_anomaly(
            category,
            source,
            reading,
            baseline,
            severity=severity,
            detail=detail,
        )

    def privacy_state(self) -> dict:
        return self.perception_support.privacy_state()

    def update_privacy_state(
        self,
        kind: str,
        target: str,
        enabled: bool | None = None,
        muted: bool | None = None,
    ) -> dict:
        return self.perception_support.update_privacy_state(kind, target, enabled=enabled, muted=muted)

    def memory_overview(self, viewer_name: str) -> dict:
        viewer = self.get_actor(viewer_name)
        return self.memory_support.overview(viewer)

    def remember(
        self,
        actor_name: str,
        memory_type: str,
        scope: str,
        summary: str,
        detail: str,
        owner: str = "",
        project: str = "",
        tags: list[str] | None = None,
        sensitivity: str = "normal",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.memory_support.remember(
            actor,
            memory_type,
            scope,
            summary,
            detail,
            owner=owner,
            project=project,
            tags=tags,
            sensitivity=sensitivity,
        )

    def review_memory(
        self,
        viewer_name: str,
        memory_type: str = "",
        owner: str = "",
        project: str = "",
    ) -> list[dict]:
        viewer = self.get_actor(viewer_name)
        return self.memory_support.review(viewer, memory_type=memory_type, owner=owner, project=project)

    def forget_memory(self, viewer_name: str, entry_id: str) -> dict:
        viewer = self.get_actor(viewer_name)
        return self.memory_support.forget(viewer, entry_id)

    def export_memory(
        self,
        viewer_name: str,
        memory_type: str = "",
        owner: str = "",
        project: str = "",
    ) -> dict:
        viewer = self.get_actor(viewer_name)
        return self.memory_support.export(viewer, memory_type=memory_type, owner=owner, project=project)

    def memory_proposals(self, status: str = "") -> list[dict]:
        return self.memory_support.proposals(status=status)

    def resolve_memory_proposal(self, proposal_id: str, decision: str) -> dict:
        return self.memory_support.resolve_proposal(proposal_id, decision)

    def active_mode(self) -> dict:
        state = self.family_support.active_mode()
        return {
            "mode": state.mode,
            "status": state.status,
            "reason": state.reason,
            "actor": state.actor,
            "timestamp": state.timestamp,
        }

    def transition_mode(self, actor_name: str, mode: str, reason: str) -> dict:
        actor = self.get_actor(actor_name)
        state = self.family_support.transition_mode(actor.display_name, mode, reason)
        return {
            "mode": state.mode,
            "status": state.status,
            "reason": state.reason,
            "actor": state.actor,
            "timestamp": state.timestamp,
        }

    def family_mode_brief(self, mode: str = "") -> dict:
        active_mode = mode or self.family_support.active_mode().mode
        return self.family_support.mode_brief(
            active_mode,
            weather=self.snapshot.weather,
            home_details=self.snapshot.home.details,
            watch_items=self.snapshot.watch_items,
            event_titles=[event.title for event in self.snapshot.events],
        )

    def family_plan(self, actor_name: str, request: str) -> str:
        actor = self.get_actor(actor_name)
        active_mode = self.family_support.active_mode().mode
        return self.family_support.family_plan(actor.display_name, request, active_mode)

    def rebekah_command_center(self, request: str) -> str:
        active_mode = self.family_support.active_mode().mode
        return self.family_support.rebekah_command_center(request, active_mode)

    def troop_plan(self, actor_name: str, request: str) -> str:
        actor = self.get_actor(actor_name)
        return self.family_support.troop_plan(actor.display_name, request)

    def grocery_support(self, actor_name: str, request: str) -> str:
        actor = self.get_actor(actor_name)
        return self.family_support.grocery_support(actor.display_name, request)

    def departure_plan(self, actor_name: str, context: str = "") -> dict:
        actor = self.get_actor(actor_name)
        garage_items = self.garage_status()
        garage_note = ""
        if garage_items:
            first = garage_items[0]
            garage_note = f"{first.get('name', 'Garage')} is {first.get('state', 'unknown')}."
        return self.family_support.departure_orchestration(
            actor.display_name,
            context,
            self.snapshot.weather,
            garage_state=garage_note,
            family_focus=self.snapshot.family_focus,
        )

    def list_departure_runs(self, limit: int = 20) -> list[dict]:
        return self.family_support.list_departure_runs(limit=limit)

    def meal_plan(self, actor_name: str, request: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.family_support.meal_plan(actor.display_name, request)

    def list_meal_plans(self, limit: int = 20) -> list[dict]:
        return self.family_support.list_meal_plans(limit=limit)

    def vehicle_plan(self, actor_name: str, request: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.family_support.vehicle_assignment(actor.display_name, request, self.snapshot.weather)

    def list_vehicle_plans(self, limit: int = 20) -> list[dict]:
        return self.family_support.list_vehicle_plans(limit=limit)

    def weather_contingency(self, actor_name: str, request: str) -> dict:
        actor = self.get_actor(actor_name)
        active_mode = self.family_support.active_mode().mode
        return self.family_support.weather_contingency(
            actor.display_name,
            request,
            self.snapshot.weather,
            active_mode,
        )

    def list_weather_plans(self, limit: int = 20) -> list[dict]:
        return self.family_support.list_weather_plans(limit=limit)

    def draft_message(
        self,
        actor_name: str,
        audience: str,
        purpose: str,
        context: str,
        tone: str = "warm",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.family_support.draft_message(actor.display_name, audience, purpose, context, tone)

    def stage_parent_message(
        self,
        actor_name: str,
        audience: str,
        purpose: str,
        context: str,
        tone: str = "warm",
    ) -> dict:
        actor = self.get_actor(actor_name)
        draft = self.family_support.stage_parent_message(actor.display_name, audience, purpose, context, tone)
        approval_request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            actor=actor.display_name,
            room="family",
            request=f"Approve parent message to {audience} about {purpose}",
            action_class="EXECUTE_MEDIUM_RISK",
            second_factor_required=False,
            status="pending",
            rationale="Parent-facing communication must be reviewed before sending.",
        )
        self.approval_store.add(approval_request)
        draft["approval_request_id"] = approval_request.request_id
        return draft

    def list_message_drafts(self, limit: int = 20) -> list[dict]:
        return self.family_support.list_drafts(limit=limit)

    def update_message_draft(self, draft_id: str, status: str) -> dict | None:
        return self.family_support.update_draft_status(draft_id, status)

    def anomaly_watch(self) -> list[dict]:
        return self.family_support.anomaly_watch(
            self.snapshot.home.details,
            self.snapshot.watch_items,
        )

    def package_or_motion_monitor(
        self,
        actor_name: str,
        category: str,
        location: str,
        detail: str,
        severity: str = "watch",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.security_support.package_or_motion_monitor(
            actor.display_name,
            category,
            location,
            detail,
            severity=severity,
        )

    def safety_escalation(
        self,
        actor_name: str,
        hazard_type: str,
        source: str,
        detail: str,
        severity: str = "critical",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.security_support.safety_escalation(
            actor.display_name,
            hazard_type,
            source,
            detail,
            severity=severity,
        )

    def weather_advisory(self, actor_name: str, context: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.security_support.weather_advisory(actor.display_name, context, self.snapshot.weather)

    def child_arrival(self, actor_name: str, location: str, detail: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.security_support.child_arrival(actor.display_name, location, detail)

    def unlock_assessment(
        self,
        actor_name: str,
        target: str,
        requested_by_voice: bool = True,
        second_factor_present: bool = False,
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.security_support.unlock_assessment(
            actor.display_name,
            target,
            requested_by_voice,
            second_factor_present,
        )

    def overnight_review(self) -> dict:
        return self.security_support.overnight_review(self.snapshot.watch_items)

    def list_security_incidents(self, limit: int = 20) -> list[dict]:
        return self.security_support.list_incidents(limit=limit)

    def list_weather_advisories(self, limit: int = 20) -> list[dict]:
        return self.security_support.list_weather(limit=limit)

    def list_arrival_events(self, limit: int = 20) -> list[dict]:
        return self.security_support.list_arrivals(limit=limit)

    def list_unlock_assessments(self, limit: int = 20) -> list[dict]:
        return self.security_support.list_unlocks(limit=limit)

    def capture_voice_note(self, actor_name: str, source: str, note: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.family_support.capture_voice_note(actor.display_name, source, note)

    def list_voice_note_tasks(self, limit: int = 20) -> list[dict]:
        return self.family_support.list_voice_note_tasks(limit=limit)

    def update_voice_note_status(self, note_id: str, status: str) -> dict | None:
        return self.family_support.update_voice_note_status(note_id, status)

    def child_boundaries(self, actor_name: str | None = None) -> list[dict]:
        if actor_name:
            actor = self.get_actor(actor_name)
            return self.tutoring_support.child_boundaries(actor)
        children = [profile for profile in self.household.users.values() if profile.permissions == "child"]
        reports: list[dict] = []
        for child in children:
            reports.extend(self.tutoring_support.child_boundaries(child))
        return reports

    def tutor(self, actor_name: str, request: str, subject: str = "") -> dict:
        actor = self.get_actor(actor_name)
        return self.tutoring_support.tutoring_turn(actor, request, subject=subject)

    def tutoring_summaries(
        self,
        viewer_name: str,
        child_name: str = "",
        limit: int = 10,
    ) -> dict:
        viewer = self.get_actor(viewer_name)
        return self.tutoring_support.parent_summaries(viewer, child_name=child_name, limit=limit)

    def device_boundary_plan(self, actor_name: str, window_label: str = "") -> dict:
        actor = self.get_actor(actor_name)
        return self.tutoring_support.device_boundary_plan(actor, window_label=window_label)

    def list_device_boundaries(self, child_name: str = "", limit: int = 20) -> list[dict]:
        return self.tutoring_support.list_device_boundaries(child_name=child_name, limit=limit)

    def update_device_boundary_status(self, routine_id: str, status: str) -> dict | None:
        return self.tutoring_support.update_device_boundary_status(routine_id, status)

    def workshop_plan(self, actor_name: str, request: str) -> str:
        actor = self.get_actor(actor_name)
        return self.workshop_support.workshop_plan(actor.display_name, request)

    def printer_status(self) -> list[dict]:
        return self.workshop_support.printer_status()

    def material_recommendation(
        self,
        actor_name: str,
        part_name: str,
        use_case: str,
        requirements: str,
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.workshop_support.material_recommendation(actor.display_name, part_name, use_case, requirements)

    def cad_package(self, actor_name: str, part_name: str, dimensions: str, constraints: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.workshop_support.cad_package(actor.display_name, part_name, dimensions, constraints)

    def print_prep(
        self,
        actor_name: str,
        part_name: str,
        printer_id: str,
        material: str,
        profile_name: str,
        notes: str,
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.workshop_support.print_prep(
            actor.display_name,
            part_name,
            printer_id,
            material,
            profile_name,
            notes,
        )

    def safety_check(self, actor_name: str, operation: str, context: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.workshop_support.safety_check(actor.display_name, operation, context)

    def inventory_summary(self) -> list[dict]:
        return self.workshop_support.inventory_summary()

    def inspect_part(
        self,
        actor_name: str,
        part_name: str,
        request: str,
        observations: str,
        goals: str,
        image_path: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.workshop_support.inspect_part(
            actor.display_name,
            part_name,
            request,
            observations,
            goals,
            image_path=image_path,
        )

    def list_workshop_inspections(self, limit: int = 10) -> list[dict]:
        return self.workshop_support.store.list_inspections(limit=limit)

    def list_cad_packages(self, limit: int = 10) -> list[dict]:
        return self.workshop_support.list_cad_packages(limit=limit)

    def list_print_preps(self, limit: int = 10) -> list[dict]:
        return self.workshop_support.list_print_preps(limit=limit)

    def list_material_recommendations(self, limit: int = 10) -> list[dict]:
        return self.workshop_support.list_material_recommendations(limit=limit)

    def list_safety_checks(self, limit: int = 10) -> list[dict]:
        return self.workshop_support.list_safety_checks(limit=limit)

    def vendor_prep(
        self,
        actor_name: str,
        part_name: str,
        vendor_target: str,
        process: str,
        material: str,
        notes: str,
    ) -> dict:
        actor = self.get_actor(actor_name)
        prep = self.workshop_support.prepare_vendor_prep(
            actor.display_name,
            part_name,
            vendor_target,
            process,
            material,
            notes,
        )
        approval_request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            actor=actor.display_name,
            room="workshop",
            request=f"Approve vendor package for {part_name} to {vendor_target}",
            action_class="EXECUTE_MEDIUM_RISK",
            second_factor_required=False,
            status="pending",
            rationale="External vendor submission requires explicit approval before any quote request is sent.",
        )
        self.approval_store.add(approval_request)
        prep["approval_request_id"] = approval_request.request_id
        prep["status"] = "pending-approval"
        return self.workshop_support.save_vendor_prep(prep)

    def list_vendor_preps(self, limit: int = 10) -> list[dict]:
        return self.workshop_support.list_vendor_preps(limit=limit)

    def update_vendor_prep_status(self, prep_id: str, status: str) -> dict | None:
        return self.workshop_support.update_vendor_prep_status(prep_id, status)
