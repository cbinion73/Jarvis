from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import agent_memory
from jarvis.tools import memory as memory_tool


class AgentMemoryStoreTests(unittest.TestCase):
    def test_agent_memory_replays_facts_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            facts_path = Path(tmp) / "agent_facts.json"
            facts_log_path = Path(tmp) / "agent_facts_log.jsonl"
            facts_state_log_path = Path(tmp) / "agent_facts_state_log.jsonl"

            with (
                patch.object(agent_memory, "_FACTS_PATH", facts_path),
                patch.object(agent_memory, "_FACTS_LOG_PATH", facts_log_path),
                patch.object(agent_memory, "_FACTS_STATE_LOG_PATH", facts_state_log_path),
            ):
                agent_memory.append_fact("Chris prefers concise summaries.")
                facts_path.write_text("", encoding="utf-8")
                facts_log_path.write_text("", encoding="utf-8")

                formatted = agent_memory.load_facts()

                self.assertIn("Chris prefers concise summaries.", formatted)

    def test_memory_tool_replays_facts_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            facts_path = Path(tmp) / "agent_facts.json"
            facts_log_path = Path(tmp) / "agent_facts_log.jsonl"
            facts_state_log_path = Path(tmp) / "agent_facts_state_log.jsonl"

            with (
                patch.object(memory_tool, "_FACTS_PATH", facts_path),
                patch.object(memory_tool, "_FACTS_LOG_PATH", facts_log_path),
                patch.object(memory_tool, "_FACTS_STATE_LOG_PATH", facts_state_log_path),
            ):
                result = asyncio.run(memory_tool.run(operation="write", content="Rebekah handles school pickup on Tuesdays."))
                self.assertFalse(result.error)

                facts_path.write_text("", encoding="utf-8")
                facts_log_path.write_text("", encoding="utf-8")
                loaded = asyncio.run(memory_tool.run(operation="read"))

                self.assertIn("Rebekah handles school pickup on Tuesdays.", loaded.output)


if __name__ == "__main__":
    unittest.main()
