from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import reminders


class RemindersStoreTests(unittest.TestCase):
    def test_replays_reminders_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reminders_path = Path(tmp) / "reminders.json"
            reminders_log_path = Path(tmp) / "reminders_log.jsonl"
            reminders_state_log_path = Path(tmp) / "reminders_state_log.jsonl"

            with (
                patch.object(reminders, "_REMINDERS_PATH", reminders_path),
                patch.object(reminders, "_REMINDERS_LOG_PATH", reminders_log_path),
                patch.object(reminders, "_REMINDERS_STATE_LOG_PATH", reminders_state_log_path),
            ):
                created = reminders.add_reminder("Check launch status", "2026-06-03T09:00:00Z", "high")

                reminders_path.write_text("", encoding="utf-8")
                reminders_log_path.write_text("", encoding="utf-8")
                listed = reminders.list_reminders()

                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]["id"], created["id"])
                self.assertEqual(listed[0]["text"], "Check launch status")
                self.assertEqual(listed[0]["priority"], "high")


if __name__ == "__main__":
    unittest.main()
