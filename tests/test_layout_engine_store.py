from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import layout_engine


class LayoutEngineStoreTests(unittest.TestCase):
    def test_replays_layout_state_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "layout_state.json"
            state_log_path = Path(tmp) / "layout_state_log.jsonl"

            with patch.object(layout_engine, "LAYOUT_STATE_PATH", state_path), patch.object(layout_engine, "LAYOUT_STATE_LOG_PATH", state_log_path):
                layout_engine.set_mode("lunch_brief", manual=True)
                state_path.write_text("", encoding="utf-8")

                replayed = layout_engine._load_state()

                self.assertEqual(replayed["override_mode"], "lunch_brief")
                self.assertIn("override_expires_at", replayed)

    def test_replays_weights_cache_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            weights_path = Path(tmp) / "layout_weights_cache.json"
            weights_log_path = Path(tmp) / "layout_weights_cache_log.jsonl"

            with patch.object(layout_engine, "WEIGHTS_CACHE_PATH", weights_path), patch.object(layout_engine, "WEIGHTS_CACHE_LOG_PATH", weights_log_path):
                with patch.object(layout_engine, "get_learned_weights", return_value={"briefing": 0.9}):
                    layout_engine.rebuild_weights_cache()
                weights_path.write_text("", encoding="utf-8")

                replayed = layout_engine.get_cached_weights("morning_brief")

                self.assertEqual(replayed["briefing"], 0.9)


if __name__ == "__main__":
    unittest.main()
