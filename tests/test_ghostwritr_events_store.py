from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import ghostwritr_events


class GhostwritrEventsStoreTests(unittest.TestCase):
    def test_replays_state_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "ghostwritr_events_state.json"
            state_log_path = Path(tmp) / "ghostwritr_events_state_log.jsonl"
            state_state_log_path = Path(tmp) / "ghostwritr_events_state_state_log.jsonl"
            payload = {
                "seen_stages": {"book-1:READY_FOR_REVIEW": "2026-06-02T12:00:00+00:00"},
                "seen_books": ["book-1"],
                "last_poll": "2026-06-02T12:00:00+00:00",
            }

            with (
                patch.object(ghostwritr_events, "_STATE_PATH", state_path),
                patch.object(ghostwritr_events, "_STATE_LOG_PATH", state_log_path),
                patch.object(ghostwritr_events, "_STATE_STATE_LOG_PATH", state_state_log_path),
            ):
                ghostwritr_events._save_state(payload)
                state_path.write_text("", encoding="utf-8")
                state_log_path.write_text("", encoding="utf-8")

                loaded = ghostwritr_events._load_state()

                self.assertEqual(loaded["seen_books"], ["book-1"])
                self.assertIn("book-1:READY_FOR_REVIEW", loaded["seen_stages"])


if __name__ == "__main__":
    unittest.main()
