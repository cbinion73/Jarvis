from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from jarvis import sleep_intelligence


class SleepIntelligenceStoreTests(unittest.TestCase):
    def test_replays_sleep_log_from_state_log_when_snapshot_is_blank(self) -> None:
        # Relative to today: a hardcoded date silently ages out of the
        # 30-day retrieval window and turns this test into a time bomb.
        entry_date = (date.today() - timedelta(days=5)).isoformat()
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            sleep_log_path = health_dir / "sleep_log.jsonl"
            sleep_state_log_path = health_dir / "sleep_log_state_log.jsonl"

            with (
                patch.object(sleep_intelligence, "_HEALTH_DIR", health_dir),
                patch.object(sleep_intelligence, "_SLEEP_LOG", sleep_log_path),
                patch.object(sleep_intelligence, "_SLEEP_STATE_LOG", sleep_state_log_path),
            ):
                sleep_intelligence.log_sleep(
                    sleep_intelligence.SleepLog(
                        date=entry_date,
                        bedtime="23:00",
                        wake_time="06:30",
                        total_hours=7.5,
                        sleep_quality=7,
                        hrv_morning=None,
                        resting_hr=None,
                        spo2_min=None,
                        notes="steady night",
                    )
                )
                sleep_log_path.write_text("", encoding="utf-8")

                entries = sleep_intelligence._load_sleep_log_entries(days=30)

                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]["date"], entry_date)
                self.assertEqual(entries[0]["total_hours"], 7.5)


if __name__ == "__main__":
    unittest.main()
