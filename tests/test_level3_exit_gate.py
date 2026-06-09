"""
Level 3 exit gate: graceful unavailable responses for stewardship routes.

Verifies that every stewardship route returns 200 + {status: "unavailable"}
when the backing call raises — no 500s bubble to the glass shell.

Routes covered:
- GET /api/stewardship-lanes  (runtime.list_stewardship_lanes raises)
- POST /api/stewardship/daily/morning  (run_morning_checkin raises)
- POST /api/stewardship/daily/complete  (run_evening_review raises)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import jarvis.approvals as approvals_module
from jarvis.approvals import ApprovalQueue

# ---------------------------------------------------------------------------
# FastAPI / uvicorn stub (same pattern as test_stewardship_daily_gap9.py)
# Must be installed BEFORE importing jarvis.service
# ---------------------------------------------------------------------------

if "fastapi" not in sys.modules:
    fastapi_stub = types.ModuleType("fastapi")
    responses_stub = types.ModuleType("fastapi.responses")
    staticfiles_stub = types.ModuleType("fastapi.staticfiles")
    uvicorn_stub = types.ModuleType("uvicorn")

    class _Route:
        def __init__(self, path, methods, endpoint):
            self.path = path; self.methods = methods; self.endpoint = endpoint

    class _Router:
        def __init__(self): self.routes = []

    class _FastAPI:
        def __init__(self, *a, **kw): self.router = _Router()
        def _reg(self, path, methods):
            def dec(fn):
                self.router.routes.append(_Route(path, methods, fn)); return fn
            return dec
        def get(self, path, *a, **kw):    return self._reg(path, {"GET"})
        def post(self, path, *a, **kw):   return self._reg(path, {"POST"})
        def put(self, path, *a, **kw):    return self._reg(path, {"PUT"})
        def patch(self, path, *a, **kw):  return self._reg(path, {"PATCH"})
        def delete(self, path, *a, **kw): return self._reg(path, {"DELETE"})
        def websocket(self, path, *a, **kw): return self._reg(path, {"WS"})
        def on_event(self, *a, **kw):     return lambda fn: fn
        def mount(self, *a, **kw):        pass

    class _HTTPException(Exception):
        def __init__(self, status_code=500, detail=""):
            super().__init__(detail); self.status_code = status_code; self.detail = detail

    class _JSONResponse:
        def __init__(self, content, status_code=200, headers=None):
            self.body = json.dumps(content).encode(); self.status_code = status_code

    fastapi_stub.FastAPI = _FastAPI
    fastapi_stub.HTTPException = _HTTPException
    fastapi_stub.Query = lambda *a, **kw: None
    fastapi_stub.File = lambda *a, **kw: None
    fastapi_stub.Form = lambda *a, **kw: None
    fastapi_stub.Request = object
    fastapi_stub.UploadFile = object
    fastapi_stub.WebSocket = object
    fastapi_stub.WebSocketDisconnect = Exception
    fastapi_stub.BackgroundTasks = object
    responses_stub.JSONResponse = _JSONResponse
    responses_stub.HTMLResponse = _JSONResponse
    responses_stub.FileResponse = _JSONResponse
    responses_stub.RedirectResponse = _JSONResponse
    responses_stub.Response = _JSONResponse
    staticfiles_stub.StaticFiles = object
    uvicorn_stub.run = lambda *a, **kw: None
    sys.modules["fastapi"] = fastapi_stub
    sys.modules["fastapi.responses"] = responses_stub
    sys.modules["fastapi.staticfiles"] = staticfiles_stub
    sys.modules["uvicorn"] = uvicorn_stub

if "langgraph.graph" not in sys.modules:
    lg = types.ModuleType("langgraph")
    lg_graph = types.ModuleType("langgraph.graph")
    class _SG:
        def __init__(self, *a, **kw): pass
        def add_node(self, *a, **kw): pass
        def add_edge(self, *a, **kw): pass
        def compile(self):
            class _C:
                def invoke(self, s): return s
            return _C()
    lg_graph.StateGraph = _SG; lg_graph.END = "END"; lg_graph.START = "START"
    lg.graph = lg_graph
    sys.modules["langgraph"] = lg; sys.modules["langgraph.graph"] = lg_graph

import jarvis.service as service_module

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class _ServiceTestBase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self._orig_cwd = os.getcwd()
        os.chdir(self.tempdir.name)
        self.addCleanup(os.chdir, self._orig_cwd)

        self._orig_root = ApprovalQueue.ROOT
        ApprovalQueue.ROOT = Path(self.tempdir.name) / "approvals"
        self.addCleanup(lambda: setattr(ApprovalQueue, "ROOT", self._orig_root))

        self._orig_guard = approvals_module._guard_singleton
        self._orig_queue = approvals_module._queue_singleton
        approvals_module._guard_singleton = None
        approvals_module._queue_singleton = None
        self.addCleanup(self._restore_singletons)

        self._orig_apple = service_module._register_apple_api
        service_module._register_apple_api = lambda app, runtime: None
        self.addCleanup(lambda: setattr(service_module, "_register_apple_api", self._orig_apple))

        self.runtime = MagicMock()
        self.runtime.list_stewardship_lanes.return_value = []
        self.app = service_module.build_app(self.runtime)

    def _restore_singletons(self):
        approvals_module._guard_singleton = self._orig_guard
        approvals_module._queue_singleton = self._orig_queue

    def _route(self, path, method="GET"):
        for r in self.app.router.routes:
            if getattr(r, "path", None) == path and method.upper() in getattr(r, "methods", set()):
                return r.endpoint
        raise AssertionError(f"Route {method} {path} not registered")

    def _run(self, coro):
        return asyncio.run(coro)

    @staticmethod
    def _body(resp) -> dict:
        body = getattr(resp, "body", None) or getattr(resp, "content", None) or b"{}"
        if isinstance(body, (bytes, bytearray)):
            return json.loads(body)
        return body if isinstance(body, dict) else {}


# ---------------------------------------------------------------------------
# /api/stewardship-lanes
# ---------------------------------------------------------------------------

class TestStewardshipLanesUnavailable(_ServiceTestBase):

    def _get(self):
        fn = self._route("/api/stewardship-lanes", "GET")
        return self._run(fn())

    def test_lanes_ok_returns_status_ok(self):
        self.runtime.list_stewardship_lanes.return_value = [{"lane_id": "daily_ops"}]
        body = self._body(self._get())
        self.assertIn("lanes", body)
        self.assertEqual(body.get("status"), "ok")

    def test_lanes_runtime_error_returns_unavailable(self):
        self.runtime.list_stewardship_lanes.side_effect = RuntimeError("backend down")
        body = self._body(self._get())
        self.assertEqual(body.get("status"), "unavailable")
        self.assertEqual(body.get("lanes"), [])
        self.assertIn("backend down", body.get("error", ""))

    def test_lanes_runtime_error_does_not_raise(self):
        self.runtime.list_stewardship_lanes.side_effect = Exception("gone")
        try:
            body = self._body(self._get())
        except Exception as exc:
            self.fail(f"Route raised instead of returning graceful payload: {exc}")
        self.assertEqual(body.get("status"), "unavailable")


# ---------------------------------------------------------------------------
# /api/stewardship/daily/morning
# ---------------------------------------------------------------------------

class TestStewardshipMorningUnavailable(_ServiceTestBase):

    def _post(self, payload=None):
        fn = self._route("/api/stewardship/daily/morning", "POST")
        return self._run(fn(payload=payload or {}))

    def test_morning_failure_returns_unavailable_not_exception(self):
        with patch("jarvis.daily_stewardship.run_morning_checkin",
                   new=AsyncMock(side_effect=RuntimeError("checkin exploded"))):
            try:
                body = self._body(self._post())
            except Exception as exc:
                self.fail(f"Route raised instead of returning graceful payload: {exc}")
        self.assertEqual(body.get("status"), "unavailable")
        self.assertIn("checkin exploded", body.get("error", ""))

    def test_morning_failure_includes_season(self):
        with patch("jarvis.daily_stewardship.run_morning_checkin",
                   new=AsyncMock(side_effect=Exception("no module"))):
            body = self._body(self._post())
        self.assertIn("season", body, "season field must survive a checkin failure")

    def test_morning_ok_still_returns_status_ok(self):
        card = {"date": "2026-06-09", "day_type": "Push"}
        with patch("jarvis.daily_stewardship.run_morning_checkin",
                   new=AsyncMock(return_value=card)):
            body = self._body(self._post())
        self.assertEqual(body.get("status"), "ok")
        self.assertEqual(body.get("day_type"), "Push")


# ---------------------------------------------------------------------------
# /api/stewardship/daily/complete
# ---------------------------------------------------------------------------

class TestStewardshipCompleteUnavailable(_ServiceTestBase):

    def _post(self, payload=None):
        fn = self._route("/api/stewardship/daily/complete", "POST")
        return self._run(fn(payload=payload or {}))

    def test_complete_failure_returns_unavailable_not_exception(self):
        with patch("jarvis.daily_stewardship.run_evening_review",
                   new=AsyncMock(side_effect=RuntimeError("review exploded"))):
            try:
                body = self._body(self._post())
            except Exception as exc:
                self.fail(f"Route raised instead of returning graceful payload: {exc}")
        self.assertEqual(body.get("status"), "unavailable")
        self.assertIn("review exploded", body.get("error", ""))

    def test_complete_failure_returns_dict_not_exception(self):
        with patch("jarvis.daily_stewardship.run_evening_review",
                   new=AsyncMock(side_effect=Exception("db gone"))):
            body = self._body(self._post())
        self.assertIsInstance(body, dict)
        self.assertEqual(body.get("status"), "unavailable")

    def test_complete_ok_still_returns_status_ok(self):
        review = {"date": "2026-06-09", "day_score": 8}
        with patch("jarvis.daily_stewardship.run_evening_review",
                   new=AsyncMock(return_value=review)):
            body = self._body(self._post())
        self.assertEqual(body.get("status"), "ok")
        self.assertEqual(body.get("day_score"), 8)


if __name__ == "__main__":
    unittest.main()
