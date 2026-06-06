from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import jarvis.approvals as approvals_module
from jarvis.approvals import ApprovalQueue, ApprovalRequest, RiskTier, init_approvals

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
            elevenlabs_voice="",
            piper_model_path=None,
            piper_speaker="0",
            second_brain_enabled=False,
        )
        self.supervision_support = _StubSupervisionSupport()

    def execute_sandbox_job(self, *, actor_name: str, job_id: str, triggered_by: str) -> dict:
        return {"ok": True, "accepted": True, "job": {"job_id": job_id, "status": "sandbox-queued"}}


class SupervisionSnapshotServiceSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.original_cwd = os.getcwd()
        os.chdir(self.tempdir.name)
        self.addCleanup(os.chdir, self.original_cwd)

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

        self.runtime = _StubRuntime()
        self.queue, self.guard = init_approvals(
            self.runtime.supervision_support,
            self.runtime.execute_sandbox_job,
        )
        self.app = service_module.build_app(self.runtime)

    def _restore_root(self) -> None:
        ApprovalQueue.ROOT = self.original_root

    def _restore_singletons(self) -> None:
        approvals_module._guard_singleton = self.original_guard
        approvals_module._queue_singleton = self.original_queue

    def _restore_register_apple_api(self) -> None:
        service_module._register_apple_api = self.original_register_apple_api

    def _route(self, path: str, method: str):
        for route in self.app.router.routes:
            if getattr(route, "path", None) == path and method.upper() in getattr(route, "methods", set()):
                return route.endpoint
        raise AssertionError(f"Could not find route {method} {path}")

    def _json_body(self, response) -> dict:
        return json.loads(response.body.decode("utf-8"))

    def _request(self, request_id: str, *, title: str) -> ApprovalRequest:
        requested_at = datetime.now(timezone.utc) - timedelta(hours=1)
        expires_at = requested_at + timedelta(days=2)
        return ApprovalRequest(
            request_id=request_id,
            agent_id="pepper",
            agent_label="Pepper",
            action_type="calendar_change",
            title=title,
            description=f"{title} for Chris",
            payload={"calendar_id": "family"},
            risk_tier=RiskTier.MEDIUM,
            actor_id="chris",
            requested_at=requested_at.isoformat(),
            expires_at=expires_at.isoformat(),
            status="pending",
            priority=2,
            tags=["calendar"],
            trust_zone_id="household_schedule",
            lane_id="daily-life",
            arena_id="household.schedule.routing",
            requested_outcome="Reschedule the pediatrician visit",
            supervision_decision={"resolution": "stage", "approval_required": True},
        )

    def test_served_routes_expose_supervision_snapshot_surface_and_snapshot(self) -> None:
        self.queue.submit(self._request("req-1", title="Route pickup change"))

        html_response = asyncio.run(self._route("/supervision-snapshot", "GET")())
        snapshot_response = asyncio.run(self._route("/api/supervision-snapshot", "GET")())

        html = html_response.body.decode("utf-8")
        snapshot = self._json_body(snapshot_response)

        self.assertIn("JARVIS Supervision Snapshot", html)
        self.assertIn("Open Approval Queue", html)
        self.assertIn("/api/approvals/req-1/approve", html)
        self.assertEqual(snapshot["attention_queue"][0]["request_id"], "req-1")
        self.assertEqual(snapshot["proof_paths"]["served_page"], "/supervision-snapshot")
        self.assertEqual(snapshot["proof_paths"]["approval_queue"], "/approval-queue")


if __name__ == "__main__":
    unittest.main()
