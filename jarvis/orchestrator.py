from __future__ import annotations

import uuid

from .config import AppConfig
from .models import RequestPlan, TaskClass, UserProfile
from .permissions import PermissionEngine


class JarvisOrchestrator:
    def __init__(self, config: AppConfig, permissions: PermissionEngine) -> None:
        self.config = config
        self.permissions = permissions

    def route(self, actor: UserProfile, room: str, request: str) -> RequestPlan:
        lowered = request.lower()
        decision = self.permissions.evaluate(actor, lowered)
        mode = self._infer_mode(room, lowered)
        module = self._select_module(mode, lowered)
        workstream = self._select_workstream(mode, module, lowered)
        task_class = self._select_task_class(mode, module, workstream, lowered)
        preferred_provider = self._select_provider(task_class, module, workstream, lowered)
        context_lane = self._select_context_lane(task_class, module, workstream)
        model = self._select_model(task_class, preferred_provider, lowered)
        rationale = (
            f"Mode '{mode}' maps to module '{module}', workstream '{workstream}', "
            f"task class '{task_class.value}', provider '{preferred_provider}', context lane '{context_lane}', "
            f"and model '{model}'. "
            f"Permission class is {decision.action_class.name}."
        )
        return RequestPlan(
            request_id=str(uuid.uuid4()),
            actor=actor.display_name,
            room=room,
            request=request,
            mode=mode,
            module=module,
            workstream=workstream,
            task_class=task_class,
            preferred_provider=preferred_provider,
            context_lane=context_lane,
            model=model,
            action_class=decision.action_class,
            allowed=decision.allowed,
            needs_approval=decision.needs_approval,
            second_factor_required=decision.second_factor_required,
            rationale=rationale,
        )

    def _infer_mode(self, room: str, request: str) -> str:
        if "scripture" in request or "prayer" in request or "chronicle" in request:
            return "chronicle-mode"
        if "workshop" in request or room == "workshop" or "printer" in request:
            return "workshop-mode"
        if "homework" in request or "quiz me" in request or "study" in request:
            return "tutor-mode"
        if "meeting" in request or room == "office" or "manuscript" in request:
            return "work-mode"
        if "dinner" in request or "grocery" in request or "family" in request:
            return "family-morning"
        return "ambient-associate"

    def _select_module(self, mode: str, request: str) -> str:
        mapping = {
            "chronicle-mode": "faith-and-formation",
            "workshop-mode": "workshop-copilot",
            "tutor-mode": "child-tutor",
            "work-mode": "executive-work",
            "family-morning": "family-logistics",
            "ambient-associate": "household-associate",
        }
        if "camera" in request or "scan" in request:
            return "perception-mesh"
        return mapping[mode]

    def _select_workstream(self, mode: str, module: str, request: str) -> str:
        if module == "executive-work":
            if "meeting" in request or "agenda" in request or "attendee" in request:
                if "criteria" in request or "framework" in request or "decision" in request:
                    return "decision-framework"
                return "meeting-prep"
            if "follow-up" in request or "follow up" in request or "transcript" in request:
                return "meeting-followup"
            if "manuscript" in request or "chapter" in request or "edit" in request:
                if "iron-clad" in request or "iron clad" in request:
                    return "iron-clad-editor"
                return "manuscript-editing"
            if "research" in request or "source" in request or "evidence" in request:
                return "research-summary"
            if "venture" in request or "market" in request or "signal" in request:
                return "venture-brief"
            if "confidential" in request or "redact" in request or "thermo" in request:
                return "confidentiality-filter"
            return "executive-brief"
        if module == "faith-and-formation":
            if "chronicle" in request:
                return "chronicle-reflection"
            if "prayer" in request:
                return "devotional-prayer"
            if "scripture" in request:
                return "devotional-scripture"
            return "devotional-pause"
        if module == "child-tutor":
            if "quiz me" in request or "warmup" in request:
                return "quiz-practice"
            if "presentation" in request or "slides" in request or "project" in request:
                return "presentation-rehearsal"
            if "outline" in request or "organize" in request:
                return "project-organization"
            if "write" in request or "answer" in request:
                return "assignment-boundary"
            return "homework-coaching"
        return mode

    def _select_task_class(self, mode: str, module: str, workstream: str, request: str) -> TaskClass:
        if any(keyword in request for keyword in ("party mode", "roundtable", "war room", "council")):
            return TaskClass.PARTY_MODE
        if workstream in {"research-summary", "venture-brief"}:
            return TaskClass.RESEARCH
        if workstream in {"confidentiality-filter", "iron-clad-editor"} or any(
            keyword in request for keyword in ("confidential", "private", "sensitive", "redact")
        ):
            return TaskClass.SENSITIVE_DRAFTING
        mapping = {
            "faith-and-formation": TaskClass.FORMATION,
            "workshop-copilot": TaskClass.WORKSHOP,
            "child-tutor": TaskClass.TUTORING,
            "executive-work": TaskClass.EXECUTIVE,
            "family-logistics": TaskClass.FAMILY,
            "household-associate": TaskClass.AMBIENT,
        }
        return mapping.get(module, TaskClass.AMBIENT)

    def _select_provider(self, task_class: TaskClass, module: str, workstream: str, request: str) -> str:
        if task_class in {TaskClass.SENSITIVE_DRAFTING, TaskClass.BACKGROUND}:
            return "ollama"
        if task_class in {TaskClass.FAMILY, TaskClass.AMBIENT} and not any(
            keyword in request for keyword in ("latest", "current", "today", "search", "source", "citation", "weather")
        ):
            return "ollama"
        if module == "workshop-copilot" and "prototype" not in request and "research" not in request:
            return "ollama"
        return "openai"

    def _select_context_lane(self, task_class: TaskClass, module: str, workstream: str) -> str:
        if task_class == TaskClass.PARTY_MODE:
            return "party-mode"
        if task_class == TaskClass.RESEARCH:
            return "research"
        if task_class == TaskClass.SENSITIVE_DRAFTING:
            return "restricted-local"
        if module == "executive-work":
            return "executive"
        if module == "family-logistics":
            return "family"
        if module == "faith-and-formation":
            return "formation"
        if module == "workshop-copilot":
            return "workshop"
        return "ambient"

    def _select_model(self, task_class: TaskClass, provider: str, request: str) -> str:
        if provider == "ollama":
            if task_class == TaskClass.BACKGROUND:
                return self.config.ollama_background_model
            if task_class in {TaskClass.FAMILY, TaskClass.AMBIENT}:
                return self.config.ollama_summarize_model
            return self.config.second_brain_model
        if "voice" in request or "talk" in request or "listen" in request:
            return self.config.openai_realtime_model
        if task_class in {
            TaskClass.EXECUTIVE,
            TaskClass.FORMATION,
            TaskClass.WORKSHOP,
            TaskClass.TUTORING,
            TaskClass.RESEARCH,
            TaskClass.PARTY_MODE,
            TaskClass.SENSITIVE_DRAFTING,
        }:
            return self.config.openai_text_model
        return self.config.openai_router_model
