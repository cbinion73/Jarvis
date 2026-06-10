"""
Level 5: presence heartbeat tests.

Verifies:
- _foreground_active() returns True when foreground_expires_at is in the future
- _foreground_active() returns False when expired or missing
- POST /api/apple/presence-heartbeat writes foreground_active=True with 5-min TTL
- Heartbeat merges with (does not destroy) existing suppress/escalate overrides
- apple_status() response includes foreground_active field
- _compute_interruption_posture() includes foreground_active in returned dict
- _choose_delivery_mode() upgrades hold_for_brief → badge_only when foreground_active=True
- _choose_delivery_mode() leaves non-hold_for_brief modes unchanged
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# FastAPI stub (must be installed before importing jarvis.apple_api)
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

import jarvis.apple_api as apple_api
from jarvis.apple_api import (
    _foreground_active,
    _read_presence_overrides,
    _write_presence_overrides,
    _compute_interruption_posture,
    _choose_delivery_mode,
    _register_apple_api,
)

HTTPException = sys.modules["fastapi"].HTTPException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _body(resp) -> dict:
    if isinstance(resp, dict):
        return resp
    raw = getattr(resp, "body", None) or b"{}"
    return json.loads(raw)


def _future_ts(minutes: int = 5) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def _past_ts(minutes: int = 5) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


class _AppleApiTestBase(unittest.TestCase):
    """Sets CWD to a temp dir so presence_overrides.json writes are isolated."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self._orig_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)
        self.addCleanup(os.chdir, self._orig_cwd)

        # Make sure the data/apple dir exists
        (Path(self.tmpdir.name) / "data" / "apple").mkdir(parents=True, exist_ok=True)

    def _route(self, path: str, method: str = "POST"):
        """Find a registered route endpoint from _register_apple_api."""
        app = _MockApp()
        runtime = MagicMock()
        _register_apple_api(app, runtime)
        for r in app.routes:
            if r["path"] == path and method.upper() in r["methods"]:
                return r["endpoint"], runtime
        raise AssertionError(f"Route {method} {path} not found")

    def _run(self, coro):
        return asyncio.run(coro)


class _MockApp:
    def __init__(self):
        self.routes: list[dict] = []

    def _reg(self, path, methods):
        def dec(fn):
            self.routes.append({"path": path, "methods": methods, "endpoint": fn})
            return fn
        return dec

    def get(self, path, *a, **kw):    return self._reg(path, {"GET"})
    def post(self, path, *a, **kw):   return self._reg(path, {"POST"})
    def put(self, path, *a, **kw):    return self._reg(path, {"PUT"})
    def patch(self, path, *a, **kw):  return self._reg(path, {"PATCH"})
    def delete(self, path, *a, **kw): return self._reg(path, {"DELETE"})
    def websocket(self, path, *a, **kw): return self._reg(path, {"WS"})
    def on_event(self, *a, **kw):     return lambda fn: fn
    def mount(self, *a, **kw):        pass


# ---------------------------------------------------------------------------
# _foreground_active() unit tests
# ---------------------------------------------------------------------------

class TestForegroundActive(_AppleApiTestBase):

    def test_returns_false_when_no_file(self):
        self.assertFalse(_foreground_active())

    def test_returns_false_when_expires_at_missing(self):
        _write_presence_overrides({"foreground_active": True})
        self.assertFalse(_foreground_active())

    def test_returns_true_when_expires_in_future(self):
        _write_presence_overrides({"foreground_expires_at": _future_ts(3)})
        self.assertTrue(_foreground_active())

    def test_returns_false_when_expired(self):
        _write_presence_overrides({"foreground_expires_at": _past_ts(1)})
        self.assertFalse(_foreground_active())

    def test_returns_false_on_corrupt_file(self):
        p = Path("data/apple/presence_overrides.json")
        p.write_text("NOT JSON")
        self.assertFalse(_foreground_active())

    def test_returns_true_one_second_before_expiry(self):
        exp = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
        _write_presence_overrides({"foreground_expires_at": exp})
        self.assertTrue(_foreground_active())


# ---------------------------------------------------------------------------
# POST /api/apple/presence-heartbeat route tests
# ---------------------------------------------------------------------------

