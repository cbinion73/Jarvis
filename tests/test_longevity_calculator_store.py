from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import longevity_calculator


class LongevityCalculatorStoreTests(unittest.TestCase):
    def test_replays_saved_estimate_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            estimate_path = Path(tmp) / "longevity_estimate.json"
            estimate_log_path = Path(tmp) / "longevity_estimate_log.jsonl"
            estimate_state_log_path = Path(tmp) / "longevity_estimate_state_log.jsonl"
            payload = {
                "computed_date": "2026-06-02",
                "estimated_life_expectancy": 78,
                "years_remaining": 25.5,
                "optimized_life_expectancy": 81,
                "trajectory_direction": "stable",
            }

            with (
                patch.object(longevity_calculator, "_ESTIMATE_PATH", estimate_path),
                patch.object(longevity_calculator, "_ESTIMATE_LOG_PATH", estimate_log_path),
                patch.object(longevity_calculator, "_ESTIMATE_STATE_LOG_PATH", estimate_state_log_path),
            ):
                longevity_calculator.append_jsonl(estimate_log_path, payload)
                longevity_calculator.append_jsonl(estimate_state_log_path, payload)
                longevity_calculator.atomic_write_json(estimate_path, payload)
                estimate_path.write_text("", encoding="utf-8")
                estimate_log_path.write_text("", encoding="utf-8")

                loaded = longevity_calculator.load_saved_estimate()

                self.assertEqual(loaded["estimated_life_expectancy"], 78)
                self.assertEqual(loaded["optimized_life_expectancy"], 81)


if __name__ == "__main__":
    unittest.main()
