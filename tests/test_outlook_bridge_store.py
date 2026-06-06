from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.outlook_bridge import OutlookBridge


class OutlookBridgeStoreTests(unittest.TestCase):
    def test_replays_token_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_path = Path(tmp) / "outlook_token.json"
            legacy_log_path = Path(tmp) / "outlook_token_log.jsonl"
            state_log_path = Path(tmp) / "outlook_token_state_log.jsonl"
            bridge = OutlookBridge(
                token_path=token_path,
                client_id="client-id",
                client_secret="client-secret",
                redirect_uri="http://localhost/callback",
            )
            payload = {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "expires_at": "2099-01-01T00:00:00+00:00",
            }

            bridge._persist_token(payload)
            token_path.write_text("", encoding="utf-8")
            legacy_log_path.write_text("", encoding="utf-8")

            replayed = bridge._load_token()

            self.assertEqual(replayed["access_token"], "access-token")
            self.assertEqual(replayed["refresh_token"], "refresh-token")


if __name__ == "__main__":
    unittest.main()
