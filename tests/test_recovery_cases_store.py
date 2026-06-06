from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jarvis.recovery_cases import RecoveryCaseStore


class RecoveryCaseStoreTests(unittest.TestCase):
    def test_replays_cases_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = RecoveryCaseStore(root)
            created = store.upsert_case(
                source_kind="integration-failure",
                title="Repair Google Workspace",
                detail="OAuth callback drift needs review.",
                related_route="/supervision-snapshot",
                related_key="integration:google-workspace",
            )

            store.path.write_text("[]\n", encoding="utf-8")
            replayed = RecoveryCaseStore(root).list_cases()

            self.assertEqual(len(replayed), 1)
            self.assertEqual(replayed[0]["case_id"], created["case_id"])
            self.assertEqual(replayed[0]["title"], "Repair Google Workspace")

    def test_update_status_persists_history_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = RecoveryCaseStore(root)
            created = store.upsert_case(
                source_kind="recent-failure",
                title="Route packet failed",
                detail="Calendar route lane timed out.",
                related_route="/command-center",
                related_key="failure:route-packet",
            )

            updated = store.update_status(
                created["case_id"],
                status="resolved",
                actor="Chris",
                note="Validated route packet after retry.",
            )

            self.assertEqual(updated["status"], "resolved")
            self.assertEqual(updated["status_label"], "Resolved")
            self.assertEqual(updated["history"][-1]["detail"], "Validated route packet after retry.")

            snapshot = json.loads(store.path.read_text(encoding="utf-8"))
            self.assertEqual(snapshot[0]["status"], "resolved")

    def test_record_execution_persists_execution_state_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = RecoveryCaseStore(root)
            created = store.upsert_case(
                source_kind="integration-failure",
                title="Repair Gmail bridge",
                detail="Bridge sync drift needs a retry loop.",
                related_route="/supervision-snapshot",
                related_key="integration:gmail-bridge",
            )

            updated = store.record_execution(
                created["case_id"],
                actor="Chris",
                action_type="retry",
                note="Executing retry loop from Recovery Center.",
            )

            self.assertEqual(updated["status"], "investigating")
            self.assertEqual(updated["status_label"], "Investigating")
            self.assertEqual(updated["execution_count"], 1)
            self.assertEqual(updated["last_execution_action"], "retry")
            self.assertEqual(updated["last_execution_status"], "executed")
            self.assertEqual(updated["history"][-1]["detail"], "Executing retry loop from Recovery Center.")

            snapshot = json.loads(store.path.read_text(encoding="utf-8"))
            self.assertEqual(snapshot[0]["execution_count"], 1)


if __name__ == "__main__":
    unittest.main()
