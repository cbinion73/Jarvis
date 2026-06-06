from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import health_bridge


class HealthBridgeStoreTests(unittest.TestCase):
    def test_replays_daily_snapshot_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            date = "2026-06-02"
            day_path = health_dir / f"{date}.json"
            day_log_path = health_dir / f"{date}_log.jsonl"

            with patch.object(health_bridge, "_HEALTH_DIR", health_dir):
                saved = health_bridge.ingest(
                    "shortcuts",
                    {"sleep_hours": 7.5, "hrv": 62, "resting_hr": 56},
                    date=date,
                )

                day_path.write_text("", encoding="utf-8")
                day_log_path.write_text("", encoding="utf-8")
                loaded = health_bridge._load_day(date)

                self.assertEqual(loaded["date"], saved["date"])
                self.assertEqual(loaded["source"], "shortcuts")
                self.assertEqual(loaded["sleep_hours"], 7.5)
                self.assertEqual(loaded["hrv"], 62)
                self.assertEqual(loaded["resting_hr"], 56)


if __name__ == "__main__":
    unittest.main()
