from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.audit import AuditLog, ProgressFocusStore


class AuditLogStoreTests(unittest.TestCase):
    def test_replays_actions_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = AuditLog(Path(tmp) / "logs")

            log.log_event(
                "event",
                {
                    "actor": "chris",
                    "detail": "Captured runtime checkpoint",
                },
            )
            log.actions_path.write_text("", encoding="utf-8")

            recent = log.list_recent()

            self.assertEqual(len(recent), 1)
            self.assertEqual(recent[0]["entry_type"], "event")
            self.assertEqual(recent[0]["actor"], "chris")
            self.assertEqual(recent[0]["detail"], "Captured runtime checkpoint")

    def test_progress_focus_store_replays_focus_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProgressFocusStore(Path(tmp) / "logs")

            saved = store.save_focus(
                module="Recovery",
                reason="Recovery is the highest-risk remaining Level 3 seam.",
                route="/progress-center",
                actor="Chris",
            )
            store.current_path.write_text("", encoding="utf-8")

            replayed = ProgressFocusStore(Path(tmp) / "logs").summary()

            self.assertEqual(replayed["latest"]["module"], "Recovery")
            self.assertEqual(replayed["latest"]["reason"], saved["reason"])
            self.assertEqual(replayed["history_count"], 1)


if __name__ == "__main__":
    unittest.main()
