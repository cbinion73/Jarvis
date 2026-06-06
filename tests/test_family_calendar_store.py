from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.family_calendar import FamilyCalendarSupport


class FamilyCalendarStoreTests(unittest.TestCase):
    def test_replays_settings_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "family_calendar.json"
            support = FamilyCalendarSupport(path=path)

            saved = support.save_settings(
                {
                    "label": "Wilson Family Calendar",
                    "source": "cozi",
                    "ics_url": "https://example.com/family.ics",
                }
            )

            path.write_text("", encoding="utf-8")
            support._log_path().write_text("", encoding="utf-8")
            loaded = support.load_settings()

            self.assertEqual(loaded, saved)


if __name__ == "__main__":
    unittest.main()
