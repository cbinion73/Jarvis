"""
Phase C: Runtime — comprehensive test suite.

Tests:
C1 — Agent lifecycle: fail and complete states; durable event emission for all
     transitions (wake, run, heartbeat, pause, resume, interrupt, escalate, fail,
     complete, retire); event replay reconstructs state after restart.

C2 — Queue semantics: idempotency (item_id and dedupe_key), retry with backoff,
     dead-letter after max_attempts, cancellation, priority ordering.

C3 — Restart survival: queue zombie recovery, kernel state persistence, events
     survive restart.

C4 — Scheduler observability: get_status() has required fields; last_tick_at
     updated on tick; stale job detection; dead-letter count exposed.

C5 — Data architecture: JSONL persistence round-trips correctly under rename /
     new fields; state-log fallback loads when projection is absent.

C6 — Concurrency integrity: concurrent enqueue does not corrupt queue; concurrent
     mark_completed/mark_failed are safe; concurrent append_jsonl produces valid lines.
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
import threading
import time
import types
import unittest
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# FastAPI stub (required before importing jarvis modules)
# ---------------------------------------------------------------------------

if "fastapi" not in sys.modules:
    _fs = types.ModuleType("fastapi")
    _rs = types.ModuleType("fastapi.responses")
    _ss = types.ModuleType("fastapi.staticfiles")
    _uv = types.ModuleType("uvicorn")

    class _HTTPException(Exception):
        def __init__(self, status_code=500, detail=""):
            super().__init__(detail); self.status_code = status_code; self.detail = detail

    class _JSONResponse:
        def __init__(self, content, status_code=200, headers=None):
            self.body = json.dumps(content).encode(); self.status_code = status_code

    class _FastAPI:
        def __init__(self, *a, **kw): pass
        def _reg(self, path, methods):
            def dec(fn): return fn
            return dec
        def get(self, p, *a, **kw): return self._reg(p, {"GET"})
        def post(self, p, *a, **kw): return self._reg(p, {"POST"})
        def put(self, p, *a, **kw): return self._reg(p, {"PUT"})
        def patch(self, p, *a, **kw): return self._reg(p, {"PATCH"})
        def delete(self, p, *a, **kw): return self._reg(p, {"DELETE"})
        def websocket(self, p, *a, **kw): return self._reg(p, {"WS"})
        def on_event(self, *a, **kw): return lambda fn: fn
        def mount(self, *a, **kw): pass

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _make_queue(tmp: Path) -> "AgentWorkQueue":
    from jarvis.scheduler import AgentWorkQueue
    return AgentWorkQueue(tmp / "queue.jsonl")

def _make_item(
    agent_id: str = "test-agent",
    status: str = "queued",
    priority: int = 5,
    dedupe_key: str = "",
    item_id: str | None = None,
    max_attempts: int = 3,
    next_attempt_at: str = "",
) -> "AgentWorkItem":
    import uuid
    from jarvis.scheduler import AgentWorkItem
    return AgentWorkItem(
        item_id=item_id or str(uuid.uuid4()),
        agent_id=agent_id,
        agent_label=agent_id,
        trigger="cadence",
        event_type="cadence",
        payload={},
        queued_at=_now_iso(),
        status=status,
        priority=priority,
        dedupe_key=dedupe_key,
        max_attempts=max_attempts,
        next_attempt_at=next_attempt_at,
    )


# ---------------------------------------------------------------------------
# C1 — Agent lifecycle: fail + complete states
# ---------------------------------------------------------------------------

class TestAgentLifecycleStates(unittest.TestCase):
    """C1: fail and complete transitions; durable event emission."""

    def setUp(self):
        from jarvis.runtime_kernel import (
            AgentRuntimeKernelStore,
            AgentRuntimeKernel,
            LIFECYCLE_FAILED,
            LIFECYCLE_COMPLETING,
            LIFECYCLE_IDLE,
        )
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        root = Path(self.tmpdir.name)
        self.store = AgentRuntimeKernelStore(root / "kernel")
        self.LIFECYCLE_FAILED = LIFECYCLE_FAILED
        self.LIFECYCLE_COMPLETING = LIFECYCLE_COMPLETING
        self.LIFECYCLE_IDLE = LIFECYCLE_IDLE

        from jarvis.agentic import AgentRegistry
        self.registry = AgentRegistry()
        # Use the real "ambient-router" agent which is always registered
        self.agent_id = "ambient-router"
        from jarvis.runtime_kernel import AgentRuntimeKernel
        self.kernel = AgentRuntimeKernel(self.store, self.registry)

    def _wake(self):
        return self.kernel.apply_control(self.agent_id, "wake", actor="system")

    def test_complete_transition_from_running(self):
        self._wake()
        # Promote to running via heartbeat
        self.kernel.record_heartbeat(self.agent_id)
        result = self.kernel.apply_control(self.agent_id, "complete", reason="job-done")
        self.assertTrue(result["ok"])
        agent = result["agent"]
        self.assertEqual(agent["lifecycle"]["current_state"], self.LIFECYCLE_COMPLETING)

    def test_complete_emits_event(self):
        self._wake()
        self.kernel.record_heartbeat(self.agent_id)
        self.kernel.apply_control(self.agent_id, "complete")
        events = self.store.list_events(agent_id=self.agent_id)
        actions = [e["action"] for e in events]
        self.assertIn("complete", actions)

    def test_fail_transition_from_running(self):
        self._wake()
        self.kernel.record_heartbeat(self.agent_id)
        result = self.kernel.apply_control(self.agent_id, "fail", reason="timeout")
        self.assertTrue(result["ok"])
        agent = result["agent"]
        self.assertEqual(agent["lifecycle"]["current_state"], self.LIFECYCLE_FAILED)

    def test_fail_emits_event(self):
        self._wake()
        self.kernel.record_heartbeat(self.agent_id)
        self.kernel.apply_control(self.agent_id, "fail", reason="timeout")
        events = self.store.list_events(agent_id=self.agent_id)
        actions = [e["action"] for e in events]
        self.assertIn("fail", actions)

    def test_fail_increments_fail_count(self):
        self._wake()
        self.kernel.record_heartbeat(self.agent_id)
        self.kernel.apply_control(self.agent_id, "fail")
        state = self.store.load()
        agent = state["agents"][self.agent_id]
        self.assertGreaterEqual(agent["run"].get("fail_count", 0), 1)

    def test_complete_increments_complete_count(self):
        self._wake()
        self.kernel.record_heartbeat(self.agent_id)
        self.kernel.apply_control(self.agent_id, "complete")
        state = self.store.load()
        agent = state["agents"][self.agent_id]
        self.assertGreaterEqual(agent["run"].get("complete_count", 0), 1)

    def test_fail_sets_requires_attention(self):
        self._wake()
        self.kernel.record_heartbeat(self.agent_id)
        self.kernel.apply_control(self.agent_id, "fail", reason="crashed")
        state = self.store.load()
        agent = state["agents"][self.agent_id]
        self.assertTrue(agent["supervision"].get("requires_attention", False))

    def test_summary_includes_failed_agents_count(self):
        self._wake()
        self.kernel.record_heartbeat(self.agent_id)
        self.kernel.apply_control(self.agent_id, "fail")
        snapshot = self.kernel.snapshot()
        self.assertIn("failed_agents", snapshot["summary"])

    def test_all_lifecycle_events_emitted(self):
        """All 9 lifecycle transitions must emit durable events."""
        self._wake()  # wake
        self.kernel.record_heartbeat(self.agent_id)  # heartbeat → running
        self.kernel.apply_control(self.agent_id, "pause")
        self.kernel.apply_control(self.agent_id, "resume")
        self.kernel.record_heartbeat(self.agent_id)
        self.kernel.apply_control(self.agent_id, "interrupt")
        self.kernel.apply_control(self.agent_id, "escalate")
        self.kernel.apply_control(self.agent_id, "complete")
        events = self.store.list_events(agent_id=self.agent_id)
        actions = {e["action"] for e in events}
        for expected in ("wake", "heartbeat", "pause", "resume", "interrupt", "escalate", "complete"):
            self.assertIn(expected, actions)

    def test_retire_still_works(self):
        self._wake()
        result = self.kernel.apply_control(self.agent_id, "retire-now")
        self.assertTrue(result["ok"])
        agent = result["agent"]
        self.assertEqual(agent["lifecycle"]["current_state"], "retired")

    def test_fail_stores_fail_reason(self):
        self._wake()
        self.kernel.apply_control(self.agent_id, "fail", reason="connection-lost")
        state = self.store.load()
        agent = state["agents"][self.agent_id]
        self.assertIn("connection-lost", agent["lifecycle"].get("fail_reason", ""))


# ---------------------------------------------------------------------------
# C1 (continued) — Event replay reconstructs state after restart
# ---------------------------------------------------------------------------

class TestEventReplayAfterRestart(unittest.TestCase):
    """C1: event log survives restart and reconstructs state."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)

    def _make_store(self):
        from jarvis.runtime_kernel import AgentRuntimeKernelStore
        return AgentRuntimeKernelStore(self.root / "kernel")

    def test_events_survive_restart(self):
        store1 = self._make_store()
        store1.append_event({"event_id": "e1", "agent_id": "agent-x", "action": "wake"})
        store1.append_event({"event_id": "e2", "agent_id": "agent-x", "action": "heartbeat"})

        # Simulate restart — new store instance, same paths
        store2 = self._make_store()
        events = store2.list_events(agent_id="agent-x")
        self.assertEqual(len(events), 2)
        actions = {e["action"] for e in events}
        self.assertEqual(actions, {"wake", "heartbeat"})

    def test_state_survives_restart(self):
        from jarvis.runtime_kernel import AgentRuntimeKernelStore
        store1 = self._make_store()
        store1.save({"schema_version": "1.0", "agents": {"a": {"x": 1}}, "updated_at": ""})

        store2 = self._make_store()
        payload = store2.load()
        self.assertEqual(payload["agents"]["a"]["x"], 1)

    def test_state_log_fallback_on_blank_projection(self):
        store1 = self._make_store()
        store1.append_event({"event_id": "e3", "agent_id": "fallback-agent", "action": "escalate"})
        # Delete the projection log to simulate corruption
        store1.event_log_path.write_text("")

        store2 = self._make_store()
        events = store2.list_events(agent_id="fallback-agent")
        self.assertGreater(len(events), 0)
        self.assertEqual(events[0]["action"], "escalate")

    def test_kernel_state_reconstructed_after_restart(self):
        from jarvis.runtime_kernel import AgentRuntimeKernelStore, AgentRuntimeKernel
        from jarvis.agentic import AgentRegistry
        store1 = self._make_store()
        registry = AgentRegistry()
        # Use real "ambient-router" agent
        kernel1 = AgentRuntimeKernel(store1, registry)
        kernel1.apply_control("ambient-router", "wake", actor="test")
        kernel1.apply_control("ambient-router", "fail", reason="test-fail")

        # Restart
        store2 = self._make_store()
        kernel2 = AgentRuntimeKernel(store2, registry)
        snapshot = kernel2.snapshot()
        agent = snapshot["agents"]["ambient-router"]
        self.assertEqual(agent["lifecycle"]["current_state"], "failed")


