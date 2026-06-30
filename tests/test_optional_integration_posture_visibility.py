from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch
from pathlib import Path

from jarvis.runtime import JarvisRuntime


def _google_status_payload(*, credentials_file_present: bool, libraries_ready: bool, token_present: bool, connected: bool, detail: str) -> dict:
    return {
        "credentials_file_present": credentials_file_present,
        "libraries_ready": libraries_ready,
        "token_present": token_present,
        "connected": connected,
        "gmail_ready": connected,
        "calendar_ready": connected,
        "detail": detail,
    }


class OptionalIntegrationPostureVisibilityTests(unittest.TestCase):
    def _make_runtime(self) -> JarvisRuntime:
        runtime = object.__new__(JarvisRuntime)
        runtime.config = SimpleNamespace(
            openai_api_key="",
            google_client_secret_path=Path("config/google_client_secret.json"),
        )
        runtime.openai_client = SimpleNamespace(
            second_brain_status=lambda: {
                "enabled": False,
                "healthy": False,
                "model_available": False,
                "provider": "ollama",
                "model": "qwen2.5:7b",
            }
        )
        runtime.home_support = SimpleNamespace(adapter=SimpleNamespace(live=False))
        return runtime

    def test_google_workspace_posture_distinguishes_credentials_from_connection(self) -> None:
        runtime = self._make_runtime()
        runtime.google_workspace = SimpleNamespace(
            status=lambda: SimpleNamespace(
                to_dict=lambda: _google_status_payload(
                    credentials_file_present=False,
                    libraries_ready=True,
                    token_present=False,
                    connected=False,
                    detail="Google client secret is missing. Add config/google_client_secret.json first.",
                )
            )
        )
        with patch.object(
            JarvisRuntime,
            "list_personal_accounts",
            lambda self: [
                {"provider": "google", "account_id": "acct-connected"},
                {"provider": "google", "account_id": "acct-planned"},
            ],
        ), patch.object(
            JarvisRuntime,
            "google_account_snapshot",
            lambda self, account_id: {
                "status": _google_status_payload(
                    credentials_file_present=False,
                    libraries_ready=True,
                    token_present=False,
                    connected=False,
                    detail="Google client secret is missing. Add config/google_client_secret.json first.",
                ),
                "account": {
                    "account_id": account_id,
                    "label": "Chris Gmail" if account_id == "acct-connected" else "Chris Google",
                    "status": "connected" if account_id == "acct-connected" else "planned",
                },
            },
        ):
            posture = runtime._google_workspace_posture()

        self.assertEqual(posture["blocking_layer"], "client_credentials")
        self.assertTrue(posture["libraries_ready"])
        self.assertFalse(posture["client_credentials_present"])
        self.assertEqual(posture["recorded_account_count"], 2)
        self.assertEqual(posture["recorded_connected_account_count"], 1)
        self.assertEqual(posture["usable_connected_account_count"], 0)
        self.assertEqual(posture["stale_recorded_connected_account_count"], 1)
        self.assertIn("client credentials are missing", posture["detail"])
        self.assertIn("Recorded accounts: 2", posture["detail"])
        self.assertIn("registry-connected: 1", posture["detail"])
        self.assertIn("marked connected in the registry but are not usable", posture["detail"])
        self.assertEqual(posture["missing_requirement_path"], "config/google_client_secret.json")
        self.assertIn("Add the Google OAuth client file at config/google_client_secret.json", posture["next_recovery_step"])
        self.assertIn("marked connected in the registry but are not usable", posture["account_hygiene_note"])

    def test_status_and_google_status_surface_posture_summary(self) -> None:
        runtime = self._make_runtime()
        runtime.google_workspace = SimpleNamespace(
            status=lambda: SimpleNamespace(
                to_dict=lambda: _google_status_payload(
                    credentials_file_present=True,
                    libraries_ready=True,
                    token_present=False,
                    connected=False,
                    detail="Google account not connected yet.",
                )
            )
        )
        with patch.object(JarvisRuntime, "list_personal_accounts", lambda self: [{"provider": "google", "account_id": "acct-1"}]), \
             patch.object(
                 JarvisRuntime,
                 "google_account_snapshot",
                 lambda self, account_id: {
                     "status": _google_status_payload(
                         credentials_file_present=True,
                         libraries_ready=True,
                         token_present=False,
                         connected=False,
                         detail="Google account not connected yet.",
                     ),
                     "account": {
                         "account_id": account_id,
                         "label": "Chris Gmail",
                         "status": "planned",
                     },
                 },
             ), \
             patch.object(JarvisRuntime, "family_calendar_summary", lambda self: {"configured": True, "error": "", "detail": "Family shared calendar is connected."}), \
             patch.object(JarvisRuntime, "openviking_status", lambda self: {"ok": False, "enabled": False, "detail": "OpenViking integration is disabled."}), \
             patch.object(JarvisRuntime, "obsidian_status", lambda self: {"ok": True, "detail": "Obsidian vault is available for local retrieval."}):
            runtime_status = {item["name"]: item for item in runtime.status()}
            google_item = runtime_status["google-workspace"]
            google_status = runtime.google_workspace_status()

            self.assertEqual(google_item["posture"]["blocking_layer"], "account_connection")
            self.assertTrue(google_item["posture"]["libraries_ready"])
            self.assertTrue(google_item["posture"]["client_credentials_present"])
            self.assertFalse(google_item["posture"]["token_present"])
            self.assertIn("no Google account token is connected", google_item["detail"])
            self.assertEqual(google_item["posture"]["stale_recorded_connected_account_count"], 0)
            self.assertEqual(google_item["posture"]["missing_requirement_path"], "")
            self.assertIn("Connect or re-import a Google account token", google_item["posture"]["next_recovery_step"])
            self.assertEqual(google_item["posture"]["account_hygiene_note"], "")

            self.assertIn("posture", google_status)
            self.assertEqual(google_status["posture"]["blocking_layer"], "account_connection")
            self.assertEqual(google_status["posture"]["recorded_account_count"], 1)
            self.assertEqual(google_status["posture"]["usable_connected_account_count"], 0)
            self.assertIn("no Google account token is connected", google_status["posture"]["detail"])
            self.assertEqual(google_status["posture"]["stale_recorded_connected_account_count"], 0)
            self.assertEqual(google_status["posture"]["missing_requirement_path"], "")
            self.assertIn("Connect or re-import a Google account token", google_status["posture"]["next_recovery_step"])


if __name__ == "__main__":
    unittest.main()
