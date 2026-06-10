"""H5: ProactiveOrchestrator signal aggregation tests.

Proves that:
1. run() creates prompts only when real signals are present.
2. De-duplication prevents duplicate pending prompts.
3. Mode signals (crisis/sabbath/etc.) create prompts; normal mode does not.
4. Approval signals create one prompt per pending approval (capped at 5).
5. Calendar events within 30 minutes create prompts; distant events do not.
6. Health check-in overdue (>25h) creates a prompt; recent check-in does not.
7. Presence (foreground_active=True) creates a delivery hint prompt when pending prompts exist.
8. All collectors fail-open — exceptions from stores do not raise.
9. POST /api/proactive/orchestrate and GET /api/proactive/pending endpoints registered.
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# FastAPI stub — same complete class-based pattern as all other test files.
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
        def add_middleware(self, *a, **kw): pass

    class _HTTPException(Exception):
        def __init__(self, status_code=500, detail=""):
            super().__init__(detail); self.status_code = status_code; self.detail = detail

    _rs.JSONResponse = dict
    _fs.FastAPI = _FastAPI
    _fs.HTTPException = _HTTPException
    _fs.Request = object
    _fs.BackgroundTasks = object
    _fs.File = lambda *a, **kw: None
    _fs.Form = lambda *a, **kw: None
    _fs.Query = lambda *a, **kw: None
    _fs.UploadFile = object
    _fs.WebSocket = object
    _fs.WebSocketDisconnect = Exception
    _fs.responses = _rs
    _fs.staticfiles = _ss
    _uv.run = lambda *a, **kw: None

    for _m, _s in (
        ("fastapi", _fs),
        ("fastapi.responses", _rs),
        ("fastapi.staticfiles", _ss),
        ("fastapi.middleware.cors", types.ModuleType("fastapi.middleware.cors")),
        ("uvicorn", _uv),
    ):
        sys.modules.setdefault(_m, _s)

import tempfile
from datetime import datetime, timezone, timedelta

from jarvis.proactive import (
    ProactiveOrchestrator,
    ProactivePromptStore,
    get_orchestrator,
)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _future(minutes: int) -> str:
    return _iso(datetime.now(timezone.utc) + timedelta(minutes=minutes))


def _past(hours: int) -> str:
    return _iso(datetime.now(timezone.utc) - timedelta(hours=hours))


class TestProactiveOrchestrator(unittest.TestCase):
    """ProactiveOrchestrator signal aggregation and de-duplication."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "proactive"

    def tearDown(self):
        self.tmp.cleanup()

    def _orch(self, runtime=None) -> ProactiveOrchestrator:
        return ProactiveOrchestrator(root=self.root, runtime=runtime)

    # ── Mode signal ──────────────────────────────────────────────────────────

    def test_crisis_mode_creates_prompt(self):
        summary = {"mode_id": "crisis", "label": "Crisis"}
        with patch("jarvis.mode_resolver.get_active_mode_summary", return_value=summary):
            result = self._orch().run("chris")
        self.assertGreater(result["created_count"], 0)
        ids = result["created_ids"]
        store = ProactivePromptStore(self.root)
        titles = {p["title"] for p in store.list_pending("chris")}
        self.assertTrue(any("Crisis" in t for t in titles))

    def test_normal_mode_does_not_create_mode_prompt(self):
        summary = {"mode_id": "normal", "label": "Normal"}
        with patch("jarvis.mode_resolver.get_active_mode_summary", return_value=summary):
            with patch("jarvis.unified_inbox.get_unified_inbox", return_value=None):
                with patch("jarvis.longevity_council.load_health_state", side_effect=Exception):
                    with patch("jarvis.apple_api._foreground_active", return_value=False):
                        result = self._orch(runtime=None).run("chris")
        # No mode prompt for normal mode; other collectors may also find nothing
        store = ProactivePromptStore(self.root)
        titles = {p["title"] for p in store.list_pending("chris")}
        self.assertFalse(any("Active mode" in t for t in titles))

    def test_sabbath_mode_creates_prompt(self):
        summary = {"mode_id": "sabbath", "label": "Sabbath"}
        with patch("jarvis.mode_resolver.get_active_mode_summary", return_value=summary):
            result = self._orch().run("chris")
        self.assertGreater(result["created_count"], 0)

    # ── Approval signal ───────────────────────────────────────────────────────

    def test_pending_approvals_create_prompts(self):
        approvals = [
            {"approval_id": f"ap-{i}", "title": f"Approval {i}", "summary": f"Need approve {i}"}
            for i in range(3)
        ]
        rt_mock = MagicMock()
        rt_mock.list_pending_approvals.return_value = approvals
        with patch("jarvis.mode_resolver.get_active_mode_summary", return_value={"mode_id": "normal"}):
            with patch("jarvis.unified_inbox.get_unified_inbox", return_value=None):
                with patch("jarvis.longevity_council.load_health_state", side_effect=Exception):
                    with patch("jarvis.apple_api._foreground_active", return_value=False):
                        result = self._orch(runtime=rt_mock).run("chris")
        self.assertEqual(result["created_count"], 3)

    def test_approvals_capped_at_five(self):
        approvals = [
            {"approval_id": f"ap-{i}", "title": f"Approval {i}"}
            for i in range(10)
        ]
        rt_mock = MagicMock()
        rt_mock.list_pending_approvals.return_value = approvals
        with patch("jarvis.mode_resolver.get_active_mode_summary", return_value={"mode_id": "normal"}):
            with patch("jarvis.unified_inbox.get_unified_inbox", return_value=None):
                with patch("jarvis.longevity_council.load_health_state", side_effect=Exception):
                    with patch("jarvis.apple_api._foreground_active", return_value=False):
                        result = self._orch(runtime=rt_mock).run("chris")
        self.assertLessEqual(result["created_count"], 5)

    # ── Calendar signal ───────────────────────────────────────────────────────

    def test_imminent_event_creates_prompt(self):
        inbox_mock = MagicMock()
        inbox_mock.get_todays_agenda.return_value = {
            "events": [{"event_id": "ev1", "title": "Team standup", "start": _future(15)}]
        }
        with patch("jarvis.mode_resolver.get_active_mode_summary", return_value={"mode_id": "normal"}):
            with patch("jarvis.unified_inbox.get_unified_inbox", return_value=inbox_mock):
                with patch("jarvis.longevity_council.load_health_state", side_effect=Exception):
                    with patch("jarvis.apple_api._foreground_active", return_value=False):
                        result = self._orch(runtime=None).run("chris")
        store = ProactivePromptStore(self.root)
        titles = {p["title"] for p in store.list_pending("chris")}
        self.assertTrue(any("standup" in t for t in titles), f"Got: {titles}")

    def test_distant_event_does_not_create_prompt(self):
        inbox_mock = MagicMock()
        inbox_mock.get_todays_agenda.return_value = {
            "events": [{"event_id": "ev2", "title": "Far future meeting", "start": _future(120)}]
        }
        with patch("jarvis.mode_resolver.get_active_mode_summary", return_value={"mode_id": "normal"}):
            with patch("jarvis.unified_inbox.get_unified_inbox", return_value=inbox_mock):
                with patch("jarvis.longevity_council.load_health_state", side_effect=Exception):
                    with patch("jarvis.apple_api._foreground_active", return_value=False):
                        result = self._orch(runtime=None).run("chris")
        store = ProactivePromptStore(self.root)
        titles = {p["title"] for p in store.list_pending("chris")}
        self.assertFalse(any("Far future" in t for t in titles))

    # ── Health signal ─────────────────────────────────────────────────────────

    def test_overdue_checkin_creates_prompt(self):
        health = {"last_checkin_at": _past(30)}  # 30 hours ago
        with patch("jarvis.mode_resolver.get_active_mode_summary", return_value={"mode_id": "normal"}):
            with patch("jarvis.unified_inbox.get_unified_inbox", return_value=None):
                with patch("jarvis.longevity_council.load_health_state", return_value=health):
                    with patch("jarvis.apple_api._foreground_active", return_value=False):
                        result = self._orch(runtime=None).run("chris")
        store = ProactivePromptStore(self.root)
        titles = {p["title"] for p in store.list_pending("chris")}
        self.assertTrue(any("overdue" in t.lower() for t in titles), f"Got: {titles}")

    def test_recent_checkin_no_health_prompt(self):
        health = {"last_checkin_at": _past(1)}  # 1 hour ago
        with patch("jarvis.mode_resolver.get_active_mode_summary", return_value={"mode_id": "normal"}):
            with patch("jarvis.unified_inbox.get_unified_inbox", return_value=None):
                with patch("jarvis.longevity_council.load_health_state", return_value=health):
                    with patch("jarvis.apple_api._foreground_active", return_value=False):
                        result = self._orch(runtime=None).run("chris")
        store = ProactivePromptStore(self.root)
        titles = {p["title"] for p in store.list_pending("chris")}
        self.assertFalse(any("overdue" in t.lower() for t in titles))

    # ── Presence signal ───────────────────────────────────────────────────────

    def test_foreground_active_creates_delivery_hint(self):
        # Seed a pending prompt so presence collector has something to surface
        store = ProactivePromptStore(self.root)
        from jarvis.proactive import ProactivePromptBuilder
        p = ProactivePromptBuilder().build(
            actor="chris", title="Pre-existing pending",
            body="Test", why_now="test",
            domain="test", source="inferred",
        )
        store.add(p)

        with patch("jarvis.mode_resolver.get_active_mode_summary", return_value={"mode_id": "normal"}):
            with patch("jarvis.unified_inbox.get_unified_inbox", return_value=None):
                with patch("jarvis.longevity_council.load_health_state", side_effect=Exception):
                    with patch("jarvis.apple_api._foreground_active", return_value=True):
                        result = self._orch(runtime=None).run("chris")
        pending = store.list_pending("chris")
        titles = {p["title"] for p in pending}
        self.assertTrue(any("Ready for review" in t for t in titles), f"Got: {titles}")

    def test_foreground_no_pending_no_presence_prompt(self):
        with patch("jarvis.mode_resolver.get_active_mode_summary", return_value={"mode_id": "normal"}):
            with patch("jarvis.unified_inbox.get_unified_inbox", return_value=None):
                with patch("jarvis.longevity_council.load_health_state", side_effect=Exception):
                    with patch("jarvis.apple_api._foreground_active", return_value=True):
                        result = self._orch(runtime=None).run("chris")
        store = ProactivePromptStore(self.root)
        titles = {p["title"] for p in store.list_pending("chris")}
        self.assertFalse(any("Ready for review" in t for t in titles))

    # ── De-duplication ─────────────────────────────────────────────────────────

    def test_dedup_prevents_duplicate_prompts(self):
        summary = {"mode_id": "crisis", "label": "Crisis"}
        with patch("jarvis.mode_resolver.get_active_mode_summary", return_value=summary):
            result1 = self._orch(runtime=None).run("chris")
        with patch("jarvis.mode_resolver.get_active_mode_summary", return_value=summary):
            result2 = self._orch(runtime=None).run("chris")
        # Second run should not create the same mode prompt again
        self.assertEqual(result2["created_count"], 0, "De-dup failed: created duplicate prompt")

    # ── Fail-open ─────────────────────────────────────────────────────────────

    def test_all_collectors_fail_open(self):
        """If every signal source raises, run() still returns without raising."""
        with patch("jarvis.mode_resolver.get_active_mode_summary", side_effect=RuntimeError("mode broken")):
            with patch("jarvis.unified_inbox.get_unified_inbox", side_effect=RuntimeError("inbox broken")):
                with patch("jarvis.longevity_council.load_health_state", side_effect=RuntimeError("health broken")):
                    with patch("jarvis.apple_api._foreground_active", side_effect=RuntimeError("presence broken")):
                        result = self._orch(runtime=None).run("chris")
        self.assertEqual(result["created_count"], 0)
        self.assertIn("run_at", result)

    # ── API surface ───────────────────────────────────────────────────────────

    def test_orchestrate_and_pending_endpoints_in_service(self):
        """Verify the H5 endpoint paths exist in service.py source (no import needed)."""
        service_path = Path(__file__).parent.parent / "jarvis" / "service.py"
        src = service_path.read_text(encoding="utf-8")
        self.assertIn('"/api/proactive/orchestrate"', src,
                      "POST /api/proactive/orchestrate not found in service.py")
        self.assertIn('"/api/proactive/pending"', src,
                      "GET /api/proactive/pending not found in service.py")


if __name__ == "__main__":
    unittest.main()