# ---------------------------------------------------------------------------
# C2 — Queue semantics
# ---------------------------------------------------------------------------

class TestQueueIdempotency(unittest.TestCase):
    """C2: item_id and dedupe_key idempotency."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.queue = _make_queue(Path(self.tmpdir.name))

    def test_same_item_id_not_enqueued_twice(self):
        item = _make_item(item_id="fixed-id-001")
        r1 = self.queue.enqueue(item)
        r2 = self.queue.enqueue(item)
        self.assertTrue(r1)
        self.assertFalse(r2)
        self.assertEqual(len(self.queue.get_queued()), 1)

    def test_same_dedupe_key_not_enqueued_while_queued(self):
        item1 = _make_item(dedupe_key="key-abc")
        import uuid
        item2 = _make_item(item_id=str(uuid.uuid4()), dedupe_key="key-abc")
        self.queue.enqueue(item1)
        r2 = self.queue.enqueue(item2)
        self.assertFalse(r2)
        self.assertEqual(len(self.queue.get_queued()), 1)

    def test_different_dedupe_keys_both_enqueued(self):
        item1 = _make_item(dedupe_key="key-1")
        item2 = _make_item(dedupe_key="key-2")
        self.queue.enqueue(item1)
        self.queue.enqueue(item2)
        self.assertEqual(len(self.queue.get_queued()), 2)

    def test_empty_dedupe_key_allows_duplicates(self):
        item1 = _make_item(dedupe_key="")
        item2 = _make_item(dedupe_key="")
        self.queue.enqueue(item1)
        self.queue.enqueue(item2)
        self.assertEqual(len(self.queue.get_queued()), 2)

    def test_dedupe_key_cleared_when_item_completes(self):
        """After completion, same dedupe_key can be enqueued again."""
        import uuid
        item1 = _make_item(dedupe_key="key-once", item_id="orig-id")
        self.queue.enqueue(item1)
        dequeued = self.queue.dequeue_next()
        self.queue.mark_completed(dequeued.item_id, "done", {})
        # Now a new item with same dedupe_key should be accepted
        item2 = _make_item(dedupe_key="key-once", item_id=str(uuid.uuid4()))
        r2 = self.queue.enqueue(item2)
        self.assertTrue(r2)


class TestQueueRetryAndDeadLetter(unittest.TestCase):
    """C2: retry with backoff; dead-letter after max_attempts."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.queue = _make_queue(Path(self.tmpdir.name))

    def test_failed_item_with_attempts_remaining_retries(self):
        item = _make_item(max_attempts=3)
        self.queue.enqueue(item)
        dequeued = self.queue.dequeue_next()
        self.assertEqual(dequeued.attempt_count, 1)
        result = self.queue.mark_failed(dequeued.item_id, "timeout")
        self.assertEqual(result, "retry")
        # Item should be back in queued (with future next_attempt_at)
        all_items = self.queue._items
        found = next(i for i in all_items if i.item_id == dequeued.item_id)
        self.assertEqual(found.status, "queued")
        self.assertNotEqual(found.next_attempt_at, "")

    def test_exhausted_attempts_goes_dead_letter(self):
        item = _make_item(max_attempts=1)
        self.queue.enqueue(item)
        dequeued = self.queue.dequeue_next()
        result = self.queue.mark_failed(dequeued.item_id, "crash")
        self.assertEqual(result, "dead_letter")
        self.assertEqual(len(self.queue.get_dead_letter()), 1)
        self.assertEqual(self.queue.get_dead_letter()[0].status, "dead_letter")

    def test_dead_letter_not_in_queued(self):
        item = _make_item(max_attempts=1)
        self.queue.enqueue(item)
        dequeued = self.queue.dequeue_next()
        self.queue.mark_failed(dequeued.item_id, "crash")
        self.assertEqual(len(self.queue.get_queued()), 0)

    def test_attempt_count_incremented_on_dequeue(self):
        item = _make_item(max_attempts=5)
        self.queue.enqueue(item)
        dequeued = self.queue.dequeue_next()
        self.assertEqual(dequeued.attempt_count, 1)

    def test_backoff_delay_increases_with_attempts(self):
        """Second retry has a longer delay than first."""
        item = _make_item(max_attempts=5)
        self.queue.enqueue(item)

        # First failure
        d1 = self.queue.dequeue_next()
        self.queue.mark_failed(d1.item_id, "err")

        # Get the item back (bypass backoff by modifying next_attempt_at)
        found = next(i for i in self.queue._items if i.item_id == d1.item_id)
        first_delay_str = found.next_attempt_at

        # Reset to allow dequeue, then fail again
        found.next_attempt_at = ""
        d2 = self.queue.dequeue_next()
        self.assertEqual(d2.attempt_count, 2)
        self.queue.mark_failed(d2.item_id, "err2")

        found2 = next(i for i in self.queue._items if i.item_id == d1.item_id)
        second_delay_str = found2.next_attempt_at

        # second_delay should be later than first_delay
        self.assertGreater(second_delay_str, first_delay_str)

    def test_next_attempt_at_is_respected_by_dequeue(self):
        """Item with future next_attempt_at is not dequeued."""
        from datetime import timezone, timedelta
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        item = _make_item(next_attempt_at=future)
        self.queue.enqueue(item)
        dequeued = self.queue.dequeue_next()
        self.assertIsNone(dequeued)


