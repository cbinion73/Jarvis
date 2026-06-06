from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import quarterly_review


class QuarterlyReviewStoreTests(unittest.TestCase):
    def test_replays_objectives_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            objectives_path = Path(tmp) / "quarterly_objectives.json"
            objectives_log_path = Path(tmp) / "quarterly_objectives_log.jsonl"
            objectives_state_log_path = Path(tmp) / "quarterly_objectives_state_log.jsonl"

            objectives = [
                {
                    "objective": "Lower LDL",
                    "domain": "cardio",
                    "why_it_matters": "Reduce ASCVD risk",
                    "baseline": "156 mg/dL",
                    "target": "<100 mg/dL",
                    "weekly_actions": ["Walk after dinner"],
                    "measurement_plan": "Repeat lipid panel in 90 days",
                }
            ]

            with (
                patch.object(quarterly_review, "_OBJECTIVES_PATH", objectives_path),
                patch.object(quarterly_review, "_OBJECTIVES_LOG_PATH", objectives_log_path),
                patch.object(quarterly_review, "_OBJECTIVES_STATE_LOG_PATH", objectives_state_log_path),
            ):
                result = asyncio.run(quarterly_review.set_objectives(objectives))
                self.assertTrue(result["ok"])

                objectives_path.write_text("", encoding="utf-8")
                objectives_log_path.write_text("", encoding="utf-8")
                loaded = asyncio.run(quarterly_review.get_current_objectives())

                self.assertEqual(len(loaded), 1)
                self.assertEqual(loaded[0]["objective"], "Lower LDL")
                self.assertEqual(loaded[0]["target"], "<100 mg/dL")


if __name__ == "__main__":
    unittest.main()
