from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.approvals import ApprovalQueue, ApprovalRequest, RiskTier


class ApprovalQueueStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.original_root = ApprovalQueue.ROOT
        ApprovalQueue.ROOT = Path(self.tempdir.name) / "approvals"
        self.addCleanup(self._restore_root)

    def _restore_root(self) -> None:
        ApprovalQueue.ROOT = self.original_root

    def _request(self, request_id: str, *, status: str = "pending") -> ApprovalRequest:
        return ApprovalRequest(
            request_id=request_id,
            agent_id="pepper",
            agent_label="Pepper",
            action_type="other",
            title="Test action",
            description="Stage a governed action",
            payload={"value": 1},
            risk_tier=RiskTier.MEDIUM.value,
            actor_id="chris",
            requested_at="2026-06-02T10:00:00+00:00",
            expires_at="2026-06-03T10:00:00+00:00",
            status=status,
        )

    def test_replays_active_queue_from_state_log_when_snapshot_is_blank(self) -> None:
        queue = ApprovalQueue()
        queue.submit(self._request("req-1"))
        queue._queue_path.write_text("", encoding="utf-8")

        replayed = ApprovalQueue()
        pending = replayed.get_pending()

        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].request_id, "req-1")
        self.assertEqual(pending[0].status, "pending")

    def test_replays_history_from_state_log_when_snapshot_is_blank(self) -> None:
        queue = ApprovalQueue()
        queue.submit(self._request("req-2"))
        queue.reject("req-2", reason="Not now", rejected_by="chris")
        queue._history_path.write_text("", encoding="utf-8")

        replayed = ApprovalQueue()
        history = replayed.get_history(limit=10)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].request_id, "req-2")
        self.assertEqual(history[0].status, "rejected")


if __name__ == "__main__":
    unittest.main()
