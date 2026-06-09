"""
Phase 3 Slice 1: _event_log.record() is wired into major action handlers.

Tests verify that:
- ApprovalGuard.request_approval writes an approval_staged event to event_log.jsonl
- ApprovalGuard.execute_approved writes an approval_executed event
- _record_navigation_route_history writes a route_previewed event
- Events have required fields: id, ts, domain, kind, title, source_id
- Failures in event log writing do not propagate to callers
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import jarvis.approvals as approvals_module
from jarvis.approvals import (
    ApprovalGuard,
    ApprovalQueue,
)
import jarvis.apple_api as apple_api


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_events(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    return [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]


def _make_guard(tmpdir: Path) -> ApprovalGuard:
    # ROOT is already set to tmpdir/"approvals" in setUp
    q = ApprovalQueue()
    guard = ApprovalGuard(queue=q)
    return guard


# ---------------------------------------------------------------------------
# Tests: request_approval writes approval_staged event
# ---------------------------------------------------------------------------

class TestRequestApprovalEvent(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        self._orig_root = ApprovalQueue.ROOT
        ApprovalQueue.ROOT = self.root / "approvals"
        self.addCleanup(lambda: setattr(ApprovalQueue, "ROOT", self._orig_root))
        self._orig_guard = approvals_module._guard_singleton
        self._orig_queue = approvals_module._queue_singleton
        approvals_module._guard_singleton = None
        approvals_module._queue_singleton = None
        self.addCleanup(self._restore)

        self._orig_event_path = approvals_module._EVENT_LOG_PATH
        self.event_log = self.root / "event_log.jsonl"
        approvals_module._EVENT_LOG_PATH = self.event_log
        self.addCleanup(lambda: setattr(approvals_module, "_EVENT_LOG_PATH", self._orig_event_path))

        self.guard = _make_guard(self.root)

    def _restore(self):
        approvals_module._guard_singleton = self._orig_guard
        approvals_module._queue_singleton = self._orig_queue

    def test_request_approval_writes_staged_event(self):
        request_id = self.guard.request_approval(
            agent_id="test-agent",
            agent_label="Test Agent",
            action_type="home_control",
            title="Turn on lights",
            description="Turn on living room lights",
            payload={"command": "turn_on"},
        )
        events = _read_events(self.event_log)
        self.assertEqual(len(events), 1)
        evt = events[0]
        self.assertEqual(evt["kind"], "approval_staged")
        self.assertEqual(evt["domain"], "approvals")
        self.assertIn("id", evt)
        self.assertIn("ts", evt)
        self.assertEqual(evt["source_id"], request_id)

    def test_staged_event_has_action_type(self):
        self.guard.request_approval(
            agent_id="test-agent",
            agent_label="Test Agent",
            action_type="calendar_event",
            title="Schedule meeting",
            description="Add meeting to calendar",
            payload={},
        )
        events = _read_events(self.event_log)
        meta = events[0].get("metadata", {})
        self.assertEqual(meta.get("action_type"), "calendar_event")

    def test_staged_event_has_actor(self):
        self.guard.request_approval(
            agent_id="test-agent",
            agent_label="Test",
            action_type="system_info",
            title="Check status",
            description="",
            payload={},
            actor_id="rebekah",
        )
        events = _read_events(self.event_log)
        self.assertEqual(events[0]["actor"], "rebekah")


# ---------------------------------------------------------------------------
# Tests: execute_approved writes approval_executed event
# ---------------------------------------------------------------------------

class TestExecuteApprovedEvent(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        self._orig_root = ApprovalQueue.ROOT
        ApprovalQueue.ROOT = self.root / "approvals"
        self.addCleanup(lambda: setattr(ApprovalQueue, "ROOT", self._orig_root))
        self._orig_guard = approvals_module._guard_singleton
        self._orig_queue = approvals_module._queue_singleton
        approvals_module._guard_singleton = None
        approvals_module._queue_singleton = None
        self.addCleanup(self._restore)

        self._orig_event_path = approvals_module._EVENT_LOG_PATH
        self.event_log = self.root / "event_log.jsonl"
        approvals_module._EVENT_LOG_PATH = self.event_log
        self.addCleanup(lambda: setattr(approvals_module, "_EVENT_LOG_PATH", self._orig_event_path))

        self.guard = _make_guard(self.root)

    def _restore(self):
        approvals_module._guard_singleton = self._orig_guard
        approvals_module._queue_singleton = self._orig_queue

    def test_execute_approved_writes_executed_event(self):
        request_id = self.guard.request_approval(
            agent_id="test-agent",
            agent_label="Test",
            action_type="system_info",
            title="Test action",
            description="A safe test action",
            payload={},
        )
        self.guard._queue.approve(request_id, approved_by="chris")
        self.guard.execute_approved(request_id)

        events = _read_events(self.event_log)
        kinds = [e["kind"] for e in events]
        self.assertIn("approval_executed", kinds)

    def test_executed_event_has_source_id(self):
        request_id = self.guard.request_approval(
            agent_id="a",
            agent_label="A",
            action_type="system_info",
            title="T",
            description="",
            payload={},
        )
        self.guard._queue.approve(request_id, approved_by="chris")
        self.guard.execute_approved(request_id)

        events = _read_events(self.event_log)
        exec_event = next((e for e in events if e["kind"] == "approval_executed"), None)
        self.assertIsNotNone(exec_event)
        self.assertEqual(exec_event["source_id"], request_id)

    def test_event_log_failure_does_not_raise(self):
        request_id = self.guard.request_approval(
            agent_id="a",
            agent_label="A",
            action_type="system_info",
            title="T",
            description="",
            payload={},
        )
        self.guard._queue.approve(request_id, approved_by="chris")
        with patch.object(approvals_module, "_EVENT_LOG_PATH", Path("/nonexistent/path/event_log.jsonl")):
            result = self.guard.execute_approved(request_id)
        self.assertIn("status", result)


# ---------------------------------------------------------------------------
# Tests: _record_navigation_route_history writes route_previewed event
# ---------------------------------------------------------------------------

class TestNavigationRouteEvent(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir("/"))

        self.event_log = self.root / "data" / "state" / "event_log.jsonl"
        (self.root / "data" / "state").mkdir(parents=True, exist_ok=True)

        self._orig_event_log = apple_api._event_log
        apple_api._event_log = apple_api._EventLogStore(self.event_log)
        self.addCleanup(lambda: setattr(apple_api, "_event_log", self._orig_event_log))

        # Patch navigation state paths to use tmpdir
        self._orig_nav_path = apple_api._NAVIGATION_STATE_PATH
        self._orig_nav_log_path = apple_api._NAVIGATION_STATE_LOG_PATH
        apple_api._NAVIGATION_STATE_PATH = self.root / "data" / "settings" / "navigation_state.json"
        apple_api._NAVIGATION_STATE_LOG_PATH = self.root / "data" / "settings" / "navigation_state_log.jsonl"
        (self.root / "data" / "settings").mkdir(parents=True, exist_ok=True)
        self.addCleanup(self._restore_nav)

    def _restore_nav(self):
        apple_api._NAVIGATION_STATE_PATH = self._orig_nav_path
        apple_api._NAVIGATION_STATE_LOG_PATH = self._orig_nav_log_path

    def test_route_previewed_event_written(self):
        apple_api._record_navigation_route_history(
            origin="Home",
            destination="Church",
            origin_mode="driving",
        )
        events = _read_events(self.event_log)
        self.assertTrue(len(events) >= 1)
        nav_events = [e for e in events if e.get("kind") == "route_previewed"]
        self.assertEqual(len(nav_events), 1)

    def test_route_event_has_origin_destination(self):
        apple_api._record_navigation_route_history(
            origin="Home",
            destination="School",
            origin_mode="walking",
        )
        events = _read_events(self.event_log)
        evt = next(e for e in events if e.get("kind") == "route_previewed")
        meta = evt.get("metadata", {})
        self.assertEqual(meta.get("origin"), "Home")
        self.assertEqual(meta.get("destination"), "School")

    def test_route_event_domain_is_navigation(self):
        apple_api._record_navigation_route_history(
            origin="Office",
            destination="Home",
            origin_mode="driving",
        )
        events = _read_events(self.event_log)
        evt = next(e for e in events if e.get("kind") == "route_previewed")
        self.assertEqual(evt["domain"], "navigation")


if __name__ == "__main__":
    unittest.main()
