from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import dexcom_sync


class DexcomSyncStoreTests(unittest.TestCase):
    def test_replays_tokens_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tokens_path = Path(tmp) / "dexcom_tokens.json"
            tokens_log_path = Path(tmp) / "dexcom_tokens_log.jsonl"
            tokens_state_log_path = Path(tmp) / "dexcom_tokens_state_log.jsonl"
            payload = {
                "access_token": "secret-token",
                "refresh_token": "refresh-token",
                "expires_at": 9999999999,
                "redirect_uri": "http://localhost/callback",
            }

            with (
                patch.object(dexcom_sync, "_TOKENS_PATH", tokens_path),
                patch.object(dexcom_sync, "_TOKENS_LOG_PATH", tokens_log_path),
                patch.object(dexcom_sync, "_TOKENS_STATE_LOG_PATH", tokens_state_log_path),
            ):
                dexcom_sync._save_tokens(payload)
                tokens_path.write_text("", encoding="utf-8")
                tokens_log_path.write_text("", encoding="utf-8")

                loaded = dexcom_sync._load_tokens()

                self.assertEqual(loaded["access_token"], "secret-token")
                self.assertEqual(loaded["refresh_token"], "refresh-token")


if __name__ == "__main__":
    unittest.main()
