from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.audit import ApprovalStore
from jarvis.models import ApprovalRequest


class ApprovalStoreTests(unittest.TestCase):
    def test_replays_pending_approvals_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ApprovalStore(Path(tmp) / "approvals")
            approval = ApprovalRequest(
                request_id="req-1",
                actor="chris",
                room="office",
                request="Approve outbound action",
                action_class="external_side_effect",
                second_factor_required=False,
                status="pending",
                rationale="Needs consent",
            )

            store.add(approval)
            store.pending_path.write_text("", encoding="utf-8")

            pending = store.list_pending()

            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["request_id"], "req-1")
            self.assertEqual(pending[0]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
