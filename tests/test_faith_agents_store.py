from __future__ import annotations

import asyncio
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from jarvis import faith_agents


class FaithAgentsStoreTests(unittest.TestCase):
    def test_replays_daily_word_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            daily_word_path = Path(tmp) / "faith_daily_word.json"
            daily_word_log_path = Path(tmp) / "faith_daily_word_log.jsonl"
            daily_word_state_log_path = Path(tmp) / "faith_daily_word_state_log.jsonl"
            fresh_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            cached = {
                "ok": True,
                "agent_id": "ezra",
                "agent_name": "Ezra",
                "agent_title": "The Scribe",
                "color": "#C9A84C",
                "domain": "Exegesis & the Text",
                "passage": "",
                "word": "Hold fast to the Word today.",
                "generated_at": fresh_time,
            }

            with (
                patch.object(faith_agents, "_DAILY_WORD_PATH", daily_word_path),
                patch.object(faith_agents, "_DAILY_WORD_LOG_PATH", daily_word_log_path),
                patch.object(faith_agents, "_DAILY_WORD_STATE_LOG_PATH", daily_word_state_log_path),
            ):
                daily_word_path.parent.mkdir(parents=True, exist_ok=True)
                faith_agents.atomic_write_json(daily_word_path, cached)
                faith_agents.append_jsonl(daily_word_log_path, {"saved_at": fresh_time, "result": cached})
                faith_agents.append_jsonl(daily_word_state_log_path, {"saved_at": fresh_time, "result": cached})

                daily_word_path.write_text("", encoding="utf-8")
                daily_word_log_path.write_text("", encoding="utf-8")
                replayed = asyncio.run(faith_agents.daily_word(runtime=None))

                self.assertEqual(replayed["agent_id"], "ezra")
                self.assertEqual(replayed["word"], "Hold fast to the Word today.")


if __name__ == "__main__":
    unittest.main()