class TestPresenceHeartbeatRoute(_AppleApiTestBase):

    def _heartbeat(self, payload: dict | None = None):
        endpoint, runtime = self._route("/api/apple/presence-heartbeat", "POST")
        return self._run(endpoint(payload=payload or {}))

    def test_route_exists(self):
        app = _MockApp()
        _register_apple_api(app, MagicMock())
        paths = [r["path"] for r in app.routes]
        self.assertIn("/api/apple/presence-heartbeat", paths)

    def test_route_is_post(self):
        app = _MockApp()
        _register_apple_api(app, MagicMock())
        for r in app.routes:
            if r["path"] == "/api/apple/presence-heartbeat":
                self.assertIn("POST", r["methods"])
                return
        self.fail("Route not found")

    def test_returns_foreground_active_true(self):
        body = _body(self._heartbeat())
        data = body.get("data", body)
        self.assertTrue(data["foreground_active"])

    def test_returns_foreground_expires_at(self):
        body = _body(self._heartbeat())
        data = body.get("data", body)
        self.assertIn("foreground_expires_at", data)

    def test_expiry_is_roughly_5_minutes(self):
        body = _body(self._heartbeat())
        data = body.get("data", body)
        exp = datetime.fromisoformat(data["foreground_expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        delta = exp - datetime.now(timezone.utc)
        # Should be between 4.5 and 5.5 minutes from now
        self.assertGreater(delta.total_seconds(), 260)
        self.assertLess(delta.total_seconds(), 340)

    def test_heartbeat_sets_foreground_active_in_file(self):
        self._heartbeat()
        self.assertTrue(_foreground_active())

    def test_heartbeat_preserves_existing_suppress_flag(self):
        _write_presence_overrides({
            "suppress_interruptions": True,
            "expires_at": _future_ts(30),
        })
        self._heartbeat()
        overrides = _read_presence_overrides()
        self.assertTrue(overrides.get("suppress_interruptions"))

    def test_heartbeat_preserves_existing_escalate_flag(self):
        _write_presence_overrides({
            "escalate_interruptions": True,
            "expires_at": _future_ts(30),
        })
        self._heartbeat()
        overrides = _read_presence_overrides()
        self.assertTrue(overrides.get("escalate_interruptions"))

    def test_second_heartbeat_extends_expiry(self):
        self._heartbeat()
        first_exp = _read_presence_overrides().get("foreground_expires_at")
        import time; time.sleep(0.05)
        self._heartbeat()
        second_exp = _read_presence_overrides().get("foreground_expires_at")
        self.assertGreaterEqual(second_exp, first_exp)


# ---------------------------------------------------------------------------
# _compute_interruption_posture() — foreground_active field
# ---------------------------------------------------------------------------

class TestComputePostureForegroundActive(_AppleApiTestBase):

    def _posture(self, watch: dict | None = None) -> dict:
        return _compute_interruption_posture(
            watch_status=watch or {},
            home_state={},
            focus_payload={},
        )

    def test_foreground_active_false_when_no_heartbeat(self):
        posture = self._posture()
        self.assertFalse(posture["foreground_active"])

    def test_foreground_active_true_when_heartbeat_live(self):
        _write_presence_overrides({"foreground_expires_at": _future_ts(3)})
        posture = self._posture()
        self.assertTrue(posture["foreground_active"])

    def test_foreground_active_false_when_heartbeat_expired(self):
        _write_presence_overrides({"foreground_expires_at": _past_ts(1)})
        posture = self._posture()
        self.assertFalse(posture["foreground_active"])


# ---------------------------------------------------------------------------
# _choose_delivery_mode() — foreground override
# ---------------------------------------------------------------------------

class TestChooseDeliveryModeForegroundOverride(unittest.TestCase):

    def _mode(self, default: str, posture_mode: str, foreground: bool = False,
              severity: str = "low", category: str = "system") -> str:
        posture = {
            "mode": posture_mode,
            "reason": "test reason",
            "foreground_active": foreground,
        }
        mode, _ = _choose_delivery_mode(
            default_mode=default,
            severity=severity,
            category=category,
            posture=posture,
        )
        return mode

    def test_quiet_hours_hold_upgraded_when_foreground(self):
        result = self._mode("badge_only", "quiet_hours", foreground=True)
        self.assertEqual(result, "badge_only")

    def test_quiet_hours_hold_not_upgraded_without_foreground(self):
        # quiet_hours + low severity → hold_for_brief normally
        result = self._mode("badge_only", "quiet_hours", foreground=False)
        self.assertEqual(result, "hold_for_brief")

    def test_quiet_hours_attention_hold_upgraded_when_foreground(self):
        result = self._mode("badge_only", "quiet_hours_attention", foreground=True)
        self.assertEqual(result, "badge_only")

    def test_default_hold_for_brief_upgraded_when_foreground(self):
        result = self._mode("hold_for_brief", "active_hours", foreground=True)
        self.assertEqual(result, "badge_only")

    def test_default_badge_only_unchanged_when_foreground(self):
        result = self._mode("badge_only", "active_hours", foreground=True)
        self.assertEqual(result, "badge_only")

    def test_escalate_not_affected_by_foreground(self):
        # escalate always returns deliver_now regardless
        result = self._mode("badge_only", "escalate", foreground=True)
        self.assertEqual(result, "deliver_now")

    def test_suppress_not_affected_by_foreground(self):
        result = self._mode("badge_only", "suppress", foreground=True, severity="low")
        self.assertEqual(result, "suppress")


if __name__ == "__main__":
    unittest.main()
