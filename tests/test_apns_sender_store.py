from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import apns_sender


class ApnsSenderStoreTests(unittest.TestCase):
    def test_replays_device_tokens_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "apns_config.json"
            key_path = Path(tmp) / "apns_key.p8"
            tokens_path = Path(tmp) / "apns_device_tokens.json"
            tokens_log_path = Path(tmp) / "apns_device_tokens_log.jsonl"
            tokens_state_log_path = Path(tmp) / "apns_device_tokens_state_log.jsonl"

            with (
                patch.object(apns_sender, "_CONFIG_PATH", config_path),
                patch.object(apns_sender, "_KEY_PATH", key_path),
                patch.object(apns_sender, "_TOKENS_PATH", tokens_path),
                patch.object(apns_sender, "_TOKENS_LOG_PATH", tokens_log_path),
                patch.object(apns_sender, "_TOKENS_STATE_LOG_PATH", tokens_state_log_path),
            ):
                apns_sender.register_device_token("chris", "token-abc")
                tokens_path.write_text("", encoding="utf-8")
                tokens_log_path.write_text("", encoding="utf-8")

                tokens = apns_sender.get_tokens("chris")

                self.assertEqual(tokens, ["token-abc"])


if __name__ == "__main__":
    unittest.main()
