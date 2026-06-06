from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import llm_gateway


class LLMGatewayStoreTests(unittest.TestCase):
    def test_replays_usage_summary_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            usage_path = Path(tmp) / "llm_usage.jsonl"
            usage_state_log = Path(tmp) / "llm_usage_state_log.jsonl"
            entry = {
                "ts": 4102444800,
                "prompt_tokens": 120,
                "completion_tokens": 30,
                "model_used": "gpt-5.4-mini",
                "backend": "openai",
                "estimated_cost_usd": 0.000036,
            }

            with (
                patch.object(llm_gateway, "_USAGE_LOG_PATH", usage_path),
                patch.object(llm_gateway, "_USAGE_STATE_LOG_PATH", usage_state_log),
            ):
                llm_gateway._record_usage(entry)
                usage_path.write_text("", encoding="utf-8")

                summary = llm_gateway.usage_summary(hours=24 * 365 * 10)

                self.assertEqual(summary["total_calls"], 1)
                self.assertEqual(summary["prompt_tokens"], 120)
                self.assertEqual(summary["completion_tokens"], 30)
                self.assertIn("gpt-5.4-mini", summary["by_model"])


if __name__ == "__main__":
    unittest.main()
