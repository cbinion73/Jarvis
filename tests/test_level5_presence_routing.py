"""
Level 5 presence-aware routing tests.

Tests cover:
- _read_presence_overrides: absent file, TTL expired, TTL active
- _write_presence_overrides: roundtrip
- _maybe_fire_escalation_push: fires on escalate/household_alert, debounces,
  skips other posture modes
- POST /api/apple/presence-override: suppress/escalate/clear modes, TTL,
  unknown-mode 400
- apple_status(): reflect suppress_interruptions and escalate_interruptions
  from active overrides
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# FastAPI stub (same pattern as other apple_api tests)
# ---------------------------------------------------------------------------

if "fastapi" not in sys.modules:
    _fs = types.ModuleType("fastapi")
    _rs = types.ModuleType("fastapi.responses")
    _ss = types.ModuleType("fastapi.staticfiles")
    _uv = types.ModuleType("uvicorn")

    class _Route:
        def __init__(self, path, methods, endpoint):
            self.path = path; self.methods = methods; self.endpoint = endpoint

    class _Router:
        def __init__(self): self.routes = []

    class _FastAPI:
        def __init__(self, *a, **kw): self.router = _Router()
        def _reg(self, path, methods):
            def dec(fn): self.router.routes.append(_Route(path, methods, fn)); return fn
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

    _fs.FastAPI = _FastAPI
    _fs.HTTPException = _HTTPException
    _fs.Query = lambda *a, **kw: None
    _fs.File = lambda *a, **kw: None
    _fs.Form = lambda *a, **kw: None
    _fs.Request = object
    _fs.UploadFile = object
    _fs.WebSocket = object
    _fs.WebSocketDisconnect = Exception
    _fs.BackgroundTasks = object
    _rs.JSONResponse = _JSONResponse
    _rs.HTMLResponse = _JSONResponse
    _rs.FileResponse = _JSONResponse
    _rs.RedirectResponse = _JSONResponse
    _rs.Response = _JSONResponse
    _ss.StaticFiles = object
    _uv.run = lambda *a, **kw: None
    sys.modules["fastapi"] = _fs
    sys.modules["fastapi.responses"] = _rs
    sys.modules["fastapi.staticfiles"] = _ss
    sys.modules["uvicorn"] = _uv

if "langgraph.graph" not in sys.modules:
    _lg = types.ModuleType("langgraph")
    _lg_g = types.ModuleType("langgraph.graph")
    class _SG:
        def __init__(self, *a, **kw): pass
        def add_node(self, *a, **kw): pass
        def add_edge(self, *a, **kw): pass
        def compile(self):
            class _C:
                def invoke(self, s): return s
            return _C()
    _lg_g.StateGraph = _SG; _lg_g.END = "END"; _lg_g.START = "START"
    _lg.graph = _lg_g
    sys.modules["langgraph"] = _lg; sys.modules["langgraph.graph"] = _lg_g

import jarvis.apple_api as api_mod
from jarvis.apple_api import (
    _read_presence_overrides,
    _write_presence_overrides,
    _fire_escalation_push,
    _maybe_fire_escalation_push,
    _PRESENCE_OVERRIDES_PATH,
)

HTTPException = sys.modules["fastapi"].HTTPException


def _iso_future(minutes: int = 60) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def _iso_past(minutes: int = 60) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _WithTempData(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self._orig_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)
        self.addCleanup(os.chdir, self._orig_cwd)

    def _write_overrides_file(self, data: dict) -> None:
        path = Path(self.tmpdir.name) / "data" / "apple" / "presence_overrides.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))


# ---------------------------------------------------------------------------
# _read_presence_overrides
# ---------------------------------------------------------------------------

class TestReadPresenceOverrides(_WithTempData):

    def test_missing_file_returns_empty(self):
        result = _read_presence_overrides()
        self.assertEqual(result, {})

    def test_invalid_json_returns_empty(self):
        path = Path("data/apple/presence_overrides.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not-json{{")
        result = _read_presence_overrides()
        self.assertEqual(result, {})

    def test_active_override_returned(self):
        path = Path("data/apple/presence_overrides.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "suppress_interruptions": True,
            "expires_at": _iso_future(60),
        }))
        result = _read_presence_overrides()
        self.assertTrue(result.get("suppress_interruptions"))

    def test_expired_override_returns_empty(self):
        path = Path("data/apple/presence_overrides.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "suppress_interruptions": True,
            "expires_at": _iso_past(5),
        }))
        result = _read_presence_overrides()
        self.assertEqual(result, {})

    def test_no_expiry_field_always_active(self):
        path = Path("data/apple/presence_overrides.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"escalate_interruptions": True}))
        result = _read_presence_overrides()
        self.assertTrue(result.get("escalate_interruptions"))


# ---------------------------------------------------------------------------
# _write / _read roundtrip
# ---------------------------------------------------------------------------

class TestWritePresenceOverrides(_WithTempData):

    def test_write_then_read_roundtrip(self):
        data = {
            "suppress_interruptions": True,
            "escalate_interruptions": False,
            "expires_at": _iso_future(30),
            "mode": "suppress",
        }
        _write_presence_overrides(data)
        result = _read_presence_overrides()
        self.assertTrue(result.get("suppress_interruptions"))
        self.assertEqual(result.get("mode"), "suppress")

    def test_write_empty_clears_state(self):
        path = Path("data/apple/presence_overrides.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"suppress_interruptions": True}))
        _write_presence_overrides({})
        result = _read_presence_overrides()
        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# _maybe_fire_escalation_push
# ---------------------------------------------------------------------------

class TestMaybeFireEscalationPush(_WithTempData):

    def _posture(self, alert_count: int = 3) -> dict:
        return {"alert_count": alert_count, "needs_count": 0}

    def test_fires_push_for_escalate_posture(self):
        fired = []
        with patch.object(api_mod, "_fire_escalation_push", side_effect=lambda **kw: fired.append(kw)):
            _maybe_fire_escalation_push("escalate", self._posture(3))
        self.assertEqual(len(fired), 1)
        self.assertIn("JARVIS", fired[0]["title"])

    def test_fires_push_for_household_alert_posture(self):
        fired = []
        with patch.object(api_mod, "_fire_escalation_push", side_effect=lambda **kw: fired.append(kw)):
            _maybe_fire_escalation_push("household_alert", self._posture(1))
        self.assertEqual(len(fired), 1)

    def test_does_not_fire_for_active_hours_posture(self):
        fired = []
        with patch.object(api_mod, "_fire_escalation_push", side_effect=lambda **kw: fired.append(kw)):
            _maybe_fire_escalation_push("active_hours", self._posture(0))
        self.assertEqual(len(fired), 0)

    def test_does_not_fire_for_suppress_posture(self):
        fired = []
        with patch.object(api_mod, "_fire_escalation_push", side_effect=lambda **kw: fired.append(kw)):
            _maybe_fire_escalation_push("suppress", self._posture(0))
        self.assertEqual(len(fired), 0)

    def test_debounces_within_5_minutes(self):
        fired = []
        with patch.object(api_mod, "_fire_escalation_push", side_effect=lambda **kw: fired.append(kw)):
            _maybe_fire_escalation_push("escalate", self._posture(3))
            _maybe_fire_escalation_push("escalate", self._posture(3))
        self.assertEqual(len(fired), 1, "Second call within 5 minutes must be debounced")

    def test_fires_again_after_debounce_window(self):
        fired = []
        past_ts = (datetime.now(timezone.utc) - timedelta(seconds=310)).isoformat()
        overrides = {"last_escalation_push_ts": past_ts}
        _write_presence_overrides(overrides)
        with patch.object(api_mod, "_fire_escalation_push", side_effect=lambda **kw: fired.append(kw)):
            _maybe_fire_escalation_push("escalate", self._posture(3))
        self.assertEqual(len(fired), 1)


# ---------------------------------------------------------------------------
# POST /api/apple/presence-override route
# ---------------------------------------------------------------------------

class TestPresenceOverrideRoute(_WithTempData):

    def _register(self):
        import jarvis.apple_api as _api
        app = sys.modules["fastapi"].FastAPI()
        runtime = MagicMock()
        runtime.status.return_value = {}
        runtime.get_focus_state.return_value = {}
        _api._register_apple_api(app, runtime)
        return app

    def _route(self, app, path, method="POST"):
        for r in app.router.routes:
            if getattr(r, "path", None) == path and method.upper() in getattr(r, "methods", set()):
                return r.endpoint
        raise AssertionError(f"Route {method} {path} not found")

    def _body(self, resp) -> dict:
        if isinstance(resp, dict):
            return resp
        raw = getattr(resp, "body", None) or b"{}"
        return json.loads(raw)

    def setUp(self):
        super().setUp()
        self.app = self._register()
        self.fn = self._route(self.app, "/api/apple/presence-override", "POST")

    def test_suppress_mode_writes_suppress_true(self):
        resp = asyncio.run(self.fn(payload={"mode": "suppress", "ttl_minutes": 30}))
        body = self._body(resp)
        self.assertTrue(body["data"]["suppress_interruptions"])
        self.assertFalse(body["data"]["escalate_interruptions"])

    def test_escalate_mode_writes_escalate_true(self):
        resp = asyncio.run(self.fn(payload={"mode": "escalate", "ttl_minutes": 15}))
        body = self._body(resp)
        self.assertTrue(body["data"]["escalate_interruptions"])
        self.assertFalse(body["data"]["suppress_interruptions"])

    def test_clear_mode_clears_both_flags(self):
        # Write an override first
        asyncio.run(self.fn(payload={"mode": "suppress"}))
        # Now clear
        resp = asyncio.run(self.fn(payload={"mode": "clear"}))
        body = self._body(resp)
        self.assertFalse(body["data"]["suppress_interruptions"])
        self.assertFalse(body["data"]["escalate_interruptions"])

    def test_unknown_mode_raises_400(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(self.fn(payload={"mode": "banana"}))
        self.assertEqual(ctx.exception.status_code, 400)

    def test_suppress_persisted_to_file(self):
        asyncio.run(self.fn(payload={"mode": "suppress", "ttl_minutes": 60}))
        stored = _read_presence_overrides()
        self.assertTrue(stored.get("suppress_interruptions"))

    def test_escalate_response_includes_expires_at(self):
        resp = asyncio.run(self.fn(payload={"mode": "escalate", "ttl_minutes": 45}))
        body = self._body(resp)
        self.assertIn("expires_at", body["data"])

    def test_ttl_clamped_to_480_max(self):
        resp = asyncio.run(self.fn(payload={"mode": "suppress", "ttl_minutes": 9999}))
        body = self._body(resp)
        # expires_at should be ~480 minutes in the future, not 9999
        exp = datetime.fromisoformat(body["data"]["expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        delta_minutes = (exp - datetime.now(timezone.utc)).total_seconds() / 60
        self.assertLessEqual(delta_minutes, 481)


# ---------------------------------------------------------------------------
# apple_status merges presence overrides
# ---------------------------------------------------------------------------

class TestAppleStatusMergesOverrides(_WithTempData):

    def _register(self):
        import jarvis.apple_api as _api
        app = sys.modules["fastapi"].FastAPI()
        runtime = MagicMock()
        runtime.status.return_value = {}
        _api._register_apple_api(app, runtime)
        return app

    def _route(self, app, path, method="GET"):
        for r in app.router.routes:
            if getattr(r, "path", None) == path and method.upper() in getattr(r, "methods", set()):
                return r.endpoint
        raise AssertionError(f"Route {method} {path} not found")

    def _body(self, resp) -> dict:
        if isinstance(resp, dict):
            return resp
        raw = getattr(resp, "body", None) or b"{}"
        return json.loads(raw)

    def setUp(self):
        super().setUp()
        self.app = self._register()
        self.status_fn = self._route(self.app, "/api/apple/status", "GET")

    def test_default_status_has_suppress_false(self):
        resp = asyncio.run(self.status_fn())
        body = self._body(resp)
        self.assertFalse(body["data"].get("suppress_interruptions"))

    def test_status_reflects_active_suppress_override(self):
        path = Path("data/apple/presence_overrides.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "suppress_interruptions": True,
            "expires_at": _iso_future(60),
        }))
        resp = asyncio.run(self.status_fn())
        body = self._body(resp)
        self.assertTrue(body["data"].get("suppress_interruptions"))

    def test_status_does_not_reflect_expired_override(self):
        path = Path("data/apple/presence_overrides.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "suppress_interruptions": True,
            "expires_at": _iso_past(5),
        }))
        resp = asyncio.run(self.status_fn())
        body = self._body(resp)
        self.assertFalse(body["data"].get("suppress_interruptions"))

    def test_status_reflects_escalate_override(self):
        path = Path("data/apple/presence_overrides.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "escalate_interruptions": True,
            "expires_at": _iso_future(30),
        }))
        resp = asyncio.run(self.status_fn())
        body = self._body(resp)
        self.assertTrue(body["data"].get("escalate_interruptions"))


if __name__ == "__main__":
    unittest.main()
