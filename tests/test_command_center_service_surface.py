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

    class _Response(_JSONResponse):
        pass

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


class _StubRuntime:
    def __init__(self) -> None:
        self.config = SimpleNamespace(
            tts_provider="auto",
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
            "selected_agents": ["ambient-router", "storm"],
            "task_agent_labels": ["Mission Planner"],
            "work_state_summary": {
                "agents": 2,
                "active_tasks": 1,
                "blocked_tasks": 0,
                "pending_reviews": 1,
                "pending_handoffs": 0,
                "pending_transfers": 0,
                "escalations": 0,
                "duplicate_suppressions": 0,
            },
        }

    def mission_work_state_snapshot(self, mission_id: str) -> dict:
        return {
            "mission_id": mission_id,
            "summary": {
                "agents": 2,
                "active_tasks": 1,
                "blocked_tasks": 0,
                "pending_reviews": 1,
                "pending_handoffs": 0,
                "pending_transfers": 0,
                "escalations": 0,
                "duplicate_suppressions": 0,
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
            "handoffs": [],
            "escalations": [],
            "duplicate_suppressions": [],
        }

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
        self.assertIn("status", briefing_snapshot)
        self.assertIn("briefing_text", briefing_snapshot)
        self.assertIn("today_board", briefing_snapshot)
        self.assertIn("open_loops", briefing_snapshot)
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
        self.assertIn("Mission Workspaces", mission_board_html)
        self.assertIn("Handoff Console", mission_board_html)
        self.assertIn("Create Handoff", mission_board_html)
        self.assertIn("Accept Handoff", mission_board_html)
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
        self.assertIn("/api/activity/operator-action", mission_board_html)
        self.assertIn("createMission()", mission_board_html)
        self.assertIn("updateMissionDetails", mission_board_html)
        self.assertIn("Related Seam:", mission_board_html)
        self.assertIn("recordMissionActivity", mission_board_html)
        self.assertIn("createMissionHandoff", mission_board_html)
        self.assertIn("acknowledgeMissionHandoff", mission_board_html)
        self.assertIn("recorded in shared activity", mission_board_html)
        self.assertIn("status", mission_board_snapshot)
        self.assertIn("mission_task_board", mission_board_snapshot)
        self.assertIn("mission_details", mission_board_snapshot)
        self.assertIn("recent_activity", mission_board_snapshot)
        self.assertIn("recent_activity_count", mission_board_snapshot["counts"])
        self.assertTrue(any("work_state" in detail for detail in mission_board_snapshot["mission_details"].values()))
        self.assertIn("proof_paths", mission_board_snapshot)
        self.assertEqual(mission_board_snapshot["proof_paths"]["module_route"], "/mission-board")
        self.assertEqual(mission_board_snapshot["proof_paths"]["module_api"], "/api/mission-board/module")
        self.assertEqual(mission_board_snapshot["proof_paths"]["mission_create_api"], "/api/missions")
        self.assertEqual(mission_board_snapshot["proof_paths"]["mission_edit_api_suffix"], "/edit")
        self.assertEqual(mission_board_snapshot["proof_paths"]["mission_handoff_api_suffix"], "/handoffs")
        self.assertEqual(mission_board_snapshot["proof_paths"]["mission_handoff_ack_suffix"], "/handoffs/{handoff_id}/acknowledge")
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

    def test_home_dashboard_returns_honest_unavailable_payload_when_db_errors(self) -> None:
        route = self._route("/api/home/dashboard", "GET")

        with patch.object(service_module, "_get_home_db", return_value=_FailingHomeDashboardDB()):
            response = asyncio.run(route())

        payload = self._json_body(response)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(payload["available"])
        self.assertIn("Home dashboard unavailable", payload["error"])
        self.assertIn("postgres unavailable", payload["error"])

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
        expected_local_today = (
            self.runtime._local_now().date().isoformat()
            if hasattr(self.runtime, "_local_now")
            else datetime.now().astimezone().date().isoformat()
        )
        self.assertEqual(module_payload["today_payload"]["date"], expected_local_today)
        self.assertEqual(module_payload["local_today"], expected_local_today)

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


if __name__ == "__main__":
    unittest.main()
