from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path

from jarvis.scheduler import AgentWorkItem, AgentWorkQueue


def _item(*, status: str = "queued", priority: int = 5, agent_id: str = "ambient-router") -> AgentWorkItem:
    return AgentWorkItem(
        item_id=str(uuid.uuid4()),
        agent_id=agent_id,
        agent_label="Ambient Router",
        trigger="manual",
        event_type="manual",
        payload={"source": "test"},
        queued_at="2026-06-02T06:00:00+00:00",
        status=status,
        priority=priority,
    )


class SchedulerQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.queue_path = Path(self.tempdir.name) / "scheduler" / "queue.jsonl"
        self.db_path = self.queue_path.parent / "scheduler.db"

    # ------------------------------------------------------------------
    # Core durability
    # ------------------------------------------------------------------

    def test_enqueue_persists_and_reloads(self) -> None:
        queue = AgentWorkQueue(self.queue_path)
        queued = _item(priority=3)

        queue.enqueue(queued)

        reloaded = AgentWorkQueue(self.queue_path)
        persisted = reloaded.get_queued()
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0].item_id, queued.item_id)
        self.assertEqual(persisted[0].priority, 3)

    def test_dequeue_marks_running_and_remains_durable(self) -> None:
        """After dequeue an item is 'running'.  On restart zombie recovery
        resets it to 'queued' so it is re-attempted rather than lost.
        """
        queue = AgentWorkQueue(self.queue_path)
        queue.enqueue(_item(priority=7))
        queue.enqueue(_item(priority=2))

        next_item = queue.dequeue_next()

        self.assertIsNotNone(next_item)
        self.assertEqual(next_item.priority, 2)
        self.assertEqual(next_item.status, "running")

        # Simulate restart: new queue instance loads from SQLite.
        # Zombie recovery resets stuck-running items back to queued.
        reloaded = AgentWorkQueue(self.queue_path)
        found = [i for i in reloaded.get_by_agent("ambient-router") if i.item_id == next_item.item_id]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].status, "queued")
        self.assertEqual(found[0].started_at, "")

    def test_crash_recovery_from_sqlite(self) -> None:
        """Items survive a hard restart (connection closed without clean shutdown)."""
        queue = AgentWorkQueue(self.queue_path)
        a = _item(priority=4)
        queue.enqueue(a)
        queue._conn.close()  # simulate abrupt shutdown

        reloaded = AgentWorkQueue(self.queue_path)
        persisted = reloaded.get_queued()
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0].item_id, a.item_id)

    def test_completed_items_restore_correctly(self) -> None:
        queue = AgentWorkQueue(self.queue_path)
        item = _item()
        queue.enqueue(item)
        queue.dequeue_next()
        queue.mark_completed(item.item_id, "done", {"output": "ok"})

        reloaded = AgentWorkQueue(self.queue_path)
        recent = reloaded.get_recent(limit=5)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].status, "completed")
        self.assertEqual(recent[0].result_text, "done")

    def test_event_history_restores_correctly(self) -> None:
        queue = AgentWorkQueue(self.queue_path)
        item = _item()
        queue.enqueue(item)
        queue.dequeue_next()
        queue.mark_completed(item.item_id, "ok", {})

        conn = sqlite3.connect(str(self.db_path))
        rows = conn.execute(
            "SELECT event_type FROM queue_events WHERE item_id = ? ORDER BY event_id",
            (item.item_id,),
        ).fetchall()
        conn.close()

        event_types = [r[0] for r in rows]
        self.assertIn("item_queued", event_types)
        self.assertIn("item_started", event_types)
        self.assertIn("item_completed", event_types)

    # ------------------------------------------------------------------
    # Storage guarantees
    # ------------------------------------------------------------------

    def test_no_jsonl_files_written(self) -> None:
        """queue.jsonl and queue_state_log.jsonl must never be created."""
        queue = AgentWorkQueue(self.queue_path)
        for _ in range(10):
            item = _item()
            queue.enqueue(item)
            queue.dequeue_next()
            queue.mark_completed(item.item_id, "x", {})

        state_log = self.queue_path.parent / "queue_state_log.jsonl"
        self.assertFalse(self.queue_path.exists(), "queue.jsonl must not be written")
        self.assertFalse(state_log.exists(), "queue_state_log.jsonl must not be written")

    def test_100k_state_updates_bounded_growth(self) -> None:
        """100 000 state-change events must not cause unbounded DB growth.

        queue_items stays at O(distinct items); queue_events grows O(events) but
        is prunable.  The critical invariant: each update UPSERTs the same row,
        not appends a new one.
        """
        queue = AgentWorkQueue(self.queue_path)

        # Enqueue one item and cycle it through complete 100 000 times.
        # Each cycle: enqueue → dequeue → complete = 3 events, 1 row in queue_items.
        CYCLES = 100_000
        for _ in range(CYCLES):
            item = _item()
            queue.enqueue(item)
            dequeued = queue.dequeue_next()
            if dequeued:
                queue.mark_completed(dequeued.item_id, "x", {})
                # purge so in-memory list doesn't grow
                queue.purge_old(max_age_hours=0)

        conn = sqlite3.connect(str(self.db_path))
        item_count = conn.execute("SELECT COUNT(*) FROM queue_items").fetchone()[0]
        event_count = conn.execute("SELECT COUNT(*) FROM queue_events").fetchone()[0]
        conn.close()

        # queue_items must be empty after purge (all completed items purged)
        self.assertEqual(item_count, 0, "All completed items should be purged")

        # Each cycle emits 3 events. Events are retained by time not count.
        # Since these are fresh (just created), they won't be pruned yet.
        # The important check: event_count scales with CYCLES * 3, not with
        # queue_items squared.  Rough upper bound: 4 events per cycle.
        self.assertLessEqual(event_count, CYCLES * 4)

        # DB file size must be reasonable — less than 500 MB
        db_size_mb = self.db_path.stat().st_size / (1024 * 1024)
        self.assertLess(db_size_mb, 500, f"DB grew to {db_size_mb:.1f} MB — exceeds 500 MB limit")

    def test_event_cleanup_removes_old_events(self) -> None:
        """cleanup_old_events() deletes rows older than 30 days."""
        queue = AgentWorkQueue(self.queue_path)
        item = _item()
        queue.enqueue(item)

        # Back-date the event to 31 days ago
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "UPDATE queue_events SET created_at = datetime('now', '-31 days')"
        )
        conn.commit()
        conn.close()

        deleted = queue.cleanup_old_events()
        self.assertGreater(deleted, 0)

        conn = sqlite3.connect(str(self.db_path))
        remaining = conn.execute("SELECT COUNT(*) FROM queue_events").fetchone()[0]
        conn.close()
        self.assertEqual(remaining, 0)

    # ------------------------------------------------------------------
    # Migration from legacy JSONL
    # ------------------------------------------------------------------

    def test_auto_migrates_active_items_from_queue_jsonl(self) -> None:
        """If queue.jsonl exists with active items and scheduler.db is absent,
        the constructor migrates active items automatically.
        """
        import json
        active = _item(status="queued", priority=2)
        done = _item(status="completed", priority=5)

        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        with self.queue_path.open("w") as f:
            f.write(json.dumps({k: v for k, v in vars(active).items()}) + "\n")
            f.write(json.dumps({k: v for k, v in vars(done).items()}) + "\n")

        queue = AgentWorkQueue(self.queue_path)
        queued = queue.get_queued()

        # Only the active item is imported; completed is skipped
        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0].item_id, active.item_id)


if __name__ == "__main__":
    unittest.main()
