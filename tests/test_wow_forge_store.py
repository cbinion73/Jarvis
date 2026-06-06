from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import wow_forge


class WowForgeStoreTests(unittest.TestCase):
    def test_replays_config_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "wow_forge.json"
            config_log_path = Path(tmp) / "wow_forge_log.jsonl"
            config_state_log_path = Path(tmp) / "wow_forge_state_log.jsonl"

            with (
                patch.object(wow_forge, "_CONFIG_PATH", config_path),
                patch.object(wow_forge, "_CONFIG_LOG_PATH", config_log_path),
                patch.object(wow_forge, "_CONFIG_STATE_LOG_PATH", config_state_log_path),
            ):
                saved = wow_forge.save_config(
                    {
                        "export_folder": "/tmp/wow",
                        "auto_import": True,
                    }
                )

                config_path.write_text("", encoding="utf-8")
                config_log_path.write_text("", encoding="utf-8")
                loaded = wow_forge.load_config()

                self.assertEqual(loaded["export_folder"], "/tmp/wow")
                self.assertTrue(loaded["auto_import"])
                self.assertEqual(loaded["blender_path"], saved["blender_path"])


if __name__ == "__main__":
    unittest.main()
