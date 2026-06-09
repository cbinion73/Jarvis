"""
Phase 3 Slice 2: notification escalate + reminder defer/stage endpoints.

Tests verify:
- POST /api/apple/notifications/{id}/escalate is registered in _register_apple_api
- escalate calls update_status with target_status="escalated"
- 404 when notification not found on escalate
- POST /api/apple/reminders/{id}/defer is registered
- defer passes hours*60 minutes to _governed_reminder_mutation
- defer defaults to 24 hours when no payload
- POST /api/apple/reminders/{id}/stage is registered
- stage calls _governed_reminder_mutation with action_label="stage"
- _apple_defer_reminder writes a deferred event to the event fabric
- _apple_stage_reminder marks reminder as staged=True in mirrored state
- _apple_stage_reminder writes a staged event to the event fabric
- _governed_reminder_mutation dispatches defer and stage action_label correctly
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
from unittest.mock import AsyncMock, MagicMock, patch

import jarvis.approvals as approvals_module
from jarvis.approvals import ApprovalQueue
import jarvis.apple_api as apple_api

# ---------------------------------------------------------------------------
# Minimal FastAPI stub
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

HTTPException = sys.modules["fastapi"].HTTPException
_FastAPI = sys.modules["fastapi"].FastAPI


def _make_apple_app(runtime_mock) -> "_FastAPI":
    """Register apple_api routes onto a fresh stub app."""
    app = _FastAPI()
    apple_api._register_apple_api(app, runtime_mock)
    return app


def _find_route(app, path: str, method: str = "POST"):
    for r in app.router.routes:
        if getattr(r, "path", None) == path and method.upper() in getattr(r, "methods", set()):
            return r.endpoint
    return None


def _body(resp) -> dict:
    """Parse response — handles both plain dicts (from _ok()) and JSONResponse objects."""
    if isinstance(resp, dict):
        return resp
    raw = getattr(resp, "body", None) or getattr(resp, "content", None) or b"{}"
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Route registration — test through _register_apple_api directly
# ---------------------------------------------------------------------------

class TestRouteRegistration(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir("/"))
        for d in ("data/apple", "data/state", "data/settings"):
            (self.root / d).mkdir(parents=True, exist_ok=True)

        self.rt = MagicMock()
        self.rt.assess_action_boundary.return_value = {
            "decision": "allow", "reason": "", "trust_zone": "household_attention",
            "authority_stage": "live", "approval_mode": "live", "arena_status": "active",
        }
        self.app = _make_apple_app(self.rt)

    def test_notification_escalate_registered(self):
        fn = _find_route(self.app, "/api/apple/notifications/{notification_id}/escalate")
        self.assertIsNotNone(fn, "escalate route not registered")

    def test_reminder_defer_registered(self):
        fn = _find_route(self.app, "/api/apple/reminders/{reminder_id}/defer")
        self.assertIsNotNone(fn, "defer route not registered")

    def test_reminder_stage_registered(self):
        fn = _find_route(self.app, "/api/apple/reminders/{reminder_id}/stage")
        self.assertIsNotNone(fn, "stage route not registered")


# ---------------------------------------------------------------------------
# Notification escalate — live route call
# ---------------------------------------------------------------------------

class TestNotificationEscalate(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir("/"))
        for d in ("data/apple", "data/state", "data/settings"):
            (self.root / d).mkdir(parents=True, exist_ok=True)

        self.rt = MagicMock()
        self.rt.assess_action_boundary.return_value = {
            "decision": "allow", "reason": "", "trust_zone": "household_attention",
            "authority_stage": "live", "approval_mode": "live", "arena_status": "active",
        }
        self.app = _make_apple_app(self.rt)

    def _call_escalate(self, notification_id: str):
        fn = _find_route(self.app, "/api/apple/notifications/{notification_id}/escalate")
        return asyncio.run(fn(notification_id))

    def test_escalate_updates_status_to_escalated(self):
        nc = apple_api._notification_center
        orig_get = nc.get
        orig_update = nc.update_status
        try:
            nc.get = lambda nid: {"id": nid, "title": "Test", "status": "new"}
            nc.update_status = MagicMock(return_value={"id": "n1", "status": "escalated"})
            self._call_escalate("n1")
            statuses = [c[0][1] for c in nc.update_status.call_args_list if len(c[0]) > 1]
            self.assertIn("escalated", statuses)
        finally:
            nc.get = orig_get
            nc.update_status = orig_update

    def test_escalate_404_on_missing_notification(self):
        nc = apple_api._notification_center
        orig_get = nc.get
        try:
            nc.get = lambda nid: None
            with self.assertRaises(HTTPException) as ctx:
                self._call_escalate("missing-id")
            self.assertEqual(ctx.exception.status_code, 404)
        finally:
            nc.get = orig_get

    def test_escalate_response_contains_escalate_action(self):
        nc = apple_api._notification_center
        orig_get = nc.get
        orig_update = nc.update_status
        try:
            nc.get = lambda nid: {"id": nid, "title": "Test", "status": "new"}
            nc.update_status = MagicMock(return_value={"id": "n1", "status": "escalated"})
            resp = self._call_escalate("n1")
            data = _body(resp)
            # _ok() wraps in {"ok": True, "data": {...}}
            inner = data.get("data") or data
            self.assertEqual(inner.get("performed_action"), "escalate")
        finally:
            nc.get = orig_get
            nc.update_status = orig_update


# ---------------------------------------------------------------------------
# Reminder defer — route call with _governed_reminder_mutation mocked
# ---------------------------------------------------------------------------

class TestReminderDefer(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir("/"))
        for d in ("data/apple", "data/state", "data/settings"):
            (self.root / d).mkdir(parents=True, exist_ok=True)

        self.rt = MagicMock()
        self.rt.assess_action_boundary.return_value = {
            "decision": "allow", "reason": "", "trust_zone": "household_tasks",
            "authority_stage": "live", "approval_mode": "live", "arena_status": "active",
        }
        self.app = _make_apple_app(self.rt)

    def _call_defer(self, reminder_id: str, payload=None):
        fn = _find_route(self.app, "/api/apple/reminders/{reminder_id}/defer")
        return asyncio.run(fn(reminder_id, payload=payload))

    def test_defer_dispatches_defer_action(self):
        with patch.object(apple_api, "_governed_reminder_mutation",
                          return_value={"status": "deferred"}) as mock_mut:
            self._call_defer("rem-1", payload={"hours": 6})
        mock_mut.assert_called_once()
        kwargs = mock_mut.call_args[1]
        self.assertEqual(kwargs.get("action_label"), "defer")
        self.assertEqual(kwargs.get("minutes"), 360)  # 6 * 60

    def test_defer_defaults_to_24h(self):
        with patch.object(apple_api, "_governed_reminder_mutation",
                          return_value={"status": "deferred"}) as mock_mut:
            self._call_defer("rem-1", payload=None)
        kwargs = mock_mut.call_args[1]
        self.assertEqual(kwargs.get("minutes"), 1440)  # 24 * 60

    def test_defer_clamps_hours_to_24_when_zero(self):
        with patch.object(apple_api, "_governed_reminder_mutation",
                          return_value={"status": "deferred"}) as mock_mut:
            self._call_defer("rem-1", payload={"hours": 0})
        kwargs = mock_mut.call_args[1]
        self.assertEqual(kwargs.get("minutes"), 1440)


# ---------------------------------------------------------------------------
# Reminder stage — route call with _governed_reminder_mutation mocked
# ---------------------------------------------------------------------------

class TestReminderStage(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir("/"))
        for d in ("data/apple", "data/state", "data/settings"):
            (self.root / d).mkdir(parents=True, exist_ok=True)

        self.rt = MagicMock()
        self.app = _make_apple_app(self.rt)

    def _call_stage(self, reminder_id: str):
        fn = _find_route(self.app, "/api/apple/reminders/{reminder_id}/stage")
        return asyncio.run(fn(reminder_id))

    def test_stage_dispatches_stage_action(self):
        with patch.object(apple_api, "_governed_reminder_mutation",
                          return_value={"status": "staged"}) as mock_mut:
            self._call_stage("rem-1")
        mock_mut.assert_called_once()
        kwargs = mock_mut.call_args[1]
        self.assertEqual(kwargs.get("action_label"), "stage")

    def test_stage_returns_ok_body(self):
        with patch.object(apple_api, "_governed_reminder_mutation",
                          return_value={"status": "staged"}):
            resp = self._call_stage("rem-1")
        data = _body(resp)
        inner = data.get("data") or data
        self.assertEqual(inner.get("status"), "staged")


# ---------------------------------------------------------------------------
# _apple_defer_reminder direct tests
# ---------------------------------------------------------------------------

class TestAppleDeferReminder(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir("/"))

        reminders_dir = self.root / "data" / "apple"
        reminders_dir.mkdir(parents=True)
        self.reminders_path = reminders_dir / "reminders.json"
        self.reminder_id = "rem-001"
        self.reminders_path.write_text(json.dumps({
            "reminders": [{"id": self.reminder_id, "title": "Call dentist", "completed": False}],
            "count": 1, "synced_at": "2026-06-09T00:00:00Z",
        }))

        self._orig_reminders_path = apple_api._APPLE_REMINDERS_PATH
        apple_api._APPLE_REMINDERS_PATH = self.reminders_path
        self.addCleanup(lambda: setattr(apple_api, "_APPLE_REMINDERS_PATH", self._orig_reminders_path))

        event_dir = self.root / "data" / "state"
        event_dir.mkdir(parents=True)
        self.event_log = event_dir / "event_log.jsonl"
        self._orig_event_log = apple_api._event_log
        apple_api._event_log = apple_api._EventLogStore(self.event_log)
        self.addCleanup(lambda: setattr(apple_api, "_event_log", self._orig_event_log))

    def _read_events(self):
        if not self.event_log.exists():
            return []
        return [json.loads(l) for l in self.event_log.read_text().splitlines() if l.strip()]

    def test_defer_returns_deferred_status(self):
        with patch("jarvis.reminders.snooze_reminder", return_value=True):
            result = apple_api._apple_defer_reminder(self.reminder_id, hours=4)
        self.assertEqual(result["status"], "deferred")

    def test_defer_writes_deferred_event(self):
        with patch("jarvis.reminders.snooze_reminder", return_value=True):
            apple_api._apple_defer_reminder(self.reminder_id, hours=24)
        events = self._read_events()
        deferred = [e for e in events if "defer" in str(e.get("title", "")).lower()]
        self.assertGreaterEqual(len(deferred), 1)

    def test_defer_404_on_missing_reminder(self):
        with patch("jarvis.reminders.snooze_reminder", return_value=False):
            with self.assertRaises(HTTPException) as ctx:
                apple_api._apple_defer_reminder("nonexistent", hours=1)
        self.assertEqual(ctx.exception.status_code, 404)


# ---------------------------------------------------------------------------
# _apple_stage_reminder direct tests
# ---------------------------------------------------------------------------

class TestAppleStageReminder(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir("/"))

        reminders_dir = self.root / "data" / "apple"
        reminders_dir.mkdir(parents=True)
        self.reminders_path = reminders_dir / "reminders.json"
        self.reminder_id = "rem-002"
        self.reminders_path.write_text(json.dumps({
            "reminders": [{"id": self.reminder_id, "title": "Buy groceries", "completed": False}],
            "count": 1, "synced_at": "2026-06-09T00:00:00Z",
        }))

        self._orig_reminders_path = apple_api._APPLE_REMINDERS_PATH
        apple_api._APPLE_REMINDERS_PATH = self.reminders_path
        self.addCleanup(lambda: setattr(apple_api, "_APPLE_REMINDERS_PATH", self._orig_reminders_path))

        event_dir = self.root / "data" / "state"
        event_dir.mkdir(parents=True)
        self.event_log = event_dir / "event_log.jsonl"
        self._orig_event_log = apple_api._event_log
        apple_api._event_log = apple_api._EventLogStore(self.event_log)
        self.addCleanup(lambda: setattr(apple_api, "_event_log", self._orig_event_log))

    def _read_reminders(self):
        data = json.loads(self.reminders_path.read_text())
        return data.get("reminders", [])

    def _read_events(self):
        if not self.event_log.exists():
            return []
        return [json.loads(l) for l in self.event_log.read_text().splitlines() if l.strip()]

    def test_stage_returns_staged_status(self):
        result = apple_api._apple_stage_reminder(self.reminder_id)
        self.assertEqual(result["status"], "staged")

    def test_stage_sets_staged_flag(self):
        apple_api._apple_stage_reminder(self.reminder_id)
        target = next((r for r in self._read_reminders() if r.get("id") == self.reminder_id), None)
        self.assertIsNotNone(target)
        self.assertTrue(target.get("staged"))

    def test_stage_records_staged_at(self):
        apple_api._apple_stage_reminder(self.reminder_id)
        target = next((r for r in self._read_reminders() if r.get("id") == self.reminder_id), None)
        self.assertIn("staged_at", target)

    def test_stage_writes_event(self):
        apple_api._apple_stage_reminder(self.reminder_id)
        events = self._read_events()
        staged = [e for e in events if "stage" in str(e.get("kind", "")).lower()
                  or "stage" in str(e.get("title", "")).lower()]
        self.assertGreaterEqual(len(staged), 1)

    def test_stage_404_on_missing_reminder(self):
        with self.assertRaises(HTTPException) as ctx:
            apple_api._apple_stage_reminder("nonexistent")
        self.assertEqual(ctx.exception.status_code, 404)


# ---------------------------------------------------------------------------
# _governed_reminder_mutation dispatch — patch _current_apple_reminder_item + runtime
# ---------------------------------------------------------------------------

class TestGovernedReminderMutationDispatch(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir("/"))

        # Inject runtime mock at module level since _governed_reminder_mutation is module-level
        rt = MagicMock()
        rt.assess_action_boundary.return_value = {
            "decision": "allow", "reason": "", "trust_zone": "household_tasks",
            "authority_stage": "live", "approval_mode": "live", "arena_status": "active",
        }
        self._had_runtime = hasattr(apple_api, "runtime")
        self._orig_runtime = getattr(apple_api, "runtime", None)
        apple_api.runtime = rt
        self.addCleanup(self._restore_runtime)

        self.fake_item = {"id": "rem-003", "title": "Walk dog", "status": "open"}

    def _restore_runtime(self):
        if self._had_runtime:
            apple_api.runtime = self._orig_runtime
        elif hasattr(apple_api, "runtime"):
            delattr(apple_api, "runtime")

    def test_defer_dispatched(self):
        with patch.object(apple_api, "_current_apple_reminder_item", return_value=self.fake_item), \
             patch.object(apple_api, "_apple_defer_reminder",
                          return_value={"status": "deferred", "reminder_id": "rem-003"}) as mock_defer:
            result = apple_api._governed_reminder_mutation("rem-003", action_label="defer", minutes=1440)
        mock_defer.assert_called_once_with("rem-003", hours=24)
        self.assertEqual(result["status"], "deferred")

    def test_stage_dispatched(self):
        with patch.object(apple_api, "_current_apple_reminder_item", return_value=self.fake_item), \
             patch.object(apple_api, "_apple_stage_reminder",
                          return_value={"status": "staged", "reminder_id": "rem-003"}) as mock_stage:
            result = apple_api._governed_reminder_mutation("rem-003", action_label="stage")
        mock_stage.assert_called_once_with("rem-003")
        self.assertEqual(result["status"], "staged")

    def test_defer_hours_minimum_1(self):
        """When minutes=0, hours passed to _apple_defer_reminder is at least 1."""
        with patch.object(apple_api, "_current_apple_reminder_item", return_value=self.fake_item), \
             patch.object(apple_api, "_apple_defer_reminder",
                          return_value={"status": "deferred", "reminder_id": "rem-003"}) as mock_defer:
            apple_api._governed_reminder_mutation("rem-003", action_label="defer", minutes=0)
        hours = mock_defer.call_args[1].get("hours", 1)
        self.assertGreaterEqual(hours, 1)


if __name__ == "__main__":
    unittest.main()
