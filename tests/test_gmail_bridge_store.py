from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from jarvis.gmail_bridge import GmailBridge


class GmailBridgeStoreTests(unittest.TestCase):
    def test_replays_credentials_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            credentials_path = Path(tmp) / "gmail_token.json"
            legacy_log_path = Path(tmp) / "gmail_token_log.jsonl"
            state_log_path = Path(tmp) / "gmail_token_state_log.jsonl"
            bridge = GmailBridge(str(credentials_path))
            credentials = _FakeCredentials(
                token="refreshed-token",
                expiry=datetime(2099, 1, 1, tzinfo=timezone.utc),
            )

            with patch.object(bridge, "_credentials_log_path", return_value=legacy_log_path), patch.object(
                bridge,
                "_credentials_state_log_path",
                return_value=state_log_path,
            ):
                bridge._persist_refreshed_token(credentials)
                credentials_path.write_text("", encoding="utf-8")
                legacy_log_path.write_text("", encoding="utf-8")

                replayed = bridge._load_credentials()

                self.assertEqual(replayed["token"], "refreshed-token")
                self.assertEqual(replayed["expiry"], "2099-01-01T00:00:00+00:00")


class _FakeCredentials:
    def __init__(self, *, token: str, expiry: datetime | None) -> None:
        self.token = token
        self.expiry = expiry


if __name__ == "__main__":
    unittest.main()
