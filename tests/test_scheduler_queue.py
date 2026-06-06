from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from jarvis.scheduler import AgentWorkItem, AgentWorkQueue


def _item(*, status: str = "queued", priority: int = 5) -> AgentWorkItem:
    return AgentWorkItem(
        item_id=str(uuid.uuid4()),
        agent_id="ambient-router",
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
        queue = AgentWorkQueue(self.queue_path)
        queue.enqueue(_item(priority=7))
        queue.enqueue(_item(priority=2))

        next_item = queue.dequeue_next()

        self.assertIsNotNone(next_item)
        self.assertEqual(next_item.priority, 2)
        self.assertEqual(next_item.status, "running")

        reloaded = AgentWorkQueue(self.queue_path)
        running = [item for item in reloaded.get_by_agent("ambient-router") if item.item_id == next_item.item_id]
        self.assertEqual(len(running), 1)
        self.assertEqual(running[0].status, "running")
        self.assertTrue(running[0].started_at)

    def test_replays_queue_from_state_log_when_snapshot_is_blank(self) -> None:
        queue = AgentWorkQueue(self.queue_path)
        queued = _item(priority=4)

        queue.enqueue(queued)
        self.queue_path.write_text("", encoding="utf-8")

        reloaded = AgentWorkQueue(self.queue_path)
        persisted = reloaded.get_queued()

        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0].item_id, queued.item_id)
        self.assertEqual(persisted[0].priority, 4)


if __name__ == "__main__":
    unittest.main()
