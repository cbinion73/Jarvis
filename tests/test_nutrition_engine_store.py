from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import nutrition_engine


class NutritionEngineStoreTests(unittest.TestCase):
    def test_replays_daily_log_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            log_path = health_dir / "nutrition_log.jsonl"
            log_state_path = health_dir / "nutrition_log_state_log.jsonl"
            entry = {
                "date": "2026-06-02",
                "meals": [
                    {
                        "name": "Protein Shake",
                        "protein_g": 30.0,
                        "carb_g": 8.0,
                        "fat_g": 4.0,
                        "calories": 190.0,
                        "time": "08:00",
                    }
                ],
                "notes": "",
            }

            with (
                patch.object(nutrition_engine, "_HEALTH_DIR", health_dir),
                patch.object(nutrition_engine, "_LOG_PATH", log_path),
                patch.object(nutrition_engine, "_LOG_STATE_PATH", log_state_path),
            ):
                nutrition_engine._write_log_entry(entry)
                log_path.write_text("", encoding="utf-8")

                replayed = nutrition_engine.get_daily_nutrition("2026-06-02")

                self.assertEqual(replayed.date, "2026-06-02")
                self.assertEqual(replayed.total_protein_g, 30.0)
                self.assertEqual(replayed.total_calories, 190.0)
                self.assertEqual(replayed.meals[0]["name"], "Protein Shake")

    def test_replays_cached_summary_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            summary_path = health_dir / "nutrition_summary.json"
            summary_log_path = health_dir / "nutrition_summary_log.jsonl"
            summary = {
                "period_start": "2026-05-27",
                "period_end": "2026-06-02",
                "days_logged": 4,
                "avg_protein_g": 96.5,
                "protein_adequacy_pct": 80.4,
                "summary": "Protein averaging 96.5g/day.",
                "cached_at": "2026-06-02T12:00:00+00:00",
            }

            with (
                patch.object(nutrition_engine, "_HEALTH_DIR", health_dir),
                patch.object(nutrition_engine, "_SUMMARY_PATH", summary_path),
                patch.object(nutrition_engine, "_SUMMARY_LOG_PATH", summary_log_path),
            ):
                nutrition_engine._save_cached_summary(summary)
                summary_path.write_text("", encoding="utf-8")

                replayed = nutrition_engine.get_cached_nutrition_summary()

                self.assertIsNotNone(replayed)
                assert replayed is not None
                self.assertEqual(replayed["avg_protein_g"], 96.5)
                self.assertEqual(replayed["summary"], "Protein averaging 96.5g/day.")


if __name__ == "__main__":
    unittest.main()
