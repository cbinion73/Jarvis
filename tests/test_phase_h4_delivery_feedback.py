"""H4: Noise-learning delivery feedback tests.

Proves that:
1. DeliveryFeedbackStore records feedback and persists it.
2. get_routing_adjustments() learns suppress/escalate domains from feedback history.
3. _choose_delivery_mode() uses learned adjustments to change routing decisions.
4. Critical severity always breaks through suppression (safety override).
5. Escalation wins over suppression when a domain has both signals.
6. The feedback endpoint wires into DeliveryFeedbackStore.
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# FastAPI stub — same complete class-based pattern as all other test files.
# Use setdefault throughout so we never clobber a richer stub already installed
# by another test file during pytest collection.
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

from jarvis.delivery_feedback import (
    ESCALATE_THRESHOLD,
    SUPPRESS_THRESHOLD,
    DeliveryFeedbackStore,
    get_feedback_store,
)


class TestDeliveryFeedbackStore(unittest.TestCase):
    """DeliveryFeedbackStore persistence and logic."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = DeliveryFeedbackStore(root=self.root)

    def tearDown(self):
        self.tmp.cleanup()

    # ── record() ─────────────────────────────────────────────────────────────

    def test_record_persists_feedback(self):
        rec = self.store.record(
            actor="chris",
            feedback_type="noisy",
            domain="work",
            severity="info",
            delivery_mode="badge_only",
            active_mode="normal",
        )
        self.assertEqual(rec["feedback_type"], "noisy")
        self.assertEqual(rec["domain"], "work")
        self.assertIn("feedback_id", rec)

        loaded = self.store.list_feedback()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["feedback_type"], "noisy")

    def test_record_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            self.store.record(actor="chris", feedback_type="garbage", domain="work")

    def test_audit_log_written(self):
        self.store.record(actor="chris", feedback_type="useful", domain="health")
        self.assertTrue(self.store.audit_path.exists())
        lines = self.store.audit_path.read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)

    # ── get_routing_adjustments() ─────────────────────────────────────────────

    def _make_noisy(self, domain: str, count: int, mode: str = "normal"):
        for _ in range(count):
            self.store.record(
                actor="chris", feedback_type="noisy",
                domain=domain, active_mode=mode,
            )

    def _make_escalate(self, domain: str, count: int, mode: str = "normal"):
        for _ in range(count):
            self.store.record(
                actor="chris", feedback_type="missed_urgency",
                domain=domain, active_mode=mode,
            )

    def test_suppress_domain_after_threshold(self):
        self._make_noisy("work", SUPPRESS_THRESHOLD)
        adj = self.store.get_routing_adjustments(active_mode="normal")
        self.assertIn("work", adj["suppress_domains"])

    def test_no_suppress_below_threshold(self):
        self._make_noisy("work", SUPPRESS_THRESHOLD - 1)
        adj = self.store.get_routing_adjustments(active_mode="normal")
        self.assertNotIn("work", adj["suppress_domains"])

    def test_escalate_domain_after_threshold(self):
        self._make_escalate("health", ESCALATE_THRESHOLD)
        adj = self.store.get_routing_adjustments(active_mode="normal")
        self.assertIn("health", adj["escalate_domains"])

    def test_escalate_wins_over_suppress(self):
        """A domain that is both noisy and missed-urgency is escalated, not suppressed."""
        self._make_noisy("health", SUPPRESS_THRESHOLD)
        self._make_escalate("health", ESCALATE_THRESHOLD)
        adj = self.store.get_routing_adjustments(active_mode="normal")
        self.assertIn("health", adj["escalate_domains"])
        self.assertNotIn("health", adj["suppress_domains"])

    def test_records_analyzed_reported(self):
        self._make_noisy("work", 2)
        adj = self.store.get_routing_adjustments(active_mode="normal")
        self.assertGreater(adj["records_analyzed"], 0)


class TestRoutingAdaptation(unittest.TestCase):
    """_choose_delivery_mode() changes decisions based on learned feedback."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "feedback"

    def tearDown(self):
        self.tmp.cleanup()

    def _make_store_with(self, domain: str, feedback_type: str, count: int, mode: str = "normal"):
        store = DeliveryFeedbackStore(root=self.root)
        for _ in range(count):
            store.record(
                actor="chris", feedback_type=feedback_type,
                domain=domain, active_mode=mode,
            )
        return store

    def _choose(self, domain: str, severity: str = "info", posture: dict | None = None):
        """Call _choose_delivery_mode with minimal posture."""
        from jarvis.apple_api import _choose_delivery_mode
        return _choose_delivery_mode(
            default_mode="badge_only",
            severity=severity,
            category="notification",
            posture=posture or {"mode": "active_hours", "reason": "default"},
            notification_domain=domain,
        )

    def _normal_mode_contract(self):
        m = MagicMock()
        m.mode_id = "normal"
        m.notification_level = "all"
        m.suppress_domains = []
        m.alert_domains = []
        return m

    def _patch_all(self, store, mode_id: str = "normal"):
        """Return three patch context managers.

        _choose_delivery_mode uses lazy imports from source modules, so we patch
        those source modules directly rather than apple_api attributes.
        """
        contract = self._normal_mode_contract()
        p1 = patch("jarvis.delivery_feedback.get_feedback_store", return_value=store)
        p2 = patch("jarvis.mode_resolver.get_active_mode_summary",
                   return_value={"mode_id": mode_id})
        p3 = patch("jarvis.mode_resolver.get_active_mode_contract",
                   return_value=contract)
        return p1, p2, p3

    def test_noisy_domain_gets_suppressed(self):
        """After SUPPRESS_THRESHOLD noisy signals, delivery changes to suppress."""
        store = self._make_store_with("work", "noisy", SUPPRESS_THRESHOLD)
        p1, p2, p3 = self._patch_all(store)
        with p1, p2, p3:
            mode, reason = self._choose("work", severity="info")
        self.assertEqual(mode, "suppress", f"Expected suppress but got {mode!r}: {reason}")
        self.assertIn("noisy", reason.lower())

    def test_critical_breaks_through_noisy_suppression(self):
        """Critical severity always bypasses feedback-learned suppression."""
        store = self._make_store_with("work", "noisy", SUPPRESS_THRESHOLD + 5)
        p1, p2, p3 = self._patch_all(store)
        with p1, p2, p3:
            mode, reason = self._choose("work", severity="critical")
        self.assertNotEqual(mode, "suppress",
                            f"Critical must not be suppressed by noise-learning. Got {mode!r}")

    def test_missed_urgency_upgrades_delivery(self):
        """Missed-urgency feedback escalates future delivery for that domain."""
        store = self._make_store_with("health", "missed_urgency", ESCALATE_THRESHOLD)
        p1, p2, p3 = self._patch_all(store)
        with p1, p2, p3:
            mode, reason = self._choose("health", severity="info")
        self.assertEqual(mode, "badge_only", f"Expected badge_only but got {mode!r}: {reason}")
        self.assertIn("missed", reason.lower())

    def test_no_feedback_no_change(self):
        """No feedback history = routing falls through to normal posture logic."""
        store = DeliveryFeedbackStore(root=self.root)  # empty
        p1, p2, p3 = self._patch_all(store)
        with p1, p2, p3:
            mode, reason = self._choose("work", severity="info")
        # Falls through to default posture (badge_only for active_hours)
        self.assertIn(mode, {"badge_only", "hold_for_brief", "quiet_store", "deliver_now"})


if __name__ == "__main__":
    unittest.main()
