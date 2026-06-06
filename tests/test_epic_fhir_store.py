from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import epic_fhir


class EpicFHIRStoreTests(unittest.TestCase):
    def test_replays_config_and_token_from_state_logs_when_snapshots_are_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            config_path = health_dir / "epic_config.json"
            token_path = health_dir / "epic_token.json"
            state_path = health_dir / "epic_pkce_state.json"
            config_log_path = health_dir / "epic_config_log.jsonl"
            token_log_path = health_dir / "epic_token_log.jsonl"
            state_log_path = health_dir / "epic_pkce_state_log.jsonl"
            config_state_log_path = health_dir / "epic_config_state_log.jsonl"
            token_state_log_path = health_dir / "epic_token_state_log.jsonl"
            state_state_log_path = health_dir / "epic_pkce_state_state_log.jsonl"

            with (
                patch.object(epic_fhir, "_HEALTH_DIR", health_dir),
                patch.object(epic_fhir, "_CONFIG_PATH", config_path),
                patch.object(epic_fhir, "_TOKEN_PATH", token_path),
                patch.object(epic_fhir, "_STATE_PATH", state_path),
                patch.object(epic_fhir, "_CONFIG_LOG_PATH", config_log_path),
                patch.object(epic_fhir, "_TOKEN_LOG_PATH", token_log_path),
                patch.object(epic_fhir, "_STATE_LOG_PATH", state_log_path),
                patch.object(epic_fhir, "_CONFIG_STATE_LOG_PATH", config_state_log_path),
                patch.object(epic_fhir, "_TOKEN_STATE_LOG_PATH", token_state_log_path),
                patch.object(epic_fhir, "_STATE_STATE_LOG_PATH", state_state_log_path),
            ):
                epic_fhir.save_config({"client_id": "abc123"})
                epic_fhir._save_token({"access_token": "secret", "expires_in": 3600})

                config_path.write_text("", encoding="utf-8")
                token_path.write_text("", encoding="utf-8")
                config_log_path.write_text("", encoding="utf-8")
                token_log_path.write_text("", encoding="utf-8")

                cfg = epic_fhir.load_config()
                token = epic_fhir._load_token()

                self.assertEqual(cfg["client_id"], "abc123")
                self.assertEqual(token["access_token"], "secret")

    def test_replays_pkce_state_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            config_path = health_dir / "epic_config.json"
            token_path = health_dir / "epic_token.json"
            state_path = health_dir / "epic_pkce_state.json"
            config_log_path = health_dir / "epic_config_log.jsonl"
            token_log_path = health_dir / "epic_token_log.jsonl"
            state_log_path = health_dir / "epic_pkce_state_log.jsonl"
            config_state_log_path = health_dir / "epic_config_state_log.jsonl"
            token_state_log_path = health_dir / "epic_token_state_log.jsonl"
            state_state_log_path = health_dir / "epic_pkce_state_state_log.jsonl"

            with (
                patch.object(epic_fhir, "_HEALTH_DIR", health_dir),
                patch.object(epic_fhir, "_CONFIG_PATH", config_path),
                patch.object(epic_fhir, "_TOKEN_PATH", token_path),
                patch.object(epic_fhir, "_STATE_PATH", state_path),
                patch.object(epic_fhir, "_CONFIG_LOG_PATH", config_log_path),
                patch.object(epic_fhir, "_TOKEN_LOG_PATH", token_log_path),
                patch.object(epic_fhir, "_STATE_LOG_PATH", state_log_path),
                patch.object(epic_fhir, "_CONFIG_STATE_LOG_PATH", config_state_log_path),
                patch.object(epic_fhir, "_TOKEN_STATE_LOG_PATH", token_state_log_path),
                patch.object(epic_fhir, "_STATE_STATE_LOG_PATH", state_state_log_path),
            ):
                epic_fhir.save_config({"client_id": "abc123"})
                with patch.object(epic_fhir.secrets, "token_urlsafe", return_value="fixed-state"), patch.object(
                    epic_fhir.secrets, "token_bytes", return_value=b"x" * 32
                ):
                    auth_url = epic_fhir.start_auth()

                self.assertIn("state=fixed-state", auth_url)
                state_path.write_text("", encoding="utf-8")
                state_log_path.write_text("", encoding="utf-8")
                replayed = epic_fhir._load_state_from_state_log()

                self.assertEqual(replayed["state"], "fixed-state")
                self.assertTrue(replayed["verifier"])


if __name__ == "__main__":
    unittest.main()
