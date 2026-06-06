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

    def test_record_remediation_persists_remediation_state_and_watch_transition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = RecoveryCaseStore(root)
            created = store.upsert_case(
                source_kind="integration-failure",
                title="Repair Maps bridge",
                detail="Route relay needs a safe remediation plan.",
                related_route="/recovery-center",
                related_key="integration:maps-bridge",
            )

            staged = store.record_remediation(
                created["case_id"],
                actor="Chris",
                action_type="stage",
                note="Stage auto-remediation before the next route hydration window.",
            )
            executed = store.record_remediation(
                created["case_id"],
                actor="Chris",
                action_type="execute",
                note="Execute auto-remediation after the route hydration window opens.",
            )

            self.assertEqual(staged["remediation_status"], "staged")
            self.assertEqual(staged["remediation_status_label"], "Staged")
            self.assertEqual(staged["remediation_count"], 1)
            self.assertEqual(executed["remediation_status"], "executed")
            self.assertEqual(executed["remediation_status_label"], "Executed")
            self.assertEqual(executed["remediation_count"], 2)
            self.assertEqual(executed["status"], "watch")
            self.assertEqual(executed["status_label"], "Watch")
            self.assertEqual(executed["history"][-1]["action"], "remediation-execute")
            self.assertEqual(executed["history"][-1]["detail"], "Execute auto-remediation after the route hydration window opens.")

            snapshot = json.loads(store.path.read_text(encoding="utf-8"))
            self.assertEqual(snapshot[0]["remediation_count"], 2)
            self.assertEqual(snapshot[0]["last_remediation_action"], "execute")


if __name__ == "__main__":
    unittest.main()
