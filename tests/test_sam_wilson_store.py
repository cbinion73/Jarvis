from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from jarvis import sam_wilson


class SamWilsonStoreTests(unittest.TestCase):
    def test_replays_protocol_cache_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "sam_protocol_today.json"
            cache_log_path = Path(tmp) / "sam_protocol_today_log.jsonl"
            payload = {
                "date": "Monday, June 2",
                "greeting": "Let's get to work.",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            with (
                patch.object(sam_wilson, "PROTOCOL_CACHE", cache_path),
                patch.object(sam_wilson, "PROTOCOL_CACHE_LOG", cache_log_path),
            ):
                sam_wilson._save_snapshot(cache_path, cache_log_path, payload)
                cache_path.write_text("", encoding="utf-8")

                loaded = sam_wilson.get_cached_protocol()

                self.assertIsNotNone(loaded)
                self.assertEqual(loaded["greeting"], "Let's get to work.")

    def test_replays_food_preferences_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prefs_path = Path(tmp) / "sam_food_prefs.json"
            prefs_log_path = Path(tmp) / "sam_food_prefs_log.jsonl"
            payload = {
                "interview_step": 3,
                "interview_complete": True,
                "interview_notes": {},
                "likes": ["salmon"],
                "dislikes": ["banana"],
                "allergies": [],
                "typical_meals": "eggs",
                "eat_out_freq": "weekly",
                "cooking_skill": "comfortable",
                "cravings": ["pizza"],
                "goals": "better glucose control",
                "wins": ["Greek yogurt"],
                "updated_at": "2026-06-02T12:00:00+00:00",
            }

            with (
                patch.object(sam_wilson, "FOOD_PREFS_PATH", prefs_path),
                patch.object(sam_wilson, "FOOD_PREFS_LOG_PATH", prefs_log_path),
            ):
                sam_wilson.save_food_preferences(dict(payload))
                prefs_path.write_text("", encoding="utf-8")

                loaded = sam_wilson.get_food_preferences()

                self.assertTrue(loaded["interview_complete"])
                self.assertEqual(loaded["likes"], ["salmon"])

    def test_replays_journal_and_adherence_state_from_append_logs_when_snapshots_are_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_path = Path(tmp) / "sam_daily_journal.jsonl"
            journal_state_log = Path(tmp) / "sam_daily_journal_state_log.jsonl"
            adherence_path = Path(tmp) / "sam_adherence.jsonl"
            adherence_state_log = Path(tmp) / "sam_adherence_state_log.jsonl"

            with (
                patch.object(sam_wilson, "JOURNAL_PATH", journal_path),
                patch.object(sam_wilson, "JOURNAL_STATE_LOG", journal_state_log),
                patch.object(sam_wilson, "ADHERENCE_LOG", adherence_path),
                patch.object(sam_wilson, "ADHERENCE_STATE_LOG", adherence_state_log),
            ):
                sam_wilson._upsert_journal(
                    "2026-06-02",
                    "Walked 30 minutes and had eggs.",
                    {"exercise": [], "food": [], "water_oz": 0, "caffeine": "", "alcohol": False, "mood": "good", "stress_level": None, "energy_level": None, "sleep_quality": None, "physical_symptoms": [], "mental_notes": "", "wins": [], "challenges": [], "adherence_items": ["breakfast"]},
                    25.0,
                    ["breakfast"],
                )
                sam_wilson._upsert_adherence("2026-06-02", ["breakfast"])

                journal_path.write_text("", encoding="utf-8")
                adherence_path.write_text("", encoding="utf-8")

                journal_records = json.loads(journal_state_log.read_text(encoding="utf-8").splitlines()[-1])["records"]
                adherence_records = json.loads(adherence_state_log.read_text(encoding="utf-8").splitlines()[-1])["records"]

                self.assertEqual(journal_records[0]["date"], "2026-06-02")
                self.assertEqual(journal_records[0]["total_protein_g"], 25.0)
                self.assertEqual(adherence_records[0]["completed"], ["breakfast"])


if __name__ == "__main__":
    unittest.main()
