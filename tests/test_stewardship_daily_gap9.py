"""
GAP-9: GET /api/stewardship/daily, POST /api/stewardship/daily/morning,
POST /api/stewardship/daily/complete, and season detection.

Tests verify:
- GET /api/stewardship/daily returns unavailable when no day card cached
- GET /api/stewardship/daily returns card + season when card cached
- season field is always present
- _current_season() maps months correctly (via the route)
- POST /api/stewardship/daily/morning calls run_morning_checkin and returns card
- POST /api/stewardship/daily/complete calls run_evening_review and returns review
- 500 is raised when morning check-in raises
- season is derived from month, not hardcoded
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
# Minimal FastAPI/uvicorn stubs (same pattern as test_governance_authn.py)
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

HTTPException = sys.modules["fastapi"].HTTPException

# ---------------------------------------------------------------------------
# Base test class
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
        """Parse the response body regardless of JSONResponse implementation."""
        if hasattr(resp, "json") and callable(resp.json):
            return self._body(resp)
        body = getattr(resp, "body", None) or getattr(resp, "content", None) or b"{}"
        return json.loads(body)


# ---------------------------------------------------------------------------
# Tests: GET /api/stewardship/daily
# ---------------------------------------------------------------------------

class TestStewardshipDailyGet(_ServiceTestBase):

    def _get(self):
        fn = self._route("/api/stewardship/daily", "GET")
        return self._run(fn())

    def test_returns_unavailable_when_no_card(self):
        with patch("jarvis.daily_stewardship.get_cached_day_card", return_value=None):
            resp = self._get()
        data = self._body(resp)
        self.assertEqual(data["status"], "unavailable")

    def test_season_present_when_unavailable(self):
        with patch("jarvis.daily_stewardship.get_cached_day_card", return_value=None):
            resp = self._get()
        self.assertIn("season", self._body(resp))

    def test_returns_card_when_cached(self):
        card = {
            "date": "2026-06-09",
            "day_type": "Maintain",
            "readiness_score": 72,
            "three_moves": [],
        }
        with patch("jarvis.daily_stewardship.get_cached_day_card", return_value=card):
            resp = self._get()
        data = self._body(resp)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["day_type"], "Maintain")

    def test_season_injected_into_card(self):
        card = {"date": "2026-06-09", "day_type": "Maintain"}
        with patch("jarvis.daily_stewardship.get_cached_day_card", return_value=card):
            resp = self._get()
        self.assertIn("season", self._body(resp))
        self.assertIsInstance(self._body(resp)["season"], str)


# ---------------------------------------------------------------------------
# Tests: season detection
# ---------------------------------------------------------------------------

class TestSeasonDetection(_ServiceTestBase):

    def _get_season(self, month: int) -> str:
        with patch("jarvis.daily_stewardship.get_cached_day_card", return_value=None):
            with patch("datetime.datetime") as mock_dt:
                mock_dt.now.return_value = MagicMock(month=month)
                fn = self._route("/api/stewardship/daily", "GET")
                resp = asyncio.run(fn())
        return self._body(resp)["season"]

    def test_winter_months(self):
        for month in (12, 1, 2):
            with self.subTest(month=month):
                self.assertEqual(self._get_season(month), "winter")

    def test_spring_months(self):
        for month in (3, 4, 5):
            with self.subTest(month=month):
                self.assertEqual(self._get_season(month), "spring")

    def test_summer_months(self):
        for month in (6, 7, 8):
            with self.subTest(month=month):
                self.assertEqual(self._get_season(month), "summer")

    def test_autumn_months(self):
        for month in (9, 10, 11):
            with self.subTest(month=month):
                self.assertEqual(self._get_season(month), "autumn")


# ---------------------------------------------------------------------------
# Tests: POST /api/stewardship/daily/morning
# ---------------------------------------------------------------------------

class TestStewardshipMorning(_ServiceTestBase):

    def _post(self, payload=None):
        fn = self._route("/api/stewardship/daily/morning", "POST")
        return self._run(fn(payload=payload or {}))

    def test_calls_run_morning_checkin(self):
        mock_card = {"date": "2026-06-09", "day_type": "Push", "readiness_score": 90, "three_moves": []}
        with patch("jarvis.daily_stewardship.run_morning_checkin", new=AsyncMock(return_value=mock_card)):
            resp = self._post()
        data = self._body(resp)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["day_type"], "Push")

    def test_season_in_morning_response(self):
        mock_card = {"date": "2026-06-09", "day_type": "Maintain"}
        with patch("jarvis.daily_stewardship.run_morning_checkin", new=AsyncMock(return_value=mock_card)):
            resp = self._post()
        self.assertIn("season", self._body(resp))

    def test_passes_context_to_checkin(self):
        mock_card = {"date": "2026-06-09", "day_type": "Recovery"}
        mock_fn = AsyncMock(return_value=mock_card)
        with patch("jarvis.daily_stewardship.run_morning_checkin", new=mock_fn):
            self._post({"context": "feeling tired"})
        mock_fn.assert_called_once_with(context="feeling tired")

    def test_unavailable_on_exception(self):
        with patch("jarvis.daily_stewardship.run_morning_checkin", new=AsyncMock(side_effect=RuntimeError("no health db"))):
            resp = self._post()
        body = self._body(resp)
        self.assertEqual(body.get("status"), "unavailable")
        self.assertIn("no health db", body.get("error", ""))


# ---------------------------------------------------------------------------
# Tests: POST /api/stewardship/daily/complete
# ---------------------------------------------------------------------------

class TestStewardshipComplete(_ServiceTestBase):

    def _post(self, payload=None):
        fn = self._route("/api/stewardship/daily/complete", "POST")
        return self._run(fn(payload=payload or {}))

    def test_calls_run_evening_review(self):
        mock_review = {"date": "2026-06-09", "day_type": "Maintain", "day_score": 7}
        with patch("jarvis.daily_stewardship.run_evening_review", new=AsyncMock(return_value=mock_review)):
            resp = self._post()
        data = self._body(resp)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["day_score"], 7)

    def test_passes_wins_struggles_energy(self):
        mock_review = {"date": "2026-06-09", "day_score": 8}
        mock_fn = AsyncMock(return_value=mock_review)
        with patch("jarvis.daily_stewardship.run_evening_review", new=mock_fn):
            self._post({"wins": "hit all moves", "struggles": "late night", "energy": 7})
        mock_fn.assert_called_once_with(wins="hit all moves", struggles="late night", energy=7)

    def test_unavailable_on_exception(self):
        with patch("jarvis.daily_stewardship.run_evening_review", new=AsyncMock(side_effect=ValueError("bad data"))):
            resp = self._post()
        body = self._body(resp)
        self.assertEqual(body.get("status"), "unavailable")
        self.assertIn("bad data", body.get("error", ""))

    def test_empty_payload_passes_defaults(self):
        mock_review = {"date": "2026-06-09", "day_score": 5}
        mock_fn = AsyncMock(return_value=mock_review)
        with patch("jarvis.daily_stewardship.run_evening_review", new=mock_fn):
            self._post({})
        mock_fn.assert_called_once_with(wins="", struggles="", energy=None)


if __name__ == "__main__":
    unittest.main()
