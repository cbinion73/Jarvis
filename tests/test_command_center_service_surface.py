from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import jarvis.approvals as approvals_module
import jarvis.command_center_index as command_center_index_module
import jarvis.quarterly_review as quarterly_review_module
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
        self.assertIn("Recovery Continuity", supervision_html)
        self.assertIn("Recent Supervision Continuity", supervision_html)
        self.assertIn("/api/activity/operator-action", supervision_html)
        self.assertIn("status", supervision_snapshot)
        self.assertIn("attention_queue", supervision_snapshot)
        self.assertIn("integrations", supervision_snapshot)
        self.assertIn("recovery_bridge", supervision_snapshot)
        self.assertIn("recent_activity", supervision_snapshot)
        self.assertIn("recent_activity_count", supervision_snapshot["counts"])
        self.assertIn("proof_paths", supervision_snapshot)
        self.assertEqual(supervision_snapshot["proof_paths"]["module_route"], "/supervision-snapshot")
        self.assertEqual(supervision_snapshot["proof_paths"]["module_api"], "/api/supervision/module")
        self.assertEqual(supervision_snapshot["proof_paths"]["recovery_action_api"], "/api/recovery/action")
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
        self.assertIn("focus_control", progress_snapshot)
        self.assertIn("history_count", progress_snapshot["counts"])
        self.assertIn("focus_history_count", progress_snapshot["counts"])
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
        self.assertIn("/api/recovery/action", recovery_html)
        self.assertIn("status", recovery_snapshot)
        self.assertIn("failure_recovery", recovery_snapshot)
        self.assertIn("pending_approvals", recovery_snapshot)
        self.assertIn("recovery_actions", recovery_snapshot)
        self.assertIn("recovery_cases", recovery_snapshot)
        self.assertIn("recorded_recovery_actions", recovery_snapshot["counts"])
        self.assertIn("recovery_case_count", recovery_snapshot["counts"])
        self.assertIn("recovery_case_execution_count", recovery_snapshot["counts"])
        self.assertIn("proof_paths", recovery_snapshot)
        self.assertEqual(recovery_snapshot["proof_paths"]["module_route"], "/recovery-center")
        self.assertEqual(recovery_snapshot["proof_paths"]["module_api"], "/api/recovery/module")
        self.assertEqual(recovery_snapshot["proof_paths"]["recovery_action_api"], "/api/recovery/action")
        self.assertEqual(recovery_snapshot["proof_paths"]["recovery_case_execute_suffix"], "/execute")
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
        self.assertIn("Shared Progress Focus", activity_html)
        self.assertIn("/progress-center", activity_html)
        self.assertIn("Home Continuity", activity_html)
        self.assertIn("status", activity_snapshot)
        self.assertIn("activity_feed", activity_snapshot)
        self.assertIn("action_journal", activity_snapshot)
        self.assertIn("home_action_result", activity_snapshot)
        self.assertIn("focus_control", activity_snapshot)
        self.assertIn("progress_next_focus", activity_snapshot)
        self.assertIn("home_bridge_count", activity_snapshot["counts"])
        self.assertIn("focus_history_count", activity_snapshot["counts"])
        self.assertTrue(any(item.get("entry_type") == "progress-snapshot" for item in activity_snapshot["activity_feed"]))
        self.assertIn("proof_paths", activity_snapshot)
        self.assertEqual(activity_snapshot["proof_paths"]["module_route"], "/activity-center")
        self.assertEqual(activity_snapshot["proof_paths"]["module_api"], "/api/activity/module")
        self.assertEqual(activity_snapshot["proof_paths"]["activity_focus_api"], "/api/activity/module/focus")
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
        self.assertIn("Living story engine", chronicle_html)
        self.assertIn("Chronicle tracks", chronicle_html)
        self.assertIn("Recent Chronicle Continuity", chronicle_html)
        self.assertIn("/api/activity/operator-action", chronicle_html)

        self.assertIn("status", chronicle_snapshot)
        self.assertIn("timeline", chronicle_snapshot)
        self.assertIn("recent_activity", chronicle_snapshot)
        self.assertIn("proof_paths", chronicle_snapshot)
        self.assertEqual(chronicle_snapshot["proof_paths"]["module_route"], "/chronicle-center")
        self.assertEqual(chronicle_snapshot["proof_paths"]["module_api"], "/api/chronicle/module")
        self.assertIn("JARVIS Navigation", navigation_html)
        self.assertIn("Preview Route Intelligence", navigation_html)
        self.assertIn("Navigation Command Center", navigation_html)
        self.assertIn("Concept Storyboard", navigation_html)
        self.assertIn("Stop Detail &amp; Route Modification", navigation_html)
        self.assertIn("Recent Route Continuity", navigation_html)
        self.assertIn("/api/activity/operator-action", navigation_html)
        self.assertIn("status", navigation_snapshot)
        self.assertIn("navigation_state", navigation_snapshot)
        self.assertIn("recent_activity", navigation_snapshot)
        self.assertIn("proof_paths", navigation_snapshot)
        self.assertEqual(navigation_snapshot["proof_paths"]["module_route"], "/navigation-center")
        self.assertEqual(navigation_snapshot["proof_paths"]["module_api"], "/api/navigation/module")
        self.assertIn("JARVIS Publish", publish_html)
        self.assertIn("Quick Draft Project", publish_html)
        self.assertIn("Editorial Review Lane", publish_html)
        self.assertIn("Refresh Publish State", publish_html)
        self.assertIn("Launch Ops Hub", publish_html)
        self.assertIn("Recent Publish Continuity", publish_html)
        self.assertIn("status", publish_snapshot)
        self.assertIn("projects", publish_snapshot)
        self.assertIn("pending_reviews", publish_snapshot)
        self.assertIn("recent_activity", publish_snapshot)
        self.assertIn("proof_paths", publish_snapshot)
        self.assertEqual(publish_snapshot["proof_paths"]["module_route"], "/publish")
        self.assertEqual(publish_snapshot["proof_paths"]["module_api"], "/api/publish/module")
        self.assertIn("JARVIS Settings", settings_html)
        self.assertIn("Save Voice Settings", settings_html)
        self.assertIn("Save Location Settings", settings_html)
        self.assertIn("Recent Settings Continuity", settings_html)
        self.assertIn("status", settings_snapshot)
        self.assertIn("voice", settings_snapshot)
        self.assertIn("location", settings_snapshot)
        self.assertIn("recent_activity", settings_snapshot)
        self.assertIn("recent_activity_count", settings_snapshot["counts"])
        self.assertIn("proof_paths", settings_snapshot)
        self.assertEqual(settings_snapshot["proof_paths"]["module_route"], "/settings-center")
        self.assertEqual(settings_snapshot["proof_paths"]["module_api"], "/api/settings/module")
        self.assertIn("JARVIS Huddle", huddle_html)
        self.assertIn("Start Overnight Research", huddle_html)
        self.assertIn("Capture Huddle Idea", huddle_html)
        self.assertIn("Agent Council Chamber", huddle_html)
        self.assertIn("Recent Huddle Continuity", huddle_html)
        self.assertIn("/api/activity/operator-action", huddle_html)
        self.assertIn("status", huddle_snapshot)
        self.assertIn("reports", huddle_snapshot)
        self.assertIn("recent_activity", huddle_snapshot)
        self.assertIn("proof_paths", huddle_snapshot)
        self.assertEqual(huddle_snapshot["proof_paths"]["module_route"], "/huddle-center")
        self.assertEqual(huddle_snapshot["proof_paths"]["module_api"], "/api/huddle/module")
        self.assertIn("JARVIS Health", health_html)
        self.assertIn("Symptom Triage", health_html)
        self.assertIn("Refresh Health State", health_html)
        self.assertIn("Health command center", health_html)
        self.assertIn("Daily Readiness", health_html)
        self.assertIn("Save Health Objective", health_html)
        self.assertIn("Recent Health Continuity", health_html)
        self.assertIn("/api/activity/operator-action", health_html)
        self.assertIn("status", health_snapshot)
        self.assertIn("current_signals", health_snapshot)
        self.assertIn("recent_activity", health_snapshot)
        self.assertIn("proof_paths", health_snapshot)
        self.assertEqual(health_snapshot["proof_paths"]["module_route"], "/health-center")
        self.assertEqual(health_snapshot["proof_paths"]["module_api"], "/api/health/module")

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
        self.assertEqual(publish_snapshot["pending_reviews_count"], 0)
        self.assertTrue(any(item.get("title") == "Approve Publish Review" for item in publish_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_label") == "Approve launch chapter" for item in publish_snapshot["recent_activity"]))
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

    def test_settings_mutations_persist_into_settings_and_activity(self) -> None:
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

        voice_payload = self._json_body(voice_response)
        location_payload = self._json_body(location_response)
        settings_snapshot = self._json_body(asyncio.run(self._route("/api/settings/module", "GET")()))
        activity_payload = self._json_body(asyncio.run(self._route("/api/activity", "GET")()))

        self.assertEqual(voice_payload["message"], "Voice settings updated.")
        self.assertTrue(location_payload["ok"])
        self.assertEqual(settings_snapshot["voice"]["tts_provider"], "elevenlabs")
        self.assertEqual(settings_snapshot["location"]["preferred_location_id"], "household-home")
        self.assertTrue(any(item.get("title") == "Save Voice Settings" for item in settings_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("title") == "Save Location Settings" for item in settings_snapshot["recent_activity"]))
        self.assertTrue(any(item.get("related_kind") == "voice-settings" for item in activity_payload))
        self.assertTrue(any(item.get("related_kind") == "location-settings" for item in activity_payload))

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


if __name__ == "__main__":
    unittest.main()
