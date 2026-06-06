from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import health_intelligence


class HealthIntelligenceStoreTests(unittest.TestCase):
    def test_replays_cached_analysis_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "helen_analysis.json"
            cache_log_path = Path(tmp) / "helen_analysis_log.jsonl"
            cache_state_log_path = Path(tmp) / "helen_analysis_state_log.jsonl"
            analysis = {
                "headline": "Steady but drifting upward on LDL.",
                "overall_score": 72,
                "risk_level": "moderate",
                "_generated_at": 9999999999,
                "_generated_utc": "2026-06-02T12:00:00",
            }

            with (
                patch.object(health_intelligence, "_CACHE_PATH", cache_path),
                patch.object(health_intelligence, "_CACHE_LOG_PATH", cache_log_path),
                patch.object(health_intelligence, "_CACHE_STATE_LOG_PATH", cache_state_log_path),
            ):
                health_intelligence._save_cached_analysis(analysis)
                cache_path.write_text("", encoding="utf-8")
                cache_log_path.write_text("", encoding="utf-8")

                replayed = health_intelligence.get_cached_analysis()

                self.assertIsNotNone(replayed)
                assert replayed is not None
                self.assertEqual(replayed["headline"], "Steady but drifting upward on LDL.")
                self.assertEqual(replayed["overall_score"], 72)


if __name__ == "__main__":
    unittest.main()
