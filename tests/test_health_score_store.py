from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import health_score


class HealthScoreStoreTests(unittest.TestCase):
    def test_replays_sleep_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleep_path = root / "sleep_log.jsonl"
            sleep_state_log = root / "sleep_log_state_log.jsonl"

            sleep_path.write_text("", encoding="utf-8")
            sleep_state_log.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "date": "2026-06-02",
                                "total_hours": 7.25,
                                "sleep_quality": 8,
                                "notes": "solid",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with (
                patch.object(health_score, "SLEEP_LOG", sleep_path),
                patch.object(health_score, "SLEEP_STATE_LOG", sleep_state_log),
            ):
                sleep = health_score._load_sleep("2026-06-02")

                self.assertEqual(sleep["date"], "2026-06-02")
                self.assertEqual(sleep["total_hours"], 7.25)
                self.assertEqual(sleep["sleep_quality"], 8)

    def test_replays_score_history_from_state_log_when_snapshot_is_blank(self) -> None:
        from datetime import date as _date
        today_str = _date.today().isoformat()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            score_path = root / "health_scores.jsonl"
            score_state_log = root / "health_scores_state_log.jsonl"

            score_path.write_text("", encoding="utf-8")
            score_state_log.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "date": today_str,
                                "score": 84,
                                "grade": "B",
                                "color": "#22c55e",
                                "has_data": True,
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with (
                patch.object(health_score, "SCORE_LOG", score_path),
                patch.object(health_score, "SCORE_STATE_LOG", score_state_log),
                patch.object(health_score, "compute_daily_score", side_effect=AssertionError("should not recompute cached score")),
            ):
                history = health_score.get_score_history(days=1)

                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]["score"], 84)
                self.assertEqual(history[0]["grade"], "B")

    def test_replays_nutrition_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nutrition_path = root / "nutrition_log.jsonl"
            nutrition_state_log = root / "nutrition_log_state_log.jsonl"

            nutrition_path.write_text("", encoding="utf-8")
            nutrition_state_log.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-06-02T12:00:00+00:00",
                        "records": [
                            {
                                "date": "2026-06-02",
                                "meals": [
                                    {
                                        "name": "Egg Bites",
                                        "protein_g": 22,
                                        "carb_g": 10,
                                        "fat_g": 9,
                                        "calories": 210,
                                    }
                                ],
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with (
                patch.object(health_score, "NUTRITION_LOG", nutrition_path),
                patch.object(health_score, "NUTRITION_STATE_LOG", nutrition_state_log),
            ):
                nutrition = health_score._load_nutrition("2026-06-02")

                self.assertEqual(nutrition["protein_g"], 22.0)
                self.assertEqual(nutrition["carb_g"], 10.0)
                self.assertEqual(nutrition["meal_names"], ["egg bites"])

    def test_replays_journal_and_adherence_from_state_logs_when_snapshots_are_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journal_path = root / "sam_daily_journal.jsonl"
            adherence_path = root / "sam_adherence.jsonl"
            journal_state_log = root / "sam_daily_journal_state_log.jsonl"
            adherence_state_log = root / "sam_adherence_state_log.jsonl"

            journal_path.write_text("", encoding="utf-8")
            adherence_path.write_text("", encoding="utf-8")
            journal_state_log.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-06-02T12:00:00+00:00",
                        "records": [{"date": "2026-06-02", "extracted": {"water_oz": 48}}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            adherence_state_log.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-06-02T12:00:00+00:00",
                        "records": [{"date": "2026-06-02", "completed": ["breakfast"]}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with (
                patch.object(health_score, "JOURNAL_LOG", journal_path),
                patch.object(health_score, "ADHERENCE_LOG", adherence_path),
                patch.object(health_score, "JOURNAL_STATE_LOG", journal_state_log),
                patch.object(health_score, "ADHERENCE_STATE_LOG", adherence_state_log),
            ):
                journal = health_score._load_journal("2026-06-02")
                adherence = health_score._load_adherence("2026-06-02")

                self.assertEqual(journal["date"], "2026-06-02")
                self.assertEqual(journal["extracted"]["water_oz"], 48)
                self.assertEqual(adherence["completed"], ["breakfast"])


if __name__ == "__main__":
    unittest.main()
