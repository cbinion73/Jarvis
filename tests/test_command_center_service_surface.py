from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import jarvis.approvals as approvals_module
import jarvis.command_center_index as command_center_index_module
import jarvis.dining as dining_module
import jarvis.quarterly_review as quarterly_review_module
import jarvis.user_profile as user_profile_module
from jarvis.approvals import ApprovalQueue, init_approvals

if "fastapi" not in sys.modules:
    fastapi_stub = types.ModuleType("fastapi")
    responses_stub = types.ModuleType("fastapi.responses")
    staticfiles_stub = types.ModuleType("fastapi.staticfiles")
    uvicorn_stub = types.ModuleType("uvicorn")

    class _Route:
        def __init__(self, path: str, methods: set[str], endpoint) -> None:
            self.path = path
            self.methods = methods
            self.endpoint = endpoint

    class _Router:
        def __init__(self) -> None:
            self.routes: list[_Route] = []

    class _FastAPI:
        def __init__(self, *args, **kwargs) -> None:
            self.router = _Router()

        def _register(self, path: str, methods: set[str]):
            def decorator(fn):
                self.router.routes.append(_Route(path, methods, fn))
                return fn

            return decorator

        def get(self, path: str, *args, **kwargs):
            return self._register(path, {"GET"})

        def post(self, path: str, *args, **kwargs):
            return self._register(path, {"POST"})

        def put(self, path: str, *args, **kwargs):
            return self._register(path, {"PUT"})

        def patch(self, path: str, *args, **kwargs):
            return self._register(path, {"PATCH"})

        def delete(self, path: str, *args, **kwargs):
            return self._register(path, {"DELETE"})

        def websocket(self, path: str, *args, **kwargs):
            return self._register(path, {"WEBSOCKET"})

        def on_event(self, *args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

        def mount(self, *args, **kwargs) -> None:
            return None

    class _HTTPException(Exception):
        def __init__(self, status_code: int, detail: str = "") -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class _JSONResponse:
        def __init__(self, content, status_code: int = 200, headers: dict | None = None) -> None:
            self.body = json.dumps(content).encode("utf-8")
            self.status_code = status_code
            self.headers = headers or {}

    class _HTMLResponse(_JSONResponse):
        pass

    class _Response:
        def __init__(self, content=b"", status_code: int = 200, headers: dict | None = None, media_type: str | None = None) -> None:
            if isinstance(content, bytes):
                self.body = content
            elif isinstance(content, str):
                self.body = content.encode("utf-8")
            else:
                self.body = json.dumps(content).encode("utf-8")
            self.status_code = status_code
            self.headers = headers or {}
            self.media_type = media_type

    class _FileResponse(_JSONResponse):
        pass

    class _RedirectResponse(_JSONResponse):
        pass

    class _StaticFiles:
        def __init__(self, *args, **kwargs) -> None:
            return None

    class _BackgroundTasks:
        def add_task(self, *args, **kwargs) -> None:
            return None

    class _Request:
        base_url = "http://testserver/"

        def __init__(self, base_url: str = "http://testserver/") -> None:
            self.base_url = base_url

    class _UploadFile:
        filename = ""
        content_type = "application/octet-stream"

    class _WebSocket:
        async def accept(self) -> None:
            return None

    class _WebSocketDisconnect(Exception):
        pass

    def _return_default(value=None, **kwargs):
        return value

    fastapi_stub.BackgroundTasks = _BackgroundTasks
    fastapi_stub.FastAPI = _FastAPI
    fastapi_stub.File = _return_default
    fastapi_stub.Form = _return_default
    fastapi_stub.HTTPException = _HTTPException
    fastapi_stub.Query = _return_default
    fastapi_stub.Request = _Request
    fastapi_stub.UploadFile = _UploadFile
    fastapi_stub.WebSocket = _WebSocket
    fastapi_stub.WebSocketDisconnect = _WebSocketDisconnect
    responses_stub.FileResponse = _FileResponse
    responses_stub.HTMLResponse = _HTMLResponse
    responses_stub.JSONResponse = _JSONResponse
    responses_stub.RedirectResponse = _RedirectResponse
    responses_stub.Response = _Response
    staticfiles_stub.StaticFiles = _StaticFiles
    uvicorn_stub.run = lambda *args, **kwargs: None
    sys.modules["fastapi"] = fastapi_stub
    sys.modules["fastapi.responses"] = responses_stub
    sys.modules["fastapi.staticfiles"] = staticfiles_stub
    sys.modules["uvicorn"] = uvicorn_stub

if "langgraph.graph" not in sys.modules:
    langgraph_module = types.ModuleType("langgraph")
    graph_module = types.ModuleType("langgraph.graph")

    class _StubStateGraph:
        def __init__(self, *_args, **_kwargs) -> None:
            self._nodes: dict[str, object] = {}

        def add_node(self, name: str, fn: object) -> None:
            self._nodes[name] = fn

        def add_edge(self, *_args, **_kwargs) -> None:
            return None

        def compile(self):
            class _Compiled:
                def invoke(self, state):
                    return state

            return _Compiled()

    graph_module.END = "END"
    graph_module.START = "START"
    graph_module.StateGraph = _StubStateGraph
    langgraph_module.graph = graph_module
    sys.modules["langgraph"] = langgraph_module
    sys.modules["langgraph.graph"] = graph_module

import jarvis.service as service_module


class _StubSupervisionSupport:
    def evaluate_action(
        self,
        *,
        agent_id: str,
        action_type: str,
        requested_outcome: str,
        trust_zone_id: str = "",
        lane_id: str = "",
        arena_id: str = "",
        context: dict | None = None,
    ) -> dict:
        return {
            "resolution": "stage",
            "sandbox_required": False,
            "approval_required": True,
            "trust_zone_id": trust_zone_id,
            "lane_id": lane_id,
            "requested_outcome": requested_outcome,
        }


class _FailingHomeDashboardDB:
    def get_dashboard_data(self) -> dict:
        raise RuntimeError("postgres unavailable")


class _FailingHomeReadDB:
    def __getattr__(self, _name: str):
        def _fail(*_args, **_kwargs):
            raise RuntimeError("postgres unavailable")

        return _fail


class _StubRuntime:
    def __init__(self) -> None:
        self.config = SimpleNamespace(
            tts_provider="fish",
            tts_fallbacks=[],
            stt_provider="auto",
            stt_fallbacks=[],
            elevenlabs_voice="",
            elevenlabs_api_key="",
            openai_api_key="",
            localai_base_url="",
            piper_binary="piper",
            piper_model_path=None,
            piper_speaker="0",
            second_brain_enabled=False,
        )
        self.config.load_household = lambda: SimpleNamespace(location_label="Home")
        self.supervision_support = _StubSupervisionSupport()
        self._accounts = [
            {
                "account_id": "acct-google-1",
                "owner_user_id": "chris",
                "owner_display_name": "Chris",
                "provider": "google",
                "service_scope": "mail_calendar",
                "label": "Chris Google",
                "login_hint": "chris@example.com",
                "status": "connected",
                "notes": "Family inbox and calendar.",
                "connection": {"status": "connected"},
            }
        ]
        self._identity_members = [
            {
                "display_name": "Chris",
                "user_id": "chris",
                "role": "parent",
                "permissions": "admin",
                "trust_level": "trusted",
                "preferred_tone": "calm and direct",
                "privacy_boundary": "personal",
                "notes": "Primary operator.",
                "device_ids": ["device-1"],
                "active": True,
            }
        ]
        self._identity_devices = [{"label": "JarvisPhone", "device_id": "device-1"}]
        self._mission_outputs = {"mission-1": []}
        self._delegation_reports = {"mission-1": []}
        self._artifact_outcomes = []
        self._autonomy_states = []
        self._research_tasks = []
        self._work_objects = {
            "checklist": {
                "checklist-1": {
                    "checklist_id": "checklist-1",
                    "object_kind": "checklist",
                    "title": "Scout campout checklist",
                    "topic": "the Scout campout",
                    "status": "created",
                }
            }
        }
        self._mission_work_state = {
            "mission_id": "mission-1",
            "summary": {
                "agents": 2,
                "active_tasks": 1,
                "blocked_tasks": 0,
                "pending_reviews": 1,
                "pending_handoffs": 1,
                "pending_transfers": 0,
                "escalations": 0,
                "duplicate_suppressions": 0,
                "delegations_requested": 1,
                "delegations_completed_with_output": 0,
                "delegations_unavailable": 0,
            },
            "agent_work_states": {
                "ambient-router": {
                    "role": "orchestrator",
                    "status": "active",
                    "ownership_mode": "lead",
                    "current_focus": "Keep mission continuity visible.",
                    "active_tasks": [{"title": "Support mission continuity"}],
                    "blocked_tasks": [],
                    "pending_reviews": [],
                    "last_handoff_at": "",
                },
                "storm": {
                    "role": "weather-intelligence",
                    "status": "ready",
                    "ownership_mode": "supporting",
                    "current_focus": "Review the mission brief.",
                    "active_tasks": [],
                    "blocked_tasks": [],
                    "pending_reviews": [{"title": "Review mission brief"}],
                    "last_handoff_at": "",
                },
            },
            "handoffs": [
                {
                    "handoff_id": "handoff-1",
                    "from_agent": "ambient-router",
                    "to_agent": "storm",
                    "task_id": "task-1",
                    "status": "accepted",
                }
            ],
            "delegations": [
                {
                    "delegation_id": "delegation-1",
                    "delegator_agent": "ambient-router",
                    "delegate_agent": "storm",
                    "task_id": "task-1",
                    "scope": "Weather review",
                    "status": "accepted",
                    "handoff_id": "handoff-1",
                    "inspectable_output_status": "requested",
                    "artifact_ref": "",
                    "report_id": "",
                    "output_id": "",
                    "producer_agent": "",
                }
            ],
            "delegation_reports": [],
            "outputs": [],
            "escalations": [],
            "duplicate_suppressions": [],
        }

    def _try_handle_calendar_event(self, request: str):
        return SimpleNamespace(output_text=f"Stub calendar write handled: {request}")

    def stage_email_draft(self, payload: dict) -> dict:
        return {
            "ok": True,
            "status": "staged",
            "subject": str(payload.get("subject") or "Email draft from JARVIS"),
            "recipient_email": str(payload.get("recipient_email") or "recipient@example.com"),
            "notes": str(payload.get("notes") or ""),
        }

    def draft_message(self, actor: str, audience: str, purpose: str, context: str, tone: str = "warm") -> dict:
        return {
            "draft_id": "draft-1",
            "actor": actor,
            "audience": audience,
            "purpose": purpose,
            "context": context,
            "tone": tone,
            "body": f"Draft for {audience}",
            "status": "staged",
        }

    def storm_weather_snapshot(self, force: bool = False) -> dict:
        return {
            "summary": "Partly cloudy with a low chance of rain.",
            "current": {
                "temperature_f": 74,
                "condition": "Partly cloudy",
                "high_f": 79,
                "low_f": 63,
                "humidity": 42,
                "wind": "6 mph NW",
            },
            "alerts": [],
            "forced": force,
        }

    def execute_sandbox_job(self, *, actor_name: str, job_id: str, triggered_by: str) -> dict:
        return {"ok": True, "accepted": True, "job": {"job_id": job_id, "status": "sandbox-queued"}}

    def mission_snapshot(self, mission_id: str) -> dict:
        return {
            "mission_id": mission_id,
            "title": "Stub Mission",
            "status": "active",
            "continuity_callback": "We discussed this before: Health was previously stated as one of the highest priorities.",
            "linked_memories": ["Health was previously stated as one of the highest priorities."],
            "selected_agents": ["ambient-router", "storm"],
            "task_agent_labels": ["Mission Planner"],
            "work_state_summary": dict(self._mission_work_state["summary"]),
            "outputs_detail": [dict(item) for item in self._mission_outputs.get(mission_id, [])],
            "delegation_reports": [dict(item) for item in self._delegation_reports.get(mission_id, [])],
        }

    def mission_control_snapshot(self, actor_name: str = "Chris") -> dict:
        return {
            "generated_at": "2026-06-11T12:00:00Z",
            "actor": actor_name,
            "summary": {"active_missions": 1},
            "active_missions": [
                {
                    "mission_id": "mission-1",
                    "title": "Health Reset",
                    "brief": "Rebuild steady health momentum.",
                    "brief_summary": {"why_it_matters": "Health has received less attention than the other major missions."},
                    "why_this_matters": "Health has received less attention than the other major missions.",
                    "next_step": "Stage a travel-resistant workout plan.",
                    "progress_signal": "Consistency matters more than intensity right now.",
                    "linked_memories": [
                        "Health was previously stated as one of the highest priorities.",
                    ],
                    "continuity_callback": "We discussed this before: Health was previously stated as one of the highest priorities.",
                    "background_prepared_outputs": [
                        {"summary": "Travel-resistant workout plan drafted."},
                    ],
                    "accountability_update": {
                        "headline": "Mission is active and ready for the next review.",
                    },
                    "mission_review": {
                        "carry_message": "You do not need to carry the whole health mission mentally today.",
                    },
                }
            ],
            "conversation_routes": [{"route": "/health-center", "route_label": "Open Health"}],
            "recommended_route": {"route": "/health-center", "route_label": "Open Health"},
        }

    def mission_work_state_snapshot(self, mission_id: str) -> dict:
        return json.loads(json.dumps(self._mission_work_state))

    def mission_outputs(self, mission_id: str) -> list[dict]:
        return [dict(item) for item in self._mission_outputs.get(mission_id, [])]

    def mission_delegation_reports(self, mission_id: str) -> list[dict]:
        return [dict(item) for item in self._delegation_reports.get(mission_id, [])]

    def mission_delegation_report(self, mission_id: str, report_id: str) -> dict | None:
        for item in self._delegation_reports.get(mission_id, []):
            if item.get("report_id") == report_id:
                return dict(item)
        return None

    def record_artifact_outcome(
        self,
        actor_name: str,
        *,
        target_kind: str,
        target_id: str,
        outcome: str,
        mission_id: str = "",
        note: str = "",
    ) -> dict:
        allowed = {"used", "completed", "helpful", "not_used", "needs_revision", "abandoned"}
        cleaned_kind = str(target_kind or "").strip()
        cleaned_target_id = str(target_id or "").strip()
        cleaned_outcome = str(outcome or "").strip().lower()
        cleaned_mission_id = str(mission_id or "").strip()
        if cleaned_outcome not in allowed:
            raise ValueError("outcome must be one of: used, completed, helpful, not_used, needs_revision, abandoned")
        if cleaned_kind == "delegation_report":
            if not cleaned_mission_id:
                raise ValueError("mission_id is required for delegation_report outcome capture")
            report = self.mission_delegation_report(cleaned_mission_id, cleaned_target_id)
            if report is None:
                raise KeyError("Delegation report not found.")
            target = {
                "target_kind": "delegation_report",
                "target_id": cleaned_target_id,
                "mission_id": cleaned_mission_id,
                "target_category": "delegated_output",
                "target_label": report.get("title", "Delegation report"),
                "artifact_ref": report.get("artifact_ref", ""),
                "storage_mode": "mission_delegation_report_record",
                "backing_store_files": [],
            }
        elif cleaned_kind == "checklist":
            record = dict(self._work_objects.get("checklist", {}).get(cleaned_target_id) or {})
            if not record:
                raise KeyError("checklist not found.")
            target = {
                "target_kind": "checklist",
                "target_id": cleaned_target_id,
                "mission_id": "",
                "target_category": "work_object",
                "target_label": record.get("title", "Checklist"),
                "artifact_ref": "",
                "storage_mode": "persisted_local_object_record",
                "backing_store_files": ["checklists.json", "checklists_log.jsonl"],
            }
        else:
            raise ValueError("Unsupported target_kind. Expected one of: checklist, delegation_report")

        recorded = {
            "outcome_id": f"outcome-{len(self._artifact_outcomes) + 1}",
            "recorded_at": "2026-06-28T13:00:00Z",
            "recorded_by": actor_name,
            "target_kind": target["target_kind"],
            "target_id": target["target_id"],
            "mission_id": target["mission_id"],
            "target_category": target["target_category"],
            "target_label": target["target_label"],
            "artifact_ref": target["artifact_ref"],
            "storage_mode": target["storage_mode"],
            "backing_store_files": list(target["backing_store_files"]),
            "outcome": cleaned_outcome,
            "note": str(note or "").strip(),
        }
        self._artifact_outcomes.append(recorded)
        history = [
            dict(item)
            for item in self._artifact_outcomes
            if item["target_kind"] == target["target_kind"]
            and item["target_id"] == target["target_id"]
            and item["mission_id"] == target["mission_id"]
        ]
        return {
            "message": "Outcome recorded. No automatic learning or behavior change was triggered in this path.",
            "target": dict(target),
            "recorded_outcome": recorded,
            "outcome_history": history,
            "allowed_outcomes": sorted(list(allowed)),
            "learning_effect": "none",
        }

    def artifact_outcome_snapshot(self, *, target_kind: str, target_id: str, mission_id: str = "") -> dict:
        cleaned_kind = str(target_kind or "").strip()
        cleaned_target_id = str(target_id or "").strip()
        cleaned_mission_id = str(mission_id or "").strip()
        if cleaned_kind == "delegation_report":
            report = self.mission_delegation_report(cleaned_mission_id, cleaned_target_id)
            if report is None:
                raise KeyError("Delegation report not found.")
            target = {
                "target_kind": "delegation_report",
                "target_id": cleaned_target_id,
                "mission_id": cleaned_mission_id,
                "target_category": "delegated_output",
                "target_label": report.get("title", "Delegation report"),
                "artifact_ref": report.get("artifact_ref", ""),
                "storage_mode": "mission_delegation_report_record",
                "backing_store_files": [],
            }
        elif cleaned_kind == "checklist":
            record = dict(self._work_objects.get("checklist", {}).get(cleaned_target_id) or {})
            if not record:
                raise KeyError("checklist not found.")
            target = {
                "target_kind": "checklist",
                "target_id": cleaned_target_id,
                "mission_id": "",
                "target_category": "work_object",
                "target_label": record.get("title", "Checklist"),
                "artifact_ref": "",
                "storage_mode": "persisted_local_object_record",
                "backing_store_files": ["checklists.json", "checklists_log.jsonl"],
            }
        else:
            raise ValueError("Unsupported target_kind. Expected one of: checklist, delegation_report")
        history = [
            dict(item)
            for item in self._artifact_outcomes
            if item["target_kind"] == target["target_kind"]
            and item["target_id"] == target["target_id"]
            and item["mission_id"] == target["mission_id"]
        ]
        return {
            "target": dict(target),
            "outcome_history": history,
            "latest_outcome": dict(history[-1]) if history else {},
            "allowed_outcomes": ["abandoned", "completed", "helpful", "needs_revision", "not_used", "used"],
            "learning_effect": "none",
        }

    def artifact_outcome_summary(self, *, mission_id: str = "", limit: int = 12) -> dict:
        cleaned_mission_id = str(mission_id or "").strip()
        filtered = [
            dict(item)
            for item in self._artifact_outcomes
            if not cleaned_mission_id or item["mission_id"] == cleaned_mission_id
        ]
        counts_by_outcome = {}
        counts_by_target_kind = {}
        counts_by_mission = {}
        for item in filtered:
            counts_by_outcome[item["outcome"]] = counts_by_outcome.get(item["outcome"], 0) + 1
            counts_by_target_kind[item["target_kind"]] = counts_by_target_kind.get(item["target_kind"], 0) + 1
            mission_key = item["mission_id"] or "unscoped"
            counts_by_mission[mission_key] = counts_by_mission.get(mission_key, 0) + 1
        recent = [dict(item) for item in reversed(filtered[-max(1, min(int(limit or 12), 50)):])]
        return {
            "mission_id": cleaned_mission_id,
            "total_records": len(filtered),
            "counts_by_outcome": counts_by_outcome,
            "counts_by_target_kind": counts_by_target_kind,
            "counts_by_mission": counts_by_mission,
            "recent_outcomes": recent,
            "allowed_outcomes": ["abandoned", "completed", "helpful", "needs_revision", "not_used", "used"],
            "learning_effect": "none",
        }

    def create_research_task(
        self,
        actor_name: str,
        *,
        title: str,
        question: str,
        desired_scope: str = "",
        status: str = "queued",
        constraints: list[str] | None = None,
        source_expectations: list[str] | None = None,
    ) -> dict:
        cleaned_title = str(title or "").strip()
        cleaned_question = str(question or "").strip()
        cleaned_status = str(status or "").strip().lower() or "queued"
        if not cleaned_title:
            raise ValueError("title is required")
        if not cleaned_question:
            raise ValueError("question is required")
        if cleaned_status not in {"queued", "in_progress", "blocked", "completed"}:
            raise ValueError("status must be one of: queued, in_progress, blocked, completed")
        recorded = {
            "task_id": f"research-task-{len(self._research_tasks) + 1}",
            "object_kind": "research_task",
            "actor": actor_name,
            "title": cleaned_title,
            "question": cleaned_question,
            "desired_scope": str(desired_scope or "").strip(),
            "status": cleaned_status,
            "constraints": [str(item).strip() for item in list(constraints or []) if str(item).strip()],
            "source_expectations": [str(item).strip() for item in list(source_expectations or []) if str(item).strip()],
            "created_at": "2026-06-28T14:00:00Z",
            "updated_at": "2026-06-28T14:00:00Z",
            "truth_mode": "explicit_intent_only",
            "research_performed": False,
            "source_discovery_performed": False,
            "autonomous_execution": False,
            "evidence_items": [],
            "evidence_refs": [],
            "synthesis": {},
        }
        self._research_tasks.append(recorded)
        return {
            "message": "Research task captured. It is queued intent only until real research work is explicitly performed.",
            "task": dict(recorded),
            "research_effect": "not_performed",
            "allowed_statuses": ["blocked", "completed", "in_progress", "queued"],
        }

    def create_autonomy_state(
        self,
        actor_name: str,
        *,
        title: str,
        objective: str,
        status: str = "queued",
        current_focus: str = "",
        next_step: str = "",
        requested_scope: str = "",
        initiation_reason: str = "",
        approval_state: str = "required",
        approval_required: bool = True,
        allowed_action_boundary: str = "",
        blocked_reason: str = "",
    ) -> dict:
        cleaned_title = str(title or "").strip()
        cleaned_objective = str(objective or "").strip()
        cleaned_status = str(status or "").strip().lower() or "queued"
        if not cleaned_title:
            raise ValueError("title is required")
        if not cleaned_objective:
            raise ValueError("objective is required")
        if not str(requested_scope or "").strip():
            raise ValueError("requested_scope is required")
        if not str(initiation_reason or "").strip():
            raise ValueError("initiation_reason is required")
        if cleaned_status not in {"queued", "in_progress", "blocked", "completed"}:
            raise ValueError("status must be one of: queued, in_progress, blocked, completed")
        recorded = {
            "autonomy_id": f"autonomy-{len(self._autonomy_states) + 1}",
            "object_kind": "autonomy_state",
            "initiated_by": actor_name,
            "title": cleaned_title,
            "objective": cleaned_objective,
            "status": cleaned_status,
            "current_focus": str(current_focus or "").strip(),
            "next_step": str(next_step or "").strip(),
            "requested_scope": str(requested_scope or "").strip(),
            "initiation_reason": str(initiation_reason or "").strip(),
            "approval_required": bool(approval_required),
            "approval_state": str(approval_state or "").strip().lower() or "required",
            "allowed_action_boundary": str(allowed_action_boundary or "").strip() or "record_visibility_only",
            "blocked_reason": str(blocked_reason or "").strip() or "autonomy execution is not enabled in this slice",
            "created_at": "2026-06-28T17:00:00Z",
            "updated_at": "2026-06-28T17:00:00Z",
            "visibility_mode": "recorded_state_only",
            "autonomous_execution_recorded": False,
            "background_execution_claimed": False,
            "progress_summary": "",
            "current_control_posture": "recorded_active",
            "last_control_action": "",
            "last_control_reason": "",
            "last_control_changed_by": "",
            "last_control_changed_at": "",
            "control_history": [],
            "readiness_state": "not_ready",
            "readiness_reason": "",
            "approval_gate_status": "approval_not_satisfied",
            "last_readiness_changed_by": "",
            "last_readiness_changed_at": "",
            "readiness_history": [],
            "local_follow_through_status": "not_triggered",
            "last_follow_through_effect": "",
            "last_follow_through_triggered_by": "",
            "last_follow_through_triggered_at": "",
            "last_follow_through_artifact_path": "",
            "follow_through_history": [],
        }
        self._autonomy_states.append(recorded)
        return {
            "message": (
                "Autonomy initiation recorded. This is an inspectable initiation-boundary record only; it does not mean autonomous execution has started, "
                "approval has been bypassed, or background work is already in progress."
            ),
            "autonomy_state": dict(recorded),
            "autonomy_effect": "visibility_only",
            "allowed_statuses": ["blocked", "completed", "in_progress", "queued"],
            "allowed_approval_states": ["approved", "not_requested", "not_required", "required"],
            "allowed_plan_action_statuses": ["proposed_not_run"],
            "allowed_control_actions": ["abort", "pause", "resume"],
            "allowed_control_postures": ["aborted", "paused", "recorded_active"],
            "allowed_readiness_states": ["not_ready", "ready_pending_approval", "ready_within_boundary"],
            "allowed_follow_through_statuses": ["local_proof_created", "not_triggered"],
        }

    def autonomy_state_snapshot(self, autonomy_id: str) -> dict:
        for item in self._autonomy_states:
            if item["autonomy_id"] == autonomy_id:
                return {
                    "autonomy_state": dict(item),
                    "autonomy_effect": "visibility_only",
                    "allowed_statuses": ["blocked", "completed", "in_progress", "queued"],
                    "allowed_approval_states": ["approved", "not_requested", "not_required", "required"],
                    "allowed_plan_action_statuses": ["proposed_not_run"],
                    "allowed_control_actions": ["abort", "pause", "resume"],
                    "allowed_control_postures": ["aborted", "paused", "recorded_active"],
                    "allowed_readiness_states": ["not_ready", "ready_pending_approval", "ready_within_boundary"],
                    "allowed_follow_through_statuses": ["local_proof_created", "not_triggered"],
                }
        raise KeyError(f"Unknown autonomy state: {autonomy_id}")

    def autonomy_state_queue_snapshot(self) -> dict:
        counts_by_status = {}
        for item in self._autonomy_states:
            counts_by_status[item["status"]] = counts_by_status.get(item["status"], 0) + 1
        return {
            "autonomy_states": [dict(item) for item in reversed(self._autonomy_states)],
            "counts_by_status": counts_by_status,
            "total_states": len(self._autonomy_states),
            "autonomy_effect": "visibility_only",
            "allowed_statuses": ["blocked", "completed", "in_progress", "queued"],
            "allowed_approval_states": ["approved", "not_requested", "not_required", "required"],
            "allowed_plan_action_statuses": ["proposed_not_run"],
            "allowed_control_actions": ["abort", "pause", "resume"],
            "allowed_control_postures": ["aborted", "paused", "recorded_active"],
            "allowed_readiness_states": ["not_ready", "ready_pending_approval", "ready_within_boundary"],
            "allowed_follow_through_statuses": ["local_proof_created", "not_triggered"],
        }

    def add_autonomy_action_plan(
        self,
        autonomy_id: str,
        *,
        planning_note: str = "",
        proposed_actions: list[dict] | None = None,
    ) -> dict:
        if not proposed_actions:
            raise ValueError("at least one proposed action is required")
        for item in self._autonomy_states:
            if item["autonomy_id"] == autonomy_id:
                normalized = []
                for index, action in enumerate(proposed_actions, start=1):
                    title = str(action.get("title") or action.get("action") or action.get("label") or "").strip()
                    if not title:
                        raise ValueError("each proposed action requires a title")
                    approval_needed = bool(action.get("approval_needed", action.get("approval_required", True)))
                    approval_state = str(action.get("approval_state", "required") or "").strip().lower() or "required"
                    if not approval_needed and approval_state == "required":
                        approval_state = "not_required"
                    normalized.append(
                        {
                            "action_id": f"{autonomy_id}-action-{index}",
                            "title": title,
                            "rationale": str(action.get("rationale", "") or "").strip(),
                            "approval_needed": approval_needed,
                            "approval_state": approval_state,
                            "execution_status": "proposed_not_run",
                            "sequence": index,
                            "planned_at": "2026-06-28T17:05:00Z",
                        }
                    )
                item["planning_note"] = str(planning_note or "").strip()
                item["proposed_actions"] = normalized
                item["planned_action_count"] = len(normalized)
                item["has_proposed_plan"] = True
                item["updated_at"] = "2026-06-28T17:05:00Z"
                return {
                    "message": "Autonomy action plan recorded. These actions are proposed only and remain not run until a later path explicitly records real execution.",
                    "autonomy_state": dict(item),
                    "autonomy_effect": "visibility_only",
                    "allowed_statuses": ["blocked", "completed", "in_progress", "queued"],
                    "allowed_approval_states": ["approved", "not_requested", "not_required", "required"],
                    "allowed_plan_action_statuses": ["proposed_not_run"],
                    "allowed_control_actions": ["abort", "pause", "resume"],
                    "allowed_control_postures": ["aborted", "paused", "recorded_active"],
                    "allowed_readiness_states": ["not_ready", "ready_pending_approval", "ready_within_boundary"],
                    "allowed_follow_through_statuses": ["local_proof_created", "not_triggered"],
                }
        raise KeyError(f"Unknown autonomy state: {autonomy_id}")

    def apply_autonomy_control_action(
        self,
        actor_name: str,
        autonomy_id: str,
        *,
        action: str,
        control_reason: str = "",
    ) -> dict:
        cleaned_action = str(action or "").strip().lower()
        if cleaned_action not in {"pause", "resume", "abort"}:
            raise ValueError("action must be one of: abort, pause, resume")
        if not str(control_reason or "").strip():
            raise ValueError("control_reason is required")
        for item in self._autonomy_states:
            if item["autonomy_id"] == autonomy_id:
                current_posture = str(item.get("current_control_posture", "recorded_active") or "recorded_active")
                if cleaned_action == "pause":
                    if current_posture == "aborted":
                        raise ValueError("aborted autonomy state cannot be paused")
                    resulting_posture = "paused"
                elif cleaned_action == "resume":
                    if current_posture == "aborted":
                        raise ValueError("aborted autonomy state cannot be resumed")
                    resulting_posture = "recorded_active"
                else:
                    resulting_posture = "aborted"
                control_entry = {
                    "action": cleaned_action,
                    "reason": str(control_reason or "").strip(),
                    "changed_by": actor_name,
                    "changed_at": "2026-06-28T17:10:00Z",
                    "resulting_posture": resulting_posture,
                }
                item["current_control_posture"] = resulting_posture
                item["last_control_action"] = cleaned_action
                item["last_control_reason"] = str(control_reason or "").strip()
                item["last_control_changed_by"] = actor_name
                item["last_control_changed_at"] = "2026-06-28T17:10:00Z"
                item["control_history"] = [*list(item.get("control_history") or []), control_entry]
                item["updated_at"] = "2026-06-28T17:10:00Z"
                return {
                    "message": "Autonomy control transition recorded. This updates recorded autonomy state posture only; it does not prove real background execution was running, paused, resumed, or interrupted.",
                    "autonomy_state": dict(item),
                    "autonomy_effect": "visibility_only",
                    "allowed_statuses": ["blocked", "completed", "in_progress", "queued"],
                    "allowed_approval_states": ["approved", "not_requested", "not_required", "required"],
                    "allowed_plan_action_statuses": ["proposed_not_run"],
                    "allowed_control_actions": ["abort", "pause", "resume"],
                    "allowed_control_postures": ["aborted", "paused", "recorded_active"],
                    "allowed_readiness_states": ["not_ready", "ready_pending_approval", "ready_within_boundary"],
                    "allowed_follow_through_statuses": ["local_proof_created", "not_triggered"],
                }
        raise KeyError(f"Unknown autonomy state: {autonomy_id}")

    def apply_autonomy_readiness_state(
        self,
        actor_name: str,
        autonomy_id: str,
        *,
        readiness_state: str,
        readiness_reason: str = "",
    ) -> dict:
        cleaned_readiness_state = str(readiness_state or "").strip().lower()
        if cleaned_readiness_state not in {"not_ready", "ready_pending_approval", "ready_within_boundary"}:
            raise ValueError("readiness_state must be one of: not_ready, ready_pending_approval, ready_within_boundary")
        if not str(readiness_reason or "").strip():
            raise ValueError("readiness_reason is required")
        for item in self._autonomy_states:
            if item["autonomy_id"] == autonomy_id:
                control_posture = str(item.get("current_control_posture", "recorded_active") or "recorded_active")
                if control_posture == "aborted" and cleaned_readiness_state != "not_ready":
                    raise ValueError("aborted autonomy state cannot be marked ready")
                approval_state = str(item.get("approval_state", "required") or "required").strip().lower()
                approval_required = bool(item.get("approval_required", False))
                if cleaned_readiness_state == "ready_within_boundary":
                    if approval_required and approval_state not in {"approved", "not_required"}:
                        raise ValueError("ready_within_boundary requires approval to be satisfied or not required")
                    approval_gate_status = "within_boundary"
                elif cleaned_readiness_state == "ready_pending_approval":
                    if not approval_required or approval_state in {"approved", "not_required"}:
                        raise ValueError("ready_pending_approval requires an unsatisfied approval gate")
                    approval_gate_status = "approval_pending"
                else:
                    approval_gate_status = "approval_not_satisfied"
                entry = {
                    "readiness_state": cleaned_readiness_state,
                    "readiness_reason": str(readiness_reason or "").strip(),
                    "approval_gate_status": approval_gate_status,
                    "changed_by": actor_name,
                    "changed_at": "2026-06-28T17:20:00Z",
                }
                item["readiness_state"] = cleaned_readiness_state
                item["readiness_reason"] = str(readiness_reason or "").strip()
                item["approval_gate_status"] = approval_gate_status
                item["last_readiness_changed_by"] = actor_name
                item["last_readiness_changed_at"] = "2026-06-28T17:20:00Z"
                item["readiness_history"] = [*list(item.get("readiness_history") or []), entry]
                item["updated_at"] = "2026-06-28T17:20:00Z"
                return {
                    "message": "Autonomy readiness recorded. This is a stored approval-gated readiness posture only; it does not mean execution started, background work is occurring, or approval has been bypassed.",
                    "autonomy_state": dict(item),
                    "autonomy_effect": "visibility_only",
                    "allowed_statuses": ["blocked", "completed", "in_progress", "queued"],
                    "allowed_approval_states": ["approved", "not_requested", "not_required", "required"],
                    "allowed_plan_action_statuses": ["proposed_not_run"],
                    "allowed_control_actions": ["abort", "pause", "resume"],
                    "allowed_control_postures": ["aborted", "paused", "recorded_active"],
                    "allowed_readiness_states": ["not_ready", "ready_pending_approval", "ready_within_boundary"],
                    "allowed_follow_through_statuses": ["local_proof_created", "not_triggered"],
                }
        raise KeyError(f"Unknown autonomy state: {autonomy_id}")

    def trigger_autonomy_local_follow_through(
        self,
        actor_name: str,
        autonomy_id: str,
        *,
        trigger_note: str = "",
    ) -> dict:
        for item in self._autonomy_states:
            if item["autonomy_id"] != autonomy_id:
                continue
            if str(item.get("readiness_state", "not_ready") or "not_ready") != "ready_within_boundary":
                raise ValueError("local follow-through trigger requires readiness_state=ready_within_boundary")
            if str(item.get("current_control_posture", "recorded_active") or "recorded_active") != "recorded_active":
                raise ValueError("local follow-through trigger requires current_control_posture=recorded_active")
            entry = {
                "status": "local_proof_created",
                "effect": "local_status_packet_written",
                "artifact_path": f"/tmp/{autonomy_id}-local-follow-through.md",
                "trigger_note": str(trigger_note or "").strip(),
                "triggered_by": actor_name,
                "triggered_at": "2026-06-28T17:30:00Z",
            }
            item["local_follow_through_status"] = "local_proof_created"
            item["last_follow_through_effect"] = "local_status_packet_written"
            item["last_follow_through_triggered_by"] = actor_name
            item["last_follow_through_triggered_at"] = "2026-06-28T17:30:00Z"
            item["last_follow_through_artifact_path"] = f"/tmp/{autonomy_id}-local-follow-through.md"
            item["follow_through_history"] = [*list(item.get("follow_through_history") or []), entry]
            item["updated_at"] = "2026-06-28T17:30:00Z"
            return {
                "message": "Local follow-through proof recorded. This ran one bounded local proof action only: a local status packet was written and linked to the autonomy record. No invisible background work, networked execution, or multi-step autonomy was started.",
                "autonomy_state": dict(item),
                "autonomy_effect": "local_follow_through_proof_only",
                "allowed_statuses": ["blocked", "completed", "in_progress", "queued"],
                "allowed_approval_states": ["approved", "not_requested", "not_required", "required"],
                "allowed_plan_action_statuses": ["proposed_not_run"],
                "allowed_control_actions": ["abort", "pause", "resume"],
                "allowed_control_postures": ["aborted", "paused", "recorded_active"],
                "allowed_readiness_states": ["not_ready", "ready_pending_approval", "ready_within_boundary"],
                "allowed_follow_through_statuses": ["local_proof_created", "not_triggered"],
            }
        raise KeyError(f"Unknown autonomy state: {autonomy_id}")

    def research_task_snapshot(self, task_id: str) -> dict:
        for item in self._research_tasks:
            if item["task_id"] == task_id:
                return {
                    "task": dict(item),
                    "research_effect": "not_performed",
                    "allowed_statuses": ["blocked", "completed", "in_progress", "queued"],
                }
        raise KeyError(f"Unknown research task: {task_id}")

    def update_research_task(
        self,
        task_id: str,
        *,
        title: str = "",
        question: str = "",
        desired_scope: str = "",
        status: str = "",
        constraints: list[str] | None = None,
        source_expectations: list[str] | None = None,
    ) -> dict:
        for index, item in enumerate(self._research_tasks):
            if item["task_id"] != task_id:
                continue
            updated = dict(item)
            if title.strip():
                updated["title"] = title.strip()
            if question.strip():
                updated["question"] = question.strip()
            updated["desired_scope"] = str(desired_scope or "").strip()
            if status.strip():
                cleaned_status = status.strip().lower()
                if cleaned_status not in {"queued", "in_progress", "blocked", "completed"}:
                    raise ValueError("status must be one of: queued, in_progress, blocked, completed")
                updated["status"] = cleaned_status
            if constraints is not None:
                updated["constraints"] = [str(entry).strip() for entry in list(constraints or []) if str(entry).strip()]
            if source_expectations is not None:
                updated["source_expectations"] = [str(entry).strip() for entry in list(source_expectations or []) if str(entry).strip()]
            if not str(updated.get("title", "")).strip():
                raise ValueError("title is required")
            if not str(updated.get("question", "")).strip():
                raise ValueError("question is required")
            updated["updated_at"] = "2026-06-28T14:30:00Z"
            self._research_tasks[index] = updated
            return {
                "message": (
                    "Research task updated. Status and task detail changes do not imply that research, source discovery, "
                    "or autonomous execution already happened."
                ),
                "task": dict(updated),
                "research_effect": "not_performed",
                "allowed_statuses": ["blocked", "completed", "in_progress", "queued"],
            }
        raise KeyError(f"Unknown research task: {task_id}")

    def add_research_task_evidence(
        self,
        task_id: str,
        *,
        source_label: str,
        source_locator: str = "",
        evidence_note: str = "",
        capture_status: str = "",
        confidence_label: str = "",
    ) -> dict:
        cleaned_source_label = str(source_label or "").strip()
        cleaned_source_locator = str(source_locator or "").strip()
        cleaned_evidence_note = str(evidence_note or "").strip()
        if not cleaned_source_label:
            raise ValueError("source_label is required")
        if not cleaned_source_locator and not cleaned_evidence_note:
            raise ValueError("source_locator or evidence_note is required")
        for index, item in enumerate(self._research_tasks):
            if item["task_id"] != task_id:
                continue
            updated = dict(item)
            evidence_items = [dict(entry) for entry in list(updated.get("evidence_items") or []) if isinstance(entry, dict)]
            created = {
                "evidence_id": f"evidence-{len(evidence_items) + 1}",
                "source_label": cleaned_source_label,
                "source_locator": cleaned_source_locator,
                "evidence_note": cleaned_evidence_note,
                "capture_status": str(capture_status or "").strip() or "captured",
                "confidence_label": str(confidence_label or "").strip(),
                "capture_mode": "manual_entry",
                "captured_at": "2026-06-28T15:00:00Z",
                "retrieval_used": False,
                "autonomous_discovery": False,
            }
            evidence_items.append(created)
            updated["evidence_items"] = evidence_items
            updated["updated_at"] = "2026-06-28T15:00:00Z"
            self._research_tasks[index] = updated
            return {
                "message": (
                    "Evidence item attached. Manual evidence capture does not imply completed research, validated synthesis, "
                    "or autonomous source discovery."
                ),
                "task": dict(updated),
                "evidence_item": dict(created),
                "research_effect": "not_performed",
            }
        raise KeyError(f"Unknown research task: {task_id}")

    def generate_research_task_synthesis(self, task_id: str) -> dict:
        for index, item in enumerate(self._research_tasks):
            if item["task_id"] != task_id:
                continue
            evidence_items = [dict(entry) for entry in list(item.get("evidence_items") or []) if isinstance(entry, dict)]
            if not evidence_items:
                raise ValueError("at least one attached evidence item is required before synthesis can be generated")
            synthesis = {
                "synthesis_id": "synthesis-1",
                "generated_at": "2026-06-28T16:00:00Z",
                "synthesis_mode": "attached_evidence_only",
                "evidence_ids_used": [str(entry.get("evidence_id", "")).strip() for entry in evidence_items if str(entry.get("evidence_id", "")).strip()],
                "evidence_count": len(evidence_items),
                "summary": "This synthesis uses only the evidence items attached to the task in the current runtime path.",
                "supported_points": [
                    f"{str(entry.get('source_label', '')).strip() or 'Evidence item'}: {str(entry.get('evidence_note', '')).strip() or 'Attached evidence note.'}"
                    for entry in evidence_items
                ],
                "uncertainties": ["These evidence items were attached manually and remain task-scoped evidence only."],
                "missing_information": ["More evidence may still be needed before the research task is actually complete."],
                "externally_validated": False,
                "autonomous_discovery_used": False,
                "research_completed_inferred": False,
            }
            updated = dict(item)
            updated["synthesis"] = synthesis
            updated["updated_at"] = "2026-06-28T16:00:00Z"
            self._research_tasks[index] = updated
            return {
                "message": (
                    "Evidence-backed synthesis generated from the evidence items already attached to this task. "
                    "It remains limited to that attached evidence set and does not imply completed research, autonomous discovery, "
                    "or external validation."
                ),
                "task": dict(updated),
                "synthesis": dict(synthesis),
                "research_effect": "not_performed",
            }
        raise KeyError(f"Unknown research task: {task_id}")

    def research_task_queue_snapshot(self) -> dict:
        counts_by_status = {}
        for item in self._research_tasks:
            counts_by_status[item["status"]] = counts_by_status.get(item["status"], 0) + 1
        return {
            "tasks": [dict(item) for item in reversed(self._research_tasks)],
            "counts_by_status": counts_by_status,
            "total_tasks": len(self._research_tasks),
            "research_effect": "not_performed",
            "allowed_statuses": ["blocked", "completed", "in_progress", "queued"],
        }

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
    ) -> dict:
        if not producing_agent.strip():
            raise ValueError("producing_agent is required")
        if not title.strip():
            raise ValueError("title is required")
        if not summary.strip():
            raise ValueError("summary is required")
        if not any((detail.strip(), key_output.strip(), next_step.strip(), evidence_note.strip())):
            raise ValueError(
                "Delegation reports need at least one useful supporting field: detail, key_output, next_step, or evidence_note."
            )
        report = {
            "report_id": "report-1",
            "mission_id": mission_id,
            "delegation_id": delegation_id,
            "producer_agent": producing_agent,
            "title": title,
            "summary": summary,
            "detail": detail,
            "key_output": key_output,
            "next_step": next_step,
            "evidence_note": evidence_note,
            "status": "completed-with-output",
            "handoff_id": "handoff-1",
            "delegator_agent": "ambient-router",
            "delegate_agent": "storm",
            "created_at": "2026-06-28T12:00:00Z",
            "output_id": "delegation-report-delegation-1",
            "artifact_ref": f"/api/missions/{mission_id}/delegation-reports/report-1",
        }
        self._delegation_reports[mission_id] = [report]
        self._mission_outputs[mission_id] = [
            {
                "output_id": "delegation-report-delegation-1",
                "kind": "delegation-report",
                "title": title,
                "summary": summary,
                "status": "completed-with-output",
                "timestamp": "2026-06-28T12:00:00Z",
                "payload_ref": report["artifact_ref"],
            }
        ]
        self._mission_work_state["summary"]["pending_handoffs"] = 0
        self._mission_work_state["summary"]["delegations_requested"] = 0
        self._mission_work_state["summary"]["delegations_completed_with_output"] = 1
        self._mission_work_state["delegation_reports"] = [dict(report)]
        self._mission_work_state["outputs"] = [dict(item) for item in self._mission_outputs[mission_id]]
        self._mission_work_state["handoffs"][0]["status"] = "completed-with-output"
        self._mission_work_state["delegations"][0]["status"] = "completed-with-output"
        self._mission_work_state["delegations"][0]["inspectable_output_status"] = "completed-with-output"
        self._mission_work_state["delegations"][0]["artifact_ref"] = report["artifact_ref"]
        self._mission_work_state["delegations"][0]["report_id"] = report["report_id"]
        self._mission_work_state["delegations"][0]["output_id"] = report["output_id"]
        self._mission_work_state["delegations"][0]["producer_agent"] = producing_agent
        return self.mission_snapshot(mission_id)

    def shell_state_snapshot(self) -> dict:
        return {"lane": "test", "dirty": False}

    def dashboard_snapshot(self) -> dict:
        return {"status": "ok"}

    def status(self) -> list[dict]:
        return [
            {
                "name": "openai-api",
                "ok": True,
                "state": "connected",
                "detail": "OpenAI API is configured.",
                "updated_at": "2026-06-08T08:00:00Z",
            },
            {
                "name": "google-workspace",
                "ok": False,
                "state": "disconnected",
                "detail": "No Google accounts are currently connected.",
                "updated_at": "2026-06-08T08:00:00Z",
            },
            {
                "name": "family-calendar",
                "ok": True,
                "state": "connected",
                "detail": "Family shared calendar is connected.",
                "updated_at": "2026-06-08T08:00:00Z",
            },
        ]

    def get_actor(self, actor_name: str):
        return SimpleNamespace(user_id=str(actor_name or "Chris").strip().lower() or "chris", display_name=actor_name)

    def _personalization_snapshot(self, actor) -> dict:
        return {
            "governance": {"enabled": True, "review_required": False},
            "insights": [{"title": "Quiet mornings reduce friction", "status": "active"}],
            "rhythms": ["Protect the first hour for briefing and setup."],
        }

    def account_registry_snapshot(self) -> dict:
        return {
            "accounts": [dict(item) for item in self._accounts],
            "owners": [{"id": "chris", "label": "Chris"}],
            "providers": [{"id": "google", "label": "Google"}],
            "services": [{"id": "mail_calendar", "label": "Mail / Calendar"}],
        }

    def update_personal_account(self, account_id: str, payload: dict) -> dict:
        for index, account in enumerate(self._accounts):
            if account["account_id"] != account_id:
                continue
            updated = {**account, **{key: value for key, value in payload.items() if value is not None}}
            self._accounts[index] = updated
            return {
                "message": f"Updated account '{updated['label']}'.",
                "account": dict(updated),
                "registry": self.account_registry_snapshot(),
            }
        raise KeyError(account_id)

    def disconnect_account(self, account_id: str) -> dict:
        for index, account in enumerate(self._accounts):
            if account["account_id"] != account_id:
                continue
            updated = {
                **account,
                "status": "planned",
                "notes": "Disconnected from Google.",
                "connection": {"status": "disconnected"},
            }
            self._accounts[index] = updated
            return {
                "ok": True,
                "message": "Account disconnected.",
                "account": dict(updated),
            }
        return {"ok": False, "message": "Account not found."}

    def google_workspace_summary(self) -> dict:
        return {"client_secret": {"configured": True, "present": True, "detail": "Google Workspace linked."}}

    def identity_overview(self) -> dict:
        return {
            "members": [dict(item) for item in self._identity_members],
            "devices": [dict(item) for item in self._identity_devices],
            "service": {
                "hosted_base_url": "https://jarvis.teambinion.org",
                "remote_admin_host": "",
                "remote_admin_user": "root",
                "hosted_provider": "Hetzner",
                "edge_provider": "Cloudflare Tunnel",
                "compose_project": "jarvis-family",
            },
        }

    def save_identity_member(self, payload: dict) -> dict:
        user_id = str(payload.get("user_id") or "").strip().lower()
        for index, member in enumerate(self._identity_members):
            if member["user_id"] != user_id:
                continue
            updated = {**member, **payload}
            self._identity_members[index] = updated
            return {"ok": True, "member": dict(updated), "identity": self.identity_overview()}
        raise ValueError("Unknown household user")


class CommandCenterServiceSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.original_cwd = os.getcwd()
        os.chdir(self.tempdir.name)
        self.addCleanup(os.chdir, self.original_cwd)
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = self.tempdir.name
        self.addCleanup(self._restore_home)

        self.original_root = ApprovalQueue.ROOT
        ApprovalQueue.ROOT = Path(self.tempdir.name) / "approvals"
        self.addCleanup(self._restore_root)

        self.original_guard = approvals_module._guard_singleton
        self.original_queue = approvals_module._queue_singleton
        approvals_module._guard_singleton = None
        approvals_module._queue_singleton = None
        self.addCleanup(self._restore_singletons)

        self.original_register_apple_api = service_module._register_apple_api
        service_module._register_apple_api = lambda app, runtime: None
        self.addCleanup(self._restore_register_apple_api)

        self.original_command_center_audit_root = command_center_index_module.DEFAULT_AUDIT_ROOT
        self.original_service_audit_root = service_module.DEFAULT_AUDIT_ROOT
        self.audit_root = Path(self.tempdir.name) / "audit"
        command_center_index_module.DEFAULT_AUDIT_ROOT = self.audit_root
        service_module.DEFAULT_AUDIT_ROOT = self.audit_root
        self.addCleanup(self._restore_audit_roots)

        self.runtime = _StubRuntime()
        self.queue, self.guard = init_approvals(
            self.runtime.supervision_support,
            self.runtime.execute_sandbox_job,
        )
        self.app = service_module.build_app(self.runtime)

    def _restore_root(self) -> None:
        ApprovalQueue.ROOT = self.original_root

    def _restore_home(self) -> None:
        if self.original_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self.original_home

    def _restore_singletons(self) -> None:
        approvals_module._guard_singleton = self.original_guard
        approvals_module._queue_singleton = self.original_queue

    def _restore_register_apple_api(self) -> None:
        service_module._register_apple_api = self.original_register_apple_api

    def _restore_audit_roots(self) -> None:
        command_center_index_module.DEFAULT_AUDIT_ROOT = self.original_command_center_audit_root
        service_module.DEFAULT_AUDIT_ROOT = self.original_service_audit_root

    def _route(self, path: str, method: str):
        for route in self.app.router.routes:
            if getattr(route, "path", None) == path and method.upper() in getattr(route, "methods", set()):
                return route.endpoint
        raise AssertionError(f"Could not find route {method} {path}")

    def _json_body(self, response) -> dict:
        return json.loads(response.body.decode("utf-8"))

    def _text_body(self, response) -> str:
        body = response.body.decode("utf-8")
        if body.startswith('"') and body.endswith('"'):
            try:
                decoded = json.loads(body)
            except json.JSONDecodeError:
                return body
            if isinstance(decoded, str):
                return decoded
        return body

    def test_served_routes_expose_command_center_index_and_snapshot(self) -> None:
        html_response = asyncio.run(self._route("/command-center", "GET")())
        chat_response = asyncio.run(self._route("/chat", "GET")())
        snapshot_response = asyncio.run(self._route("/api/command-center", "GET")())
        approval_response = asyncio.run(self._route("/approval-queue", "GET")())
        approval_api_response = asyncio.run(self._route("/api/approval/module", "GET")())
        supervision_response = asyncio.run(self._route("/supervision-snapshot", "GET")())
        supervision_api_response = asyncio.run(self._route("/api/supervision/module", "GET")())
        briefing_response = asyncio.run(self._route("/briefing-center", "GET")())
        briefing_api_response = asyncio.run(self._route("/api/briefing/module", "GET")())
        progress_response = asyncio.run(self._route("/progress-center", "GET")())
        progress_api_response = asyncio.run(self._route("/api/progress/module", "GET")())
        recovery_response = asyncio.run(self._route("/recovery-center", "GET")())
        recovery_api_response = asyncio.run(self._route("/api/recovery/module", "GET")())
        mission_board_response = asyncio.run(self._route("/mission-board", "GET")())
        mission_board_api_response = asyncio.run(self._route("/api/mission-board/module", "GET")())
        activity_response = asyncio.run(self._route("/activity-center", "GET")())
        activity_api_response = asyncio.run(self._route("/api/activity/module", "GET")())
        agent_ops_response = asyncio.run(self._route("/agent-ops-center", "GET")())
        agent_ops_api_response = asyncio.run(self._route("/api/agent-ops/module", "GET")())
        chronicle_response = asyncio.run(self._route("/chronicle-center", "GET")())
        chronicle_api_response = asyncio.run(self._route("/api/chronicle/module", "GET")())
        navigation_response = asyncio.run(self._route("/navigation-center", "GET")())
        navigation_api_response = asyncio.run(self._route("/api/navigation/module", "GET")())
        publish_response = asyncio.run(self._route("/publish", "GET")())
        publish_api_response = asyncio.run(self._route("/api/publish/module", "GET")())
        settings_response = asyncio.run(self._route("/settings-center", "GET")())
        settings_api_response = asyncio.run(self._route("/api/settings/module", "GET")())
        huddle_response = asyncio.run(self._route("/huddle-center", "GET")())
        huddle_api_response = asyncio.run(self._route("/api/huddle/module", "GET")())
        health_response = asyncio.run(self._route("/health-center", "GET")())
        health_api_response = asyncio.run(self._route("/api/health/module", "GET")())
        vision_api_response = asyncio.run(self._route("/api/vision/module", "GET")())
        intel_api_response = asyncio.run(self._route("/api/intel/module", "GET")())

        html = self._text_body(html_response)
        chat_html = self._text_body(chat_response)
        snapshot = self._json_body(snapshot_response)
        approval_html = self._text_body(approval_response)
        approval_snapshot = self._json_body(approval_api_response)
        supervision_html = self._text_body(supervision_response)
        supervision_snapshot = self._json_body(supervision_api_response)
        briefing_html = self._text_body(briefing_response)
        briefing_snapshot = self._json_body(briefing_api_response)
        progress_html = self._text_body(progress_response)
        progress_snapshot = self._json_body(progress_api_response)
        recovery_html = self._text_body(recovery_response)
        recovery_snapshot = self._json_body(recovery_api_response)
        mission_board_html = self._text_body(mission_board_response)
        mission_board_snapshot = self._json_body(mission_board_api_response)
        activity_html = self._text_body(activity_response)
        activity_snapshot = self._json_body(activity_api_response)
        agent_ops_html = self._text_body(agent_ops_response)
        agent_ops_snapshot = self._json_body(agent_ops_api_response)
        chronicle_html = self._text_body(chronicle_response)
        chronicle_snapshot = self._json_body(chronicle_api_response)
        navigation_html = self._text_body(navigation_response)
        navigation_snapshot = self._json_body(navigation_api_response)
        publish_html = self._text_body(publish_response)
        publish_snapshot = self._json_body(publish_api_response)
        settings_html = self._text_body(settings_response)
        settings_snapshot = self._json_body(settings_api_response)
        huddle_html = self._text_body(huddle_response)
        huddle_snapshot = self._json_body(huddle_api_response)
        health_html = self._text_body(health_response)
        health_snapshot = self._json_body(health_api_response)
        vision_snapshot = self._json_body(vision_api_response)
        intel_snapshot = self._json_body(intel_api_response)

        self.assertIn("JARVIS Command Center Index", html)
        self.assertIn("/approval-queue", html)
        self.assertIn("/supervision-snapshot", html)
        self.assertIn("Agent Roster &amp; Ops", html)
        self.assertIn("Mission &amp; Task Board", html)
        self.assertIn("Core Modules", html)
        self.assertIn("Progress Dashboard", html)
        self.assertIn("Seam Tracker", html)
        self.assertIn("Today at a Glance", html)
        self.assertIn("Last Home Action", html)
        self.assertIn("Hosted Edge", html)
        self.assertIn("https://jarvis.teambinion.org", html)
        self.assertIn("deploy/deploy.sh", html)
        self.assertIn("Focus Actions", html)
        self.assertIn("homeOverview.innerHTML = homeOverviewHtml", html)
        self.assertIn("homeActionResult.innerHTML = homeActionResultHtml", html)
        self.assertIn("buildVisibleActivityEntries", html)
        self.assertGreaterEqual(snapshot["surface_count"], 4)
        self.assertIn("Chat with JARVIS", chat_html)
        self.assertIn("/api/respond", chat_html)
        self.assertIn("/api/chat-state", chat_html)
        self.assertIn("Chat-only mode keeps the experience conversational.", chat_html)
        self.assertNotIn("Executive control, life operating posture", chat_html)
        self.assertIn("home_overview", snapshot)
        self.assertIn("actions", snapshot["home_overview"])
        self.assertGreaterEqual(len(snapshot["home_overview"]["actions"]), 2)
        self.assertIn("action_result", snapshot["home_overview"])
        self.assertIn("activity_bridge", snapshot["home_overview"]["action_result"])
        self.assertIn("hosted_deployment", snapshot)
        self.assertEqual(snapshot["hosted_deployment"]["hosted_url"], "https://jarvis.teambinion.org")
        self.assertIn("agent_ops_roster", snapshot)
        self.assertGreaterEqual(snapshot["agent_ops_roster"]["item_count"], 1)
        self.assertIn("mission_task_board", snapshot)
        self.assertGreaterEqual(snapshot["mission_task_board"]["item_count"], 1)
        self.assertIn("core_modules", snapshot)
        self.assertGreaterEqual(snapshot["core_modules"]["item_count"], 10)
        self.assertIn("progress_dashboard", snapshot)
        self.assertGreaterEqual(snapshot["progress_dashboard"]["item_count"], 5)
        self.assertIn("seam_tracker", snapshot)
        self.assertGreaterEqual(snapshot["seam_tracker"]["item_count"], 3)
        self.assertTrue(any(item["path"] == "/api/agent-registry" for item in snapshot["json_endpoints"]))
        self.assertIn("JARVIS Approval Queue", approval_html)
        self.assertIn("Refresh Approval Queue", approval_html)
        self.assertIn("Inspect Request", approval_html)
        self.assertIn("Recovery Continuity", approval_html)
        self.assertIn("Recent Approval Continuity", approval_html)
        self.assertIn("/api/activity/operator-action", approval_html)
        self.assertIn("status", approval_snapshot)
        self.assertIn("pending", approval_snapshot)
        self.assertIn("history", approval_snapshot)
        self.assertIn("recovery_bridge", approval_snapshot)
        self.assertIn("recent_activity", approval_snapshot)
        self.assertIn("recent_activity_count", approval_snapshot["counts"])
        self.assertIn("proof_paths", approval_snapshot)
        self.assertEqual(approval_snapshot["proof_paths"]["module_route"], "/approval-queue")
        self.assertEqual(approval_snapshot["proof_paths"]["module_api"], "/api/approval/module")
        self.assertEqual(approval_snapshot["proof_paths"]["recovery_action_api"], "/api/recovery/action")
        self.assertIn("JARVIS Supervision Snapshot", supervision_html)
        self.assertIn("Refresh Supervision State", supervision_html)
        self.assertIn("Inspect Supervision Item", supervision_html)
        self.assertIn("Integration Recovery Lane", supervision_html)
        self.assertIn("Supervision Recovery Cases", supervision_html)
        self.assertIn("Stage Recovery Case", supervision_html)
        self.assertIn("Recovery Continuity", supervision_html)
        self.assertIn("Recent Supervision Continuity", supervision_html)
        self.assertIn("/api/activity/operator-action", supervision_html)
        self.assertIn("status", supervision_snapshot)
        self.assertIn("attention_queue", supervision_snapshot)
        self.assertIn("integrations", supervision_snapshot)
        self.assertIn("integration_recovery_lane", supervision_snapshot)
        self.assertIn("recovery_cases", supervision_snapshot)
        self.assertIn("recovery_bridge", supervision_snapshot)
        self.assertIn("recent_activity", supervision_snapshot)
        self.assertIn("integration_recovery_count", supervision_snapshot["counts"])
        self.assertIn("recent_activity_count", supervision_snapshot["counts"])
        self.assertIn("proof_paths", supervision_snapshot)
        self.assertEqual(supervision_snapshot["proof_paths"]["module_route"], "/supervision-snapshot")
        self.assertEqual(supervision_snapshot["proof_paths"]["module_api"], "/api/supervision/module")
        self.assertEqual(supervision_snapshot["proof_paths"]["recovery_action_api"], "/api/recovery/action")
        self.assertEqual(supervision_snapshot["proof_paths"]["supervision_review_action_suffix"], "/api/supervision/reviews/{request_id}/{action}")
        self.assertEqual(supervision_snapshot["proof_paths"]["supervision_integration_recovery_suffix"], "/api/supervision/integrations/{integration_name}/recovery")
        self.assertIn("JARVIS Daily Brief", briefing_html)
        self.assertIn("Refresh Daily Brief", briefing_html)
        self.assertIn("Generate Live Brief", briefing_html)
        self.assertIn("Recent Brief Continuity", briefing_html)
        self.assertIn("What Is Waiting", briefing_html)
        self.assertIn("What JARVIS Did While You Were Away", briefing_html)
        self.assertIn("Things You May Have Forgotten", briefing_html)
        self.assertIn("Next Honest Step", briefing_html)
        self.assertIn("Health was previously stated as one of the highest priorities.", briefing_html)
        self.assertIn("status", briefing_snapshot)
        self.assertIn("briefing_text", briefing_snapshot)
        self.assertIn("today_board", briefing_snapshot)
        self.assertIn("open_loops", briefing_snapshot)
        self.assertIn("what_is_waiting", briefing_snapshot["morning_brief"])
        self.assertIn("while_you_were_away", briefing_snapshot["morning_brief"])
        self.assertIn("recommendation_action", briefing_snapshot["morning_brief"])
        self.assertIn("action_kind", briefing_snapshot["morning_brief"]["recommendation_action"])
        self.assertIn("recent_activity", briefing_snapshot)
        self.assertIn("recent_activity_count", briefing_snapshot["counts"])
        self.assertIn("proof_paths", briefing_snapshot)
        self.assertEqual(briefing_snapshot["proof_paths"]["module_route"], "/briefing-center")
        self.assertEqual(briefing_snapshot["proof_paths"]["module_api"], "/api/briefing/module")
        self.assertEqual(briefing_snapshot["proof_paths"]["activity_api"], "/api/activity/operator-action")
        self.assertIn("JARVIS Progress", progress_html)
        self.assertIn("Refresh Progress State", progress_html)
        self.assertIn('id="level3-checklist"', progress_html)
        self.assertIn('href="#level3-checklist"', progress_html)
        self.assertIn("Hosted Readiness", progress_html)
        self.assertIn("Durable Progress History", progress_html)
        self.assertIn("Seam History:", progress_html)
        self.assertIn("Save Next Focus", progress_html)
        self.assertIn("Save Seam State", progress_html)
        self.assertIn("deploy/deploy.sh", progress_html)
        self.assertIn("https://jarvis.teambinion.org", progress_html)
        self.assertIn("Inspect Readiness", progress_html)
        self.assertIn("Remaining Level 3 Checklist", progress_html)
        self.assertIn("Next Recommended Slice", progress_html)
        self.assertIn("jarvis/command_center_index.py", progress_html)
        self.assertIn("status", progress_snapshot)
        self.assertIn("progress_dashboard", progress_snapshot)
        self.assertIn("seam_tracker", progress_snapshot)
        self.assertIn("level3_checklist", progress_snapshot)
        self.assertIn("progress_persistence", progress_snapshot)
        self.assertIn("seam_persistence", progress_snapshot)
        self.assertIn("focus_control", progress_snapshot)
        self.assertIn("history_count", progress_snapshot["counts"])
        self.assertIn("focus_history_count", progress_snapshot["counts"])
        self.assertIn("seam_history_count", progress_snapshot["counts"])
        self.assertIn("latest", progress_snapshot["progress_persistence"])
        self.assertIn("recent", progress_snapshot["progress_persistence"])
        self.assertTrue(any(item.get("related_missions") for item in progress_snapshot["seam_tracker"]["items"]))
        self.assertTrue(any(item.get("related_missions") for item in progress_snapshot["progress_persistence"]["latest"].get("seam_items", [])))
        self.assertEqual(progress_snapshot["level3_checklist"]["route"], "/progress-center#level3-checklist")
        self.assertIn("hosted_deployment", progress_snapshot)
        self.assertEqual(progress_snapshot["hosted_deployment"]["hosted_url"], "https://jarvis.teambinion.org")
        self.assertIn("lane_progress", progress_snapshot)
        self.assertIn("proof_paths", progress_snapshot)
        self.assertEqual(progress_snapshot["proof_paths"]["module_route"], "/progress-center")
        self.assertEqual(progress_snapshot["proof_paths"]["module_api"], "/api/progress/module")
        self.assertEqual(progress_snapshot["proof_paths"]["focus_api"], "/api/progress/focus")
        self.assertEqual(progress_snapshot["proof_paths"]["hosted_url"], "https://jarvis.teambinion.org")
        self.assertIn("progress_snapshot_json", progress_snapshot["proof_paths"])
        self.assertIn("progress_snapshot_history", progress_snapshot["proof_paths"])
        self.assertIn("progress_focus_json", progress_snapshot["proof_paths"])
        self.assertIn("progress_focus_history", progress_snapshot["proof_paths"])
        self.assertIn("seam_api_prefix", progress_snapshot["proof_paths"])
        self.assertIn("seam_tracker_json", progress_snapshot["proof_paths"])
        self.assertIn("seam_tracker_history", progress_snapshot["proof_paths"])
        self.assertIn("JARVIS Failure &amp; Recovery", recovery_html)
        self.assertIn("Refresh Failure State", recovery_html)
        self.assertIn("Inspect Recovery Item", recovery_html)
        self.assertIn("Recovery Continuity", recovery_html)
        self.assertIn("Recovery Action Journal", recovery_html)
        self.assertIn("Execute Recovery Gate", recovery_html)
        self.assertIn("Stage Retry", recovery_html)
        self.assertIn("Mark Stabilized", recovery_html)
        self.assertIn("Mark Investigating", recovery_html)
        self.assertIn("Mark Watch", recovery_html)
        self.assertIn("Mark Resolved", recovery_html)
        self.assertIn("Execute Retry Loop", recovery_html)
        self.assertIn("Stabilize Recovery Loop", recovery_html)
        self.assertIn("Stage Auto-Remediation", recovery_html)
        self.assertIn("Execute Auto-Remediation", recovery_html)
        self.assertIn("Prepare Healing Plan", recovery_html)
        self.assertIn("Execute Next Healing Step", recovery_html)
        self.assertIn("/api/recovery/action", recovery_html)
        self.assertIn("status", recovery_snapshot)
        self.assertIn("failure_recovery", recovery_snapshot)
        self.assertIn("pending_approvals", recovery_snapshot)
        self.assertIn("recovery_actions", recovery_snapshot)
        self.assertIn("recovery_cases", recovery_snapshot)
        self.assertIn("recorded_recovery_actions", recovery_snapshot["counts"])
        self.assertIn("recovery_case_count", recovery_snapshot["counts"])
        self.assertIn("recovery_case_execution_count", recovery_snapshot["counts"])
        self.assertIn("recovery_case_remediation_count", recovery_snapshot["counts"])
        self.assertIn("recovery_case_plan_count", recovery_snapshot["counts"])
        self.assertIn("proof_paths", recovery_snapshot)
        self.assertEqual(recovery_snapshot["proof_paths"]["module_route"], "/recovery-center")
        self.assertEqual(recovery_snapshot["proof_paths"]["module_api"], "/api/recovery/module")
        self.assertEqual(recovery_snapshot["proof_paths"]["recovery_action_api"], "/api/recovery/action")
        self.assertEqual(recovery_snapshot["proof_paths"]["recovery_case_execute_suffix"], "/execute")
        self.assertEqual(recovery_snapshot["proof_paths"]["recovery_case_remediation_suffix"], "/remediation")
        self.assertEqual(recovery_snapshot["proof_paths"]["recovery_case_plan_suffix"], "/plan")
        self.assertEqual(recovery_snapshot["proof_paths"]["recovery_case_plan_execute_suffix"], "/plan/execute-next")
        self.assertIn("JARVIS Mission &amp; Task Board", mission_board_html)
        self.assertIn("Refresh Mission Board", mission_board_html)
        self.assertIn("Mission Authoring", mission_board_html)
        self.assertIn("Create Mission", mission_board_html)
        self.assertIn("Save Mission Detail", mission_board_html)
        self.assertIn("Inspect Mission", mission_board_html)
        self.assertIn("Recent Mission Continuity", mission_board_html)
        self.assertIn("Continuity Callback", mission_board_html)
        self.assertIn("Relevant Memory", mission_board_html)
        self.assertIn("Mission Workspaces", mission_board_html)
        self.assertIn("Handoff Console", mission_board_html)
        self.assertIn("Create Handoff", mission_board_html)
        self.assertIn("Accept Handoff", mission_board_html)
        self.assertIn("Delegation Report Queue", mission_board_html)
        self.assertIn("Submit Delegation Report", mission_board_html)
        self.assertIn("Inspect Delegation Report", mission_board_html)
        self.assertIn("Pending Delegation Reports", mission_board_html)
        self.assertIn("Completed Delegation Reports", mission_board_html)
        self.assertIn("Unavailable Delegation Reports", mission_board_html)
        self.assertIn("Open Outcome Review", mission_board_html)
        self.assertIn("Mark Active", mission_board_html)
        self.assertIn("Mark Ready", mission_board_html)
        self.assertIn("Mark Blocked", mission_board_html)
        self.assertIn("/api/missions/", mission_board_html)
        self.assertIn('id="create-mission-button"', mission_board_html)
        self.assertIn('id="save-mission-detail-button"', mission_board_html)
        self.assertIn("/work-state", mission_board_html)
        self.assertIn("/edit", mission_board_html)
        self.assertIn("/handoffs", mission_board_html)
        self.assertIn("/acknowledge", mission_board_html)
        self.assertIn("/delegations/{delegation_id}/report", mission_board_html)
        self.assertIn("/delegation-reports", mission_board_html)
        self.assertIn("/mission-board/delegation-report/", mission_board_html)
        self.assertIn("/mission-board/artifact-outcome/", mission_board_html)
        self.assertIn("#delegation-review-requested", mission_board_html)
        self.assertIn("#delegation-review-completed", mission_board_html)
        self.assertIn("#delegation-review-unavailable", mission_board_html)
        self.assertIn("/api/activity/operator-action", mission_board_html)
        self.assertIn("createMission()", mission_board_html)
        self.assertIn("updateMissionDetails", mission_board_html)
        self.assertIn("Related Seam:", mission_board_html)
        self.assertIn("recordMissionActivity", mission_board_html)
        self.assertIn("createMissionHandoff", mission_board_html)
        self.assertIn("acknowledgeMissionHandoff", mission_board_html)
        self.assertIn("submitDelegationReport", mission_board_html)
        self.assertIn("Key Output", mission_board_html)
        self.assertIn("Next Step", mission_board_html)
        self.assertIn("Evidence Note", mission_board_html)
        self.assertIn("at least one useful field", mission_board_html)
        self.assertIn("recorded in shared activity", mission_board_html)
        self.assertIn("status", mission_board_snapshot)
        self.assertIn("mission_task_board", mission_board_snapshot)
        self.assertIn("mission_details", mission_board_snapshot)
        self.assertIn("recent_activity", mission_board_snapshot)
        self.assertIn("recent_activity_count", mission_board_snapshot["counts"])
        self.assertTrue(any("work_state" in detail for detail in mission_board_snapshot["mission_details"].values()))
        self.assertTrue(any("outputs_detail" in detail for detail in mission_board_snapshot["mission_details"].values()))
        self.assertTrue(any("delegation_reports" in detail for detail in mission_board_snapshot["mission_details"].values()))
        self.assertIn("proof_paths", mission_board_snapshot)
        self.assertEqual(mission_board_snapshot["proof_paths"]["module_route"], "/mission-board")
        self.assertEqual(mission_board_snapshot["proof_paths"]["module_api"], "/api/mission-board/module")
        self.assertEqual(mission_board_snapshot["proof_paths"]["mission_create_api"], "/api/missions")
        self.assertEqual(mission_board_snapshot["proof_paths"]["mission_edit_api_suffix"], "/edit")
        self.assertEqual(mission_board_snapshot["proof_paths"]["mission_outputs_api_suffix"], "/outputs")
        self.assertEqual(mission_board_snapshot["proof_paths"]["mission_handoff_api_suffix"], "/handoffs")
        self.assertEqual(mission_board_snapshot["proof_paths"]["mission_handoff_ack_suffix"], "/handoffs/{handoff_id}/acknowledge")
        self.assertEqual(mission_board_snapshot["proof_paths"]["mission_delegation_reports_api_suffix"], "/delegation-reports")
        self.assertEqual(
            mission_board_snapshot["proof_paths"]["mission_delegation_report_submit_suffix"],
            "/delegations/{delegation_id}/report",
        )
        self.assertTrue(any(detail.get("related_seams") for detail in mission_board_snapshot["mission_details"].values()))

        self.assertIn("JARVIS Activity Feed", activity_html)
        self.assertIn("Refresh Activity Feed", activity_html)
        self.assertIn("Inspect Event", activity_html)
        self.assertIn("Home Bridges", activity_html)
        self.assertIn("Progress Snapshot Persisted", activity_html)
        self.assertIn("Promote to Progress Focus", activity_html)
        self.assertIn("Mark Reviewing", activity_html)
        self.assertIn("Review Lane", activity_html)
        self.assertIn("Shared Progress Focus", activity_html)
        self.assertIn("/progress-center", activity_html)
        self.assertIn("Home Continuity", activity_html)
        self.assertIn("status", activity_snapshot)
        self.assertIn("activity_feed", activity_snapshot)
        self.assertIn("action_journal", activity_snapshot)
        self.assertIn("review_lane", activity_snapshot)
        self.assertIn("home_action_result", activity_snapshot)
        self.assertIn("focus_control", activity_snapshot)
        self.assertIn("progress_next_focus", activity_snapshot)
        self.assertIn("home_bridge_count", activity_snapshot["counts"])
        self.assertIn("focus_history_count", activity_snapshot["counts"])
        self.assertIn("review_count", activity_snapshot["counts"])
        self.assertTrue(any(item.get("entry_type") == "progress-snapshot" for item in activity_snapshot["activity_feed"]))
        self.assertIn("proof_paths", activity_snapshot)
        self.assertEqual(activity_snapshot["proof_paths"]["module_route"], "/activity-center")
        self.assertEqual(activity_snapshot["proof_paths"]["module_api"], "/api/activity/module")
        self.assertEqual(activity_snapshot["proof_paths"]["activity_focus_api"], "/api/activity/module/focus")
        self.assertEqual(activity_snapshot["proof_paths"]["activity_review_api"], "/api/activity/module/review")
        self.assertIn("JARVIS Agent Operations", agent_ops_html)
        self.assertIn("Refresh Agent Ops State", agent_ops_html)
        self.assertIn("Queue Agent Run", agent_ops_html)
        self.assertIn("Save Assignment", agent_ops_html)
        self.assertIn("Outcome Review", agent_ops_html)
        self.assertIn("Recent Agent Ops Continuity", agent_ops_html)
        self.assertIn("Promote Task Agent", agent_ops_html)
        self.assertIn("Retire Task Agent", agent_ops_html)
        self.assertIn("/assignment", agent_ops_html)
        self.assertIn("saveTaskAgentAssignment", agent_ops_html)
        self.assertIn("/api/activity/operator-action", agent_ops_html)
        self.assertIn("status", agent_ops_snapshot)
        self.assertIn("agent_ops_roster", agent_ops_snapshot)
        self.assertIn("mission_options", agent_ops_snapshot)
        self.assertIn("agent_reviews", agent_ops_snapshot)
        self.assertIn("scheduler_status", agent_ops_snapshot)
        self.assertIn("recent_activity", agent_ops_snapshot)
        self.assertIn("task_agents", agent_ops_snapshot["counts"])
        self.assertIn("recent_activity_count", agent_ops_snapshot["counts"])
        self.assertTrue(any(item.get("source_kind") == "task-agent" for item in agent_ops_snapshot["agent_ops_roster"]["items"]))
        self.assertGreaterEqual(len(agent_ops_snapshot["mission_options"]), 1)
        self.assertTrue(any(review.get("recent_decisions") is not None for review in agent_ops_snapshot["agent_reviews"].values()))
        self.assertIn("proof_paths", agent_ops_snapshot)
        self.assertEqual(agent_ops_snapshot["proof_paths"]["module_route"], "/agent-ops-center")
        self.assertEqual(agent_ops_snapshot["proof_paths"]["module_api"], "/api/agent-ops/module")
        self.assertEqual(agent_ops_snapshot["proof_paths"]["assignment_api_prefix"], "/api/agents/")
        self.assertEqual(agent_ops_snapshot["proof_paths"]["missions_api"], "/api/missions")
        self.assertEqual(agent_ops_snapshot["proof_paths"]["mission_work_state_api_prefix"], "/api/missions/")
        self.assertIn("JARVIS Chronicle", chronicle_html)
        self.assertIn("Generate Devotional Pause", chronicle_html)
        self.assertIn("Capture Chronicle Note", chronicle_html)
        self.assertIn("Review Lane", chronicle_html)
        self.assertIn("Study Next", chronicle_html)
        self.assertIn("Queue Family Handoff", chronicle_html)
        self.assertIn("Living story engine", chronicle_html)
        self.assertIn("Chronicle tracks", chronicle_html)
        self.assertIn("Recent Chronicle Continuity", chronicle_html)
        self.assertIn("/api/chronicle/entries/", chronicle_html)

        self.assertIn("status", chronicle_snapshot)
        self.assertIn("timeline", chronicle_snapshot)
        self.assertIn("recent_activity", chronicle_snapshot)
        self.assertIn("review_lane", chronicle_snapshot)
        self.assertIn("review_count", chronicle_snapshot["counts"])
        self.assertIn("proof_paths", chronicle_snapshot)
        self.assertEqual(chronicle_snapshot["proof_paths"]["module_route"], "/chronicle-center")
        self.assertEqual(chronicle_snapshot["proof_paths"]["module_api"], "/api/chronicle/module")
        self.assertEqual(chronicle_snapshot["proof_paths"]["entry_review_api_suffix"], "/api/chronicle/entries/{entry_id}/review")
        self.assertIn("JARVIS Navigation", navigation_html)
        self.assertIn("Preview Route Intelligence", navigation_html)
        self.assertIn("Navigation Command Center", navigation_html)
        self.assertIn("Concept Storyboard", navigation_html)
        self.assertIn("Route Preview Workspace", navigation_html)
        self.assertIn("Stored routes can be resumed from shared navigation state in this runtime.", navigation_html)
        self.assertIn("save a route preview and load live route intelligence when this runtime can provide it", navigation_html)
        self.assertIn("Stop Detail &amp; Route Modification", navigation_html)
        self.assertIn("Resume Route History", navigation_html)
        self.assertIn("Recent Route Continuity", navigation_html)
        self.assertIn("/api/activity/operator-action", navigation_html)
        self.assertIn("status", navigation_snapshot)
        self.assertIn("navigation_state", navigation_snapshot)
        self.assertIn("route_history", navigation_snapshot)
        self.assertIn("recent_activity", navigation_snapshot)
        self.assertIn("proof_paths", navigation_snapshot)
        self.assertEqual(navigation_snapshot["proof_paths"]["module_route"], "/navigation-center")
        self.assertEqual(navigation_snapshot["proof_paths"]["module_api"], "/api/navigation/module")
        self.assertEqual(navigation_snapshot["proof_paths"]["resume_api"], "/api/navigation/module/resume")
        self.assertIn("JARVIS Publish", publish_html)
        self.assertIn("Quick Draft Project", publish_html)
        self.assertIn("Editorial Review Lane", publish_html)
        self.assertIn("Launch Checklist Lane", publish_html)
        self.assertIn("Refresh Publish State", publish_html)
        self.assertIn("Launch Ops Hub", publish_html)
        self.assertIn("Launch History Lane", publish_html)
        self.assertIn("Recent Publish Continuity", publish_html)
        self.assertIn("status", publish_snapshot)
        self.assertIn("projects", publish_snapshot)
        self.assertIn("pending_reviews", publish_snapshot)
        self.assertIn("launch_workspace", publish_snapshot)
        self.assertIn("launch_history", publish_snapshot)
        self.assertIn("recent_activity", publish_snapshot)
        self.assertIn("runtime_note", publish_snapshot)
        self.assertIn("availability_notes", publish_snapshot)
        self.assertIn("counts", publish_snapshot)
        self.assertIn("proof_paths", publish_snapshot)
        self.assertEqual(publish_snapshot["proof_paths"]["module_route"], "/publish")
        self.assertEqual(publish_snapshot["proof_paths"]["module_api"], "/api/publish/module")
        self.assertEqual(publish_snapshot["proof_paths"]["launch_plan_api"], "/api/publishing/launch-plan")
        self.assertEqual(publish_snapshot["proof_paths"]["launch_scan_api"], "/api/publishing/launch-scan")
        self.assertEqual(publish_snapshot["proof_paths"]["activity_api"], "/api/activity/operator-action")
        self.assertIn("projects", publish_snapshot["counts"])
        self.assertIn("reviews", publish_snapshot["counts"])
        self.assertIn("history", publish_snapshot["counts"])
        self.assertIn("JARVIS Settings", settings_html)
        self.assertIn("Save Voice Settings", settings_html)
        self.assertIn("Save + Preview", settings_html)
        self.assertIn("TTS Provider", settings_html)
        self.assertIn("Configured readiness", settings_html)
        self.assertIn("Last live readiness", settings_html)
        self.assertIn("Last live fallback", settings_html)
        self.assertIn("Save Location Settings", settings_html)
        self.assertIn("Save Profile Defaults", settings_html)
        self.assertIn("Account Command Deck", settings_html)
        self.assertIn("Connector Provisioning Lane", settings_html)
        self.assertIn("Save Connector Controls", settings_html)
        self.assertIn("Family Identity Command Deck", settings_html)
        self.assertIn("Save Family Identity", settings_html)
        self.assertIn("Recent Settings Continuity", settings_html)
        self.assertIn("status", settings_snapshot)
        self.assertIn("voice", settings_snapshot)
        self.assertIn("location", settings_snapshot)
        self.assertIn("connector_lane", settings_snapshot)
        self.assertIn("recent_activity", settings_snapshot)
        self.assertIn("recent_activity_count", settings_snapshot["counts"])
        self.assertIn("connector_attention_count", settings_snapshot["counts"])
        self.assertIn("proof_paths", settings_snapshot)
        self.assertEqual(settings_snapshot["proof_paths"]["module_route"], "/settings-center")
        self.assertEqual(settings_snapshot["proof_paths"]["module_api"], "/api/settings/module")
        self.assertEqual(settings_snapshot["proof_paths"]["account_settings_api"], "/api/settings/account")
        self.assertEqual(settings_snapshot["proof_paths"]["connector_settings_api"], "/api/settings/connector")
        self.assertEqual(settings_snapshot["proof_paths"]["family_identity_api"], "/api/settings/family-member")
        self.assertEqual(settings_snapshot["proof_paths"]["profile_settings_api"], "/api/settings/profile")
        self.assertIn("JARVIS Huddle", huddle_html)
        self.assertIn("Start Overnight Research", huddle_html)
        self.assertIn("Capture Huddle Idea", huddle_html)
        self.assertIn("Agent Council Chamber", huddle_html)
        self.assertIn("Recent Huddle Continuity", huddle_html)
        self.assertIn("Research Now", huddle_html)
        self.assertIn("/api/huddle/ideas", huddle_html)
        self.assertIn("status", huddle_snapshot)
        self.assertIn("runtime_note", huddle_snapshot)
        self.assertIn("availability_notes", huddle_snapshot)
        self.assertIn("counts", huddle_snapshot)
        self.assertIn("reports", huddle_snapshot)
        self.assertIn("pipeline", huddle_snapshot)
        self.assertIn("idea_inbox", huddle_snapshot)
        self.assertIn("recent_activity", huddle_snapshot)
        self.assertIn("proof_paths", huddle_snapshot)
        self.assertEqual(huddle_snapshot["proof_paths"]["module_route"], "/huddle-center")
        self.assertEqual(huddle_snapshot["proof_paths"]["module_api"], "/api/huddle/module")
        self.assertEqual(huddle_snapshot["proof_paths"]["activity_api"], "/api/activity/operator-action")
        self.assertIn("JARVIS Health", health_html)
        self.assertIn("Symptom Triage", health_html)
        self.assertIn("Refresh Health State", health_html)
        self.assertIn("Health command center", health_html)
        self.assertIn("Daily Readiness", health_html)
        self.assertIn("Save Health Objective", health_html)
        self.assertIn("Manual Health Check-In", health_html)
        self.assertIn("Save Health Check-In", health_html)
        self.assertIn("Recent Manual Check-Ins", health_html)
        self.assertIn("Historical Review Lane", health_html)
        self.assertIn("Mark Watch", health_html)
        self.assertIn("Adjust Protocol", health_html)
        self.assertIn("Recent Health Continuity", health_html)
        self.assertIn("/api/activity/operator-action", health_html)
        self.assertIn("status", health_snapshot)
        self.assertIn("current_signals", health_snapshot)
        self.assertIn("recent_activity", health_snapshot)
        self.assertIn("recent_checkins", health_snapshot)
        self.assertIn("checkin_count", health_snapshot)
        self.assertIn("review_lane", health_snapshot)
        self.assertIn("review_count", health_snapshot)
        self.assertIn("review_status_counts", health_snapshot)
        self.assertIn("runtime_note", health_snapshot)
        self.assertIn("availability_notes", health_snapshot)
        self.assertIn("counts", health_snapshot)
        self.assertIn("proof_paths", health_snapshot)
        self.assertEqual(health_snapshot["proof_paths"]["module_route"], "/health-center")
        self.assertEqual(health_snapshot["proof_paths"]["module_api"], "/api/health/module")
        self.assertIn("signals", health_snapshot["counts"])
        self.assertIn("clusters", health_snapshot["counts"])
        self.assertIn("objectives", health_snapshot["counts"])
        self.assertIn("checkins", health_snapshot["counts"])
        self.assertIn("review_items", health_snapshot["counts"])
        self.assertIn("status", vision_snapshot)
        self.assertIn("runtime_note", vision_snapshot)
        self.assertIn("availability_notes", vision_snapshot)
        self.assertIn("state_snapshot", vision_snapshot)
        self.assertIn("perception_overview", vision_snapshot)
        self.assertIn("privacy_state", vision_snapshot)
        self.assertIn("scene_overview", vision_snapshot)
        self.assertIn("quick_actions", vision_snapshot)
        self.assertIn("counts", vision_snapshot)
        self.assertIn("proof_paths", vision_snapshot)
        self.assertEqual(vision_snapshot["proof_paths"]["module_api"], "/api/vision/module")
        self.assertEqual(vision_snapshot["proof_paths"]["vision_state_api"], "/api/vision-state")
        self.assertEqual(vision_snapshot["proof_paths"]["perception_api"], "/api/perception-overview")
        self.assertEqual(vision_snapshot["proof_paths"]["privacy_update_api"], "/api/privacy-update")
        self.assertIn("captures", vision_snapshot["counts"])
        self.assertIn("observations", vision_snapshot["counts"])
        self.assertIn("anomalies", vision_snapshot["counts"])
        self.assertIn("status", intel_snapshot)
        self.assertIn("signal_sources", intel_snapshot)
        self.assertIn("truths", intel_snapshot)
        self.assertIn("routing", intel_snapshot)
        self.assertIn("continuity", intel_snapshot)
        self.assertIn("summary_cards", intel_snapshot)
        self.assertIn("insights", intel_snapshot)
        self.assertIn("patterns", intel_snapshot)
        self.assertIn("timeline", intel_snapshot)
        self.assertIn("doctrine", intel_snapshot)
        self.assertIn("teach_actions", intel_snapshot)
        self.assertIn("radar", intel_snapshot)
        self.assertIn("counts", intel_snapshot)
        self.assertIn("proof_paths", intel_snapshot)
        self.assertEqual(intel_snapshot["proof_paths"]["module_api"], "/api/intel/module")
        self.assertEqual(intel_snapshot["proof_paths"]["status_api"], "/api/status")
        self.assertEqual(intel_snapshot["proof_paths"]["activity_api"], "/api/activity/module")
        self.assertTrue(intel_snapshot["counts"]["signals"] >= len(intel_snapshot["signal_sources"]))
        self.assertEqual(health_snapshot["proof_paths"]["checkins_api"], "/api/health/checkins")
        self.assertEqual(health_snapshot["proof_paths"]["checkin_review_api"], "/api/health/checkins/{checkin_id}/review")

    def test_briefing_center_renders_google_calendar_count_level_planning_signal(self) -> None:
        from jarvis.morning_brief_pipeline import MorningBriefResult

        brief = MorningBriefResult(
            generated_at="2026-06-28T12:00:00+00:00",
            actor="Chris",
            greeting="Good morning, Chris. I've been paying attention.",
            what_changed=["No new JARVIS commits in the last 24 hours."],
            what_matters=[
                "Calendar pressure: connected Google Calendar returned 3 upcoming events for planning. This is count-level context, not event interpretation."
            ],
            what_is_waiting=["Inbox pressure: connected Gmail did not return unread items for this brief."],
            while_you_were_away=["No recorded catch-up traces were visible in this runtime path."],
            may_have_forgotten=["Calendar context is loaded for this brief: live — Google Calendar returned 3 upcoming events."],
            jarvis_prepared=["Memory system is live with 0 entries and 0 profile facts."],
            recommendation="Use the live brief signals you already have before expanding scope.",
            recommendation_action={
                "action_kind": "narrative_only",
                "title": "No single next surface is staged",
                "detail": "This recommendation combines brief signals, so JARVIS is staying narrative instead of pretending there is one precise handoff target.",
                "truth_note": "No direct route or saved object was staged for this recommendation in the current runtime path.",
            },
            truth_labels={
                "git_activity": "live",
                "memory": "unavailable",
                "profile_facts": "unavailable",
                "workstreams": "live",
                "agents": "live",
                "open_loops": "live",
                "health_data": "unavailable — health DB not connected locally",
                "calendar": "live — Google Calendar returned 3 upcoming events",
                "email": "connected-but-empty — Gmail is connected but no unread inbox items were retrieved",
                "obsidian_context": "local — Obsidian vault is available for local retrieval",
                "activity_trace": "empty — no recent assistant-action traces are visible",
                "delegation_trace": "empty — no recent delegation reports are visible",
                "research_trace": "empty — no recent research-task traces are visible",
                "outcome_trace": "empty — no recent artifact outcome traces are visible",
                "autonomy_trace": "empty — no recent autonomy traces are visible",
            },
        )

        with patch("jarvis.morning_brief_pipeline.generate_morning_brief", return_value=brief):
            response = asyncio.run(self._route("/briefing-center", "GET")())

        html = self._text_body(response)
        self.assertIn(
            "Calendar pressure: connected Google Calendar returned 3 upcoming events for planning. This is count-level context, not event interpretation.",
            html,
        )

    def test_briefing_center_renders_open_loop_pressure_split_between_waiting_and_revisit(self) -> None:
        from jarvis.morning_brief_pipeline import MorningBriefResult

        brief = MorningBriefResult(
            generated_at="2026-06-28T12:00:00+00:00",
            actor="Chris",
            greeting="Good morning, Chris. I've been paying attention.",
            what_changed=["No new JARVIS commits in the last 24 hours."],
            what_matters=["3 open loops are waiting on you, and 1 needs a revisit."],
            what_is_waiting=[
                "Inbox pressure: connected Gmail did not return unread items for this brief.",
                'System pressure: 4 recorded open loops need follow-through — 3 waiting on you and 1 due for revisit. Top recorded item: "Approve household budget draft".',
            ],
            while_you_were_away=["No recorded catch-up traces were visible in this runtime path."],
            may_have_forgotten=["Calendar context is still limited: connected-but-empty — calendar support is connected but no upcoming events were retrieved."],
            jarvis_prepared=["Memory system is live with 0 entries and 0 profile facts."],
            recommendation="Use the live brief signals you already have before expanding scope.",
            recommendation_action={
                "action_kind": "narrative_only",
                "title": "No single next surface is staged",
                "detail": "This recommendation combines brief signals, so JARVIS is staying narrative instead of pretending there is one precise handoff target.",
                "truth_note": "No direct route or saved object was staged for this recommendation in the current runtime path.",
            },
            truth_labels={
                "git_activity": "live",
                "memory": "unavailable",
                "profile_facts": "unavailable",
                "workstreams": "live",
                "agents": "live",
                "open_loops": "live",
                "health_data": "unavailable — health DB not connected locally",
                "calendar": "connected-but-empty — calendar support is connected but no upcoming events were retrieved",
                "email": "connected-but-empty — Gmail is connected but no unread inbox items were retrieved",
                "obsidian_context": "local — Obsidian vault is available for local retrieval",
                "activity_trace": "empty — no recent assistant-action traces are visible",
                "delegation_trace": "empty — no recent delegation reports are visible",
                "research_trace": "empty — no recent research-task traces are visible",
                "outcome_trace": "empty — no recent artifact outcome traces are visible",
                "autonomy_trace": "empty — no recent autonomy traces are visible",
            },
        )

        with patch("jarvis.morning_brief_pipeline.generate_morning_brief", return_value=brief):
            response = asyncio.run(self._route("/briefing-center", "GET")())

        html = self._text_body(response)
        self.assertIn(
            "System pressure: 4 recorded open loops need follow-through",
            html,
        )
        self.assertIn("3 waiting on you and 1 due for revisit", html)
        self.assertIn("Approve household budget draft", html)
        self.assertIn("3 open loops are waiting on you, and 1 needs a revisit.", html)

    def test_briefing_center_renders_combined_pressure_recommendation_with_direct_inbox_handoff(self) -> None:
        from jarvis.morning_brief_pipeline import MorningBriefResult

        brief = MorningBriefResult(
            generated_at="2026-06-28T12:00:00+00:00",
            actor="Chris",
            greeting="Good morning, Chris. I've been paying attention.",
            what_changed=["No new JARVIS commits in the last 24 hours."],
            what_matters=[
                "Calendar pressure: connected Google Calendar returned 2 upcoming events for planning. This is count-level context, not event interpretation.",
                "3 open loops are waiting on you, and 1 needs a revisit.",
            ],
            what_is_waiting=[
                "Inbox pressure: connected Gmail returned 6 unread items. This is waiting pressure, not thread understanding.",
                'System pressure: 4 recorded open loops need follow-through — 3 waiting on you and 1 due for revisit. Top recorded item: "Approve household budget draft".',
            ],
            while_you_were_away=["No recorded catch-up traces were visible in this runtime path."],
            may_have_forgotten=["Calendar context is loaded for this brief: live — Google Calendar returned 2 upcoming events."],
            jarvis_prepared=["Memory system is live with 0 entries and 0 profile facts."],
            recommendation=(
                "Connected Gmail shows 6 unread items, your calendar already has 2 upcoming events, and 3 open loops are already waiting on you. "
                "Start with inbox pressure before staging more follow-through."
            ),
            recommendation_action={
                "action_kind": "direct_route",
                "title": "Review stacked inbox pressure first",
                "detail": "Email Center is the most precise current first surface when inbox, calendar, and open-loop pressure are all active at once.",
                "route": "/email-center",
                "route_label": "Open Email Center",
                "truth_note": "This opens the inbox surface first. It does not interpret thread meaning or resolve calendar and open-loop pressure by itself.",
            },
            truth_labels={
                "git_activity": "live",
                "memory": "unavailable",
                "profile_facts": "unavailable",
                "workstreams": "live",
                "agents": "live",
                "open_loops": "live",
                "health_data": "unavailable — health DB not connected locally",
                "calendar": "live — Google Calendar returned 2 upcoming events",
                "email": "live — Gmail returned 6 unread items",
                "obsidian_context": "local — Obsidian vault is available for local retrieval",
                "activity_trace": "empty — no recent assistant-action traces are visible",
                "delegation_trace": "empty — no recent delegation reports are visible",
                "research_trace": "empty — no recent research-task traces are visible",
                "outcome_trace": "empty — no recent artifact outcome traces are visible",
                "autonomy_trace": "empty — no recent autonomy traces are visible",
            },
        )

        with patch("jarvis.morning_brief_pipeline.generate_morning_brief", return_value=brief):
            response = asyncio.run(self._route("/briefing-center", "GET")())

        html = self._text_body(response)
        self.assertIn(
            "Connected Gmail shows 6 unread items, your calendar already has 2 upcoming events, and 3 open loops are already waiting on you.",
            html,
        )
        self.assertIn("Review stacked inbox pressure first", html)
        self.assertIn("Open Email Center", html)
        self.assertIn(
            "This opens the inbox surface first. It does not interpret thread meaning or resolve calendar and open-loop pressure by itself.",
            html,
        )

    def test_briefing_center_prioritizes_recorded_catch_up_over_generic_activity(self) -> None:
        from jarvis.morning_brief_pipeline import MorningBriefResult

        brief = MorningBriefResult(
            generated_at="2026-06-28T12:00:00+00:00",
            actor="Chris",
            greeting="Good morning, Chris. I've been paying attention.",
            what_changed=["No new JARVIS commits in the last 24 hours."],
            what_matters=["No new pressure changes were recorded for this check."],
            what_is_waiting=["Inbox pressure is quiet in this runtime snapshot."],
            while_you_were_away=[
                "Delegation catch-up: 1 delegation report completed with inspectable output.",
                "Research catch-up: 1 task synthesis update recorded from attached evidence only.",
                "Outcome review: 2 explicit artifact outcome records captured.",
                "Autonomy proof: 1 local follow-through proof packet recorded. This is local proof only, not broad autonomous execution.",
            ],
            may_have_forgotten=["Calendar context is still limited: connected-but-empty — calendar support is connected but no upcoming events were retrieved."],
            jarvis_prepared=["Memory system is live with 0 entries and 0 profile facts."],
            recommendation="Review the recorded catch-up outputs before opening new work.",
            recommendation_action={
                "action_kind": "direct_route",
                "title": "Inspect latest delegation report",
                "detail": "Review contractor packet is a real completed delegation output and can be opened directly.",
                "route": "/mission-board/delegation-report/mission-1/r-1?return_to=%2Fbriefing-center",
                "route_label": "Open Delegation Report",
                "truth_note": "This opens a recorded delegation report. It does not imply any new delegated work ran beyond the stored output.",
            },
            truth_labels={
                "git_activity": "live",
                "memory": "unavailable",
                "profile_facts": "unavailable",
                "workstreams": "live",
                "agents": "live",
                "open_loops": "live",
                "health_data": "unavailable — health DB not connected locally",
                "calendar": "connected-but-empty — calendar support is connected but no upcoming events were retrieved",
                "email": "connected-but-empty — Gmail is connected but no unread inbox items were retrieved",
                "obsidian_context": "local — Obsidian vault is available for local retrieval",
                "activity_trace": "recorded",
                "delegation_trace": "recorded",
                "research_trace": "recorded",
                "outcome_trace": "recorded",
                "autonomy_trace": "recorded",
            },
        )

        with patch("jarvis.morning_brief_pipeline.generate_morning_brief", return_value=brief):
            response = asyncio.run(self._route("/briefing-center", "GET")())

        html = self._text_body(response)
        self.assertIn("Delegation catch-up: 1 delegation report completed with inspectable output.", html)
        self.assertIn("Research catch-up: 1 task synthesis update recorded from attached evidence only.", html)
        self.assertIn("Outcome review: 2 explicit artifact outcome records captured.", html)
        self.assertIn(
            "Autonomy proof: 1 local follow-through proof packet recorded. This is local proof only, not broad autonomous execution.",
            html,
        )
        self.assertNotIn("Recorded assistant activity: 1 assistant action logged.", html)

    def test_briefing_center_renders_obsidian_support_as_grounding_help_without_fake_recall(self) -> None:
        from jarvis.morning_brief_pipeline import MorningBriefResult

        brief = MorningBriefResult(
            generated_at="2026-06-28T12:00:00+00:00",
            actor="Chris",
            greeting="Good morning, Chris. I've been paying attention.",
            what_changed=["No new JARVIS commits in the last 24 hours."],
            what_matters=["3 open loops are waiting on you, and 1 needs a revisit."],
            what_is_waiting=[
                'System pressure: 4 recorded open loops need follow-through — 3 waiting on you and 1 due for revisit. Top recorded item: "Approve household budget draft".'
            ],
            while_you_were_away=["No recorded catch-up traces were visible in this runtime path."],
            may_have_forgotten=[
                "Obsidian local context is available if you want to ground today's follow-through in prior notes. This brief did not open or recall any specific note."
            ],
            jarvis_prepared=["Memory system is live with 0 entries and 0 profile facts."],
            recommendation="Use the live brief signals you already have before expanding scope.",
            recommendation_action={
                "action_kind": "narrative_only",
                "title": "No single next surface is staged",
                "detail": "This recommendation combines brief signals, so JARVIS is staying narrative instead of pretending there is one precise handoff target.",
                "truth_note": "No direct route or saved object was staged for this recommendation in the current runtime path.",
            },
            truth_labels={
                "git_activity": "live",
                "memory": "unavailable",
                "profile_facts": "unavailable",
                "workstreams": "live",
                "agents": "live",
                "open_loops": "live",
                "health_data": "unavailable — health DB not connected locally",
                "calendar": "connected-but-empty — calendar support is connected but no upcoming events were retrieved",
                "email": "connected-but-empty — Gmail is connected but no unread inbox items were retrieved",
                "obsidian_context": "local — Obsidian vault is available for local retrieval",
                "activity_trace": "empty — no recent assistant-action traces are visible",
                "delegation_trace": "empty — no recent delegation reports are visible",
                "research_trace": "empty — no recent research-task traces are visible",
                "outcome_trace": "empty — no recent artifact outcome traces are visible",
                "autonomy_trace": "empty — no recent autonomy traces are visible",
            },
        )

        with patch("jarvis.morning_brief_pipeline.generate_morning_brief", return_value=brief):
            response = asyncio.run(self._route("/briefing-center", "GET")())

        html = self._text_body(response)
        self.assertIn(
            "Obsidian local context is available if you want to ground today's follow-through in prior notes.",
            html,
        )
        self.assertIn("This brief did not open or recall any specific note.", html)

    def test_home_dashboard_returns_honest_unavailable_payload_when_db_errors(self) -> None:
        route = self._route("/api/home/dashboard", "GET")

        with patch.object(service_module, "_get_home_db", return_value=_FailingHomeDashboardDB()):
            response = asyncio.run(route())

        payload = self._json_body(response)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(payload["available"])
        self.assertIn("Home dashboard unavailable", payload["error"])
        self.assertIn("postgres unavailable", payload["error"])

    def test_home_read_routes_return_honest_unavailable_payloads_when_db_errors(self) -> None:
        routes_with_empty_keys = {
            "/api/home/projects": "projects",
            "/api/home/tasks": "tasks",
            "/api/home/tasks/overdue": "tasks",
            "/api/home/tasks/today": "tasks",
            "/api/home/email": "emails",
            "/api/home/calendar": "events",
            "/api/home/calendar/upcoming": "events",
        }

        with patch.object(service_module, "_get_home_db", return_value=_FailingHomeReadDB()):
            for path, empty_key in routes_with_empty_keys.items():
                response = asyncio.run(self._route(path, "GET")())
                payload = self._json_body(response)
                self.assertEqual(response.status_code, 200, msg=path)
                self.assertFalse(payload["available"], msg=path)
                self.assertIn("unavailable", payload["error"], msg=path)
                self.assertIn("postgres unavailable", payload["error"], msg=path)
                self.assertEqual(payload[empty_key], [], msg=path)

            email_stats_response = asyncio.run(self._route("/api/home/email/stats", "GET")())
            email_stats_payload = self._json_body(email_stats_response)
            self.assertEqual(email_stats_response.status_code, 200)
            self.assertFalse(email_stats_payload["available"])
            self.assertIn("Home email stats unavailable", email_stats_payload["error"])
            self.assertEqual(email_stats_payload["stats"], {})

    def test_mission_delegation_report_routes_expose_inspectable_output_surface(self) -> None:
        create_response = asyncio.run(
            self._route("/api/missions/{mission_id}/delegations/{delegation_id}/report", "POST")(
                mission_id="mission-1",
                delegation_id="delegation-1",
                payload={
                    "producing_agent": "storm",
                    "title": "Weather review delivered",
                    "summary": "Storm returned a concrete travel weather readout.",
                    "detail": "This is a bounded delegation artifact, not a background autonomy claim.",
                    "key_output": "Weather posture is safe enough for the current trip window.",
                    "next_step": "Proceed with the current route plan.",
                    "evidence_note": "Bounded local review only; no invisible agent execution.",
                },
            )
        )
        reports_response = asyncio.run(
            self._route("/api/missions/{mission_id}/delegation-reports", "GET")(mission_id="mission-1")
        )
        report_response = asyncio.run(
            self._route("/api/missions/{mission_id}/delegation-reports/{report_id}", "GET")(
                mission_id="mission-1",
                report_id="report-1",
            )
        )
        work_state_response = asyncio.run(
            self._route("/api/missions/{mission_id}/work-state", "GET")(mission_id="mission-1")
        )

        created = self._json_body(create_response)
        reports = self._json_body(reports_response)
        report = self._json_body(report_response)
        work_state = self._json_body(work_state_response)

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(len(created["delegation_reports"]), 1)
        self.assertEqual(created["delegation_reports"][0]["producer_agent"], "storm")
        self.assertEqual(created["delegation_reports"][0]["key_output"], "Weather posture is safe enough for the current trip window.")
        self.assertEqual(created["outputs_detail"][0]["kind"], "delegation-report")
        self.assertEqual(reports[0]["status"], "completed-with-output")
        self.assertEqual(report["artifact_ref"], "/api/missions/mission-1/delegation-reports/report-1")
        self.assertEqual(work_state["summary"]["delegations_completed_with_output"], 1)
        self.assertEqual(work_state["delegations"][0]["inspectable_output_status"], "completed-with-output")

    def test_delegation_report_review_surface_renders_readable_report_fields(self) -> None:
        asyncio.run(
            self._route("/api/missions/{mission_id}/delegations/{delegation_id}/report", "POST")(
                mission_id="mission-1",
                delegation_id="delegation-1",
                payload={
                    "producing_agent": "storm",
                    "title": "Weather review delivered",
                    "summary": "Storm returned a concrete travel weather readout.",
                    "detail": "This report proves delegated work through a readable review page.",
                    "key_output": "The route can stay as planned.",
                    "next_step": "Share the weather call with the mission owner.",
                    "evidence_note": "Derived from the submitted delegation report payload only.",
                },
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/delegation-report/{mission_id}/{report_id}", "GET")(
                mission_id="mission-1",
                report_id="report-1",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Mission Board Delegation Review", review_html)
        self.assertIn("Weather review delivered", review_html)
        self.assertIn("Storm returned a concrete travel weather readout.", review_html)
        self.assertIn("The route can stay as planned.", review_html)
        self.assertIn("Share the weather call with the mission owner.", review_html)
        self.assertIn("Derived from the submitted delegation report payload only.", review_html)
        self.assertIn("This report proves delegated work through a readable review page.", review_html)
        self.assertIn("producer", review_html.lower())
        self.assertIn("ambient-router", review_html)
        self.assertIn("storm", review_html)
        self.assertIn("Open Outcome Review", review_html)
        self.assertIn("/api/missions/mission-1/delegation-reports/report-1", review_html)
        self.assertIn("delegation-report-delegation-1", review_html)
        self.assertIn("Return to Delegation Queue", review_html)
        self.assertIn("/mission-board?mission_id=mission-1#delegation-review-completed", review_html)

    def test_delegation_report_review_surface_honors_safe_return_to_continuity_link(self) -> None:
        asyncio.run(
            self._route("/api/missions/{mission_id}/delegations/{delegation_id}/report", "POST")(
                mission_id="mission-1",
                delegation_id="delegation-1",
                payload={
                    "producing_agent": "storm",
                    "title": "Weather review delivered",
                    "summary": "Storm returned a concrete travel weather readout.",
                    "detail": "Readable output is available.",
                },
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/delegation-report/{mission_id}/{report_id}", "GET")(
                mission_id="mission-1",
                report_id="report-1",
                return_to="/mission-board?mission_id=mission-1#delegation-review-requested",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn('/mission-board?mission_id=mission-1#delegation-review-requested', review_html)

    def test_delegation_report_review_surface_ignores_unsafe_return_to_target(self) -> None:
        asyncio.run(
            self._route("/api/missions/{mission_id}/delegations/{delegation_id}/report", "POST")(
                mission_id="mission-1",
                delegation_id="delegation-1",
                payload={
                    "producing_agent": "storm",
                    "title": "Weather review delivered",
                    "summary": "Storm returned a concrete travel weather readout.",
                    "detail": "Readable output is available.",
                },
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/delegation-report/{mission_id}/{report_id}", "GET")(
                mission_id="mission-1",
                report_id="report-1",
                return_to="https://example.com/outside",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("/mission-board?mission_id=mission-1#delegation-review-completed", review_html)
        self.assertNotIn("https://example.com/outside", review_html)

    def test_delegation_report_review_surface_degrades_plainly_when_report_is_missing(self) -> None:
        review_response = asyncio.run(
            self._route("/mission-board/delegation-report/{mission_id}/{report_id}", "GET")(
                mission_id="mission-1",
                report_id="missing-report",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 404)
        self.assertIn("unavailable", review_html.lower())
        self.assertIn("This delegation report is unavailable in the current runtime path.", review_html)

    def test_delegation_report_route_rejects_summary_only_completion(self) -> None:
        with self.assertRaises(service_module.HTTPException) as exc_info:
            asyncio.run(
                self._route("/api/missions/{mission_id}/delegations/{delegation_id}/report", "POST")(
                    mission_id="mission-1",
                    delegation_id="delegation-1",
                    payload={
                        "producing_agent": "storm",
                        "title": "Weather review delivered",
                        "summary": "Storm returned a concrete travel weather readout.",
                    },
                )
            )

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertIn("Delegation reports need at least one useful supporting field", exc_info.exception.detail)

    def test_artifact_outcome_route_records_real_checklist_outcome_without_learning_claim(self) -> None:
        response = asyncio.run(
            self._route("/api/artifact-outcomes", "POST")(
                {
                    "actor": "Chris",
                    "target_kind": "checklist",
                    "target_id": "checklist-1",
                    "outcome": "helpful",
                    "note": "Used this to get packed for the campout.",
                }
            )
        )
        payload = self._json_body(response)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload["recorded_outcome"]["outcome"], "helpful")
        self.assertEqual(payload["target"]["target_category"], "work_object")
        self.assertEqual(payload["target"]["storage_mode"], "persisted_local_object_record")
        self.assertEqual(payload["learning_effect"], "none")
        self.assertIn("No automatic learning or behavior change", payload["message"])

        snapshot_response = asyncio.run(
            self._route("/api/artifact-outcomes/{target_kind}/{target_id}", "GET")(
                target_kind="checklist",
                target_id="checklist-1",
                mission_id="",
            )
        )
        snapshot_payload = self._json_body(snapshot_response)

        self.assertEqual(snapshot_response.status_code, 200)
        self.assertEqual(snapshot_payload["latest_outcome"]["outcome"], "helpful")
        self.assertEqual(len(snapshot_payload["outcome_history"]), 1)

    def test_artifact_outcome_route_records_real_delegation_report_outcome(self) -> None:
        asyncio.run(
            self._route("/api/missions/{mission_id}/delegations/{delegation_id}/report", "POST")(
                mission_id="mission-1",
                delegation_id="delegation-1",
                payload={
                    "producing_agent": "storm",
                    "title": "Weather review delivered",
                    "summary": "Storm returned a concrete travel weather readout.",
                    "detail": "Readable output is available.",
                },
            )
        )

        response = asyncio.run(
            self._route("/api/artifact-outcomes", "POST")(
                {
                    "actor": "Chris",
                    "target_kind": "delegation_report",
                    "target_id": "report-1",
                    "mission_id": "mission-1",
                    "outcome": "used",
                    "note": "I used the delegated readout to continue the mission.",
                }
            )
        )
        payload = self._json_body(response)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload["recorded_outcome"]["outcome"], "used")
        self.assertEqual(payload["target"]["target_category"], "delegated_output")
        self.assertEqual(payload["target"]["artifact_ref"], "/api/missions/mission-1/delegation-reports/report-1")
        self.assertEqual(payload["learning_effect"], "none")

    def test_artifact_outcome_route_rejects_unknown_target(self) -> None:
        with self.assertRaises(service_module.HTTPException) as exc_info:
            asyncio.run(
                self._route("/api/artifact-outcomes", "POST")(
                    {
                        "actor": "Chris",
                        "target_kind": "checklist",
                        "target_id": "missing-checklist",
                        "outcome": "used",
                    }
                )
            )

        self.assertEqual(exc_info.exception.status_code, 404)
        self.assertIn("checklist not found", exc_info.exception.detail.lower())

    def test_artifact_outcome_route_rejects_invalid_outcome_label(self) -> None:
        with self.assertRaises(service_module.HTTPException) as exc_info:
            asyncio.run(
                self._route("/api/artifact-outcomes", "POST")(
                    {
                        "actor": "Chris",
                        "target_kind": "checklist",
                        "target_id": "checklist-1",
                        "outcome": "excellent",
                    }
                )
            )

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertIn("outcome must be one of", exc_info.exception.detail)

    def test_artifact_outcome_review_surface_renders_recorded_outcome_fields(self) -> None:
        asyncio.run(
            self._route("/api/artifact-outcomes", "POST")(
                {
                    "actor": "Chris",
                    "target_kind": "checklist",
                    "target_id": "checklist-1",
                    "outcome": "helpful",
                    "note": "Used this to get packed for the campout.",
                }
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/artifact-outcome/{target_kind}/{target_id}", "GET")(
                target_kind="checklist",
                target_id="checklist-1",
                mission_id="",
                return_to="/mission-board",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Artifact Outcome Review", review_html)
        self.assertIn("Scout campout checklist", review_html)
        self.assertIn("helpful", review_html)
        self.assertIn("Used this to get packed for the campout.", review_html)
        self.assertIn("Update Outcome", review_html)
        self.assertIn("/api/artifact-outcomes", review_html)
        self.assertIn("artifact-outcome-select", review_html)
        self.assertIn("/mission-board/artifact-outcomes", review_html)
        self.assertIn("Return to Mission Board", review_html)
        self.assertIn("learning effect: none", review_html.lower())
        self.assertIn("This page shows explicit recorded outcome history for this target only.", review_html)
        self.assertIn("No automatic learning or behavior change is implied by this surface.", review_html)

    def test_artifact_outcome_review_surface_stays_plain_when_no_outcome_exists(self) -> None:
        review_response = asyncio.run(
            self._route("/mission-board/artifact-outcome/{target_kind}/{target_id}", "GET")(
                target_kind="checklist",
                target_id="checklist-1",
                mission_id="",
                return_to="/mission-board",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("No Outcome Recorded Yet", review_html)
        self.assertIn("No outcome has been recorded for this artifact yet in the current runtime path.", review_html)
        self.assertIn("No explicit outcome has been recorded yet.", review_html)
        self.assertIn("Record Outcome", review_html)
        self.assertIn("Return to Mission Board", review_html)
        self.assertIn('<option value="used">used</option>', review_html)
        self.assertIn("Recording an outcome here updates the real stored review history for this target.", review_html)

    def test_artifact_outcome_review_surface_supports_revising_existing_explicit_judgment(self) -> None:
        asyncio.run(
            self._route("/api/missions/{mission_id}/delegations/{delegation_id}/report", "POST")(
                mission_id="mission-1",
                delegation_id="delegation-1",
                payload={
                    "producing_agent": "storm",
                    "title": "Weather review delivered",
                    "summary": "Storm returned a concrete travel weather readout.",
                    "detail": "Readable output is available.",
                },
            )
        )

        asyncio.run(
            self._route("/api/artifact-outcomes", "POST")(
                {
                    "actor": "Chris",
                    "target_kind": "delegation_report",
                    "target_id": "report-1",
                    "mission_id": "mission-1",
                    "outcome": "used",
                    "note": "I used the first delegated output.",
                }
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/artifact-outcome/{target_kind}/{target_id}", "GET")(
                target_kind="delegation_report",
                target_id="report-1",
                mission_id="mission-1",
                return_to="/mission-board?mission_id=mission-1#delegation-review-completed",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Update Outcome", review_html)
        self.assertIn("I used the first delegated output.", review_html)
        self.assertIn("Return to Mission Board", review_html)
        self.assertIn("return_to=%2Fmission-board%3Fmission_id%3Dmission-1%23delegation-review-completed", review_html)
        self.assertIn("You can record a new explicit judgment here if the latest outcome needs to be revised.", review_html)

    def test_artifact_outcome_summary_api_aggregates_real_recorded_judgments(self) -> None:
        asyncio.run(
            self._route("/api/missions/{mission_id}/delegations/{delegation_id}/report", "POST")(
                mission_id="mission-1",
                delegation_id="delegation-1",
                payload={
                    "producing_agent": "storm",
                    "title": "Weather review delivered",
                    "summary": "Storm returned a concrete travel weather readout.",
                    "detail": "Readable output is available.",
                },
            )
        )
        asyncio.run(
            self._route("/api/artifact-outcomes", "POST")(
                {
                    "actor": "Chris",
                    "target_kind": "checklist",
                    "target_id": "checklist-1",
                    "outcome": "helpful",
                    "note": "Used it for the campout.",
                }
            )
        )
        asyncio.run(
            self._route("/api/artifact-outcomes", "POST")(
                {
                    "actor": "Chris",
                    "target_kind": "delegation_report",
                    "target_id": "report-1",
                    "mission_id": "mission-1",
                    "outcome": "used",
                    "note": "Used the delegated readout to continue the mission.",
                }
            )
        )

        response = asyncio.run(self._route("/api/artifact-outcomes-summary", "GET")(mission_id=""))
        payload = self._json_body(response)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["total_records"], 2)
        self.assertEqual(payload["counts_by_outcome"]["helpful"], 1)
        self.assertEqual(payload["counts_by_outcome"]["used"], 1)
        self.assertEqual(payload["counts_by_target_kind"]["checklist"], 1)
        self.assertEqual(payload["counts_by_target_kind"]["delegation_report"], 1)
        self.assertEqual(payload["learning_effect"], "none")
        self.assertEqual(payload["recent_outcomes"][0]["target_kind"], "delegation_report")

    def test_artifact_outcome_summary_review_surface_stays_truthful_and_mission_filterable(self) -> None:
        asyncio.run(
            self._route("/api/missions/{mission_id}/delegations/{delegation_id}/report", "POST")(
                mission_id="mission-1",
                delegation_id="delegation-1",
                payload={
                    "producing_agent": "storm",
                    "title": "Weather review delivered",
                    "summary": "Storm returned a concrete travel weather readout.",
                    "detail": "Readable output is available.",
                },
            )
        )
        asyncio.run(
            self._route("/api/artifact-outcomes", "POST")(
                {
                    "actor": "Chris",
                    "target_kind": "delegation_report",
                    "target_id": "report-1",
                    "mission_id": "mission-1",
                    "outcome": "completed",
                    "note": "Closed the loop from the delegated weather review.",
                }
            )
        )

        review_response = asyncio.run(self._route("/mission-board/artifact-outcomes", "GET")(mission_id="mission-1"))
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Outcome Summary", review_html)
        self.assertIn("Mission mission-1", review_html)
        self.assertIn("completed", review_html)
        self.assertIn("Weather review delivered", review_html)
        self.assertIn("This is recorded outcome history only. It does not imply automatic learning, optimization, or behavior change.", review_html)
        self.assertIn("/api/artifact-outcomes-summary?mission_id=mission-1", review_html)
        self.assertIn("/mission-board/artifact-outcome/delegation_report/report-1?mission_id=mission-1&return_to=%2Fmission-board%2Fartifact-outcomes%3Fmission_id%3Dmission-1", review_html)

    def test_artifact_outcome_summary_to_review_link_preserves_summary_return_path(self) -> None:
        asyncio.run(
            self._route("/api/artifact-outcomes", "POST")(
                {
                    "actor": "Chris",
                    "target_kind": "checklist",
                    "target_id": "checklist-1",
                    "outcome": "used",
                    "note": "Used this in the current run.",
                }
            )
        )

        summary_response = asyncio.run(self._route("/mission-board/artifact-outcomes", "GET")(mission_id=""))
        summary_html = self._text_body(summary_response)

        self.assertEqual(summary_response.status_code, 200)
        self.assertIn("/mission-board/artifact-outcome/checklist/checklist-1?return_to=%2Fmission-board%2Fartifact-outcomes", summary_html)

    def test_artifact_outcome_review_surface_names_summary_return_path_plainly(self) -> None:
        asyncio.run(
            self._route("/api/artifact-outcomes", "POST")(
                {
                    "actor": "Chris",
                    "target_kind": "checklist",
                    "target_id": "checklist-1",
                    "outcome": "used",
                    "note": "Used this in the current run.",
                }
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/artifact-outcome/{target_kind}/{target_id}", "GET")(
                target_kind="checklist",
                target_id="checklist-1",
                mission_id="",
                return_to="/mission-board/artifact-outcomes",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Return to Outcome Summary", review_html)

    def test_research_task_route_captures_real_intent_without_claiming_research_happened(self) -> None:
        response = asyncio.run(
            self._route("/api/research-tasks", "POST")(
                {
                    "actor": "Chris",
                    "title": "Pool robot options",
                    "question": "Which pool robot direction should I compare first?",
                    "desired_scope": "Capture the scope and constraints before any live research.",
                    "constraints": ["Stay under $1,000"],
                    "source_expectations": ["manufacturer specs", "owner reviews"],
                }
            )
        )
        payload = self._json_body(response)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload["task"]["object_kind"], "research_task")
        self.assertEqual(payload["task"]["status"], "queued")
        self.assertEqual(payload["research_effect"], "not_performed")
        self.assertFalse(bool(payload["task"]["research_performed"]))
        self.assertIn("queued intent only", payload["message"].lower())

    def test_research_task_route_rejects_missing_question(self) -> None:
        with self.assertRaises(service_module.HTTPException) as exc_info:
            asyncio.run(
                self._route("/api/research-tasks", "POST")(
                    {
                        "actor": "Chris",
                        "title": "Pool robot options",
                        "question": "",
                    }
                )
            )

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertIn("question is required", exc_info.exception.detail)

    def test_research_task_queue_surface_renders_inspectable_queued_objects_plainly(self) -> None:
        asyncio.run(
            self._route("/api/research-tasks", "POST")(
                {
                    "actor": "Chris",
                    "title": "Retirement communities",
                    "question": "What should I compare across retirement communities near Northern Kentucky?",
                    "desired_scope": "Hold the research intent and source expectations only.",
                    "source_expectations": ["pricing", "care level", "distance"],
                }
            )
        )

        queue_response = asyncio.run(self._route("/mission-board/research-tasks", "GET")())
        queue_html = self._text_body(queue_response)

        self.assertEqual(queue_response.status_code, 200)
        self.assertIn("Research Task Queue", queue_html)
        self.assertIn("Inspectable Research Task Records", queue_html)
        self.assertIn("Retirement communities", queue_html)
        self.assertIn("What should I compare across retirement communities near Northern Kentucky?", queue_html)
        self.assertIn("queued", queue_html)
        self.assertIn("Return to Mission Board", queue_html)
        self.assertIn("Inspect Research Task Record", queue_html)
        self.assertIn("inspectable research task records only", queue_html)
        self.assertIn("does not mean the research has already been performed", queue_html)
        self.assertIn("/api/research-tasks", queue_html)
        self.assertIn("/mission-board/research-tasks/research-task-1?return_to=%2Fmission-board%2Fresearch-tasks", queue_html)

    def test_research_task_queue_api_lists_real_captured_tasks(self) -> None:
        asyncio.run(
            self._route("/api/research-tasks", "POST")(
                {
                    "actor": "Chris",
                    "title": "Scout trailer storage",
                    "question": "What storage constraints should I check first for Scout trailer options?",
                    "status": "blocked",
                    "constraints": ["Need weather protection first"],
                }
            )
        )

        response = asyncio.run(self._route("/api/research-tasks", "GET")())
        payload = self._json_body(response)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["total_tasks"], 1)
        self.assertEqual(payload["counts_by_status"]["blocked"], 1)
        self.assertEqual(payload["tasks"][0]["title"], "Scout trailer storage")
        self.assertEqual(payload["research_effect"], "not_performed")

    def test_research_task_review_surface_renders_real_task_and_truth_boundary(self) -> None:
        asyncio.run(
            self._route("/api/research-tasks", "POST")(
                {
                    "actor": "Chris",
                    "title": "Pool robot options",
                    "question": "Which pool robot direction should I compare first?",
                    "desired_scope": "Capture constraints before any real research work starts.",
                    "constraints": ["Stay under $1,000"],
                    "source_expectations": ["manufacturer specs", "owner reviews"],
                }
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/research-tasks/{task_id}", "GET")(
                task_id="research-task-1",
                return_to="/mission-board/research-tasks",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Research Task Review", review_html)
        self.assertIn("Pool robot options", review_html)
        self.assertIn("Which pool robot direction should I compare first?", review_html)
        self.assertIn("Research has not yet been performed for this task in the current runtime path.", review_html)
        self.assertIn("Return to Research Task Queue", review_html)
        self.assertIn("inspectable research task record only", review_html)
        self.assertIn("does not claim completed research, discovered sources, or autonomous background execution", review_html)
        self.assertIn("Attach at least one evidence item first.", review_html)
        self.assertIn('href="/mission-board/research-tasks"', review_html)
        self.assertIn("/api/research-tasks/research-task-1", review_html)
        self.assertIn("Update Research Task", review_html)
        self.assertIn("/api/research-tasks/research-task-1", review_html)

    def test_research_task_update_route_revises_fields_and_status_without_fake_research_claim(self) -> None:
        asyncio.run(
            self._route("/api/research-tasks", "POST")(
                {
                    "actor": "Chris",
                    "title": "Pool robot options",
                    "question": "Which pool robot direction should I compare first?",
                    "desired_scope": "Capture constraints before any real research work starts.",
                }
            )
        )

        response = asyncio.run(
            self._route("/api/research-tasks/{task_id}", "POST")(
                task_id="research-task-1",
                payload={
                    "title": "Pool robot shortlist",
                    "question": "Which pool robot shortlist should I compare first?",
                    "desired_scope": "Hold the scope while I gather sources later.",
                    "status": "blocked",
                    "constraints": ["Keep it under $1,000"],
                    "source_expectations": ["manufacturer specs"],
                },
            )
        )
        payload = self._json_body(response)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["task"]["title"], "Pool robot shortlist")
        self.assertEqual(payload["task"]["status"], "blocked")
        self.assertEqual(payload["task"]["constraints"], ["Keep it under $1,000"])
        self.assertEqual(payload["research_effect"], "not_performed")
        self.assertFalse(bool(payload["task"]["research_performed"]))
        self.assertIn("do not imply", payload["message"].lower())

    def test_research_task_review_surface_shows_updated_state_cleanly(self) -> None:
        asyncio.run(
            self._route("/api/research-tasks", "POST")(
                {
                    "actor": "Chris",
                    "title": "Retirement communities",
                    "question": "What should I compare first?",
                    "desired_scope": "Start narrow.",
                }
            )
        )
        asyncio.run(
            self._route("/api/research-tasks/{task_id}", "POST")(
                task_id="research-task-1",
                payload={
                    "title": "Retirement communities shortlist",
                    "question": "Which retirement communities should I compare first near Northern Kentucky?",
                    "desired_scope": "Focus on pricing, care level, and distance.",
                    "status": "in_progress",
                    "constraints": ["Stay within driving distance"],
                    "source_expectations": ["pricing", "care level"],
                },
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/research-tasks/{task_id}", "GET")(
                task_id="research-task-1",
                return_to="/mission-board/research-tasks",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Retirement communities shortlist", review_html)
        self.assertIn("in_progress", review_html)
        self.assertIn("Stay within driving distance", review_html)
        self.assertIn("pricing, care level", review_html)
        self.assertIn("Changing status alone still does not prove that research output or sources exist.", review_html)

    def test_research_task_evidence_route_attaches_manual_item_without_fake_research_claim(self) -> None:
        asyncio.run(
            self._route("/api/research-tasks", "POST")(
                {
                    "actor": "Chris",
                    "title": "Pool robot options",
                    "question": "Which pool robot direction should I compare first?",
                    "desired_scope": "Keep it narrow for now.",
                }
            )
        )

        response = asyncio.run(
            self._route("/api/research-tasks/{task_id}/evidence", "POST")(
                task_id="research-task-1",
                payload={
                    "source_label": "Owner review thread",
                    "source_locator": "https://example.com/review-thread",
                    "evidence_note": "Several owners reported easy maintenance.",
                    "capture_status": "captured",
                    "confidence_label": "preliminary",
                },
            )
        )
        payload = self._json_body(response)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload["evidence_item"]["source_label"], "Owner review thread")
        self.assertEqual(payload["evidence_item"]["capture_mode"], "manual_entry")
        self.assertFalse(bool(payload["evidence_item"]["retrieval_used"]))
        self.assertEqual(payload["research_effect"], "not_performed")
        self.assertFalse(bool(payload["task"]["research_performed"]))
        self.assertIn("does not imply completed research", payload["message"].lower())

    def test_research_task_evidence_route_rejects_empty_evidence_item(self) -> None:
        asyncio.run(
            self._route("/api/research-tasks", "POST")(
                {
                    "actor": "Chris",
                    "title": "Pool robot options",
                    "question": "Which pool robot direction should I compare first?",
                }
            )
        )

        with self.assertRaises(service_module.HTTPException) as exc_info:
            asyncio.run(
                self._route("/api/research-tasks/{task_id}/evidence", "POST")(
                    task_id="research-task-1",
                    payload={
                        "source_label": "",
                        "source_locator": "",
                        "evidence_note": "",
                    },
                )
            )

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertIn("source_label is required", exc_info.exception.detail)

    def test_research_task_review_surface_renders_captured_evidence_items_plainly(self) -> None:
        asyncio.run(
            self._route("/api/research-tasks", "POST")(
                {
                    "actor": "Chris",
                    "title": "Retirement communities",
                    "question": "What should I compare first?",
                    "desired_scope": "Hold the scope first.",
                }
            )
        )
        asyncio.run(
            self._route("/api/research-tasks/{task_id}/evidence", "POST")(
                task_id="research-task-1",
                payload={
                    "source_label": "Facility brochure",
                    "source_locator": "/local/notes/facility-brochure.pdf",
                    "evidence_note": "Lists care levels and distance notes.",
                    "capture_status": "captured",
                    "confidence_label": "manual note",
                },
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/research-tasks/{task_id}", "GET")(
                task_id="research-task-1",
                return_to="/mission-board/research-tasks",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Evidence Items", review_html)
        self.assertIn("Facility brochure", review_html)
        self.assertIn("/local/notes/facility-brochure.pdf", review_html)
        self.assertIn("Lists care levels and distance notes.", review_html)
        self.assertIn("manual_entry", review_html)
        self.assertIn("do not, by themselves, prove final conclusions, validated synthesis, or completed research", review_html)
        self.assertIn("Attach Evidence Item", review_html)

    def test_research_task_synthesis_route_generates_attached_evidence_only_summary(self) -> None:
        asyncio.run(
            self._route("/api/research-tasks", "POST")(
                {
                    "actor": "Chris",
                    "title": "Retirement communities",
                    "question": "What should I compare first?",
                    "desired_scope": "Hold the scope first.",
                }
            )
        )
        asyncio.run(
            self._route("/api/research-tasks/{task_id}/evidence", "POST")(
                task_id="research-task-1",
                payload={
                    "source_label": "Facility brochure",
                    "source_locator": "/local/notes/facility-brochure.pdf",
                    "evidence_note": "Lists care levels and distance notes.",
                    "capture_status": "captured",
                    "confidence_label": "manual note",
                },
            )
        )

        response = asyncio.run(
            self._route("/api/research-tasks/{task_id}/synthesis", "POST")(task_id="research-task-1")
        )
        payload = self._json_body(response)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload["synthesis"]["synthesis_mode"], "attached_evidence_only")
        self.assertEqual(payload["synthesis"]["evidence_count"], 1)
        self.assertIn("attached evidence set", payload["message"].lower())
        self.assertFalse(bool(payload["task"]["research_performed"]))

    def test_research_task_synthesis_route_rejects_task_without_evidence(self) -> None:
        asyncio.run(
            self._route("/api/research-tasks", "POST")(
                {
                    "actor": "Chris",
                    "title": "Pool robot options",
                    "question": "Which pool robot direction should I compare first?",
                }
            )
        )

        with self.assertRaises(service_module.HTTPException) as exc_info:
            asyncio.run(
                self._route("/api/research-tasks/{task_id}/synthesis", "POST")(task_id="research-task-1")
            )

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertIn("at least one attached evidence item is required", exc_info.exception.detail)

    def test_research_task_review_surface_renders_evidence_backed_synthesis_with_uncertainty(self) -> None:
        asyncio.run(
            self._route("/api/research-tasks", "POST")(
                {
                    "actor": "Chris",
                    "title": "Retirement communities",
                    "question": "What should I compare first?",
                    "desired_scope": "Hold the scope first.",
                }
            )
        )
        asyncio.run(
            self._route("/api/research-tasks/{task_id}/evidence", "POST")(
                task_id="research-task-1",
                payload={
                    "source_label": "Facility brochure",
                    "source_locator": "/local/notes/facility-brochure.pdf",
                    "evidence_note": "Lists care levels and distance notes.",
                    "capture_status": "captured",
                    "confidence_label": "manual note",
                },
            )
        )
        asyncio.run(
            self._route("/api/research-tasks/{task_id}/synthesis", "POST")(task_id="research-task-1")
        )

        review_response = asyncio.run(
            self._route("/mission-board/research-tasks/{task_id}", "GET")(
                task_id="research-task-1",
                return_to="/mission-board/research-tasks",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Evidence-Backed Synthesis", review_html)
        self.assertIn("What Appears Supported", review_html)
        self.assertIn("Uncertain / Missing", review_html)
        self.assertIn("attached-evidence-only synthesis", review_html)
        self.assertIn("Generate Evidence-Backed Synthesis", review_html)

    def test_research_task_review_surface_rejects_unknown_task(self) -> None:
        with self.assertRaises(service_module.HTTPException) as exc_info:
            asyncio.run(
                self._route("/mission-board/research-tasks/{task_id}", "GET")(
                    task_id="missing-task",
                    return_to="/mission-board/research-tasks",
                )
            )

        self.assertEqual(exc_info.exception.status_code, 404)
        self.assertIn("Unknown research task", exc_info.exception.detail)

    def test_autonomy_state_route_captures_visibility_only_record(self) -> None:
        response = asyncio.run(
            self._route("/api/autonomy-states", "POST")(
                {
                    "actor": "Chris",
                    "title": "Retirement workshop watch",
                    "objective": "Keep the retirement workshop lane visible for later supervised follow-through.",
                    "current_focus": "Waiting for explicit next evidence.",
                    "next_step": "Recheck the workshop brief before any follow-through.",
                    "requested_scope": "Hold the workshop lane visible and proposed only.",
                    "initiation_reason": "Chris wants the lane preserved without starting autonomous work.",
                }
            )
        )
        payload = self._json_body(response)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload["autonomy_state"]["object_kind"], "autonomy_state")
        self.assertEqual(payload["autonomy_state"]["status"], "queued")
        self.assertEqual(payload["autonomy_effect"], "visibility_only")
        self.assertFalse(bool(payload["autonomy_state"]["autonomous_execution_recorded"]))
        self.assertEqual(payload["autonomy_state"]["approval_state"], "required")
        self.assertEqual(payload["autonomy_state"]["allowed_action_boundary"], "record_visibility_only")
        self.assertIn("initiation-boundary record only", payload["message"].lower())

    def test_autonomy_state_queue_surface_renders_truthful_visibility_rows(self) -> None:
        asyncio.run(
            self._route("/api/autonomy-states", "POST")(
                {
                    "actor": "Chris",
                    "title": "Pool robot follow-up watch",
                    "objective": "Hold the pool robot follow-up as visible autonomy state only.",
                    "current_focus": "Visibility only until explicit follow-through is requested.",
                    "next_step": "Keep the next question visible.",
                    "requested_scope": "Track the follow-up as proposed visibility only.",
                    "initiation_reason": "Chris wants the follow-up held for later review.",
                }
            )
        )

        queue_response = asyncio.run(self._route("/mission-board/autonomy-states", "GET")())
        queue_html = self._text_body(queue_response)

        self.assertEqual(queue_response.status_code, 200)
        self.assertIn("Autonomy State Queue", queue_html)
        self.assertIn("Recorded Autonomy State and Boundary Queue", queue_html)
        self.assertIn("Pool robot follow-up watch", queue_html)
        self.assertIn("stored autonomy records and boundaries", queue_html)
        self.assertIn("Track the follow-up as proposed visibility only.", queue_html)
        self.assertIn("Chris wants the follow-up held for later review.", queue_html)
        self.assertIn("Inspect Autonomy State Record", queue_html)
        self.assertIn("record_visibility_only", queue_html)
        self.assertIn("does not by itself prove autonomous execution", queue_html)
        self.assertIn("/api/autonomy-states", queue_html)
        self.assertIn("/mission-board/autonomy-states/autonomy-1?return_to=%2Fmission-board%2Fautonomy-states", queue_html)

    def test_autonomy_state_review_surface_renders_real_state_and_boundary(self) -> None:
        asyncio.run(
            self._route("/api/autonomy-states", "POST")(
                {
                    "actor": "Chris",
                    "title": "Retirement workshop watch",
                    "objective": "Keep the retirement workshop lane visible for later supervised follow-through.",
                    "status": "blocked",
                    "current_focus": "Waiting on a human decision.",
                    "next_step": "Review the current objective with Chris.",
                    "requested_scope": "Keep the lane visible, but do not execute work from it yet.",
                    "initiation_reason": "Chris wants a bounded proposed autonomy lane only.",
                    "approval_state": "required",
                    "allowed_action_boundary": "record_visibility_only",
                    "blocked_reason": "Awaiting explicit approval before any follow-through exists.",
                }
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/autonomy-states/{autonomy_id}", "GET")(
                autonomy_id="autonomy-1",
                return_to="/mission-board/autonomy-states",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Autonomy State Review", review_html)
        self.assertIn("Retirement workshop watch", review_html)
        self.assertIn("Return to Autonomy State Queue", review_html)
        self.assertIn("Waiting on a human decision.", review_html)
        self.assertIn("Review the current objective with Chris.", review_html)
        self.assertIn("Keep the lane visible, but do not execute work from it yet.", review_html)
        self.assertIn("Chris wants a bounded proposed autonomy lane only.", review_html)
        self.assertIn("Awaiting explicit approval before any follow-through exists.", review_html)
        self.assertIn("recorded autonomy state and boundary only", review_html.lower())
        self.assertIn("inspectable autonomy record with stored boundaries", review_html.lower())
        self.assertIn("/api/autonomy-states/autonomy-1", review_html)

    def test_autonomy_plan_route_records_proposed_not_run_actions(self) -> None:
        asyncio.run(
            self._route("/api/autonomy-states", "POST")(
                {
                    "actor": "Chris",
                    "title": "Retirement workshop watch",
                    "objective": "Keep a bounded autonomy record for later supervised planning.",
                    "requested_scope": "Hold the lane visibly until approval is explicit.",
                    "initiation_reason": "Chris wants inspectable autonomy planning without execution.",
                }
            )
        )

        response = asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/plan", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "planning_note": "These are next possible moves only if Chris wants them reviewed.",
                    "proposed_actions": [
                        {
                            "title": "Draft three follow-up questions for the workshop decision.",
                            "rationale": "Clarify what approval would need before any real follow-through exists.",
                            "approval_needed": True,
                        }
                    ],
                },
            )
        )
        payload = self._json_body(response)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload["autonomy_state"]["planned_action_count"], 1)
        self.assertTrue(bool(payload["autonomy_state"]["has_proposed_plan"]))
        self.assertEqual(payload["autonomy_state"]["proposed_actions"][0]["execution_status"], "proposed_not_run")
        self.assertEqual(payload["autonomy_state"]["proposed_actions"][0]["approval_state"], "required")
        self.assertIn("proposed only", payload["message"].lower())

    def test_autonomy_state_review_surface_renders_proposed_action_plan_truthfully(self) -> None:
        asyncio.run(
            self._route("/api/autonomy-states", "POST")(
                {
                    "actor": "Chris",
                    "title": "Pool robot follow-up watch",
                    "objective": "Keep a bounded autonomy record for later supervised planning.",
                    "requested_scope": "Visibility only until approval becomes explicit.",
                    "initiation_reason": "Chris wants inspectable autonomy planning without execution.",
                }
            )
        )
        asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/plan", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "planning_note": "These actions stay proposed until a later slice records real execution.",
                    "proposed_actions": [
                        {
                            "title": "Collect the open questions for the pool robot follow-up.",
                            "rationale": "Keep the next review step explicit without implying that it already ran.",
                            "approval_needed": True,
                        },
                        {
                            "title": "Queue a human review checkpoint.",
                            "rationale": "Make the approval dependency visible before any action is allowed.",
                            "approval_needed": False,
                        },
                    ],
                },
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/autonomy-states/{autonomy_id}", "GET")(
                autonomy_id="autonomy-1",
                return_to="/mission-board/autonomy-states",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Proposed Action Plan", review_html)
        self.assertIn("These actions stay proposed until a later slice records real execution.", review_html)
        self.assertIn("Collect the open questions for the pool robot follow-up.", review_html)
        self.assertIn("Execution status: proposed_not_run", review_html)
        self.assertIn("Approval needed: yes", review_html)
        self.assertIn("Approval needed: no", review_html)
        self.assertIn("Approval state: not_required", review_html)
        self.assertIn("does not mean the actions ran", review_html)

    def test_autonomy_control_route_records_pause_resume_abort_truthfully(self) -> None:
        asyncio.run(
            self._route("/api/autonomy-states", "POST")(
                {
                    "actor": "Chris",
                    "title": "Retirement workshop watch",
                    "objective": "Keep a bounded autonomy record for later supervised review.",
                    "requested_scope": "Hold the lane visibly until approval is explicit.",
                    "initiation_reason": "Chris wants inspectable autonomy state without execution.",
                }
            )
        )

        pause_response = asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/control", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "actor": "Chris",
                    "action": "pause",
                    "control_reason": "Hold the record while Chris reviews the current scope.",
                },
            )
        )
        resume_response = asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/control", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "actor": "Chris",
                    "action": "resume",
                    "control_reason": "Return it to recorded active posture for later review.",
                },
            )
        )
        abort_response = asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/control", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "actor": "Chris",
                    "action": "abort",
                    "control_reason": "Chris no longer wants this recorded autonomy lane kept open.",
                },
            )
        )

        pause_payload = self._json_body(pause_response)
        resume_payload = self._json_body(resume_response)
        abort_payload = self._json_body(abort_response)

        self.assertEqual(pause_response.status_code, 201)
        self.assertEqual(pause_payload["autonomy_state"]["current_control_posture"], "paused")
        self.assertEqual(resume_payload["autonomy_state"]["current_control_posture"], "recorded_active")
        self.assertEqual(abort_payload["autonomy_state"]["current_control_posture"], "aborted")
        self.assertEqual(abort_payload["autonomy_state"]["last_control_action"], "abort")
        self.assertEqual(len(abort_payload["autonomy_state"]["control_history"]), 3)
        self.assertIn("recorded autonomy state posture only", abort_payload["message"].lower())

    def test_autonomy_state_review_surface_renders_control_history_truthfully(self) -> None:
        asyncio.run(
            self._route("/api/autonomy-states", "POST")(
                {
                    "actor": "Chris",
                    "title": "Pool robot follow-up watch",
                    "objective": "Keep a bounded autonomy record for later supervised review.",
                    "requested_scope": "Hold the lane visibly until approval is explicit.",
                    "initiation_reason": "Chris wants inspectable autonomy state without execution.",
                }
            )
        )
        asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/control", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "actor": "Chris",
                    "action": "pause",
                    "control_reason": "Pause the recorded lane while the scope is being reviewed.",
                },
            )
        )
        asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/control", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "actor": "Chris",
                    "action": "resume",
                    "control_reason": "Resume recorded active posture for later review.",
                },
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/autonomy-states/{autonomy_id}", "GET")(
                autonomy_id="autonomy-1",
                return_to="/mission-board/autonomy-states",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Recorded Control State", review_html)
        self.assertIn("Current posture: recorded_active", review_html)
        self.assertIn("Pause, resume, and abort here apply to recorded autonomy state only.", review_html)
        self.assertIn("Control Transition 1", review_html)
        self.assertIn("Resulting posture: recorded_active", review_html)
        self.assertIn("Resulting posture: paused", review_html)
        self.assertIn("not proof that real autonomous execution was running", review_html)

    def test_autonomy_readiness_route_records_approval_gated_posture(self) -> None:
        asyncio.run(
            self._route("/api/autonomy-states", "POST")(
                {
                    "actor": "Chris",
                    "title": "Retirement workshop readiness",
                    "objective": "Keep a bounded autonomy record for later supervised follow-through.",
                    "requested_scope": "Hold the lane visibly until approval is explicit.",
                    "initiation_reason": "Chris wants inspectable readiness without execution.",
                }
            )
        )

        pending_response = asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/readiness", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "actor": "Chris",
                    "readiness_state": "ready_pending_approval",
                    "readiness_reason": "The scope is defined, but approval still has to be satisfied.",
                },
            )
        )
        pending_payload = self._json_body(pending_response)

        self.assertEqual(pending_response.status_code, 201)
        self.assertEqual(pending_payload["autonomy_state"]["readiness_state"], "ready_pending_approval")
        self.assertEqual(pending_payload["autonomy_state"]["approval_gate_status"], "approval_pending")
        self.assertIn("approval-gated readiness posture only", pending_payload["message"].lower())

        # simulate later explicit approval without introducing execution
        self.runtime._autonomy_states[0]["approval_state"] = "approved"

        ready_response = asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/readiness", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "actor": "Chris",
                    "readiness_state": "ready_within_boundary",
                    "readiness_reason": "Approval is now satisfied and the record is ready within the stored boundary.",
                },
            )
        )
        ready_payload = self._json_body(ready_response)

        self.assertEqual(ready_response.status_code, 201)
        self.assertEqual(ready_payload["autonomy_state"]["readiness_state"], "ready_within_boundary")
        self.assertEqual(ready_payload["autonomy_state"]["approval_gate_status"], "within_boundary")
        self.assertFalse(bool(ready_payload["autonomy_state"]["autonomous_execution_recorded"]))

    def test_autonomy_readiness_route_rejects_ready_within_boundary_without_approval(self) -> None:
        asyncio.run(
            self._route("/api/autonomy-states", "POST")(
                {
                    "actor": "Chris",
                    "title": "Not approved lane",
                    "objective": "Keep a bounded autonomy record for later supervised follow-through.",
                    "requested_scope": "Hold the lane visibly until approval is explicit.",
                    "initiation_reason": "Chris wants inspectable readiness without execution.",
                }
            )
        )

        with self.assertRaises(service_module.HTTPException) as exc_info:
            asyncio.run(
                self._route("/api/autonomy-states/{autonomy_id}/readiness", "POST")(
                    autonomy_id="autonomy-1",
                    payload={
                        "actor": "Chris",
                        "readiness_state": "ready_within_boundary",
                        "readiness_reason": "Try to mark it fully ready too early.",
                    },
                )
            )

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertIn("ready_within_boundary requires approval to be satisfied", exc_info.exception.detail)

    def test_autonomy_state_review_surface_renders_readiness_gate_truthfully(self) -> None:
        asyncio.run(
            self._route("/api/autonomy-states", "POST")(
                {
                    "actor": "Chris",
                    "title": "Pool robot readiness",
                    "objective": "Keep a bounded autonomy record for later supervised follow-through.",
                    "requested_scope": "Hold the lane visibly until approval is explicit.",
                    "initiation_reason": "Chris wants inspectable readiness without execution.",
                }
            )
        )
        asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/readiness", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "actor": "Chris",
                    "readiness_state": "ready_pending_approval",
                    "readiness_reason": "The scope is clear, but approval is still pending.",
                },
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/autonomy-states/{autonomy_id}", "GET")(
                autonomy_id="autonomy-1",
                return_to="/mission-board/autonomy-states",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Readiness Gate", review_html)
        self.assertIn("Latest Readiness", review_html)
        self.assertIn("ready_pending_approval", review_html)
        self.assertIn("Approval gate: approval_pending", review_html)
        self.assertIn("Readiness here is a stored gate only.", review_html)
        self.assertIn("This is a stored readiness gate only", review_html)

    def test_autonomy_follow_through_route_records_one_local_proof_effect(self) -> None:
        asyncio.run(
            self._route("/api/autonomy-states", "POST")(
                {
                    "actor": "Chris",
                    "title": "Retirement workshop local proof",
                    "objective": "Keep a bounded autonomy record for later supervised follow-through.",
                    "requested_scope": "Hold the lane visibly until approval is explicit.",
                    "initiation_reason": "Chris wants one local proof-of-follow-through only.",
                    "approval_state": "approved",
                }
            )
        )
        asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/readiness", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "actor": "Chris",
                    "readiness_state": "ready_within_boundary",
                    "readiness_reason": "Approval is satisfied and the record is ready within the stored boundary.",
                },
            )
        )

        response = asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/follow-through", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "actor": "Chris",
                    "trigger_note": "Write the smallest inspectable proof packet only.",
                },
            )
        )
        payload = self._json_body(response)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload["autonomy_state"]["local_follow_through_status"], "local_proof_created")
        self.assertEqual(payload["autonomy_state"]["last_follow_through_effect"], "local_status_packet_written")
        self.assertIn("/tmp/autonomy-1-local-follow-through.md", payload["autonomy_state"]["last_follow_through_artifact_path"])
        self.assertIn("one bounded local proof action only", payload["message"].lower())
        self.assertFalse(bool(payload["autonomy_state"]["autonomous_execution_recorded"]))

    def test_autonomy_follow_through_route_rejects_not_ready_record(self) -> None:
        asyncio.run(
            self._route("/api/autonomy-states", "POST")(
                {
                    "actor": "Chris",
                    "title": "Too early follow-through",
                    "objective": "Keep a bounded autonomy record for later supervised follow-through.",
                    "requested_scope": "Hold the lane visibly until approval is explicit.",
                    "initiation_reason": "Chris wants inspectable state only.",
                }
            )
        )

        with self.assertRaises(service_module.HTTPException) as exc_info:
            asyncio.run(
                self._route("/api/autonomy-states/{autonomy_id}/follow-through", "POST")(
                    autonomy_id="autonomy-1",
                    payload={
                        "actor": "Chris",
                        "trigger_note": "Try to run it too early.",
                    },
                )
            )

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertIn("requires readiness_state=ready_within_boundary", exc_info.exception.detail)

    def test_autonomy_state_review_surface_renders_local_follow_through_proof_truthfully(self) -> None:
        asyncio.run(
            self._route("/api/autonomy-states", "POST")(
                {
                    "actor": "Chris",
                    "title": "Pool robot local proof",
                    "objective": "Keep a bounded autonomy record for later supervised follow-through.",
                    "requested_scope": "Hold the lane visibly until approval is explicit.",
                    "initiation_reason": "Chris wants one local proof-of-follow-through only.",
                    "approval_state": "approved",
                }
            )
        )
        asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/readiness", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "actor": "Chris",
                    "readiness_state": "ready_within_boundary",
                    "readiness_reason": "Approval is satisfied and the record is ready within the stored boundary.",
                },
            )
        )
        asyncio.run(
            self._route("/api/autonomy-states/{autonomy_id}/follow-through", "POST")(
                autonomy_id="autonomy-1",
                payload={
                    "actor": "Chris",
                    "trigger_note": "Write the smallest inspectable proof packet only.",
                },
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/autonomy-states/{autonomy_id}", "GET")(
                autonomy_id="autonomy-1",
                return_to="/mission-board/autonomy-states",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("Local Follow-Through Proof", review_html)
        self.assertIn("local_proof_created", review_html)
        self.assertIn("local_status_packet_written", review_html)
        self.assertIn("/tmp/autonomy-1-local-follow-through.md", review_html)
        self.assertIn("This trigger only proves one bounded local effect", review_html)
        self.assertIn("local proof-of-follow-through only", review_html)

    def test_autonomy_state_review_surface_rejects_unknown_state(self) -> None:
        with self.assertRaises(service_module.HTTPException) as exc_info:
            asyncio.run(
                self._route("/mission-board/autonomy-states/{autonomy_id}", "GET")(
                    autonomy_id="missing-state",
                    return_to="/mission-board/autonomy-states",
                )
            )

        self.assertEqual(exc_info.exception.status_code, 404)
        self.assertIn("Unknown autonomy state", exc_info.exception.detail)

    def test_delegation_report_review_surface_links_to_outcome_review_surface(self) -> None:
        asyncio.run(
            self._route("/api/missions/{mission_id}/delegations/{delegation_id}/report", "POST")(
                mission_id="mission-1",
                delegation_id="delegation-1",
                payload={
                    "producing_agent": "storm",
                    "title": "Weather review delivered",
                    "summary": "Storm returned a concrete travel weather readout.",
                    "detail": "Readable output is available.",
                },
            )
        )

        review_response = asyncio.run(
            self._route("/mission-board/delegation-report/{mission_id}/{report_id}", "GET")(
                mission_id="mission-1",
                report_id="report-1",
                return_to="/mission-board?mission_id=mission-1#delegation-review-completed",
            )
        )
        review_html = self._text_body(review_response)

        self.assertEqual(review_response.status_code, 200)
        self.assertIn("inspectable delegation output and recorded provenance only", review_html.lower())
        self.assertIn("/mission-board/artifact-outcome/delegation_report/report-1?mission_id=mission-1", review_html)

    def test_mission_board_module_surfaces_requested_and_completed_delegation_report_states(self) -> None:
        before_response = asyncio.run(self._route("/api/mission-board/module", "GET")())
        before_payload = self._json_body(before_response)
        mission_id = next(iter(before_payload["mission_details"]))
        before_detail = before_payload["mission_details"][mission_id]
        before_work_state = before_detail["work_state"]

        self.assertEqual(before_work_state["summary"]["delegations_requested"], 1)
        self.assertEqual(before_work_state["summary"]["delegations_completed_with_output"], 0)
        self.assertEqual(before_work_state["delegations"][0]["inspectable_output_status"], "requested")
        self.assertEqual(before_detail["delegation_reports"], [])

        asyncio.run(
            self._route("/api/missions/{mission_id}/delegations/{delegation_id}/report", "POST")(
                mission_id=mission_id,
                delegation_id="delegation-1",
                payload={
                    "producing_agent": "storm",
                    "title": "Weather review delivered",
                    "summary": "Storm returned a concrete travel weather readout.",
                    "detail": "This report proves delegated work through a visible artifact path.",
                    "key_output": "Weather risk is contained for the current route.",
                },
            )
        )

        after_response = asyncio.run(self._route("/api/mission-board/module", "GET")())
        after_payload = self._json_body(after_response)
        after_detail = after_payload["mission_details"][mission_id]
        after_work_state = after_detail["work_state"]

        self.assertEqual(after_work_state["summary"]["delegations_requested"], 0)
        self.assertEqual(after_work_state["summary"]["delegations_completed_with_output"], 1)
        self.assertEqual(after_work_state["delegations"][0]["inspectable_output_status"], "completed-with-output")
        self.assertEqual(after_detail["delegation_reports"][0]["producer_agent"], "storm")
        self.assertEqual(after_detail["delegation_reports"][0]["key_output"], "Weather risk is contained for the current route.")
        self.assertEqual(after_detail["delegation_reports"][0]["artifact_ref"], f"/api/missions/{mission_id}/delegation-reports/report-1")
        self.assertEqual(after_detail["outputs_detail"][0]["kind"], "delegation-report")

    def test_mission_board_route_query_preserves_selected_mission_for_delegation_continuity(self) -> None:
        mission_board_response = asyncio.run(
            self._route("/mission-board", "GET")()
        )
        mission_board_html = self._text_body(mission_board_response)

        self.assertIn('new URLSearchParams(window.location.search)', mission_board_html)
        self.assertIn('searchParams.set("mission_id", selectedMissionId)', mission_board_html)

    def test_chronicle_center_links_to_status_api_instead_of_post_only_devotional_api(self) -> None:
        chronicle_response = asyncio.run(self._route("/chronicle-center", "GET")())
        chronicle_html = self._text_body(chronicle_response)

        self.assertIn("/api/chronicle/status", chronicle_html)
        self.assertNotIn('href="/api/devotional-pause"', chronicle_html)

    def test_home_action_events_persist_into_shared_activity_surfaces(self) -> None:
        record_response = asyncio.run(
            self._route("/api/activity/home-action", "POST")(
                {
                    "actor": "Chris",
                    "domain": "command-center",
                    "action": "Move Mission to Now",
                    "status": "ok",
                    "detail": "Action succeeded: /api/missions/weather-family/status",
                    "why_now": "Command center home action advanced the visible mission lane.",
                    "result_summary": "Home action result: ok",
                    "route": "/mission-board",
                    "route_label": "Open Mission Board",
                    "succeeded": True,
                }
            )
        )
        activity_response = asyncio.run(self._route("/api/activity", "GET")())
        activity_module_response = asyncio.run(self._route("/api/activity/module", "GET")())

        record_payload = self._json_body(record_response)
        activity_payload = self._json_body(activity_response)
        activity_module_payload = self._json_body(activity_module_response)

        self.assertEqual(record_payload["status"], "recorded")
        self.assertEqual(record_payload["entry_type"], "home-action")
        self.assertTrue(any(item.get("entry_type") == "home-action" for item in activity_payload))
        self.assertTrue(any(item.get("related_route") == "/mission-board" for item in activity_payload))
        self.assertTrue(any(item.get("entry_type") == "home-action" for item in activity_module_payload["activity_feed"]))

    def test_operator_action_events_persist_into_shared_activity_surfaces(self) -> None:
        record_response = asyncio.run(
            self._route("/api/activity/operator-action", "POST")(
                {
                    "actor": "Chris",
                    "domain": "command-center",
                    "action": "Approve Request",
                    "title": "Approve local rollout",
                    "status": "ok",
                    "detail": "Action succeeded: /api/approvals/req-1/approve",
                    "why_now": "Command center operator action resolved a surfaced approval decision.",
                    "result_summary": "Operator action result: ok",
                    "route": "/approval-queue",
                    "route_label": "Open Approval Queue",
                    "related_kind": "approval",
                    "related_label": "Approve local rollout",
                    "succeeded": True,
                }
            )
        )
        activity_response = asyncio.run(self._route("/api/activity", "GET")())
        activity_module_response = asyncio.run(self._route("/api/activity/module", "GET")())

        record_payload = self._json_body(record_response)
        activity_payload = self._json_body(activity_response)
        activity_module_payload = self._json_body(activity_module_response)
        action_journal = activity_module_payload["action_journal"]

        self.assertEqual(record_payload["status"], "recorded")
        self.assertEqual(record_payload["entry_type"], "operator-action")
        self.assertTrue(any(item.get("entry_type") == "operator-action" for item in activity_payload))
        self.assertTrue(any(item.get("related_route") == "/approval-queue" for item in activity_payload))
        self.assertTrue(any(item.get("entry_type") == "operator-action" for item in activity_module_payload["activity_feed"]))
        self.assertGreaterEqual(int(action_journal.get("operator_count", 0) or 0), 1)
        self.assertTrue(any(item.get("kind") == "operator-action" for item in action_journal.get("entries", [])))

    def test_activity_focus_mutation_updates_progress_and_activity_feed(self) -> None:
        asyncio.run(
            self._route("/api/activity/operator-action", "POST")(
                {
                    "actor": "Chris",
                    "domain": "recovery",
                    "action": "Stabilize Recovery Loop",
                    "title": "Dropbox sync failure",
                    "status": "ok",
                    "detail": "Recovery execution needs a shared follow-through focus.",
                    "why_now": "Activity Feed focus promotion should be able to advance shared progress state from a live recovery event.",
                    "result_summary": "Recovery action result: ok",
                    "route": "/recovery-center",
                    "route_label": "Open Recovery Center",
                    "related_kind": "recovery-case",
                    "related_label": "Dropbox sync failure",
                    "succeeded": True,
                }
            )
        )

        focus_response = asyncio.run(
            self._route("/api/activity/module/focus", "POST")(
                {
                    "actor": "Chris",
                    "title": "Dropbox sync failure",
                    "detail": "Recovery execution needs a shared follow-through focus.",
                    "related_route": "/recovery-center",
                    "related_kind": "recovery-case",
                }
            )
        )

        focus_payload = self._json_body(focus_response)
        activity_module_payload = self._json_body(asyncio.run(self._route("/api/activity/module", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

        self.assertEqual(focus_payload["status"], "recorded")
        self.assertEqual(focus_payload["focus"]["module"], "Recovery")
        self.assertEqual(activity_module_payload["progress_next_focus"], "Recovery")
        self.assertEqual(activity_module_payload["focus_control"]["latest"]["module"], "Recovery")
        self.assertTrue(any(item.get("title") == "Promote Activity Focus" for item in activity_module_payload["activity_feed"]))
        self.assertEqual(progress_snapshot["progress_next_focus"], "Recovery")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Recovery")

    def test_activity_review_mutation_persists_review_lane_and_linked_module_continuity(self) -> None:
        asyncio.run(
            self._route("/api/activity/operator-action", "POST")(
                {
                    "actor": "Chris",
                    "domain": "recovery",
                    "action": "Investigate Relay Failure",
                    "title": "Dropbox sync failure",
                    "detail": "Activity review should create durable review state and linked recovery continuity.",
                    "why_now": "Activity Feed review lane should bridge into the related recovery surface.",
                    "result_summary": "Recovery review staged",
                    "route": "/recovery-center",
                    "route_label": "Open Recovery Center",
                    "related_kind": "recovery-case",
                    "related_label": "Dropbox sync failure",
                    "succeeded": True,
                }
            )
        )

        activity_module_before = self._json_body(asyncio.run(self._route("/api/activity/module", "GET")()))
        selected = next(
            item for item in activity_module_before["activity_feed"]
            if item.get("title") == "Investigate Relay Failure"
        )

        review_response = asyncio.run(
            self._route("/api/activity/module/review", "POST")(
                {
                    "actor": "Chris",
                    "event_id": selected["event_id"],
                    "title": selected["title"],
                    "detail": "Keep this recovery case hot until the bridge is stable.",
                    "status": "reviewing",
                    "related_route": selected["related_route"],
                    "related_kind": selected["related_kind"],
                    "route_label": selected["route_label"],
                }
            )
        )

        review_payload = self._json_body(review_response)
        activity_module_after = self._json_body(asyncio.run(self._route("/api/activity/module", "GET")()))
        self.assertEqual(review_payload["status"], "recorded")
        self.assertEqual(review_payload["review"]["status"], "reviewing")
        self.assertEqual(review_payload["focus"]["module"], "Recovery")
        self.assertTrue(any(item.get("event_id") == selected["event_id"] for item in activity_module_after["review_lane"]))
        refreshed = next(item for item in activity_module_after["activity_feed"] if item.get("event_id") == selected["event_id"])
        self.assertEqual(refreshed["review_status"], "reviewing")

    def test_recovery_case_mutations_persist_into_shared_activity(self) -> None:
        recovery_module_response = asyncio.run(self._route("/api/recovery/module", "GET")())
        recovery_payload = self._json_body(recovery_module_response)
        self.assertGreaterEqual(len(recovery_payload["recovery_cases"]), 1)
        case_id = recovery_payload["recovery_cases"][0]["case_id"]

        update_response = asyncio.run(
            self._route("/api/recovery/cases/{case_id}", "POST")(
                case_id,
                {
                    "actor": "Chris",
                    "status": "investigating",
                    "note": "Working the integration failure from Recovery Center.",
                },
            )
        )
        updated_payload = self._json_body(update_response)
        self.assertEqual(updated_payload["status"], "recorded")
        self.assertEqual(updated_payload["case"]["status"], "investigating")

        activity_response = asyncio.run(self._route("/api/activity", "GET")())
        activity_payload = self._json_body(activity_response)
        self.assertTrue(any(item.get("entry_type") == "operator-action" for item in activity_payload))
        self.assertTrue(any(item.get("related_kind") == "recovery-case" for item in activity_payload))

    def test_recovery_case_execution_persists_into_recovery_and_activity(self) -> None:
        recovery_module_response = asyncio.run(self._route("/api/recovery/module", "GET")())
        recovery_payload = self._json_body(recovery_module_response)
        self.assertGreaterEqual(len(recovery_payload["recovery_cases"]), 1)
        case_id = recovery_payload["recovery_cases"][0]["case_id"]

        execute_response = asyncio.run(
            self._route("/api/recovery/cases/{case_id}/execute", "POST")(
                case_id,
                {
                    "actor": "Chris",
                    "action_type": "retry",
                    "note": "Executing retry loop from Recovery Center.",
                },
            )
        )
        execute_payload = self._json_body(execute_response)
        self.assertEqual(execute_payload["status"], "recorded")
        self.assertEqual(execute_payload["case"]["status"], "investigating")
        self.assertEqual(execute_payload["case"]["execution_count"], 1)
        self.assertEqual(execute_payload["action"]["target_kind"], "recovery-case")
        self.assertEqual(execute_payload["action"]["status"], "executed")
        self.assertEqual(execute_payload["focus"]["module"], "Recovery")

        refreshed_recovery = self._json_body(asyncio.run(self._route("/api/recovery/module", "GET")()))
        activity_payload = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

        self.assertTrue(any(item.get("case_id") == case_id and int(item.get("execution_count", 0) or 0) >= 1 for item in refreshed_recovery["recovery_cases"]))
        self.assertTrue(any(item.get("target_id") == case_id for item in refreshed_recovery["recovery_actions"]["recent"]))
        self.assertTrue(any(item.get("related_kind") == "recovery-case" for item in activity_payload))
        self.assertEqual(progress_snapshot["progress_next_focus"], "Recovery")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Recovery")

    def test_recovery_case_remediation_persists_into_recovery_activity_and_progress(self) -> None:
        recovery_module_response = asyncio.run(self._route("/api/recovery/module", "GET")())
        recovery_payload = self._json_body(recovery_module_response)
        self.assertGreaterEqual(len(recovery_payload["recovery_cases"]), 1)
        case_id = recovery_payload["recovery_cases"][0]["case_id"]

        stage_response = asyncio.run(
            self._route("/api/recovery/cases/{case_id}/remediation", "POST")(
                case_id,
                {
                    "actor": "Chris",
                    "action_type": "stage",
                    "note": "Stage auto-remediation from Recovery Center.",
                },
            )
        )
        stage_payload = self._json_body(stage_response)
        self.assertEqual(stage_payload["status"], "recorded")
        self.assertEqual(stage_payload["case"]["remediation_status"], "staged")
        self.assertEqual(stage_payload["action"]["action_type"], "remediation-stage")
        self.assertEqual(stage_payload["action"]["status"], "staged")
        self.assertEqual(stage_payload["focus"]["module"], "Recovery")

        execute_response = asyncio.run(
            self._route("/api/recovery/cases/{case_id}/remediation", "POST")(
                case_id,
                {
                    "actor": "Chris",
                    "action_type": "execute",
                    "note": "Execute auto-remediation from Recovery Center.",
                },
            )
        )
        execute_payload = self._json_body(execute_response)
        self.assertEqual(execute_payload["status"], "recorded")
        self.assertEqual(execute_payload["case"]["remediation_status"], "executed")
        self.assertEqual(execute_payload["case"]["remediation_count"], 2)
        self.assertEqual(execute_payload["case"]["status"], "watch")
        self.assertEqual(execute_payload["action"]["action_type"], "remediation-execute")
        self.assertEqual(execute_payload["action"]["status"], "executed")
        self.assertEqual(execute_payload["focus"]["module"], "Recovery")

        refreshed_recovery = self._json_body(asyncio.run(self._route("/api/recovery/module", "GET")()))
        activity_payload = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

        target_case = next(item for item in refreshed_recovery["recovery_cases"] if item.get("case_id") == case_id)
        self.assertEqual(target_case["remediation_status"], "executed")
        self.assertGreaterEqual(int(target_case.get("remediation_count", 0) or 0), 2)
        self.assertTrue(any(item.get("target_id") == case_id and str(item.get("action_type")) == "remediation-execute" for item in refreshed_recovery["recovery_actions"]["recent"]))
        self.assertTrue(
            any(
                item.get("related_kind") == "recovery-case"
                and "auto-remediation" in str(item.get("detail") or item.get("title") or "").lower()
                for item in activity_payload
            )
        )
        self.assertEqual(progress_snapshot["progress_next_focus"], "Recovery")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Recovery")

    def test_recovery_case_plan_persists_into_recovery_activity_and_progress(self) -> None:
        recovery_module_response = asyncio.run(self._route("/api/recovery/module", "GET")())
        recovery_payload = self._json_body(recovery_module_response)
        self.assertGreaterEqual(len(recovery_payload["recovery_cases"]), 1)
        case_id = recovery_payload["recovery_cases"][0]["case_id"]

        plan_response = asyncio.run(
            self._route("/api/recovery/cases/{case_id}/plan", "POST")(
                case_id,
                {
                    "actor": "Chris",
                    "steps": [
                        {"label": "Confirm signal", "detail": "Reproduce the failure in the live route."},
                        {"label": "Heal dependency", "detail": "Repair the connector before the next refresh."},
                    ],
                    "note": "Prepared a route-healing plan from Recovery Center.",
                },
            )
        )
        step_response = asyncio.run(
            self._route("/api/recovery/cases/{case_id}/plan/execute-next", "POST")(
                case_id,
                {
                    "actor": "Chris",
                    "note": "Executed the next healing step from Recovery Center.",
                },
            )
        )

        plan_payload = self._json_body(plan_response)
        step_payload = self._json_body(step_response)
        self.assertEqual(plan_payload["status"], "recorded")
        self.assertEqual(plan_payload["case"]["remediation_plan_count"], 2)
        self.assertEqual(plan_payload["action"]["action_type"], "remediation-plan")
        self.assertEqual(step_payload["status"], "recorded")
        self.assertEqual(step_payload["step"]["status"], "completed")
        self.assertEqual(step_payload["action"]["action_type"], "remediation-plan-step")

        refreshed_recovery = self._json_body(asyncio.run(self._route("/api/recovery/module", "GET")()))
        activity_payload = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

        target_case = next(item for item in refreshed_recovery["recovery_cases"] if item.get("case_id") == case_id)
        self.assertEqual(target_case["remediation_plan_count"], 2)
        self.assertEqual(target_case["remediation_plan_completed_count"], 1)
        self.assertEqual(target_case["remediation_plan_status"], "in_progress")
        self.assertTrue(any(item.get("target_id") == case_id and str(item.get("action_type")) == "remediation-plan-step" for item in refreshed_recovery["recovery_actions"]["recent"]))
        self.assertTrue(any(item.get("related_kind") == "recovery-case" and "healing step" in str(item.get("detail") or "").lower() for item in activity_payload))
        self.assertEqual(progress_snapshot["progress_next_focus"], "Recovery")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Recovery")

    def test_module_activity_continuity_populates_publish_huddle_and_navigation_payloads(self) -> None:
        asyncio.run(
            self._route("/api/activity/operator-action", "POST")(
                {
                    "actor": "Chris",
                    "domain": "publish",
                    "action": "Create Draft Project",
                    "detail": "Created publish draft from module route.",
                    "why_now": "Publish continuity smoke test.",
                    "result_summary": "Draft created",
                    "route": "/publish",
                    "route_label": "Open Publish",
                    "related_kind": "publishing-project",
                    "related_label": "Test launch draft",
                    "succeeded": True,
                }
            )
        )
        asyncio.run(
            self._route("/api/activity/operator-action", "POST")(
                {
                    "actor": "Chris",
                    "domain": "huddle",
                    "action": "Start Overnight Research",
                    "detail": "Started party mode from module route.",
                    "why_now": "Huddle continuity smoke test.",
                    "result_summary": "Party mode started",
                    "route": "/huddle-center",
                    "route_label": "Open Huddle",
                    "related_kind": "party-mode",
                    "related_label": "Overnight research",
                    "succeeded": True,
                }
            )
        )
        asyncio.run(
            self._route("/api/activity/operator-action", "POST")(
                {
                    "actor": "Chris",
                    "domain": "navigation",
                    "action": "Preview Route Intelligence",
                    "detail": "Persisted route preview from module route.",
                    "why_now": "Navigation continuity smoke test.",
                    "result_summary": "Route preview refreshed",
                    "route": "/navigation-center",
                    "route_label": "Open Navigation",
                    "related_kind": "route-preview",
                    "related_label": "Springfield",
                    "succeeded": True,
                }
            )
        )

        publish_snapshot = self._json_body(asyncio.run(self._route("/api/publish/module", "GET")()))
        huddle_snapshot = self._json_body(asyncio.run(self._route("/api/huddle/module", "GET")()))
        navigation_snapshot = self._json_body(asyncio.run(self._route("/api/navigation/module", "GET")()))

        self.assertTrue(any(item.get("title") == "Create Draft Project" for item in publish_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("title") == "Start Overnight Research" for item in huddle_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("title") == "Preview Route Intelligence" for item in navigation_snapshot["recent_activity"]))

    def test_navigation_route_history_resume_updates_module_state_activity_and_progress(self) -> None:
        from jarvis.apple_api import _record_navigation_route_history

        _, seeded_route = _record_navigation_route_history(
            origin="Home Base",
            destination="Office",
            origin_mode="home",
            parks_historic_radius_miles=25,
            source_label="Navigation test seed",
        )
        self.assertEqual(seeded_route["destination"], "Office")
        self.runtime.storm_route_weather = lambda origin, destination: {
            "origin": {"label": origin},
            "destination": {"label": destination},
            "summary": f"Preview ready for {origin} -> {destination}.",
            "hazard_active": False,
            "route": {
                "distance_miles": 12,
                "duration_minutes": 18,
                "coordinates": [[38.95, -84.47], [39.10, -84.51]],
                "steps": [],
            },
        }

        module_before = self._json_body(asyncio.run(self._route("/api/navigation/module", "GET")()))
        self.assertEqual(len(module_before["route_history"]), 1)
        route_id = module_before["route_history"][0]["route_id"]

        resume_response = self._json_body(
            asyncio.run(
                self._route("/api/navigation/module/resume", "POST")(
                    {"route_id": route_id, "actor": "Chris"}
                )
            )
        )
        self.assertEqual(resume_response["status"], "resumed")
        self.assertEqual(resume_response["route"]["destination"], "Office")
        self.assertEqual(resume_response["focus"]["module"], "Navigation")

        module_after = self._json_body(asyncio.run(self._route("/api/navigation/module", "GET")()))
        history_entry = next(item for item in module_after["route_history"] if item.get("route_id") == route_id)
        from jarvis.audit import AuditLog

        self.assertEqual(history_entry["resume_count"], 1)
        recent_activity = AuditLog(Path("data/logs")).list_recent(limit=8, entry_type="operator-action")
        self.assertTrue(any(item.get("action") == "Resume Navigation Route" for item in recent_activity))

    def test_huddle_idea_actions_update_huddle_continuity_and_progress_focus(self) -> None:
        async def _capture_payload() -> dict[str, str]:
            return {
                "actor": "Chris",
                "text": "Research a tighter morning family launch cadence",
                "domain": "family",
            }

        capture_response = asyncio.run(
            self._route("/api/huddle/ideas", "POST")(SimpleNamespace(json=_capture_payload))
        )
        capture_payload = self._json_body(capture_response)
        idea_id = capture_payload["idea"]["id"]

        queue_response = asyncio.run(
            self._route("/api/huddle/ideas/{idea_id}/queue", "POST")(idea_id=idea_id, payload={"actor": "Chris"})
        )
        queue_payload = self._json_body(queue_response)

        huddle_snapshot = self._json_body(asyncio.run(self._route("/api/huddle/module", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

        self.assertEqual(queue_payload["idea"]["status"], "queued")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Huddle")
        self.assertTrue(
            any(item.get("title") == "Capture Huddle Idea" for item in huddle_snapshot["recent_activity"])
        )
        self.assertTrue(
            any(item.get("title") == "Queue Huddle Idea" for item in huddle_snapshot["recent_activity"])
        )
        self.assertTrue(
            any(item.get("id") == idea_id and item.get("status") == "queued" for item in huddle_snapshot["idea_inbox"]["recent"])
        )

    def test_publish_review_action_updates_publish_continuity_and_progress_focus(self) -> None:
        publishing_root = Path.home() / ".jarvis" / "publishing"
        publishing_root.mkdir(parents=True, exist_ok=True)
        reviews_path = publishing_root / "ghostwritr_reviews.jsonl"
        reviews_path.write_text(
            json.dumps(
                {
                    "review_id": "rev-1",
                    "title": "Approve launch chapter",
                    "slug": "launch-chapter",
                    "track_type": "book",
                    "chapter_number": 12,
                    "stage_key": "editorial_review",
                    "stage_display": "Editorial Review",
                    "content_preview": "Final launch chapter copy is ready for sign-off.",
                    "word_count": 1840,
                    "ready_since": "2026-06-06T06:00:00Z",
                    "jarvis_status": "pending",
                    "approval_id": "",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = self._json_body(
            asyncio.run(
                self._route("/api/publishing/draft/approve", "POST")(
                    {
                        "review_id": "rev-1",
                        "actor": "Chris",
                    }
                )
            )
        )

        publish_snapshot = self._json_body(asyncio.run(self._route("/api/publish/module", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

        self.assertEqual(result["status"], "approved")
        self.assertEqual(result["focus"]["module"], "Publish")
        self.assertEqual(result["history_entry"]["status_label"], "Approved")
        self.assertEqual(publish_snapshot["pending_reviews_count"], 0)
        self.assertGreaterEqual(publish_snapshot["history_count"], 1)
        self.assertTrue(any(item.get("title") == "Approve Publish Review" for item in publish_snapshot["launch_history"]["items"]))
        self.assertTrue(any(item.get("title") == "Approve Publish Review" for item in publish_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_label") == "Approve launch chapter" for item in publish_snapshot["recent_activity"]))
        self.assertEqual(progress_snapshot["progress_next_focus"], "Publish")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Publish")

    def test_publish_checklist_action_updates_workspace_continuity_and_progress_focus(self) -> None:
        import jarvis.publishing_suite as publishing_suite_module

        publishing_suite_module._publishing_singleton = None
        publishing_suite_module.init_publishing()

        async def _create_payload() -> dict[str, str]:
            return {
                "title": "Launch Checklist Project",
                "project_type": "book",
                "platform": "KDP",
                "status": "editing",
            }

        create_result = self._json_body(
            asyncio.run(
                self._route("/api/publishing/projects", "POST")(
                    SimpleNamespace(json=_create_payload)
                )
            )
        )
        project_id = create_result["project_id"]

        result = self._json_body(
            asyncio.run(
                self._route("/api/publishing/checklist/step", "POST")(
                    {
                        "project_id": project_id,
                        "step": "manuscript_final",
                        "completed": True,
                        "actor": "Chris",
                    }
                )
            )
        )

        publish_snapshot = self._json_body(asyncio.run(self._route("/api/publish/module", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))
        workspace = dict(publish_snapshot.get("launch_workspace") or {})
        checklist = list(workspace.get("checklist") or [])
        matched = next((item for item in checklist if item.get("step") == "manuscript_final"), {})

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["focus"]["module"], "Publish")
        self.assertEqual(result["history_entry"]["status_label"], "Completed")
        self.assertEqual(result["workspace"]["project_id"], project_id)
        self.assertEqual(workspace.get("project_id"), project_id)
        self.assertTrue(bool(matched.get("completed")))
        self.assertEqual(workspace.get("checklist_progress"), "1/11")
        self.assertTrue(any(item.get("title") == "Create Draft Project" for item in publish_snapshot["launch_history"]["items"]))
        self.assertTrue(any(item.get("title") == "Complete Publish Checklist Step" for item in publish_snapshot["launch_history"]["items"]))
        self.assertTrue(any(item.get("title") == "Complete Publish Checklist Step" for item in publish_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_label") == "Launch Checklist Project" for item in publish_snapshot["recent_activity"]))
        self.assertEqual(progress_snapshot["progress_next_focus"], "Publish")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Publish")

    def test_agent_ops_activity_populates_agent_ops_continuity(self) -> None:
        asyncio.run(
            self._route("/api/activity/operator-action", "POST")(
                {
                    "actor": "Chris",
                    "domain": "agent-ops",
                    "action": "Queue Agent Run",
                    "detail": "Queued agent run from the Agent Ops route.",
                    "why_now": "Agent Ops continuity smoke test.",
                    "result_summary": "Agent run queued with item wi-123.",
                    "route": "/agent-ops-center",
                    "route_label": "Open Agent Ops",
                    "related_kind": "agent",
                    "related_label": "storm",
                    "succeeded": True,
                }
            )
        )

        agent_ops_snapshot = self._json_body(asyncio.run(self._route("/api/agent-ops/module", "GET")()))

        self.assertTrue(any(item.get("title") == "Queue Agent Run" for item in agent_ops_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_label") == "storm" for item in agent_ops_snapshot["recent_activity"]))

    def test_mission_activity_populates_mission_board_continuity(self) -> None:
        asyncio.run(
            self._route("/api/activity/operator-action", "POST")(
                {
                    "actor": "Chris",
                    "domain": "mission-board",
                    "action": "Move Mission to Now",
                    "detail": "Moved mission into the now lane from Mission Board.",
                    "why_now": "Mission Board continuity smoke test.",
                    "result_summary": "Mission moved into the now lane.",
                    "route": "/mission-board",
                    "route_label": "Open Mission Board",
                    "related_kind": "mission",
                    "related_label": "weather-family",
                    "succeeded": True,
                }
            )
        )

        mission_board_snapshot = self._json_body(asyncio.run(self._route("/api/mission-board/module", "GET")()))

        self.assertTrue(any(item.get("title") == "Move Mission to Now" for item in mission_board_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_label") == "weather-family" for item in mission_board_snapshot["recent_activity"]))

    def test_approval_activity_populates_approval_queue_continuity(self) -> None:
        asyncio.run(
            self._route("/api/activity/operator-action", "POST")(
                {
                    "actor": "Chris",
                    "domain": "approval",
                    "action": "Approve Approval Request",
                    "detail": "Approval action approve recorded from the Approval Queue.",
                    "why_now": "Approval Queue continuity smoke test.",
                    "result_summary": "Approval action status: approved",
                    "route": "/approval-queue",
                    "route_label": "Open Approval Queue",
                    "related_kind": "approval",
                    "related_label": "Promote storm agent tooling",
                    "succeeded": True,
                }
            )
        )

        approval_snapshot = self._json_body(asyncio.run(self._route("/api/approval/module", "GET")()))

        self.assertTrue(any(item.get("title") == "Approve Approval Request" for item in approval_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_label") == "Promote storm agent tooling" for item in approval_snapshot["recent_activity"]))

    def test_supervision_activity_populates_supervision_continuity(self) -> None:
        asyncio.run(
            self._route("/api/activity/operator-action", "POST")(
                {
                    "actor": "Chris",
                    "domain": "supervision",
                    "action": "Reject Supervision Item",
                    "detail": "Supervision action reject recorded from the Supervision Snapshot.",
                    "why_now": "Supervision continuity smoke test.",
                    "result_summary": "Supervision action status: rejected",
                    "route": "/supervision-snapshot",
                    "route_label": "Open Supervision Snapshot",
                    "related_kind": "supervision-item",
                    "related_label": "Watchtower deployment proposal",
                    "succeeded": True,
                }
            )
        )

        supervision_snapshot = self._json_body(asyncio.run(self._route("/api/supervision/module", "GET")()))

        self.assertTrue(any(item.get("title") == "Reject Supervision Item" for item in supervision_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_label") == "Watchtower deployment proposal" for item in supervision_snapshot["recent_activity"]))

    def test_supervision_review_action_persists_into_supervision_and_progress(self) -> None:
        submit_response = asyncio.run(
            self._route("/api/approvals/submit", "POST")(
                {
                    "agent_id": "watchtower",
                    "agent_label": "Watchtower",
                    "action_type": "deployment_review",
                    "title": "Watchtower deployment proposal",
                    "description": "Need bounded review before proceeding.",
                    "payload_data": {"environment": "production"},
                    "actor_id": "chris",
                    "priority": 4,
                    "tags": ["supervision", "deployment"],
                    "context": {"route": "/supervision-snapshot"},
                }
            )
        )
        self.assertEqual(self._json_body(submit_response)["status"], "submitted")

        supervision_snapshot = self._json_body(asyncio.run(self._route("/api/supervision/module", "GET")()))
        self.assertGreaterEqual(len(supervision_snapshot["attention_queue"]), 1)
        item = supervision_snapshot["attention_queue"][0]

        response = asyncio.run(
            self._route("/api/supervision/reviews/{request_id}/{action}", "POST")(
                item["request_id"],
                "reject",
                {
                    "actor": "Chris",
                    "title": item["title"],
                    "reason": "Need a safer plan first.",
                },
            )
        )
        refreshed_supervision = self._json_body(asyncio.run(self._route("/api/supervision/module", "GET")()))
        activity_snapshot = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

        result = self._json_body(response)

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["focus"]["module"], "Supervision")
        self.assertTrue(any(entry.get("title") == "Reject Supervision Item" for entry in refreshed_supervision["recent_activity"]))
        self.assertTrue(any(entry.get("related_label") == item["title"] for entry in refreshed_supervision["recent_activity"]))
        self.assertTrue(any(entry.get("related_kind") == "supervision-item" for entry in activity_snapshot))
        self.assertEqual(progress_snapshot["progress_next_focus"], "Supervision")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Supervision")

    def test_supervision_integration_recovery_creates_durable_case_and_recovery_focus(self) -> None:
        supervision_snapshot = self._json_body(asyncio.run(self._route("/api/supervision/module", "GET")()))
        self.assertGreaterEqual(len(supervision_snapshot["integration_recovery_lane"]), 1)
        target = next(item for item in supervision_snapshot["integration_recovery_lane"] if not item.get("ok"))

        response = asyncio.run(
            self._route("/api/supervision/integrations/{integration_name}/recovery", "POST")(
                target["name"],
                {"actor": "Chris"},
            )
        )
        refreshed_supervision = self._json_body(asyncio.run(self._route("/api/supervision/module", "GET")()))
        recovery_snapshot = self._json_body(asyncio.run(self._route("/api/recovery/module", "GET")()))
        activity_snapshot = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

        result = self._json_body(response)

        self.assertEqual(result["status"], "staged")
        self.assertEqual(result["focus"]["module"], "Recovery")
        self.assertEqual(result["integration"]["name"], target["name"])
        self.assertTrue(any(entry.get("name") == target["name"] and entry.get("case_id") for entry in refreshed_supervision["integration_recovery_lane"]))
        self.assertTrue(any(case.get("related_key") == target["name"] for case in refreshed_supervision["recovery_cases"]))
        self.assertTrue(any(case.get("related_key") == target["name"] for case in recovery_snapshot["recovery_cases"]))
        self.assertTrue(any(entry.get("title") == "Stage Supervision Recovery Case" for entry in activity_snapshot))
        self.assertEqual(progress_snapshot["progress_next_focus"], "Recovery")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Recovery")

    def test_health_objective_mutation_persists_into_health_and_activity(self) -> None:
        objectives_path = Path(self.tempdir.name) / "health" / "quarterly_objectives.json"
        objectives_log_path = objectives_path.with_name("quarterly_objectives_log.jsonl")
        objectives_state_log_path = objectives_path.with_name("quarterly_objectives_state_log.jsonl")
        objectives_path.parent.mkdir(parents=True, exist_ok=True)

        class _JSONRequest:
            def __init__(self, payload: dict) -> None:
                self._payload = payload

            async def json(self) -> dict:
                return self._payload

        with (
            patch.object(quarterly_review_module, "_OBJECTIVES_PATH", objectives_path),
            patch.object(quarterly_review_module, "_OBJECTIVES_LOG_PATH", objectives_log_path),
            patch.object(quarterly_review_module, "_OBJECTIVES_STATE_LOG_PATH", objectives_state_log_path),
        ):
            response = asyncio.run(
                self._route("/api/health/quarterly/objectives", "POST")(
                    _JSONRequest(
                        {
                            "objectives": [
                                {
                                    "objective": "Lower A1c by improving post-meal glucose control",
                                    "domain": "metabolic health",
                                    "why_it_matters": "A1c drift is one of the clearest live risks in the health posture.",
                                    "baseline": "A1c 7.3%",
                                    "target": "A1c under 6.8%",
                                    "weekly_actions": ["Walk after dinner five nights a week"],
                                    "measurement_plan": "Review weekly glucose and adherence signals every Sunday.",
                                }
                            ]
                        }
                    )
                )
            )
            activity_response = asyncio.run(
                self._route("/api/activity/operator-action", "POST")(
                    {
                        "actor": "Chris",
                        "domain": "health",
                        "action": "Save Health Objective",
                        "detail": "Health objective saved into the quarterly objective store.",
                        "why_now": "Health route persisted a real coaching objective directly from the operator flow.",
                        "result_summary": "Saved 1 health objective.",
                        "route": "/health-center",
                        "route_label": "Open Health",
                        "related_kind": "health-objective",
                        "related_label": "Lower A1c by improving post-meal glucose control",
                        "succeeded": True,
                    }
                )
            )
            health_snapshot = self._json_body(asyncio.run(self._route("/api/health/module", "GET")()))

        result = self._json_body(response)
        activity_result = self._json_body(activity_response)

        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["focus"]["module"], "Health")
        self.assertEqual(activity_result["status"], "recorded")
        self.assertTrue(any(item.get("objective") == "Lower A1c by improving post-meal glucose control" for item in health_snapshot["objectives"]))
        self.assertTrue(any(item.get("title") == "Save Health Objective" for item in health_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_label") == "Lower A1c by improving post-meal glucose control" for item in health_snapshot["recent_activity"]))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))
        self.assertEqual(progress_snapshot["progress_next_focus"], "Health")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Health")

    def test_health_checkin_mutation_persists_into_health_and_activity(self) -> None:
        async def _payload() -> dict[str, object]:
            return {
                "actor": "Chris",
                "actor_id": "chris",
                "symptoms": "Low energy after poor sleep",
                "note": "Late night, no walk, and heavier dinner than normal.",
                "energy_level": 4,
                "sleep_hours": 5.5,
                "stress_level": 7,
                "source": "test-health-route",
            }

        response = asyncio.run(
            self._route("/api/health/checkins", "POST")(
                SimpleNamespace(json=_payload)
            )
        )
        listing = self._json_body(asyncio.run(self._route("/api/health/checkins", "GET")(actor="chris")))
        health_snapshot = self._json_body(asyncio.run(self._route("/api/health/module", "GET")()))
        activity_snapshot = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

        result = self._json_body(response)

        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["checkin"]["symptoms"], "Low energy after poor sleep")
        self.assertEqual(result["focus"]["module"], "Health")
        self.assertEqual(listing["count"], 1)
        self.assertEqual(health_snapshot["checkin_count"], 1)
        self.assertEqual(health_snapshot["latest_checkin"]["symptoms"], "Low energy after poor sleep")
        self.assertTrue(any(item.get("symptoms") == "Low energy after poor sleep" for item in health_snapshot["recent_checkins"]))
        self.assertTrue(any(item.get("title") == "Save Health Check-In" for item in health_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("subtitle") == "Late night, no walk, and heavier dinner than normal." for item in health_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_kind") == "health-checkin" for item in activity_snapshot))
        self.assertEqual(progress_snapshot["progress_next_focus"], "Health")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Health")

    def test_health_checkin_review_persists_review_lane_and_shared_continuity(self) -> None:
        async def _create_payload() -> dict[str, object]:
            return {
                "actor": "Chris",
                "actor_id": "chris",
                "symptoms": "Lingering fatigue after poor sleep",
                "note": "Manual entry from the Health command center.",
                "energy_level": 4,
                "sleep_hours": 5.0,
                "stress_level": 6,
                "source": "test-health-route",
            }

        create_response = asyncio.run(
            self._route("/api/health/checkins", "POST")(
                SimpleNamespace(json=_create_payload)
            )
        )
        created = self._json_body(create_response)["checkin"]

        async def _review_payload() -> dict[str, object]:
            return {
                "actor": "Chris",
                "status": "adjust",
                "note": "Reduce training load and prioritize recovery protocol tomorrow.",
            }

        review_response = asyncio.run(
            self._route("/api/health/checkins/{checkin_id}/review", "POST")(
                created["checkin_id"],
                SimpleNamespace(json=_review_payload),
            )
        )
        listing = self._json_body(asyncio.run(self._route("/api/health/checkins", "GET")(actor="chris")))
        health_snapshot = self._json_body(asyncio.run(self._route("/api/health/module", "GET")()))
        activity_snapshot = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

        result = self._json_body(review_response)

        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["checkin"]["review_status"], "adjust")
        self.assertEqual(result["checkin"]["review_status_label"], "Adjust Protocol")
        self.assertEqual(result["focus"]["module"], "Health")
        self.assertEqual(listing["review_count"], 1)
        self.assertEqual(listing["review_status_counts"]["adjust"], 1)
        self.assertTrue(any(item.get("review_status") == "adjust" for item in health_snapshot["recent_checkins"]))
        self.assertTrue(any(item.get("review_status") == "adjust" for item in health_snapshot["review_lane"]))
        self.assertTrue(any(item.get("title") == "Review Health Check-In" for item in health_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_kind") == "health-checkin-review" for item in activity_snapshot))
        self.assertEqual(progress_snapshot["progress_next_focus"], "Health")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Health")

    def test_settings_mutations_persist_into_settings_and_activity(self) -> None:
        profiles_dir = Path(self.tempdir.name) / "settings" / "profiles"
        with patch.object(user_profile_module, "PROFILES_DIR", profiles_dir):
            voice_response = asyncio.run(
                self._route("/api/voice-settings", "POST")(
                    {
                        "actor": "Chris",
                        "tts_provider": "elevenlabs",
                        "elevenlabs_voice": "alloy",
                        "piper_model_path": "",
                        "piper_speaker": "2",
                    }
                )
            )
            location_response = asyncio.run(
                self._route("/api/location-settings", "POST")(
                    {
                        "actor": "Chris",
                        "preferred_location_id": "household-home",
                    }
                )
            )
            profile_response = asyncio.run(
                self._route("/api/settings/profile", "POST")(
                    {
                        "actor": "Chris",
                        "notifications": {
                            "approvals": False,
                            "health_alerts": False,
                        },
                        "privacy": {
                            "private_chronicle": False,
                            "share_health_with_family": True,
                        },
                        "dashboard": {
                            "show_health": False,
                            "show_publishing": True,
                        },
                    }
                )
            )

            voice_payload = self._json_body(voice_response)
            location_payload = self._json_body(location_response)
            profile_payload = self._json_body(profile_response)
            settings_snapshot = self._json_body(asyncio.run(self._route("/api/settings/module", "GET")()))
            activity_payload = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))
            progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

            self.assertEqual(voice_payload["message"], "Voice settings updated.")
            self.assertTrue(location_payload["ok"])
            self.assertEqual(profile_payload["message"], "Profile defaults updated.")
            self.assertEqual(settings_snapshot["voice"]["tts_provider"], "elevenlabs")
            self.assertEqual(settings_snapshot["location"]["preferred_location_id"], "household-home")
            self.assertFalse(settings_snapshot["permissions"]["notifications"]["approvals"])
            self.assertFalse(settings_snapshot["permissions"]["privacy"]["private_chronicle"])
            self.assertTrue(settings_snapshot["permissions"]["privacy"]["share_health_with_family"])
            self.assertFalse(settings_snapshot["permissions"]["dashboard"]["show_health"])
            self.assertTrue(settings_snapshot["permissions"]["dashboard"]["show_publishing"])
            self.assertTrue(any(item.get("title") == "Save Voice Settings" for item in settings_snapshot["recent_activity"]))
            self.assertTrue(any(item.get("title") == "Save Location Settings" for item in settings_snapshot["recent_activity"]))
            self.assertTrue(any(item.get("title") == "Save Profile Defaults" for item in settings_snapshot["recent_activity"]))
            self.assertTrue(any(item.get("related_kind") == "voice-settings" for item in activity_payload))
            self.assertTrue(any(item.get("related_kind") == "location-settings" for item in activity_payload))
            self.assertTrue(any(item.get("related_kind") == "profile-settings" for item in activity_payload))
            self.assertEqual(progress_snapshot["progress_next_focus"], "Settings")
            self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Settings")

    def test_voice_synthesize_honors_explicit_saved_provider_selection(self) -> None:
        asyncio.run(
            self._route("/api/voice-settings", "POST")(
                {
                    "actor": "Chris",
                    "tts_provider": "fish",
                    "elevenlabs_voice": "",
                    "piper_model_path": "",
                    "piper_speaker": "0",
                }
            )
        )

        class _Pipeline:
            def __init__(self) -> None:
                self.called = False

            def synthesize(self, text: str):
                self.called = True
                return (b"pipeline-audio", "mp3")

            def get_status(self) -> dict:
                return {"active_provider": "elevenlabs"}

        class _Friday:
            def prepare_for_voice(self, text: str) -> str:
                return text

        pipeline = _Pipeline()
        captured: dict[str, object] = {}

        def _generate(config, text: str, voice_settings: dict | None = None):
            captured["text"] = text
            captured["voice_settings"] = dict(voice_settings or {})
            return SimpleNamespace(
                data=b"fish-bytes",
                content_type="audio/mpeg",
                provider="fish",
                requested_provider="fish",
                attempted_providers=("fish",),
                provider_failures=(),
            )

        with patch.object(service_module, "get_pipeline", return_value=pipeline), patch.object(
            service_module,
            "get_friday",
            return_value=_Friday(),
        ), patch.object(service_module, "generate_tts_audio", side_effect=_generate) as mocked_generate:
            response = asyncio.run(
                self._route("/api/voice/synthesize", "POST")(
                    {"text": "Speak this aloud."}
                )
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Jarvis-Voice-Requested-Provider"), "fish")
        self.assertEqual(response.headers.get("X-Jarvis-Voice-Effective-Provider"), "fish")
        self.assertEqual(response.headers.get("X-Jarvis-Voice-Selection-Mode"), "explicit")
        self.assertEqual(response.headers.get("X-Jarvis-Voice-Provider"), "fish")
        self.assertFalse(pipeline.called)
        mocked_generate.assert_called_once()
        self.assertEqual(captured["text"], "Speak this aloud.")
        self.assertEqual(captured["voice_settings"]["tts_provider"], "fish")

    def test_voice_synthesize_surfaces_truthful_fallback_headers_when_explicit_provider_drops_to_system(self) -> None:
        asyncio.run(
            self._route("/api/voice-settings", "POST")(
                {
                    "actor": "Chris",
                    "tts_provider": "fish",
                    "elevenlabs_voice": "",
                    "piper_model_path": "",
                    "piper_speaker": "0",
                }
            )
        )

        class _Pipeline:
            def synthesize(self, text: str):
                return (b"pipeline-audio", "mp3")

            def get_status(self) -> dict:
                return {"active_provider": "elevenlabs"}

        class _Friday:
            def prepare_for_voice(self, text: str) -> str:
                return text

        fallback_audio = SimpleNamespace(
            data=b"system-bytes",
            content_type="audio/wav",
            provider="system",
            requested_provider="fish",
            attempted_providers=("fish", "system"),
            provider_failures=("fish: Fish Audio HTTP 401",),
        )

        with patch.object(service_module, "get_pipeline", return_value=_Pipeline()), patch.object(
            service_module,
            "get_friday",
            return_value=_Friday(),
        ), patch.object(service_module, "generate_tts_audio", return_value=fallback_audio):
            response = asyncio.run(
                self._route("/api/voice/synthesize", "POST")(
                    {"text": "Speak this aloud."}
                )
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Jarvis-Voice-Requested-Provider"), "fish")
        self.assertEqual(response.headers.get("X-Jarvis-Voice-Effective-Provider"), "system")
        self.assertEqual(response.headers.get("X-Jarvis-Voice-Fallback-From"), "fish")
        self.assertEqual(response.headers.get("X-Jarvis-Voice-Attempted-Providers"), "fish,system")
        self.assertEqual(response.headers.get("X-Jarvis-Voice-Fallback-Count"), "1")
        self.assertIn("fish: Fish Audio HTTP 401", response.headers.get("X-Jarvis-Voice-Fallback-Reason", ""))

    def test_settings_center_voice_controls_surface_shows_live_blocker_and_fallback_posture(self) -> None:
        asyncio.run(
            self._route("/api/voice-settings", "POST")(
                {
                    "actor": "Chris",
                    "tts_provider": "fish",
                    "elevenlabs_voice": "",
                    "piper_model_path": "",
                    "piper_speaker": "0",
                }
            )
        )

        class _Pipeline:
            def synthesize(self, text: str):
                return (b"pipeline-audio", "mp3")

            def get_status(self) -> dict:
                return {"active_provider": "system"}

        class _Friday:
            def prepare_for_voice(self, text: str) -> str:
                return text

        fallback_audio = SimpleNamespace(
            data=b"system-bytes",
            content_type="audio/wav",
            provider="system",
            requested_provider="fish",
            attempted_providers=("fish", "system"),
            provider_failures=(
                "fish: Fish Audio request failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed",
            ),
        )

        with patch.object(service_module, "get_pipeline", return_value=_Pipeline()), patch.object(
            service_module,
            "get_friday",
            return_value=_Friday(),
        ), patch.object(service_module, "generate_tts_audio", return_value=fallback_audio):
            response = asyncio.run(
                self._route("/api/voice/synthesize", "POST")(
                    {"text": "Check the saved provider route."}
                )
            )

        self.assertEqual(response.status_code, 200)
        settings_html = self._text_body(asyncio.run(self._route("/settings-center", "GET")()))
        settings_snapshot = self._json_body(asyncio.run(self._route("/api/settings/module", "GET")()))
        stack_status = settings_snapshot["voice"]["stack_status"]

        self.assertIn("Configured readiness", settings_html)
        self.assertIn("Last live readiness", settings_html)
        self.assertIn("Last live blocker", settings_html)
        self.assertIn("Last live fallback", settings_html)
        self.assertIn("ssl transport blocked", settings_html)
        self.assertIn("Fish Audio request failed", settings_html)
        self.assertEqual(stack_status["selected_tts_provider"], "fish")
        self.assertFalse(stack_status["selected_tts_provider_live_ready"])
        self.assertEqual(stack_status["selected_tts_provider_live_state"], "ssl_transport_blocked")
        self.assertEqual(stack_status["last_live_effective_tts_provider"], "system")
        self.assertIn("certificate verify failed", stack_status["selected_tts_provider_live_reason"].lower())

    def test_settings_center_voice_controls_surface_exposes_preview_parity_copy(self) -> None:
        settings_html = self._text_body(asyncio.run(self._route("/settings-center", "GET")()))

        self.assertIn("voice-preview-text", settings_html)
        self.assertIn("Save + Preview", settings_html)
        self.assertIn("function previewVoiceSettings() {", settings_html)
        self.assertIn("Preview requested ${requested}, but playback used ${effective}. Live blocker: ${blocker}", settings_html)
        self.assertIn("Preview requested ${requested} and played with ${effective}.", settings_html)
        self.assertIn("Configured voice source saved. Running preview through the current voice route", settings_html)
        self.assertIn("Saved. Configured voice source:", settings_html)
        self.assertIn("Preview failed:", settings_html)

    def test_voice_synthesize_reports_auto_pipeline_when_selection_is_auto(self) -> None:
        class _Pipeline:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def synthesize(self, text: str):
                self.calls.append(text)
                return (b"pipeline-audio", "mp3")

            def get_status(self) -> dict:
                return {"active_provider": "elevenlabs"}

        class _Friday:
            def prepare_for_voice(self, text: str) -> str:
                return f"voice::{text}"

        pipeline = _Pipeline()

        with patch.object(service_module, "get_pipeline", return_value=pipeline), patch.object(
            service_module,
            "get_friday",
            return_value=_Friday(),
        ), patch.object(service_module, "generate_tts_audio") as mocked_generate:
            response = asyncio.run(
                self._route("/api/voice/synthesize", "POST")(
                    {"text": "Use the normal voice path."}
                )
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Jarvis-Voice-Requested-Provider"), "auto")
        self.assertEqual(response.headers.get("X-Jarvis-Voice-Effective-Provider"), "elevenlabs")
        self.assertEqual(response.headers.get("X-Jarvis-Voice-Selection-Mode"), "auto-pipeline")
        self.assertEqual(response.headers.get("X-Jarvis-Voice-Provider"), "elevenlabs")
        self.assertEqual(pipeline.calls, ["voice::Use the normal voice path."])
        mocked_generate.assert_not_called()

    def test_settings_account_mutations_persist_into_settings_and_activity(self) -> None:
        save_response = asyncio.run(
            self._route("/api/settings/account", "POST")(
                {
                    "actor": "Chris",
                    "account_id": "acct-google-1",
                    "label": "Chris Family Google",
                    "login_hint": "family@example.com",
                    "status": "paused",
                }
            )
        )
        disconnect_response = asyncio.run(
            self._route("/api/settings/accounts/{account_id}/disconnect", "POST")(
                account_id="acct-google-1",
                payload={"actor": "Chris"},
            )
        )

        save_payload = self._json_body(save_response)
        disconnect_payload = self._json_body(disconnect_response)
        settings_snapshot = self._json_body(asyncio.run(self._route("/api/settings/module", "GET")()))
        activity_payload = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

        self.assertTrue(save_payload["ok"])
        self.assertTrue(disconnect_payload["ok"])
        self.assertEqual(settings_snapshot["counts"]["account_count"], 1)
        self.assertEqual(settings_snapshot["counts"]["connected_account_count"], 0)
        account = settings_snapshot["accounts"]["accounts"][0]
        self.assertEqual(account["label"], "Chris Family Google")
        self.assertEqual(account["login_hint"], "family@example.com")
        self.assertEqual(account["status"], "planned")
        self.assertTrue(any(item.get("title") == "Save Account Controls" for item in settings_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("title") == "Disconnect Account" for item in settings_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_kind") == "settings-account" for item in activity_payload))
        self.assertEqual(progress_snapshot["progress_next_focus"], "Settings")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Settings")

    def test_settings_connector_mutations_persist_into_settings_and_activity(self) -> None:
        connector_response = asyncio.run(
            self._route("/api/settings/connector", "POST")(
                {
                    "actor": "Chris",
                    "account_id": "acct-google-1",
                    "service_scope": "calendar",
                    "status": "watch",
                    "notes": "Calendar still needs OAuth repair before mail is re-enabled.",
                }
            )
        )

        connector_payload = self._json_body(connector_response)
        settings_snapshot = self._json_body(asyncio.run(self._route("/api/settings/module", "GET")()))
        activity_payload = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

        self.assertTrue(connector_payload["ok"])
        connector = settings_snapshot["connector_lane"][0]
        self.assertEqual(connector["service_scope"], "calendar")
        self.assertEqual(connector["status"], "watch")
        self.assertEqual(connector["notes"], "Calendar still needs OAuth repair before mail is re-enabled.")
        self.assertTrue(connector["needs_attention"])
        self.assertTrue(any(item.get("title") == "Save Connector Controls" for item in settings_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_kind") == "settings-connector" for item in activity_payload))
        self.assertEqual(progress_snapshot["progress_next_focus"], "Settings")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Settings")

    def test_settings_family_identity_mutations_persist_into_settings_and_activity(self) -> None:
        identity_response = asyncio.run(
            self._route("/api/settings/family-member", "POST")(
                {
                    "actor": "Chris",
                    "user_id": "chris",
                    "role": "operator",
                    "permissions": "household-admin",
                    "trust_level": "trusted",
                    "preferred_tone": "warm and direct",
                    "notes": "Primary morning and launch owner.",
                }
            )
        )

        identity_payload = self._json_body(identity_response)
        settings_snapshot = self._json_body(asyncio.run(self._route("/api/settings/module", "GET")()))
        activity_payload = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))

        self.assertTrue(identity_payload["ok"])
        member = settings_snapshot["identity"]["members"][0]
        self.assertEqual(member["role"], "operator")
        self.assertEqual(member["permissions"], "household-admin")
        self.assertEqual(member["preferred_tone"], "warm and direct")
        self.assertEqual(member["notes"], "Primary morning and launch owner.")
        self.assertTrue(any(item.get("title") == "Save Family Identity" for item in settings_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_kind") == "settings-family-identity" for item in activity_payload))
        self.assertEqual(progress_snapshot["progress_next_focus"], "Settings")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Settings")

    def test_chronicle_activity_populates_chronicle_continuity(self) -> None:
        asyncio.run(
            self._route("/api/activity/operator-action", "POST")(
                {
                    "actor": "Chris",
                    "domain": "chronicle",
                    "action": "Capture Chronicle Note",
                    "detail": "Chronicle reflection captured into the live timeline.",
                    "why_now": "Chronicle continuity smoke test.",
                    "result_summary": "Chronicle note captured.",
                    "route": "/chronicle-center",
                    "route_label": "Open Chronicle",
                    "related_kind": "chronicle-entry",
                    "related_label": "gratitude in the middle of fatigue",
                    "succeeded": True,
                }
            )
        )

        chronicle_snapshot = self._json_body(asyncio.run(self._route("/api/chronicle/module", "GET")()))

        self.assertTrue(any(item.get("title") == "Capture Chronicle Note" for item in chronicle_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_label") == "gratitude in the middle of fatigue" for item in chronicle_snapshot["recent_activity"]))

    def test_chronicle_review_mutation_persists_review_lane_and_progress(self) -> None:
        self.runtime.chronicle_timeline = lambda limit=10: [
            {
                "entry_id": "chronicle-entry-1",
                "theme": "Gratitude in the middle of fatigue",
                "reflection": "We found calm after the pressure eased.",
                "actor": "Chris",
                "timestamp": "2026-06-06T09:00:00Z",
                "entry_type": "reflection",
            }
        ]
        self.runtime.chronicle_theme_summary = lambda limit=25: {"themes": [{"theme": "gratitude", "count": 1}]}

        response = self._json_body(
            asyncio.run(
                self._route("/api/chronicle/entries/{entry_id}/review", "POST")(
                    "chronicle-entry-1",
                    {
                        "actor": "Chris",
                        "status": "family",
                        "title": "Gratitude in the middle of fatigue",
                        "entry_type": "reflection",
                        "note": "Bring this into tonight's family devotional.",
                    }
                )
            )
        )
        chronicle_snapshot = self._json_body(asyncio.run(self._route("/api/chronicle/module", "GET")()))
        from jarvis.audit import AuditLog
        recent_activity = AuditLog(Path("data/logs")).list_recent(limit=6, entry_type="operator-action")

        self.assertEqual(response["status"], "recorded")
        self.assertEqual(response["review"]["review_status_label"], "Queue Family Handoff")
        self.assertEqual(response["focus"]["module"], "Chronicle")
        self.assertTrue(any(item.get("entry_id") == "chronicle-entry-1" for item in chronicle_snapshot["review_lane"]))
        self.assertGreaterEqual(chronicle_snapshot["counts"]["review_count"], 1)
        self.assertTrue(any(item.get("related_kind") == "chronicle-review" for item in recent_activity))

    def test_legacy_chronicle_routes_expose_recent_context_patterns_and_capture(self) -> None:
        from jarvis.chronicle_bridge import init_chronicle_bridge

        init_chronicle_bridge()

        capture_response = self._json_body(
            asyncio.run(
                self._route("/api/chronicle/quick-capture", "POST")(
                    {
                        "type": "gratitude",
                        "content": "Thank God for a calm evening after a loud day.",
                        "passage": "Psalm 46:10",
                    }
                )
            )
        )
        write_response = self._json_body(
            asyncio.run(
                self._route("/api/chronicle/write-entry", "POST")(
                    {
                        "entry": {
                            "type": "study",
                            "title": "Bible Study — Psalm 23",
                            "body": "The Lord is my shepherd. I want to remember the quiet trust here.",
                            "passage": "Psalm 23",
                            "themes": ["study", "trust"],
                        }
                    }
                )
            )
        )
        recent_payload = self._json_body(asyncio.run(self._route("/api/chronicle/recent", "GET")()))
        context_payload = self._json_body(asyncio.run(self._route("/api/chronicle/context", "GET")()))
        patterns_payload = self._json_body(asyncio.run(self._route("/api/chronicle/patterns", "GET")()))
        search_payload = self._json_body(
            asyncio.run(self._route("/api/chronicle/search", "GET")(q="shepherd"))
        )
        prayer_response = self._json_body(
            asyncio.run(
                self._route("/api/chronicle/update-prayer", "POST")(
                    {
                        "id": "legacy-prayer-1",
                        "timesPrayed": 3,
                        "lastPrayedAt": "2026-06-08",
                        "answered": True,
                        "dateAnswered": "2026-06-08",
                        "answerSummary": "Marked answered from Legacy.",
                    }
                )
            )
        )

        self.assertTrue(capture_response["ok"])
        self.assertTrue(write_response["ok"])
        self.assertTrue(recent_payload["ok"])
        self.assertIn("entries", recent_payload)
        self.assertGreaterEqual(recent_payload["total"], 2)
        self.assertTrue(any("Psalm 23" in str(item.get("title")) for item in recent_payload["entries"]))
        self.assertTrue(context_payload["ok"])
        self.assertIn("top_themes", context_payload)
        self.assertTrue(patterns_payload["ok"])
        self.assertIn("entry_type_breakdown", patterns_payload)
        self.assertTrue(search_payload["ok"])
        self.assertTrue(any("Psalm 23" in str(item.get("title")) for item in search_payload["entries"]))
        self.assertTrue(prayer_response["ok"])
        self.assertEqual(prayer_response["prayer"]["timesPrayed"], 3)
        self.assertTrue(prayer_response["prayer"]["answered"])

    def test_faith_routes_expose_module_daily_word_agents_and_chat(self) -> None:
        from jarvis.chronicle_bridge import init_chronicle_bridge

        init_chronicle_bridge()

        async def _fake_daily_word(_runtime):
            return {
                "ok": True,
                "agent_id": "ezra",
                "agent_name": "Ezra",
                "agent_title": "The Scribe",
                "color": "#C9A84C",
                "domain": "Exegesis & the Text",
                "passage": "Psalm 23",
                "word": "The Shepherd is with you in the real work of today.",
                "generated_at": "2026-06-08T12:00:00+00:00",
            }

        async def _fake_chat(*, agent_id: str, messages: list[dict], runtime, passage: str = ""):
            return f"{agent_id}:{passage}:{messages[-1]['content']}"

        with patch("jarvis.faith_agents.daily_word", _fake_daily_word), patch(
            "jarvis.faith_agents.chat", _fake_chat
        ):
            daily_word_payload = self._json_body(asyncio.run(self._route("/api/faith/daily-word", "GET")()))
            agents_payload = self._json_body(asyncio.run(self._route("/api/faith/agents", "GET")()))
            module_payload = self._json_body(asyncio.run(self._route("/api/faith/module", "GET")()))
            chat_payload = self._json_body(
                asyncio.run(
                    self._route("/api/faith/chat", "POST")(
                        {
                            "agent_id": "ezra",
                            "passage": "Psalm 23",
                            "messages": [{"role": "user", "content": "What should I notice?"}],
                        }
                    )
                )
            )

        self.assertTrue(daily_word_payload["ok"])
        self.assertTrue(daily_word_payload["available"])
        self.assertEqual(daily_word_payload["passage"], "Psalm 23")
        self.assertTrue(agents_payload["ok"])
        self.assertGreater(len(agents_payload["agents"]), 0)
        self.assertTrue(module_payload["ok"])
        self.assertIn("daily_word", module_payload)
        self.assertIn("chronicle_context", module_payload)
        self.assertIn("chronicle_patterns", module_payload)
        self.assertIn("prayer_items", module_payload)
        self.assertIn("availability_notes", module_payload)
        self.assertTrue(chat_payload["ok"])
        self.assertIn("What should I notice?", chat_payload["reply"])

    def test_faith_module_uses_hosted_chronicle_context_when_local_daily_word_is_unavailable(self) -> None:
        from jarvis.chronicle_bridge import init_chronicle_bridge

        init_chronicle_bridge()
        self.runtime.identity_overview = lambda: {
            "members": [dict(item) for item in self.runtime._identity_members],
            "devices": [dict(item) for item in self.runtime._identity_devices],
            "service": {
                "hosted_base_url": "https://jarvis.teambinion.org",
                "remote_admin_host": "5.78.212.15",
                "remote_admin_user": "root",
                "hosted_provider": "Hetzner",
                "edge_provider": "Cloudflare Tunnel",
                "compose_project": "jarvis-family",
            },
        }

        async def _missing_daily_word(_runtime):
            return {
                "ok": False,
                "available": False,
                "agent_name": "JARVIS",
                "passage": "",
                "word": "",
                "message": "Daily word unavailable",
            }

        def _fake_subprocess_run(cmd, capture_output=False, text=False, timeout=None, check=False):
            joined = " ".join(str(part) for part in cmd)
            if "/api/chronicle/recent" in joined:
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "ok": True,
                            "entries": [
                                {
                                    "id": "chronicle-remote-1",
                                    "entry_id": "chronicle-remote-1",
                                    "date": "2026-06-09",
                                    "type": "reflection",
                                    "title": "Morning Reflection — Tuesday, June 9",
                                    "body": "Reflection from hosted Chronicle.",
                                    "passage": "James 1:5",
                                    "themes": ["wisdom"],
                                }
                            ],
                            "total": 1,
                            "tags": ["wisdom"],
                            "prayer_items": [],
                            "active_prayers": 0,
                            "answered_prayers": 0,
                            "formation_rhythms": [],
                            "owned_books": [],
                            "chronicle_available": True,
                        }
                    ),
                    stderr="",
                )
            if "/api/chronicle/morning-context" in joined:
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "reflection_prompt": "Scripture: James 1:5\n\nAsk God for wisdom before acting.",
                            "scripture_of_day": {
                                "ref": "James 1:5",
                                "text": "If any of you lacks wisdom, you should ask God.",
                            },
                        }
                    ),
                    stderr="",
                )
            return SimpleNamespace(returncode=1, stdout="", stderr="unhandled")

        with patch("jarvis.faith_agents.daily_word", _missing_daily_word), patch(
            "jarvis.service._get_chronicle_bridge", return_value=None
        ), patch("jarvis.service.subprocess.run", _fake_subprocess_run):
            module_payload = self._json_body(asyncio.run(self._route("/api/faith/module", "GET")()))

        self.assertTrue(module_payload["ok"])
        self.assertTrue(module_payload["daily_word"]["available"])
        self.assertEqual(module_payload["daily_word"]["passage"], "James 1:5")
        self.assertIn("Ask God for wisdom", module_payload["daily_word"]["word"])

    def test_faith_module_prefers_local_chronicle_bridge_context(self) -> None:
        async def _missing_daily_word(_runtime):
            return {
                "ok": False,
                "available": False,
                "agent_name": "JARVIS",
                "passage": "",
                "word": "",
                "message": "Daily word unavailable",
            }

        class _FakeBridge:
            def get_pending_entries(self):
                return []

            def get_morning_spiritual_context(self, actor_id: str = "chris"):
                return {
                    "reflection_prompt": "Scripture: James 1:5\n\nAsk God for wisdom before acting.",
                    "scripture_of_day": {
                        "ref": "James 1:5",
                        "text": "If any of you lacks wisdom, you should ask God.",
                    },
                }

        def _fake_subprocess_run(cmd, capture_output=False, text=False, timeout=None, check=False):
            joined = " ".join(str(part) for part in cmd)
            if "/api/chronicle/recent" in joined:
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "ok": True,
                            "entries": [],
                            "total": 0,
                            "tags": [],
                            "prayer_items": [],
                            "active_prayers": 0,
                            "answered_prayers": 0,
                            "formation_rhythms": [],
                            "owned_books": [],
                            "chronicle_available": True,
                        }
                    ),
                    stderr="",
                )
            return SimpleNamespace(returncode=1, stdout="", stderr="unhandled")

        with patch("jarvis.faith_agents.daily_word", _missing_daily_word), patch(
            "jarvis.service._get_chronicle_bridge", return_value=_FakeBridge()
        ), patch("jarvis.service.subprocess.run", _fake_subprocess_run):
            module_payload = self._json_body(asyncio.run(self._route("/api/faith/module", "GET")()))

        self.assertTrue(module_payload["ok"])
        self.assertTrue(module_payload["daily_word"]["available"])
        self.assertEqual(module_payload["daily_word"]["passage"], "James 1:5")
        self.assertIn("Ask God for wisdom", module_payload["daily_word"]["word"])

    def test_faith_chat_route_surfaces_empty_reply_honestly(self) -> None:
        async def _empty_chat(*, agent_id: str, messages: list[dict], runtime, passage: str = ""):
            return ""

        with patch("jarvis.faith_agents.chat", _empty_chat):
            chat_payload = self._json_body(
                asyncio.run(
                    self._route("/api/faith/chat", "POST")(
                        {
                            "agent_id": "paul",
                            "passage": "Philippians 4:6",
                            "messages": [{"role": "user", "content": "Help me pray about anxiety."}],
                        }
                    )
                )
            )

        self.assertFalse(chat_payload["ok"])
        self.assertFalse(chat_payload["available"])
        self.assertEqual(chat_payload["agent_id"], "paul")
        self.assertIn("no faith response was returned", chat_payload["detail"].lower())

    def test_agents_routes_expose_module_and_roster(self) -> None:
        module_payload = self._json_body(asyncio.run(self._route("/api/agents/module", "GET")()))
        roster_payload = self._json_body(asyncio.run(self._route("/api/agents/roster", "GET")()))

        self.assertTrue(module_payload["available"])
        self.assertIn("status", module_payload)
        self.assertIn("roster", module_payload)
        self.assertIn("activity_feed", module_payload)
        self.assertIn("pending_requests", module_payload)
        self.assertIn("collaboration", module_payload)
        self.assertIn("trust", module_payload)
        self.assertIn("specializations", module_payload)
        self.assertIn("performance", module_payload)
        self.assertIn("runtime", module_payload)
        self.assertIn("proof_paths", module_payload)
        self.assertEqual(module_payload["proof_paths"]["module_route"], "/agents")
        self.assertEqual(module_payload["proof_paths"]["module_api"], "/api/agents/module")
        self.assertEqual(module_payload["proof_paths"]["roster_api"], "/api/agents/roster")
        self.assertGreaterEqual(len(module_payload["roster"]["items"]), 1)

        self.assertTrue(roster_payload["available"])
        self.assertGreaterEqual(roster_payload["count"], 1)
        self.assertGreaterEqual(len(roster_payload["agents"]), 1)

    def test_navigation_and_health_support_routes_return_honest_json_when_unavailable(self) -> None:
        maps_payload = self._json_body(asyncio.run(self._route("/api/nav/maps-key", "GET")()))
        usage_payload = self._json_body(asyncio.run(self._route("/api/google/maps-usage", "GET")()))

        self.assertTrue(maps_payload["ok"])
        self.assertIn("available", maps_payload)
        self.assertIn("key_configured", maps_payload)
        self.assertTrue(usage_payload["ok"])
        self.assertIn("available", usage_payload)
        self.assertIn("usage", usage_payload)

        original_import = __import__

        def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name.endswith("health_db") or (name == "" and "health_db" in fromlist):
                raise ImportError("health_db unavailable in test")
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=_fake_import):
            ecg_payload = self._json_body(asyncio.run(self._route("/api/health/ecg", "GET")()))
            summary_payload = self._json_body(asyncio.run(self._route("/api/health/db/summary", "GET")()))

        self.assertFalse(ecg_payload["ok"])
        self.assertFalse(ecg_payload["available"])
        self.assertEqual(ecg_payload["readings"], [])
        self.assertIn("unavailable", ecg_payload["error"].lower())
        self.assertFalse(summary_payload["ok"])
        self.assertFalse(summary_payload["available"])
        self.assertEqual(summary_payload["today"], {})
        self.assertEqual(summary_payload["recent"], [])
        self.assertIn("unavailable", summary_payload["error"].lower())

    def test_navigation_route_api_saves_shared_state_but_admits_live_routing_is_unavailable(self) -> None:
        async def _payload() -> dict[str, object]:
            return {
                "origin": "Home",
                "destination": "Springfield, VA",
                "parks_historic_radius_miles": 25,
            }

        route_payload = self._json_body(
            asyncio.run(
                self._route("/api/nav/route", "POST")(
                    SimpleNamespace(json=_payload)
                )
            )
        )

        self.assertTrue(route_payload["ok"])
        self.assertFalse(route_payload["available"])
        self.assertTrue(route_payload["persisted"])
        self.assertIn("unavailable", route_payload["message"].lower())
        self.assertIn("saved to shared navigation state only", route_payload["message"].lower())
        self.assertEqual(route_payload["route"]["origin"], "Home")
        self.assertEqual(route_payload["route"]["destination"], "Springfield, VA")

        module_payload = self._json_body(asyncio.run(self._route("/api/navigation/module", "GET")()))
        self.assertTrue(
            any(
                item.get("origin") == "Home" and item.get("destination") == "Springfield, VA"
                for item in module_payload["route_history"]
            )
        )

    def test_catalyst_routes_expose_module_and_live_ops_surfaces(self) -> None:
        module_payload = self._json_body(asyncio.run(self._route("/api/catalyst/module", "GET")()))

        self.assertIn("available", module_payload)
        self.assertIn("counts", module_payload)
        self.assertIn("builder", module_payload)
        self.assertIn("execution", module_payload)
        self.assertIn("governance", module_payload)
        self.assertIn("intervention", module_payload)
        self.assertIn("voice", module_payload)
        self.assertIn("proof_paths", module_payload)
        self.assertEqual(module_payload["proof_paths"]["module_api"], "/api/catalyst/module")
        self.assertEqual(module_payload["proof_paths"]["overview_api"], "/api/catalyst-overview")
        self.assertEqual(module_payload["proof_paths"]["live_state_api"], "/api/catalyst-live-state")
        self.assertEqual(module_payload["proof_paths"]["ops_api"], "/api/apple/catalyst/ops")
        self.assertEqual(module_payload["proof_paths"]["activity_api"], "/api/activity/operator-action")
        self.assertIn("active_workflows", module_payload["counts"])
        self.assertIsInstance(module_payload["builder"], dict)
        self.assertIsInstance(module_payload["execution"], dict)
        self.assertIsInstance(module_payload["voice"], dict)

    def test_forge_routes_expose_module_and_bridge_surfaces(self) -> None:
        class _JSONRequest:
            def __init__(self, payload: dict) -> None:
                self._payload = payload

            async def json(self) -> dict:
                return self._payload

        wow_export = Path(self.tempdir.name) / "wow-export"
        wow_export.mkdir(parents=True, exist_ok=True)
        (wow_export / "paladin.glb").write_bytes(b"glb")

        project_payload = self._json_body(
            asyncio.run(
                self._route("/api/forge/projects", "POST")(
                    _JSONRequest(
                        {
                            "title": "Garage Charger Mount",
                            "description": "Wall mount for garage charger.",
                            "intake_type": "file_upload",
                        }
                    )
                )
            )
        )
        project_id = project_payload["id"]

        asyncio.run(
            self._route("/api/forge/wow/config", "POST")(
                _JSONRequest(
                    {
                        "export_folder": str(wow_export),
                        "wow_install_path": str(wow_export / "wow"),
                        "blender_path": str(wow_export / "blender"),
                    }
                )
            )
        )

        module_payload = self._json_body(
            asyncio.run(self._route("/api/forge/module", "GET")(project_id=project_id))
        )
        wow_status = self._json_body(asyncio.run(self._route("/api/forge/wow/status", "GET")()))
        wow_models = self._json_body(asyncio.run(self._route("/api/forge/wow/models", "GET")()))

        self.assertTrue(module_payload["available"])
        self.assertIn("active_project", module_payload)
        self.assertEqual(module_payload["active_project_id"], project_id)
        self.assertEqual(module_payload["active_project"]["title"], "Garage Charger Mount")
        self.assertIn("capture", module_payload)
        self.assertIn("council", module_payload)
        self.assertIn("pipeline", module_payload)
        self.assertIn("memory", module_payload)
        self.assertIn("manufacturing", module_payload)
        self.assertIn("systems", module_payload)
        self.assertIn("wow", module_payload)
        self.assertIn("convert", module_payload)
        self.assertEqual(module_payload["proof_paths"]["module_api"], "/api/forge/module")
        self.assertEqual(module_payload["proof_paths"]["wow_status_api"], "/api/forge/wow/status")
        self.assertEqual(module_payload["proof_paths"]["convert_format_api"], "/api/forge/convert/format")

        self.assertTrue(wow_status["ok"])
        self.assertTrue(wow_status["export_folder_exists"])
        self.assertTrue(wow_models["ok"])
        self.assertEqual(wow_models["count"], 1)
        self.assertEqual(wow_models["models"][0]["filename"], "paladin.glb")

    def test_workshop_routes_expose_module_and_live_work_surfaces(self) -> None:
        module_payload = self._json_body(asyncio.run(self._route("/api/workshop/module", "GET")()))

        self.assertIn("available", module_payload)
        self.assertIn("counts", module_payload)
        self.assertIn("command_center", module_payload)
        self.assertIn("board", module_payload)
        self.assertIn("work_orders", module_payload)
        self.assertIn("delegation", module_payload)
        self.assertIn("blockers", module_payload)
        self.assertIn("execution_lane", module_payload)
        self.assertIn("intelligence", module_payload)
        self.assertIn("resumption", module_payload)
        self.assertIn("capacity", module_payload)
        self.assertIn("templates", module_payload)
        self.assertIn("quick_actions", module_payload)
        self.assertIn("proof_paths", module_payload)
        self.assertEqual(module_payload["proof_paths"]["module_api"], "/api/workshop/module")
        self.assertEqual(module_payload["proof_paths"]["workshop_projects_api"], "/api/workshop/projects")
        self.assertEqual(module_payload["proof_paths"]["workshop_jobs_api"], "/api/workshop/jobs")
        self.assertEqual(module_payload["proof_paths"]["activity_api"], "/api/activity/operator-action")
        self.assertIsInstance(module_payload["board"]["lanes"], list)
        self.assertGreaterEqual(len(module_payload["board"]["lanes"]), 1)
        self.assertIsInstance(module_payload["templates"], list)
        self.assertIsInstance(module_payload["quick_actions"], list)

    def test_foundry_routes_expose_module_and_live_asset_surfaces(self) -> None:
        module_payload = self._json_body(asyncio.run(self._route("/api/foundry/module", "GET")()))

        self.assertIn("available", module_payload)
        self.assertIn("counts", module_payload)
        self.assertIn("hero", module_payload)
        self.assertIn("pipeline", module_payload)
        self.assertIn("asset_types", module_payload)
        self.assertIn("performance", module_payload)
        self.assertIn("health", module_payload)
        self.assertIn("projects", module_payload)
        self.assertIn("publishing", module_payload)
        self.assertIn("offers", module_payload)
        self.assertIn("audience", module_payload)
        self.assertIn("incubator", module_payload)
        self.assertIn("launch", module_payload)
        self.assertIn("proof_paths", module_payload)
        self.assertEqual(module_payload["proof_paths"]["module_api"], "/api/foundry/module")
        self.assertEqual(module_payload["proof_paths"]["projects_api"], "/api/home/projects?status=active")
        self.assertEqual(module_payload["proof_paths"]["publishing_module_api"], "/api/publish/module")
        self.assertEqual(module_payload["proof_paths"]["ideas_api"], "/api/ideas")
        self.assertEqual(module_payload["proof_paths"]["dossiers_api"], "/api/dossiers")
        self.assertEqual(module_payload["proof_paths"]["activity_api"], "/api/activity/operator-action")
        self.assertIsInstance(module_payload["projects"], list)
        self.assertIsInstance(module_payload["incubator"]["ideas"], list)
        self.assertIsInstance(module_payload["launch"]["checklist"], list)

    def test_home_routes_expose_module_and_live_household_surfaces(self) -> None:
        module_payload = self._json_body(asyncio.run(self._route("/api/home/module", "GET")()))

        self.assertIn("available", module_payload)
        self.assertIn("counts", module_payload)
        self.assertIn("overview", module_payload)
        self.assertIn("agenda", module_payload)
        self.assertIn("environment", module_payload)
        self.assertIn("people", module_payload)
        self.assertIn("queue", module_payload)
        self.assertIn("trusted_actions", module_payload)
        self.assertIn("health", module_payload)
        self.assertIn("modes", module_payload)
        self.assertIn("spaces", module_payload)
        self.assertIn("return_prep", module_payload)
        self.assertIn("insights", module_payload)
        self.assertIn("proof_paths", module_payload)
        self.assertEqual(module_payload["proof_paths"]["module_api"], "/api/home/module")
        self.assertEqual(module_payload["proof_paths"]["overview_api"], "/api/home-overview")
        self.assertEqual(module_payload["proof_paths"]["dashboard_api"], "/api/home/dashboard")
        self.assertEqual(module_payload["proof_paths"]["tasks_today_api"], "/api/home/tasks/today")
        self.assertEqual(module_payload["proof_paths"]["sync_api"], "/api/home/sync")
        self.assertEqual(module_payload["proof_paths"]["operator_activity_api"], "/api/activity/operator-action")
        self.assertIsInstance(module_payload["people"], list)
        self.assertIsInstance(module_payload["queue"], list)
        self.assertIsInstance(module_payload["trusted_actions"], list)

    def test_email_routes_expose_module_and_safe_action_boundary(self) -> None:
        module_payload = self._json_body(asyncio.run(self._route("/api/email/module", "GET")()))

        self.assertIn("available", module_payload)
        self.assertIn("counts", module_payload)
        self.assertIn("emails", module_payload)
        self.assertIn("stats", module_payload)
        self.assertIn("source_rows", module_payload)
        self.assertIn("inbox_overview", module_payload)
        self.assertIn("priority_rows", module_payload)
        self.assertIn("intelligence_cards", module_payload)
        self.assertIn("health_rows", module_payload)
        self.assertIn("categories", module_payload)
        self.assertIn("threads", module_payload)
        self.assertIn("pending_actions", module_payload)
        self.assertIn("automation_rows", module_payload)
        self.assertIn("snoozed_rows", module_payload)
        self.assertIn("compose_actions", module_payload)
        self.assertIn("quick_search_actions", module_payload)
        self.assertIn("trusted_actions", module_payload)
        self.assertIn("proof_paths", module_payload)
        self.assertEqual(module_payload["proof_paths"]["module_route"], "/email-center")
        self.assertEqual(module_payload["proof_paths"]["module_api"], "/api/email/module")
        self.assertEqual(module_payload["proof_paths"]["home_email_api"], "/api/home/email")
        self.assertEqual(module_payload["proof_paths"]["mark_read_api"], "/api/home/email/{email_id}/read")
        self.assertEqual(module_payload["proof_paths"]["sync_api"], "/api/home/sync")
        self.assertEqual(module_payload["proof_paths"]["draft_api"], "/api/stage/email/draft")
        self.assertEqual(module_payload["proof_paths"]["action_api"], "/api/email/module/action")
        self.assertIsInstance(module_payload["emails"], list)
        self.assertIsInstance(module_payload["source_rows"], list)
        self.assertIsInstance(module_payload["trusted_actions"], list)

        action_payload = self._json_body(
            asyncio.run(
                self._route("/api/email/module/action", "POST")(
                    payload={"action": "stage-draft", "prompt": "Draft a short follow-up email about the workshop review."}
                )
            )
        )
        self.assertTrue(action_payload["ok"])
        self.assertEqual(action_payload["action"], "stage-draft")
        self.assertEqual(action_payload["mode"], "review-draft")
        self.assertEqual(action_payload["message"], "Email draft staged for review.")
        self.assertIn("Mailbox-native reply staging", action_payload["boundary_note"])

    def test_news_routes_expose_module_and_safe_action_boundary(self) -> None:
        world_rows = [
            {
                "source": "BBC",
                "title": "AI policy talks intensify across Europe",
                "summary": "Governments are weighing new technology and safety rules this week.",
                "link": "https://example.com/world-1",
            },
            {
                "source": "AP",
                "title": "Storm watch remains active for the region",
                "summary": "Local leaders are tracking weather risk and school timing.",
                "link": "https://example.com/world-2",
            },
        ]
        finance_rows = [
            {
                "source": "BLOOMBERG",
                "title": "Markets steady as inflation cools",
                "summary": "Investors are watching rates, trade, and earnings guidance.",
                "link": "https://example.com/finance-1",
            }
        ]

        with (
            patch("jarvis.rss_briefing.fetch_world_news", return_value=world_rows),
            patch("jarvis.rss_briefing.fetch_finance_news", return_value=finance_rows),
        ):
            module_payload = self._json_body(asyncio.run(self._route("/api/news/module", "GET")()))
            action_payload = self._json_body(
                asyncio.run(
                    self._route("/api/news/module/action", "POST")(
                        payload={
                            "action": "save-article",
                            "title": "Save Top Story",
                            "article_title": "AI policy talks intensify across Europe",
                            "detail": "Record this story for later review.",
                        }
                    )
                )
            )

        self.assertIn("available", module_payload)
        self.assertIn("counts", module_payload)
        self.assertIn("balance", module_payload)
        self.assertIn("sentiment", module_payload)
        self.assertIn("featured_article", module_payload)
        self.assertIn("top_story_list", module_payload)
        self.assertIn("briefing_cards", module_payload)
        self.assertIn("watchlist_rows", module_payload)
        self.assertIn("category_rows", module_payload)
        self.assertIn("insight_rows", module_payload)
        self.assertIn("source_rows", module_payload)
        self.assertIn("weather_rows", module_payload)
        self.assertIn("deep_dive_rows", module_payload)
        self.assertIn("quick_actions", module_payload)
        self.assertIn("trusted_actions", module_payload)
        self.assertIn("proof_paths", module_payload)
        self.assertEqual(module_payload["proof_paths"]["module_route"], "/news-center")
        self.assertEqual(module_payload["proof_paths"]["module_api"], "/api/news/module")
        self.assertEqual(module_payload["proof_paths"]["news_api"], "/api/news")
        self.assertEqual(module_payload["proof_paths"]["weather_api"], "/api/storm-weather")
        self.assertEqual(module_payload["proof_paths"]["action_api"], "/api/news/module/action")
        self.assertEqual(module_payload["counts"]["top_stories"], 3)
        self.assertEqual(module_payload["featured_article"]["title"], "AI policy talks intensify across Europe")
        self.assertTrue(action_payload["ok"])
        self.assertEqual(action_payload["action"], "save-article")
        self.assertEqual(action_payload["message"], "Article saved to shared continuity.")

    def test_legacy_needs_you_and_publishing_alias_module_routes_are_exposed(self) -> None:
        route_expectations = {
            "/api/legacy/module": "/api/chronicle/module",
            "/api/needs-you/module": "/api/progress/module",
            "/api/publishing/module": "/api/publish/module",
        }

        for route, canonical in route_expectations.items():
            payload = self._json_body(asyncio.run(self._route(route, "GET")()))
            self.assertIn("available", payload, msg=route)
            self.assertIn("status", payload, msg=route)
            self.assertIn("proof_paths", payload, msg=route)
            self.assertEqual(payload["proof_paths"]["module_api"], canonical, msg=route)

    def test_faith_module_exposes_standard_surface_metadata(self) -> None:
        payload = self._json_body(asyncio.run(self._route("/api/faith/module", "GET")()))

        self.assertTrue(payload["ok"])
        self.assertIn("available", payload)
        self.assertIn("status", payload)
        self.assertIn("summary", payload)
        self.assertIn("runtime_note", payload)
        self.assertIn("what_became_real", payload)
        self.assertIn("remains_partial", payload)
        self.assertIn("daily_word", payload)
        self.assertIn("agents", payload)
        self.assertIn("continuity", payload)

    def test_shell_backed_experiences_expose_direct_entry_routes(self) -> None:
        routes = {
            "/home-center": "window.__JARVIS_START_VIEW = 'home'",
            "/calendar-center": "window.__JARVIS_START_VIEW = 'calendar'",
            "/email-center": "window.__JARVIS_START_VIEW = 'email'",
            "/news-center": "window.__JARVIS_START_VIEW = 'news'",
            "/social-center": "window.__JARVIS_START_VIEW = 'social'",
            "/legacy-center": "window.__JARVIS_START_VIEW = 'chronicle'",
            "/faith-center": "window.__JARVIS_START_VIEW = 'faith'",
            "/agents-center": "window.__JARVIS_START_VIEW = 'agents'",
            "/intel-center": "window.__JARVIS_START_VIEW = 'intelligence'",
            "/forge-center": "window.__JARVIS_START_VIEW = 'forge'",
            "/catalyst-center": "window.__JARVIS_START_VIEW = 'catalyst'",
            "/foundry-center": "window.__JARVIS_START_VIEW = 'foundry'",
            "/workshop-center": "window.__JARVIS_START_VIEW = 'workshop'",
            "/vision-center": "window.__JARVIS_START_VIEW = 'vision'",
            "/journey-center": "window.__JARVIS_START_VIEW = 'journey'",
            "/needs-you-center": "window.__JARVIS_START_VIEW = 'notifications'",
        }

        for path, marker in routes.items():
            response = asyncio.run(self._route(path, "GET")())
            html = self._text_body(response)
            self.assertIn(marker, html, msg=path)
            self.assertIn("JARVIS", html, msg=path)

    def test_shell_backed_experiences_expose_alias_entry_routes(self) -> None:
        routes = {
            "/agents": "window.__JARVIS_START_VIEW = 'agents'",
            "/forge": "window.__JARVIS_START_VIEW = 'forge'",
            "/foundry": "window.__JARVIS_START_VIEW = 'foundry'",
            "/workshop": "window.__JARVIS_START_VIEW = 'workshop'",
            "/vision": "window.__JARVIS_START_VIEW = 'vision'",
            "/journey": "window.__JARVIS_START_VIEW = 'journey'",
        }

        for path, marker in routes.items():
            response = asyncio.run(self._route(path, "GET")())
            html = self._text_body(response)
            self.assertIn(marker, html, msg=path)
            self.assertIn("JARVIS", html, msg=path)

    def test_social_routes_expose_module_and_safe_action_boundary(self) -> None:
        module_payload = self._json_body(asyncio.run(self._route("/api/social/module", "GET")()))

        self.assertIn("available", module_payload)
        self.assertIn("counts", module_payload)
        self.assertIn("headline_stats", module_payload)
        self.assertIn("sidebar_counts", module_payload)
        self.assertIn("platform_rows", module_payload)
        self.assertIn("mini_stats", module_payload)
        self.assertIn("calendar_rows", module_payload)
        self.assertIn("performance_rows", module_payload)
        self.assertIn("inbox_rows", module_payload)
        self.assertIn("pipeline_rows", module_payload)
        self.assertIn("audience", module_payload)
        self.assertIn("theme_rows", module_payload)
        self.assertIn("health", module_payload)
        self.assertIn("sentiment_rows", module_payload)
        self.assertIn("recommendation_rows", module_payload)
        self.assertIn("security_rows", module_payload)
        self.assertIn("summary_cards", module_payload)
        self.assertIn("footer_rows", module_payload)
        self.assertIn("trusted_actions", module_payload)
        self.assertIn("quick_actions", module_payload)
        self.assertIn("proof_paths", module_payload)
        self.assertEqual(module_payload["proof_paths"]["module_route"], "/social-center")
        self.assertEqual(module_payload["proof_paths"]["module_api"], "/api/social/module")
        self.assertEqual(module_payload["proof_paths"]["publishing_projects_api"], "/api/publishing/projects")
        self.assertEqual(module_payload["proof_paths"]["publishing_social_api"], "/api/publishing/social/posts")
        self.assertEqual(module_payload["proof_paths"]["social_pending_api"], "/api/social/posts/pending")
        self.assertEqual(module_payload["proof_paths"]["social_approve_api"], "/api/social/post/approve/{post_id}")
        self.assertEqual(module_payload["proof_paths"]["social_execute_api"], "/api/social/execute")
        self.assertEqual(module_payload["proof_paths"]["action_api"], "/api/social/module/action")
        self.assertIsInstance(module_payload["platform_rows"], list)
        self.assertIsInstance(module_payload["trusted_actions"], list)

        action_payload = self._json_body(
            asyncio.run(
                self._route("/api/social/module/action", "POST")(
                    payload={
                        "action": "create-post",
                        "platform": "linkedin",
                        "content": "A short social post drafted from the Social Media desktop test.",
                    }
                )
            )
        )
        self.assertTrue(action_payload["ok"])
        self.assertEqual(action_payload["action"], "create-post")
        self.assertEqual(action_payload["message"], "Social post draft created.")
        self.assertEqual(action_payload["post"]["platform"], "linkedin")

    def test_calendar_routes_expose_module_and_safe_action_boundary(self) -> None:
        module_payload = self._json_body(asyncio.run(self._route("/api/calendar/module", "GET")()))

        self.assertIn("available", module_payload)
        self.assertIn("counts", module_payload)
        self.assertIn("today_payload", module_payload)
        self.assertIn("upcoming_payload", module_payload)
        self.assertIn("workflow", module_payload)
        self.assertIn("source_rows", module_payload)
        self.assertIn("trusted_actions", module_payload)
        self.assertIn("proof_paths", module_payload)
        self.assertIn("local_today", module_payload)
        self.assertEqual(module_payload["proof_paths"]["module_route"], "/calendar-center")
        self.assertEqual(module_payload["proof_paths"]["module_api"], "/api/calendar/module")
        self.assertEqual(module_payload["proof_paths"]["today_api"], "/api/home/calendar/today")
        self.assertEqual(module_payload["proof_paths"]["upcoming_api"], "/api/home/calendar/upcoming?days=7")
        self.assertEqual(module_payload["proof_paths"]["workflow_api"], "/api/apple/calendar/state")
        self.assertEqual(module_payload["proof_paths"]["sync_api"], "/api/home/sync")
        self.assertEqual(module_payload["proof_paths"]["action_api"], "/api/calendar/module/action")
        self.assertIsInstance(module_payload["trusted_actions"], list)
        self.assertIsInstance(module_payload["source_rows"], list)
        self.assertIn("runtime_note", module_payload)
        self.assertIn("availability_notes", module_payload)
        expected_local_today = (
            self.runtime._local_now().date().isoformat()
            if hasattr(self.runtime, "_local_now")
            else datetime.now().astimezone().date().isoformat()
        )
        self.assertEqual(module_payload["today_payload"]["date"], expected_local_today)
        self.assertEqual(module_payload["local_today"], expected_local_today)
        if (
            not module_payload["today_payload"].get("events")
            and not module_payload["upcoming_payload"].get("events")
            and not module_payload["source_rows"]
            and module_payload["availability_notes"]
        ):
            self.assertEqual(module_payload["runtime_note"], module_payload["availability_notes"][0])

        action_payload = self._json_body(
            asyncio.run(
                self._route("/api/calendar/module/action", "POST")(
                    payload={"action": "focus-block", "prompt": "Block off time for focus work tomorrow at 9am on my calendar"}
                )
            )
        )
        self.assertTrue(action_payload["ok"])
        self.assertEqual(action_payload["action"], "focus-block")
        self.assertIn("Stub calendar write handled", action_payload["message"])

    def test_dining_routes_expose_module_and_live_search_surfaces(self) -> None:
        nearby_rows = [
            {
                "place_id": "place-1",
                "name": "River Sushi",
                "address": "1 Main St, Cincinnati, OH",
                "rating": 4.7,
                "review_count": 812,
                "price": "$$$",
                "open_now": True,
                "distance_mi": 4.2,
                "lat": 39.1031,
                "lng": -84.5120,
                "types": ["restaurant", "japanese_restaurant"],
                "photo_ref": "",
            },
            {
                "place_id": "place-2",
                "name": "Skyline Patio Grill",
                "address": "50 View Ave, Covington, KY",
                "rating": 4.4,
                "review_count": 391,
                "price": "$$",
                "open_now": False,
                "distance_mi": 6.1,
                "lat": 39.0837,
                "lng": -84.5086,
                "types": ["restaurant", "bar"],
                "photo_ref": "",
            },
        ]
        favorites = [
            {
                "place_id": "place-1",
                "name": "River Sushi",
                "address": "1 Main St, Cincinnati, OH",
                "rating": 4.7,
            }
        ]
        recommend_packet = {
            "meal_type": "dinner",
            "open_now_filter": True,
            "goals": "Protein forward",
            "allergies": [],
            "sam_context": "Top dinner picks near you right now.",
            "recommendations": [nearby_rows[0]],
        }

        with (
            patch.object(dining_module, "nearby_restaurants", return_value=nearby_rows),
            patch.object(dining_module, "recommend_restaurants", return_value=recommend_packet),
            patch.object(dining_module, "get_favorites", return_value=favorites),
        ):
            dining_response = asyncio.run(
                self._route("/dining-center", "GET")(
                    query="sushi with a view",
                    cuisine="japanese",
                    open_now=True,
                    prefs="view,4.0+",
                    quick_filter="best",
                )
            )
            dining_api_response = asyncio.run(
                self._route("/api/dining/module", "GET")(
                    query="sushi with a view",
                    cuisine="japanese",
                    open_now=True,
                    prefs="view,4.0+",
                    quick_filter="best",
                    limit=8,
                )
            )
            nearby_response = asyncio.run(
                self._route("/api/dining/nearby", "GET")(
                    cuisine="japanese",
                    open_now=True,
                    min_rating=4.0,
                    radius_miles=10.0,
                    limit=8,
                    query="sushi with a view",
                    prefs="view,4.0+",
                )
            )

        dining_html = self._text_body(dining_response)
        dining_snapshot = self._json_body(dining_api_response)
        nearby_snapshot = self._json_body(nearby_response)

        self.assertIn("JARVIS Dining", dining_html)
        self.assertIn("Favorite Signals", dining_html)
        self.assertIn("Reservation Coordination", dining_html)
        self.assertIn("Recent Dining Continuity", dining_html)
        self.assertIn("available", dining_snapshot)
        self.assertIn("runtime_note", dining_snapshot)
        self.assertIn("availability_notes", dining_snapshot)
        self.assertIn("counts", dining_snapshot)
        self.assertIn("results", dining_snapshot)
        self.assertIn("favorites", dining_snapshot)
        self.assertIn("reservation_partner", dining_snapshot)
        self.assertIn("recent_searches", dining_snapshot)
        self.assertIn("recent_reservation_intents", dining_snapshot)
        self.assertIn("proof_paths", dining_snapshot)
        self.assertEqual(dining_snapshot["proof_paths"]["module_route"], "/dining-center")
        self.assertEqual(dining_snapshot["proof_paths"]["module_api"], "/api/dining/module")
        self.assertEqual(dining_snapshot["proof_paths"]["favorite_api"], "/api/dining/favorite")
        self.assertEqual(dining_snapshot["proof_paths"]["reservation_intent_api"], "/api/dining/reservation-intent")
        self.assertEqual(dining_snapshot["counts"]["favorites"], 1)
        self.assertEqual(len(dining_snapshot["results"]), 2)
        self.assertEqual(dining_snapshot["selected_place"]["name"], "River Sushi")
        self.assertEqual(nearby_snapshot["count"], 2)
        self.assertTrue(all("match_score" in item for item in nearby_snapshot["restaurants"]))

    def test_open_loop_action_populates_daily_brief_continuity(self) -> None:
        self.runtime.apply_open_loop_action = lambda actor_name, **kwargs: {
            "ok": True,
            "actor": actor_name,
            "domain": kwargs.get("domain", ""),
            "item_id": kwargs.get("item_id", ""),
            "action": kwargs.get("action", ""),
            "record": {"status": "deferred"},
            "open_loops": {"items": []},
        }
        self.runtime.shell_state_snapshot = lambda: {}
        self.runtime.dashboard_snapshot = lambda: {}

        response = asyncio.run(
            self._route("/api/open-loops/action", "POST")(
                {
                    "actor": "Chris",
                    "domain": "family",
                    "item_id": "draft-1",
                    "action": "defer-1d",
                    "item_title": "Confirm family note",
                    "item_summary": "Need to defer this until tomorrow.",
                    "route": "/briefing-center",
                    "route_label": "Open Daily Brief",
                    "activity_domain": "briefing",
                    "why_now": "Daily Brief follow-through moved a live open-loop item forward.",
                    "result_summary": "Daily Brief continuity updated from an open-loop action.",
                    "related_kind": "open-loop",
                    "related_label": "Confirm family note",
                }
            )
        )
        result_payload = self._json_body(response)
        self.assertTrue(result_payload["ok"])

        activity_payload = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))
        briefing_snapshot = self._json_body(asyncio.run(self._route("/api/briefing/module", "GET")()))

        self.assertTrue(any(item.get("related_route") == "/briefing-center" for item in activity_payload))
        self.assertTrue(any(item.get("related_kind") == "open-loop" for item in activity_payload))
        self.assertTrue(any(item.get("title") == "Defer 1D" for item in briefing_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_label") == "Confirm family note" for item in briefing_snapshot["recent_activity"]))

    def test_progress_focus_mutation_persists_into_progress_and_activity(self) -> None:
        response = asyncio.run(
            self._route("/api/progress/focus", "POST")(
                {
                    "actor": "Chris",
                    "module": "Recovery",
                    "reason": "Recovery is the highest-risk remaining Level 3 seam.",
                    "route": "/progress-center",
                }
            )
        )
        focus_payload = self._json_body(response)
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))
        activity_payload = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))

        self.assertEqual(focus_payload["status"], "recorded")
        self.assertEqual(focus_payload["focus"]["module"], "Recovery")
        self.assertEqual(progress_snapshot["progress_next_focus"], "Recovery")
        self.assertEqual(progress_snapshot["focus_control"]["latest"]["module"], "Recovery")
        self.assertTrue(any(item.get("title") == "Set Progress Focus" for item in activity_payload))
        self.assertTrue(any(item.get("related_label") == "Recovery" for item in activity_payload))
        self.assertTrue(any(item.get("related_kind") == "progress-focus" for item in activity_payload))

    def test_progress_seam_mutation_persists_into_progress_and_activity(self) -> None:
        progress_snapshot = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))
        seam_item = next(item for item in progress_snapshot["seam_tracker"]["items"] if item.get("name") == "Progress Module Standalone Surface")
        mission = (seam_item.get("related_missions") or [])[0]

        response = asyncio.run(
            self._route("/api/progress/seams/{seam_name}", "POST")(
                "Progress Module Standalone Surface",
                {
                    "actor": "Chris",
                    "module": seam_item["module"],
                    "status": "Durable",
                    "note": "Progress seam is now durable and pinned to the hosted closure mission.",
                    "mission_id": mission.get("mission_id"),
                    "mission_title": mission.get("title"),
                    "mission_lane": mission.get("lane"),
                    "mission_route": mission.get("route"),
                }
            )
        )
        seam_payload = self._json_body(response)
        refreshed_progress = self._json_body(asyncio.run(self._route("/api/progress/module", "GET")()))
        activity_payload = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))

        self.assertEqual(seam_payload["status"], "recorded")
        self.assertEqual(seam_payload["seam"]["status"], "Durable")
        self.assertEqual(seam_payload["seam"]["linked_mission"]["mission_id"], mission.get("mission_id"))
        self.assertEqual(seam_payload["focus"]["module"], seam_item["module"])

        updated_seam = next(item for item in refreshed_progress["seam_tracker"]["items"] if item.get("name") == "Progress Module Standalone Surface")
        self.assertEqual(updated_seam["status"], "Durable")
        self.assertEqual(updated_seam["related_missions"][0]["mission_id"], mission.get("mission_id"))
        self.assertTrue(any(item.get("name") == "Progress Module Standalone Surface" for item in refreshed_progress["seam_persistence"]["records"]))
        self.assertTrue(any(item.get("related_kind") == "progress-seam" for item in activity_payload))
        self.assertTrue(any(item.get("related_label") == "Progress Module Standalone Surface" for item in activity_payload))

    def test_dexcom_routes_are_registered_and_use_live_base_url(self) -> None:
        from jarvis import dexcom_sync

        status_endpoint = self._route("/api/health/dexcom/status", "GET")
        connect_endpoint = self._route("/api/health/dexcom/connect", "GET")
        callback_endpoint = self._route("/api/health/dexcom/callback", "GET")
        current_endpoint = self._route("/api/health/dexcom/current", "GET")
        sync_endpoint = self._route("/api/health/dexcom/sync", "POST")

        request = service_module.Request("https://jarvis.teambinion.org/")

        with patch.object(dexcom_sync, "get_connection_status", return_value={"connected": False, "configured": True, "message": "Not connected"}), patch.object(
            dexcom_sync,
            "build_auth_url",
            return_value="https://api.dexcom.com/v3/oauth2/login?client_id=test",
        ) as build_auth_url, patch.object(
            dexcom_sync,
            "exchange_code",
            new=unittest.mock.AsyncMock(return_value={"access_token": "token"}),
        ) as exchange_code, patch.object(
            dexcom_sync,
            "get_current_reading",
            new=unittest.mock.AsyncMock(return_value={"glucose_mgdl": 120}),
        ), patch.object(
            dexcom_sync,
            "sync_egvs",
            new=unittest.mock.AsyncMock(return_value={"ok": True, "count": 3}),
        ):
            status_response = asyncio.run(status_endpoint())
            connect_response = asyncio.run(connect_endpoint(request))
            callback_html = asyncio.run(callback_endpoint(request, code="abc123"))
            current_response = asyncio.run(current_endpoint())
            sync_response = asyncio.run(sync_endpoint())

        status_body = self._json_body(status_response)
        current_body = self._json_body(current_response)
        sync_body = self._json_body(sync_response)

        self.assertTrue(status_body["ok"])
        self.assertTrue(status_body["configured"])
        self.assertEqual(build_auth_url.call_args.args[0], "https://jarvis.teambinion.org/api/health/dexcom/callback")
        self.assertEqual(getattr(connect_response, "status_code", None), 302)
        self.assertIn("Dexcom connected", callback_html)
        exchange_code.assert_awaited_once_with("abc123", "https://jarvis.teambinion.org/api/health/dexcom/callback")
        self.assertEqual(current_body["current"]["glucose_mgdl"], 120)
        self.assertTrue(sync_body["ok"])
        self.assertEqual(sync_body["count"], 3)

    def test_kdp_routes_support_credentials_sync_and_2fa_submission(self) -> None:
        from jarvis import kdp_scraper, kdp_store

        class _JSONRequest:
            def __init__(self, payload: dict) -> None:
                self._payload = payload

            async def json(self) -> dict:
                return self._payload

        credentials_get = self._route("/api/kdp/credentials", "GET")
        credentials_post = self._route("/api/kdp/credentials", "POST")
        sync_endpoint = self._route("/api/kdp/sync", "POST")
        sync_status_endpoint = self._route("/api/kdp/sync-status", "GET")
        two_factor_endpoint = self._route("/api/kdp/2fa-code", "POST")

        with (
            patch.object(kdp_store, "load_sync_meta", return_value={"last_synced_at": "2026-06-10T05:00:00+00:00", "book_count": 2, "status": "synced"}),
            patch.object(kdp_scraper, "save_credentials") as save_credentials,
            patch.object(kdp_scraper, "sync", new=unittest.mock.AsyncMock(return_value={"ok": True, "started": True, "status": "running"})),
            patch.object(kdp_scraper, "get_sync_state", return_value={"status": "needs_2fa", "running": True, "needs_2fa": True, "last_error": None}),
            patch.object(kdp_scraper, "submit_2fa_code", new=unittest.mock.AsyncMock(return_value=True)) as submit_code,
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.stat", return_value=SimpleNamespace(st_size=32)),
        ):
            credentials_body = self._json_body(asyncio.run(credentials_get()))
            save_body = self._json_body(asyncio.run(credentials_post(_JSONRequest({"email": "author@example.com", "password": "secret"}))))
            sync_body = self._json_body(asyncio.run(sync_endpoint()))
            sync_status_body = self._json_body(asyncio.run(sync_status_endpoint()))
            two_factor_body = self._json_body(asyncio.run(two_factor_endpoint(_JSONRequest({"code": "123456"}))))

        self.assertTrue(credentials_body["configured"])
        save_credentials.assert_called_once_with("author@example.com", "secret")
        self.assertTrue(save_body["ok"])
        self.assertTrue(sync_body["started"])
        self.assertEqual(sync_status_body["status"], "needs_2fa")
        self.assertTrue(sync_status_body["needs_2fa"])
        submit_code.assert_awaited_once_with("123456")
        self.assertTrue(two_factor_body["ok"])

    def test_finance_routes_support_manual_and_plaid_connectors(self) -> None:
        from jarvis.financial_intelligence import Account, Transaction

        store = SimpleNamespace(
            load_accounts=lambda: [
                Account(
                    account_id="manual-acct",
                    name="Checking",
                    account_type="checking",
                    institution="Local Bank",
                    balance=2500.0,
                    currency="USD",
                    last_updated="2026-06-10T00:00:00+00:00",
                    is_manual=True,
                ),
                Account(
                    account_id="plaid:acct-1",
                    name="Linked Brokerage",
                    account_type="investment",
                    institution="Fidelity",
                    balance=5000.0,
                    currency="USD",
                    last_updated="2026-06-10T00:00:00+00:00",
                    is_manual=False,
                ),
            ],
            upsert_account=lambda account: None,
            delete_account=lambda account_id: account_id == "manual-acct",
            load_streams=lambda: [],
            delete_stream=lambda stream_id: True,
            load_goals=lambda: [],
            delete_goal=lambda goal_id: True,
        )
        plaid = SimpleNamespace(
            status=lambda: {"available": True, "configured": True, "connected": False, "detail": "Ready", "item_count": 0, "linked_account_count": 1},
            create_link_token=lambda user_id="chris": {"ok": True, "available": True, "link_token": "link-token"},
            exchange_public_token=lambda **kwargs: {"ok": True, "available": True, "item_id": "item-1", "imported_accounts": 1, "imported_transactions": 2},
            sync_all=lambda: {"ok": True, "available": True, "synced_items": 1, "imported_accounts": 1, "imported_transactions": 2},
        )
        finance = SimpleNamespace(
            _store=store,
            plaid=plaid,
        )

        with patch("jarvis.financial_intelligence.get_finance", return_value=finance):
            accounts_body = self._json_body(asyncio.run(self._route("/api/finance/accounts", "GET")()))
            create_body = self._json_body(asyncio.run(self._route("/api/finance/accounts", "POST")({"name": "Savings", "account_type": "savings", "institution": "Marcus", "balance": 1000})))
            delete_body = self._json_body(asyncio.run(self._route("/api/finance/accounts/{account_id}", "DELETE")("manual-acct")))
            plaid_status = self._json_body(asyncio.run(self._route("/api/finance/plaid/status", "GET")()))
            link_token = self._json_body(asyncio.run(self._route("/api/finance/plaid/link-token", "POST")()))
            exchange = self._json_body(asyncio.run(self._route("/api/finance/plaid/exchange-public-token", "POST")({"public_token": "public-123", "institution_name": "Plaid Bank"})))
            sync = self._json_body(asyncio.run(self._route("/api/finance/plaid/sync", "POST")()))

        self.assertEqual(len(accounts_body), 2)
        self.assertEqual(create_body["account"]["name"], "Savings")
        self.assertTrue(delete_body["ok"])
        self.assertTrue(plaid_status["configured"])
        self.assertEqual(link_token["link_token"], "link-token")
        self.assertEqual(exchange["item_id"], "item-1")
        self.assertEqual(sync["synced_items"], 1)


if __name__ == "__main__":
    unittest.main()
