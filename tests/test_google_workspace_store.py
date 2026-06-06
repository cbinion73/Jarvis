from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.accounts import PersonalAccount
from jarvis.google_workspace import GoogleWorkspaceSupport


def _make_config(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        google_token_path=root / "google_token.json",
        google_client_secret_path=root / "client_secret.json",
    )


def _make_account() -> PersonalAccount:
    return PersonalAccount(
        account_id="acct-123",
        owner_user_id="chris",
        owner_display_name="Chris",
        provider="google",
        service_scope="mail_calendar",
        label="Chris Google",
        login_hint="chris@example.com",
        status="active",
    )


class GoogleWorkspaceStoreTests(unittest.TestCase):
    def test_replays_pending_oauth_state_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            support = GoogleWorkspaceSupport(_make_config(root))
            payload = {
                "pending-state": {
                    "account_id": "acct-123",
                    "code_verifier": "verifier-xyz",
                }
            }

            support._pending_states = payload
            support._save_pending_states()
            support.pending_state_path.write_text("", encoding="utf-8")
            support._log_path_for(support.pending_state_path).write_text("", encoding="utf-8")

            replayed = GoogleWorkspaceSupport(_make_config(root))

            self.assertIn("pending-state", replayed._pending_states)
            self.assertEqual(replayed._pending_states["pending-state"]["account_id"], "acct-123")
            self.assertEqual(replayed._pending_states["pending-state"]["code_verifier"], "verifier-xyz")

    def test_replays_token_payload_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            support = GoogleWorkspaceSupport(_make_config(root))
            account = _make_account()
            token_path = support._token_path_for(account)
            payload = {
                "token": "secret-token",
                "refresh_token": "refresh-token",
                "client_id": "client-id",
                "client_secret": "client-secret",
                "scopes": ["scope-a"],
            }

            support._save_dict_snapshot(token_path, payload)
            token_path.write_text("", encoding="utf-8")
            support._log_path_for(token_path).write_text("", encoding="utf-8")

            replayed = GoogleWorkspaceSupport(_make_config(root))
            loaded = replayed._load_token_payload(account)

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded["token"], "secret-token")
            self.assertEqual(loaded["refresh_token"], "refresh-token")


if __name__ == "__main__":
    unittest.main()