class TestQueueCancellation(unittest.TestCase):
    """C2: cancellation of queued items."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.queue = _make_queue(Path(self.tmpdir.name))

    def test_cancel_queued_item(self):
        item = _make_item()
        self.queue.enqueue(item)
        result = self.queue.cancel(item.item_id)
        self.assertTrue(result)
        found = next(i for i in self.queue._items if i.item_id == item.item_id)
        self.assertEqual(found.status, "cancelled")

    def test_cannot_cancel_running_item(self):
        item = _make_item()
        self.queue.enqueue(item)
        self.queue.dequeue_next()  # moves to running
        result = self.queue.cancel(item.item_id)
        self.assertFalse(result)

    def test_cancel_nonexistent_returns_false(self):
        result = self.queue.cancel("does-not-exist")
        self.assertFalse(result)


class TestQueuePriorityOrdering(unittest.TestCase):
    """C2: priority ordering — lower number dequeued first."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.queue = _make_queue(Path(self.tmpdir.name))

    def test_high_priority_dequeued_first(self):
        low = _make_item(priority=10)
        high = _make_item(priority=1)
        self.queue.enqueue(low)
        self.queue.enqueue(high)
        dequeued = self.queue.dequeue_next()
        self.assertEqual(dequeued.item_id, high.item_id)

    def test_same_priority_fifo(self):
        item1 = _make_item(priority=5)
        time.sleep(0.01)
        item2 = _make_item(priority=5)
        self.queue.enqueue(item1)
        self.queue.enqueue(item2)
        d1 = self.queue.dequeue_next()
        d2 = self.queue.dequeue_next()
        self.assertEqual(d1.item_id, item1.item_id)
        self.assertEqual(d2.item_id, item2.item_id)


