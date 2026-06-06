from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import scenario_engine


class ScenarioEngineStoreTests(unittest.TestCase):
    def test_replays_saved_scenarios_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scenarios_path = Path(tmp) / "scenarios.jsonl"
            scenarios_state_log = Path(tmp) / "scenarios_state_log.jsonl"
            result = scenario_engine.ScenarioResult(
                scenario_name="weight_loss_10",
                changes_applied=["Lose 10% body weight"],
                timeframe_months=12,
                projected_outcomes=[],
                ascvd_risk_delta="-3%",
                safety_flags=[],
                evidence_grade="B",
                narrative="Risk improves modestly.",
                generated_at="2026-06-02T12:00:00",
            )

            with (
                patch.object(scenario_engine, "_SCENARIOS_LOG_PATH", scenarios_path),
                patch.object(scenario_engine, "_SCENARIOS_STATE_LOG_PATH", scenarios_state_log),
            ):
                scenario_engine.save_scenario(result)
                scenarios_path.write_text("", encoding="utf-8")

                loaded = scenario_engine.get_saved_scenarios()

                self.assertEqual(len(loaded), 1)
                self.assertEqual(loaded[0]["scenario_name"], "weight_loss_10")
                self.assertEqual(loaded[0]["ascvd_risk_delta"], "-3%")


if __name__ == "__main__":
    unittest.main()
