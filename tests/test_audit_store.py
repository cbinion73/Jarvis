from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.audit import AuditLog


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


if __name__ == "__main__":
    unittest.main()
