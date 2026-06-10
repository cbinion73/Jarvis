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

    def test_falls_back_to_legacy_home_tokens_when_persistent_snapshot_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tokens_path = Path(tmp) / "data" / "health" / "dexcom_tokens.json"
            tokens_log_path = tokens_path.with_name("dexcom_tokens_log.jsonl")
            tokens_state_log_path = tokens_path.with_name("dexcom_tokens_state_log.jsonl")
            legacy_tokens_path = Path(tmp) / ".jarvis" / "dexcom_tokens.json"
            legacy_tokens_path.parent.mkdir(parents=True, exist_ok=True)
            legacy_tokens_path.write_text(
                '{"access_token":"legacy-token","refresh_token":"legacy-refresh","expires_at":9999999999}',
                encoding="utf-8",
            )

            with (
                patch.object(dexcom_sync, "_TOKENS_PATH", tokens_path),
                patch.object(dexcom_sync, "_TOKENS_LOG_PATH", tokens_log_path),
                patch.object(dexcom_sync, "_TOKENS_STATE_LOG_PATH", tokens_state_log_path),
                patch.object(dexcom_sync, "_LEGACY_TOKENS_PATH", legacy_tokens_path),
                patch.object(dexcom_sync, "_LEGACY_TOKENS_LOG_PATH", legacy_tokens_path.with_name("dexcom_tokens_log.jsonl")),
                patch.object(dexcom_sync, "_LEGACY_TOKENS_STATE_LOG_PATH", legacy_tokens_path.with_name("dexcom_tokens_state_log.jsonl")),
            ):
                loaded = dexcom_sync._load_tokens()

                self.assertEqual(loaded["access_token"], "legacy-token")
                self.assertEqual(loaded["refresh_token"], "legacy-refresh")


if __name__ == "__main__":
    unittest.main()
