from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.audit import AuditLog, ProgressFocusStore, SeamTrackerStore


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

    def test_seam_tracker_store_replays_current_records_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SeamTrackerStore(Path(tmp) / "logs")

            saved = store.save_seam_state(
                name="Progress Module Standalone Surface",
                module="Progress",
                status="Durable",
                note="Progress seam is now durable and linked to the hosted closure lane.",
                actor="Chris",
                route="/progress-center",
                linked_mission={
                    "mission_id": "mission-1",
                    "title": "Hosted closure lane",
                    "lane": "now",
                    "route": "/mission-board",
                },
            )
            store.current_path.write_text("", encoding="utf-8")

            replayed = SeamTrackerStore(Path(tmp) / "logs").summary()

            self.assertEqual(replayed["records"][0]["name"], "Progress Module Standalone Surface")
            self.assertEqual(replayed["records"][0]["status"], "Durable")
            self.assertEqual(replayed["records"][0]["linked_mission"]["mission_id"], "mission-1")
            self.assertEqual(replayed["history_count"], 1)
            self.assertEqual(replayed["recent"][0]["operator_note"], saved["operator_note"])


if __name__ == "__main__":
    unittest.main()
