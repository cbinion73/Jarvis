from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import kasa_bridge


class KasaScenesStoreTests(unittest.TestCase):
    def test_replays_scenes_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scenes_path = Path(tmp) / "kasa_scenes.json"
            scenes_log_path = Path(tmp) / "kasa_scenes_log.jsonl"
            scenes_state_log_path = Path(tmp) / "kasa_scenes_state_log.jsonl"
            custom = [
                {
                    "id": "focus",
                    "name": "Focus",
                    "icon": "💡",
                    "actions": [{"match": "office", "state": True, "brightness": 75}],
                }
            ]

            with (
                patch.object(kasa_bridge, "_SCENES_PATH", scenes_path),
                patch.object(kasa_bridge, "_SCENES_LOG_PATH", scenes_log_path),
                patch.object(kasa_bridge, "_SCENES_STATE_LOG_PATH", scenes_state_log_path),
            ):
                kasa_bridge._save_scenes(custom)
                scenes_path.write_text("", encoding="utf-8")
                scenes_log_path.write_text("", encoding="utf-8")

                replayed = kasa_bridge._load_scenes()

                self.assertEqual(len(replayed), 1)
                self.assertEqual(replayed[0]["id"], "focus")
                self.assertEqual(replayed[0]["actions"][0]["brightness"], 75)


if __name__ == "__main__":
    unittest.main()
