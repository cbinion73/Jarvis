"""check_google_workspace must reflect the real, per-account connection state.

Google accounts connect via a per-account token file
(data/google/{account_id}.json), not the single legacy
config.google_token_path. A prior version of this check only looked at the
legacy path, so a genuinely, successfully connected account still reported
"not connected" forever on the dashboard. These tests pin all three real
states: legacy-path connected, per-account connected (legacy missing —
production's actual shape), and truly not connected.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest import mock

from jarvis.config import AppConfig
from jarvis.integrations import check_google_workspace


class GoogleWorkspaceCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env_backup = {
            key: os.environ.get(key)
            for key in ("JARVIS_GOOGLE_CLIENT_SECRET", "JARVIS_GOOGLE_TOKEN_PATH")
        }

    def tearDown(self) -> None:
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _config(self, tmp_path: Path, *, client_secret_present: bool) -> AppConfig:
        client_secret = tmp_path / "client_secret.json"
        if client_secret_present:
            client_secret.write_text("{}", encoding="utf-8")
        token_path = tmp_path / "google" / "google_token.json"
        os.environ["JARVIS_GOOGLE_CLIENT_SECRET"] = str(client_secret)
        os.environ["JARVIS_GOOGLE_TOKEN_PATH"] = str(token_path)
        return AppConfig.from_env()

    def test_missing_client_secret_fails(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(Path(tmp), client_secret_present=False)
            result = check_google_workspace(config)
        self.assertFalse(result.ok)
        self.assertIn("client secret", result.detail.lower())

    def test_legacy_token_path_still_recognized(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(Path(tmp), client_secret_present=True)
            config.google_token_path.parent.mkdir(parents=True, exist_ok=True)
            config.google_token_path.write_text("{}", encoding="utf-8")
            result = check_google_workspace(config)
        self.assertTrue(result.ok)

    def test_per_account_token_recognized_when_legacy_path_absent(self) -> None:
        # This is production's actual shape: the real connect flow writes
        # data/google/{account_id}.json and never touches the legacy path.
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = self._config(tmp_path, client_secret_present=True)
            token_dir = config.google_token_path.parent
            token_dir.mkdir(parents=True, exist_ok=True)
            account_id = "7d04d6dc-3346-4aa7-8ae4-7ea2354e0d8b"
            (token_dir / f"{account_id}.json").write_text("{}", encoding="utf-8")

            accounts_path = tmp_path / "accounts.json"
            accounts_path.write_text(
                json.dumps([{
                    "account_id": account_id,
                    "provider": "google",
                    "label": "Chris Gmail",
                }]),
                encoding="utf-8",
            )
            with mock.patch("jarvis.accounts.ACCOUNTS_PATH", accounts_path):
                result = check_google_workspace(config)
        self.assertTrue(result.ok)
        self.assertIn("Chris Gmail", result.detail)

    def test_registered_account_with_no_token_file_is_not_connected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = self._config(tmp_path, client_secret_present=True)
            config.google_token_path.parent.mkdir(parents=True, exist_ok=True)

            accounts_path = tmp_path / "accounts.json"
            accounts_path.write_text(
                json.dumps([{
                    "account_id": "unconnected-account",
                    "provider": "google",
                    "label": "Chris Google",
                }]),
                encoding="utf-8",
            )
            with mock.patch("jarvis.accounts.ACCOUNTS_PATH", accounts_path):
                result = check_google_workspace(config)
        self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()
