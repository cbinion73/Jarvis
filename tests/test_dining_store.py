from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import dining


class DiningStoreTests(unittest.TestCase):
    def test_replays_cache_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "dining_cache.json"
            cache_log_path = Path(tmp) / "dining_cache_log.jsonl"
            cache_state_log_path = Path(tmp) / "dining_cache_state_log.jsonl"

            with (
                patch.object(dining, "CACHE_PATH", cache_path),
                patch.object(dining, "CACHE_LOG_PATH", cache_log_path),
                patch.object(dining, "CACHE_STATE_LOG_PATH", cache_state_log_path),
            ):
                dining._save_cache({"nearby:any": {"ts": 123, "data": [{"name": "Cafe"}]}})

                cache_path.write_text("", encoding="utf-8")
                cache_log_path.write_text("", encoding="utf-8")
                loaded = dining._load_cache()

                self.assertEqual(loaded["nearby:any"]["ts"], 123)
                self.assertEqual(loaded["nearby:any"]["data"][0]["name"], "Cafe")

    def test_replays_favorites_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            favorites_path = Path(tmp) / "dining_favorites.json"
            favorites_log_path = Path(tmp) / "dining_favorites_log.jsonl"
            favorites_state_log_path = Path(tmp) / "dining_favorites_state_log.jsonl"

            with (
                patch.object(dining, "FAVORITES_PATH", favorites_path),
                patch.object(dining, "FAVORITES_LOG_PATH", favorites_log_path),
                patch.object(dining, "FAVORITES_STATE_LOG_PATH", favorites_state_log_path),
            ):
                result = dining.toggle_favorite("place-1", "Test Cafe", "123 Main", 4.5)

                favorites_path.write_text("", encoding="utf-8")
                favorites_log_path.write_text("", encoding="utf-8")
                loaded = dining.get_favorites()

                self.assertEqual(result["action"], "added")
                self.assertEqual(len(loaded), 1)
                self.assertEqual(loaded[0]["place_id"], "place-1")
                self.assertEqual(loaded[0]["name"], "Test Cafe")


if __name__ == "__main__":
    unittest.main()
