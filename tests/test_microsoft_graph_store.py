from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.accounts import PersonalAccount
from jarvis.microsoft_graph import MicrosoftGraphSupport


def _make_config(root: Path) -> SimpleNamespace:
    token_path = root / "token.json"
    return SimpleNamespace(
        microsoft_client_id="client-id",
        microsoft_tenant_id="tenant-id",
        microsoft_client_secret="client-secret",
        microsoft_redirect_uri="https://example.test/callback",
        microsoft_token_path=token_path,
        microsoft_authority="common",
    )


def _make_account() -> PersonalAccount:
    return PersonalAccount(
        account_id="acct-123",
        owner_user_id="chris",
        owner_display_name="Chris",
        provider="outlook",
        service_scope="mail_calendar",
        label="Chris Outlook",
        login_hint="chris@example.com",
        status="active",
    )


class MicrosoftGraphStoreTests(unittest.TestCase):
    def test_replays_pending_oauth_state_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            support = MicrosoftGraphSupport(_make_config(root))
            account = _make_account()

            result = support.build_connect_url(account, "https://example.test")
            self.assertTrue(result["ok"])

            pending_path = root / "pending_oauth.json"
            pending_log_path = root / "pending_oauth_log.jsonl"
            pending_path.write_text("", encoding="utf-8")
            pending_log_path.write_text("", encoding="utf-8")

            replayed = MicrosoftGraphSupport(_make_config(root))

            self.assertIn(result["state"], replayed._pending_states)
            self.assertEqual(replayed._pending_states[result["state"]]["account_id"], "acct-123")

    def test_replays_account_token_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _make_config(root)
            support = MicrosoftGraphSupport(config)

            support._save_token(
                {
                    "access_token": "secret-token",
                    "refresh_token": "refresh-token",
                    "expires_in": 3600,
                },
                account_id="acct-123",
            )

            token_path = root / "acct-123.json"
            token_log_path = root / "acct-123_log.jsonl"
            token_path.write_text("", encoding="utf-8")
            token_log_path.write_text("", encoding="utf-8")

            replayed = MicrosoftGraphSupport(config)
            token = replayed._load_token(_make_account())

            self.assertIsNotNone(token)
            assert token is not None
            self.assertEqual(token["access_token"], "secret-token")
            self.assertEqual(token["refresh_token"], "refresh-token")


if __name__ == "__main__":
    unittest.main()
