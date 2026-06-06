from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import ideas


class IdeasStoreTests(unittest.TestCase):
    def test_replays_ideas_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ideas_path = Path(tmp) / "ideas.json"
            ideas_log_path = Path(tmp) / "ideas_log.jsonl"
            ideas_state_log_path = Path(tmp) / "ideas_state_log.jsonl"

            with (
                patch.object(ideas, "_IDEAS_PATH", ideas_path),
                patch.object(ideas, "_IDEAS_LOG_PATH", ideas_log_path),
                patch.object(ideas, "_IDEAS_STATE_LOG_PATH", ideas_state_log_path),
            ):
                created = ideas.add_idea("Explore a new JARVIS briefing surface", tags=["briefing"])

                ideas_path.write_text("", encoding="utf-8")
                ideas_log_path.write_text("", encoding="utf-8")
                listed = ideas.list_ideas()

                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]["id"], created["id"])
                self.assertEqual(listed[0]["text"], created["text"])
                self.assertEqual(listed[0]["tags"], ["briefing"])


if __name__ == "__main__":
    unittest.main()
