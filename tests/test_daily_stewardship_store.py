from __future__ import annotations

import asyncio
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

from jarvis import daily_stewardship


class DailyStewardshipStoreTests(unittest.TestCase):
    def test_replays_day_card_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            day_card_path = Path(tmp) / "day_card.json"
            day_card_log_path = Path(tmp) / "day_card_log.jsonl"
            day_card_state_log_path = Path(tmp) / "day_card_state_log.jsonl"
            day_card = {
                "date": date.today().isoformat(),
                "day_type": "Maintain",
                "readiness_score": 72,
                "oracle_pathway": "O-CLEAR",
                "oracle_summary": "Stable",
                "signals": {"sleep_hours": 7.1},
                "classification_reason": "Normal readiness",
                "three_moves": [{"move": "Walk after lunch"}],
                "if_then_rule": "If tired, take a short walk.",
                "context": None,
                "generated_at": "2026-06-02T09:00:00",
            }

            with (
                patch.object(daily_stewardship, "_DAY_CARD_PATH", day_card_path),
                patch.object(daily_stewardship, "_DAY_CARD_LOG_PATH", day_card_log_path),
                patch.object(daily_stewardship, "_DAY_CARD_STATE_LOG_PATH", day_card_state_log_path),
            ):
                daily_stewardship._save_day_card(day_card)

                day_card_path.write_text("", encoding="utf-8")
                day_card_log_path.write_text("", encoding="utf-8")
                replayed = daily_stewardship.get_cached_day_card()

                self.assertIsNotNone(replayed)
                assert replayed is not None
                self.assertEqual(replayed["day_type"], "Maintain")
                self.assertEqual(replayed["three_moves"][0]["move"], "Walk after lunch")

    def test_run_morning_checkin_writes_append_log_backed_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            day_card_path = Path(tmp) / "day_card.json"
            day_card_log_path = Path(tmp) / "day_card_log.jsonl"
            day_card_state_log_path = Path(tmp) / "day_card_state_log.jsonl"

            with (
                patch.object(daily_stewardship, "_DAY_CARD_PATH", day_card_path),
                patch.object(daily_stewardship, "_DAY_CARD_LOG_PATH", day_card_log_path),
                patch.object(daily_stewardship, "_DAY_CARD_STATE_LOG_PATH", day_card_state_log_path),
                patch.object(
                    daily_stewardship,
                    "get_morning_signals",
                    AsyncMock(return_value={"sleep_hours": 7.5, "hrv": 51, "resting_hr": 58, "latest_glucose": 110}),
                ),
                patch.object(
                    daily_stewardship,
                    "_get_oracle_pathway_lightweight",
                    AsyncMock(return_value=("O-CLEAR", "Steady today.")),
                ),
                patch.object(
                    daily_stewardship,
                    "classify_day_type",
                    AsyncMock(return_value={"day_type": "Push", "reason": "Strong readiness", "readiness_score": 91}),
                ),
                patch.object(
                    daily_stewardship,
                    "generate_three_moves",
                    AsyncMock(return_value=[{"move": "Honor the Push plan."}]),
                ),
                patch.object(daily_stewardship, "_generate_if_then_rule", return_value="If energy dips, walk."),
            ):
                card = asyncio.run(daily_stewardship.run_morning_checkin())

                self.assertEqual(card["oracle_summary"], "Steady today.")
                self.assertTrue(day_card_path.exists())
                self.assertTrue(day_card_log_path.exists())
                self.assertTrue(day_card_state_log_path.exists())

                day_card_path.write_text("", encoding="utf-8")
                day_card_log_path.write_text("", encoding="utf-8")
                replayed = daily_stewardship.get_cached_day_card()

                self.assertIsNotNone(replayed)
                assert replayed is not None
                self.assertEqual(replayed["oracle_summary"], "Steady today.")
                self.assertEqual(replayed["if_then_rule"], "If energy dips, walk.")


if __name__ == "__main__":
    unittest.main()