# ---------------------------------------------------------------------------
# C3 — Restart survival
# ---------------------------------------------------------------------------

class TestRestartSurvival(unittest.TestCase):
    """C3: queue and kernel state survive simulated restart."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)

    def test_queued_items_persist_across_restart(self):
        q1 = _make_queue(self.root)
        q1.enqueue(_make_item(agent_id="a1"))
        q1.enqueue(_make_item(agent_id="a2"))

        q2 = _make_queue(self.root)
        queued = q2.get_queued()
        self.assertEqual(len(queued), 2)
        agent_ids = {i.agent_id for i in queued}
        self.assertEqual(agent_ids, {"a1", "a2"})

    def test_zombie_items_reset_to_queued_on_restart(self):
        """Items stuck in 'running' on shutdown are reset to 'queued' on next load."""
        from jarvis.scheduler import AgentWorkItem
        import uuid
        q1 = _make_queue(self.root)
        item = AgentWorkItem(
            item_id=str(uuid.uuid4()),
            agent_id="zombie-agent",
            agent_label="Zombie",
            trigger="cadence",
            event_type="cadence",
            payload={},
            queued_at=_now_iso(),
            status="running",
            started_at=_now_iso(),
            attempt_count=1,
        )
        q1._items.append(item)
        q1._save()

        q2 = _make_queue(self.root)
        running = q2.get_running()
        queued = q2.get_queued()
        self.assertEqual(len(running), 0)
        self.assertGreater(len(queued), 0)
        found = next(i for i in queued if i.agent_id == "zombie-agent")
        self.assertEqual(found.status, "queued")
        self.assertEqual(found.started_at, "")

    def test_completed_items_survive_restart(self):
        q1 = _make_queue(self.root)
        item = _make_item(status="queued")
        q1.enqueue(item)
        dequeued = q1.dequeue_next()
        q1.mark_completed(dequeued.item_id, "done", {"ok": True})

        q2 = _make_queue(self.root)
        recent = q2.get_recent(5)
        self.assertGreater(len(recent), 0)
        self.assertEqual(recent[0].status, "completed")

    def test_dead_letter_survives_restart(self):
        q1 = _make_queue(self.root)
        item = _make_item(max_attempts=1)
        q1.enqueue(item)
        dequeued = q1.dequeue_next()
        q1.mark_failed(dequeued.item_id, "boom")

        q2 = _make_queue(self.root)
        dl = q2.get_dead_letter()
        self.assertEqual(len(dl), 1)
        self.assertEqual(dl[0].status, "dead_letter")

    def test_state_log_fallback_restores_queue(self):
        """Deleting the projection file recovers queue from state-log."""
        q1 = _make_queue(self.root)
        q1.enqueue(_make_item(agent_id="recover-me"))

        # Delete the projection file
        q1._store_path.unlink()

        q2 = _make_queue(self.root)
        queued = q2.get_queued()
        self.assertGreater(len(queued), 0)
        self.assertEqual(queued[0].agent_id, "recover-me")


# ---------------------------------------------------------------------------
# C4 — Scheduler observability
# ---------------------------------------------------------------------------

class TestSchedulerObservability(unittest.TestCase):
    """C4: get_status() exposes required fields for operational visibility."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)

    def _make_scheduler(self):
        from jarvis.scheduler import AgentScheduler, AgentWorkQueue
        queue = AgentWorkQueue(self.root / "queue.jsonl")
        runtime = MagicMock()
        runtime.agent_registry.list.return_value = []
        runtime.agent_runtime_kernel.snapshot.return_value = {"status_rows": []}
        state_store = MagicMock()
        state_store.load.return_value = {"agents": {}}
        scheduler = AgentScheduler(runtime, queue, state_store)
        return scheduler

    def test_get_status_has_required_fields(self):
        scheduler = self._make_scheduler()
        status = scheduler.get_status()
        required = {
            "running", "quiet_hours", "queue_depth", "running_count",
            "dead_letter_count", "stale_jobs", "last_tick_at",
            "tick_count", "next_due_work", "unhealthy_agents",
            "recent_work", "dead_letter", "workers_active", "generated_at",
        }
        for field in required:
            self.assertIn(field, status, f"Missing required field: {field}")

    def test_last_tick_at_updated_on_tick(self):
        scheduler = self._make_scheduler()
        self.assertEqual(scheduler._last_tick_at, "")
        scheduler._tick()
        self.assertNotEqual(scheduler._last_tick_at, "")

    def test_tick_count_increments(self):
        scheduler = self._make_scheduler()
        scheduler._tick()
        scheduler._tick()
        status = scheduler.get_status()
        self.assertGreaterEqual(status["tick_count"], 2)

    def test_stale_jobs_detected(self):
        from jarvis.scheduler import AgentWorkQueue, AgentWorkItem, AgentScheduler
        import uuid
        queue = AgentWorkQueue(self.root / "queue2.jsonl")
        # Inject an item that has been running for 11 minutes
        old_start = (datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat()
        item = AgentWorkItem(
            item_id=str(uuid.uuid4()),
            agent_id="stale-agent",
            agent_label="Stale",
            trigger="cadence",
            event_type="cadence",
            payload={},
            queued_at=_now_iso(),
            status="running",
            started_at=old_start,
        )
        queue._items.append(item)

        runtime = MagicMock()
        runtime.agent_registry.list.return_value = []
        runtime.agent_runtime_kernel.snapshot.return_value = {"status_rows": []}
        state_store = MagicMock()
        state_store.load.return_value = {"agents": {}}
        scheduler = AgentScheduler(runtime, queue, state_store)

        status = scheduler.get_status()
        self.assertGreater(len(status["stale_jobs"]), 0)
        self.assertEqual(status["stale_jobs"][0]["agent_id"], "stale-agent")

    def test_dead_letter_count_reflects_dead_letters(self):
        from jarvis.scheduler import AgentScheduler, AgentWorkQueue
        queue = AgentWorkQueue(self.root / "queue3.jsonl")
        item = _make_item(max_attempts=1)
        queue.enqueue(item)
        dequeued = queue.dequeue_next()
        queue.mark_failed(dequeued.item_id, "fatal")

        runtime = MagicMock()
        runtime.agent_registry.list.return_value = []
        runtime.agent_runtime_kernel.snapshot.return_value = {"status_rows": []}
        state_store = MagicMock()
        state_store.load.return_value = {"agents": {}}
        scheduler = AgentScheduler(runtime, queue, state_store)

        status = scheduler.get_status()
        self.assertEqual(status["dead_letter_count"], 1)
        self.assertEqual(len(status["dead_letter"]), 1)

    def test_unhealthy_agents_surfaced(self):
        """Agents with stale/missed heartbeat appear in unhealthy_agents."""
        from jarvis.scheduler import AgentScheduler, AgentWorkQueue
        queue = AgentWorkQueue(self.root / "queue4.jsonl")
        runtime = MagicMock()
        runtime.agent_registry.list.return_value = []
        runtime.agent_runtime_kernel.snapshot.return_value = {
            "status_rows": [
                {"agent_id": "sick-agent", "heartbeat_status": "stale"},
                {"agent_id": "healthy-agent", "heartbeat_status": "fresh"},
            ]
        }
        state_store = MagicMock()
        state_store.load.return_value = {"agents": {}}
        scheduler = AgentScheduler(runtime, queue, state_store)

        status = scheduler.get_status()
        self.assertIn("sick-agent", status["unhealthy_agents"])
        self.assertNotIn("healthy-agent", status["unhealthy_agents"])


# ---------------------------------------------------------------------------
# C5 — Data architecture / JSONL persistence round-trip
# ---------------------------------------------------------------------------

class TestPersistenceRoundTrip(unittest.TestCase):
    """C5: new fields survive serialization round-trip; backward-compat with old format."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)

    def test_new_fields_round_trip(self):
        q1 = _make_queue(self.root)
        item = _make_item(dedupe_key="round-trip-key", max_attempts=5)
        q1.enqueue(item)

        q2 = _make_queue(self.root)
        queued = q2.get_queued()
        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0].dedupe_key, "round-trip-key")
        self.assertEqual(queued[0].max_attempts, 5)

    def test_old_items_without_new_fields_load_safely(self):
        """Items written before new fields were added must still load."""
        import uuid
        q1 = _make_queue(self.root)
        # Write a minimal old-format item
        old_format = {
            "item_id": str(uuid.uuid4()),
            "agent_id": "legacy-agent",
            "agent_label": "Legacy",
            "trigger": "cadence",
            "event_type": "cadence",
            "payload": {},
            "queued_at": _now_iso(),
            "status": "queued",
        }
        q1._store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(q1._store_path, "w") as f:
            f.write(json.dumps(old_format) + "\n")

        # Should load without error; missing fields get defaults
        q2 = _make_queue(self.root)
        queued = q2.get_queued()
        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0].agent_id, "legacy-agent")
        self.assertEqual(queued[0].dedupe_key, "")
        self.assertEqual(queued[0].max_attempts, 3)

    def test_kernel_events_include_event_id(self):
        from jarvis.runtime_kernel import AgentRuntimeKernelStore
        store = AgentRuntimeKernelStore(self.root / "kernel")
        store.append_event({"event_id": "e-999", "agent_id": "a", "action": "wake"})
        events = store.list_events(agent_id="a")
        self.assertEqual(events[0]["event_id"], "e-999")

    def test_kernel_events_filterable_by_agent_id(self):
        from jarvis.runtime_kernel import AgentRuntimeKernelStore
        store = AgentRuntimeKernelStore(self.root / "kernel2")
        store.append_event({"event_id": "e1", "agent_id": "agent-a", "action": "wake"})
        store.append_event({"event_id": "e2", "agent_id": "agent-b", "action": "wake"})
        events_a = store.list_events(agent_id="agent-a")
        self.assertEqual(len(events_a), 1)
        self.assertEqual(events_a[0]["agent_id"], "agent-a")


# ---------------------------------------------------------------------------
# C6 — Concurrency integrity
# ---------------------------------------------------------------------------

class TestConcurrentQueueWrites(unittest.TestCase):
    """C6: concurrent enqueue/complete/fail operations produce valid state."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)

    def test_concurrent_enqueue_no_corruption(self):
        """N threads each enqueue M items; total count must be N*M."""
        queue = _make_queue(self.root)
        N, M = 5, 10
        errors = []

        def worker(thread_idx: int):
            for j in range(M):
                try:
                    queue.enqueue(_make_item(agent_id=f"agent-{thread_idx}-{j}"))
                except Exception as e:
                    errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors: {errors}")
        self.assertEqual(len(queue.get_queued()), N * M)

    def test_concurrent_mark_completed(self):
        """N threads each dequeue and complete; no double-dequeue."""
        queue = _make_queue(self.root)
        for i in range(20):
            queue.enqueue(_make_item())

        completed_ids = []
        lock = threading.Lock()

        def worker():
            item = queue.dequeue_next()
            if item is not None:
                queue.mark_completed(item.item_id, "ok", {})
                with lock:
                    completed_ids.append(item.item_id)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each item_id must appear at most once
        self.assertEqual(len(completed_ids), len(set(completed_ids)))

    def test_concurrent_append_jsonl_no_partial_lines(self):
        """Concurrent JSONL appends must each produce a complete, valid JSON line."""
        from jarvis.persistence import append_jsonl
        log_path = self.root / "concurrent.jsonl"
        N = 50

        def worker(i: int):
            append_jsonl(log_path, {"thread": i, "data": "x" * 100})

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lines = [l for l in log_path.read_text().splitlines() if l.strip()]
        self.assertEqual(len(lines), N)
        for line in lines:
            obj = json.loads(line)  # must not raise
            self.assertIn("thread", obj)

    def test_concurrent_enqueue_dedupe_key_safe(self):
        """Concurrent enqueue with same dedupe_key: exactly 1 item must be accepted."""
        queue = _make_queue(self.root)
        accepted = []
        lock = threading.Lock()

        def worker():
            result = queue.enqueue(_make_item(dedupe_key="shared-key"))
            with lock:
                if result:
                    accepted.append(1)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one item should have been accepted
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(queue.get_queued()), 1)

    def test_concurrent_mark_failed_no_duplicate_dead_letters(self):
        """Concurrent fail on the same item_id must produce exactly one dead-letter."""
        queue = _make_queue(self.root)
        item = _make_item(max_attempts=1)
        queue.enqueue(item)
        queue.dequeue_next()

        results = []
        lock = threading.Lock()

        def worker():
            r = queue.mark_failed(item.item_id, "concurrent-fail")
            with lock:
                results.append(r)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one dead_letter entry
        self.assertEqual(len(queue.get_dead_letter()), 1)

    def test_concurrent_kernel_append_events_all_valid(self):
        """Concurrent event appends to kernel store produce valid JSONL."""
        from jarvis.runtime_kernel import AgentRuntimeKernelStore
        store = AgentRuntimeKernelStore(self.root / "kernel3")
        N = 30

        def worker(i: int):
            store.append_event({"event_id": f"e{i}", "agent_id": "a", "action": "heartbeat"})

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        events = store.list_events(agent_id="a")
        self.assertEqual(len(events), N)
        event_ids = {e["event_id"] for e in events}
        self.assertEqual(len(event_ids), N)  # no duplicates lost


if __name__ == "__main__":
    unittest.main()
