from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import digital_twin


class DigitalTwinStoreTests(unittest.TestCase):
    def test_replays_twin_state_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            health_state_path = health_dir / "chris_health_state.json"
            twin_state_path = health_dir / "twin_state.json"
            twin_state_log_path = health_dir / "twin_state_log.jsonl"
            prediction_log_path = health_dir / "twin_predictions.jsonl"
            state = {
                "calibrated_at": "2026-06-02T12:00:00",
                "patient_context": {"name": "Chris"},
                "trajectories": {"a1c": {"current_value": 7.3}},
                "predictions": [],
            }

            with (
                patch.object(digital_twin, "_HEALTH_DIR", health_dir),
                patch.object(digital_twin, "_HEALTH_STATE_PATH", health_state_path),
                patch.object(digital_twin, "_TWIN_STATE_PATH", twin_state_path),
                patch.object(digital_twin, "_TWIN_STATE_LOG_PATH", twin_state_log_path),
                patch.object(digital_twin, "_PREDICTION_LOG_PATH", prediction_log_path),
            ):
                digital_twin._save_twin_state(state)
                twin_state_path.write_text("", encoding="utf-8")

                replayed = digital_twin._load_twin_state()

                self.assertIsNotNone(replayed)
                assert replayed is not None
                self.assertEqual(replayed["patient_context"]["name"], "Chris")
                self.assertEqual(replayed["trajectories"]["a1c"]["current_value"], 7.3)


if __name__ == "__main__":
    unittest.main()
