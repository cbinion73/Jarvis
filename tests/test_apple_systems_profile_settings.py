from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import jarvis.user_profile as user_profile_module
from jarvis.apple_api import (
    _disconnect_apple_settings_account,
    _save_apple_settings_account,
    _save_apple_settings_connector,
    _save_apple_settings_family_member,
    _save_apple_settings_profile,
)
from jarvis.audit import AuditLog, ProgressFocusStore


class _StubActor:
    def __init__(self, user_id: str = "chris") -> None:
        self.user_id = user_id


class _StubRuntime:
    def __init__(self) -> None:
        self._accounts = [
            {
                "account_id": "acct-google-1",
                "provider": "google",
                "label": "Chris Google",
                "login_hint": "chris@example.com",
                "status": "connected",
                "service_scope": "mail_calendar",
                "notes": "Family inbox and calendar.",
            }
        ]
        self._members = [
            {
                "user_id": "chris",
                "display_name": "Chris",
                "role": "parent",
                "permissions": "admin",
                "trust_level": "trusted",
                "preferred_tone": "calm and direct",
                "privacy_boundary": "personal",
                "notes": "Primary operator.",
                "device_ids": ["device-1"],
                "active": True,
            }
        ]

    def get_actor(self, actor_name: str) -> _StubActor:
        return _StubActor("chris")

    def _invalidate_snapshot_cache(self, *args, **kwargs) -> None:
        return None

    def update_personal_account(self, account_id: str, payload: dict) -> dict:
        for index, account in enumerate(self._accounts):
            if account["account_id"] != account_id:
                continue
            updated = {**account, **{key: value for key, value in payload.items() if value is not None}}
            self._accounts[index] = updated
            return {"message": f"Updated account '{updated['label']}'.", "account": updated}
        raise KeyError(account_id)

    def disconnect_account(self, account_id: str) -> dict:
        for index, account in enumerate(self._accounts):
            if account["account_id"] != account_id:
                continue
            updated = {**account, "status": "planned", "notes": "Disconnected from Google."}
            self._accounts[index] = updated
            return {"ok": True, "message": "Account disconnected.", "account": updated}
        return {"ok": False, "message": "Account not found."}

    def save_identity_member(self, payload: dict) -> dict:
        user_id = payload["user_id"]
        for index, member in enumerate(self._members):
            if member["user_id"] != user_id:
                continue
            updated = {**member, **payload}
            self._members[index] = updated
            return {"ok": True, "member": updated, "identity": {"members": list(self._members), "devices": []}}
        raise ValueError("Unknown household user")


class AppleSystemsProfileSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = Path.cwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmpdir.cleanup()

    def test_save_apple_profile_defaults_records_activity_and_focus(self) -> None:
        profiles_dir = Path("data/settings/profiles")
        with patch.object(user_profile_module, "PROFILES_DIR", profiles_dir):
            result = _save_apple_settings_profile(
                _StubRuntime(),
                {
                    "notifications": {"approvals": False, "health_alerts": False},
                    "privacy": {"private_chronicle": False, "share_health_with_family": True},
                    "dashboard": {"show_health": False, "show_publishing": True},
                },
                actor_name="chris",
            )

        self.assertEqual(result["message"], "Profile defaults updated.")
        self.assertFalse(result["settings"]["notifications"]["approvals"])
        self.assertFalse(result["settings"]["privacy"]["private_chronicle"])
        self.assertTrue(result["settings"]["dashboard"]["show_publishing"])

        focus_summary = ProgressFocusStore(Path("data/logs")).summary(limit=4)
        self.assertEqual(focus_summary["latest"]["module"], "Settings")

        recent = AuditLog(Path("data/logs")).list_recent(limit=4, entry_type="operator-action")
        self.assertEqual(recent[0]["action"], "Save Apple Profile Defaults")
        self.assertEqual(recent[0]["related_kind"], "profile-settings")

    def test_save_apple_account_controls_records_activity_and_focus(self) -> None:
        runtime = _StubRuntime()
        result = _save_apple_settings_account(
            runtime,
            "acct-google-1",
            {
                "label": "Chris Family Google",
                "login_hint": "family@example.com",
                "status": "paused",
            },
            actor_name="chris",
        )

        self.assertEqual(result["message"], "Updated account 'Chris Family Google'.")
        self.assertEqual(result["account"]["label"], "Chris Family Google")
        self.assertEqual(result["account"]["status"], "paused")

        focus_summary = ProgressFocusStore(Path("data/logs")).summary(limit=4)
        self.assertEqual(focus_summary["latest"]["module"], "Settings")

        recent = AuditLog(Path("data/logs")).list_recent(limit=4, entry_type="operator-action")
        self.assertEqual(recent[0]["action"], "Save Apple Account Controls")
        self.assertEqual(recent[0]["related_kind"], "settings-account")

    def test_disconnect_apple_account_records_activity_and_focus(self) -> None:
        runtime = _StubRuntime()
        result = _disconnect_apple_settings_account(runtime, "acct-google-1", actor_name="chris")

        self.assertEqual(result["message"], "Account disconnected.")
        self.assertEqual(result["account"]["status"], "planned")

        focus_summary = ProgressFocusStore(Path("data/logs")).summary(limit=4)
        self.assertEqual(focus_summary["latest"]["module"], "Settings")

        recent = AuditLog(Path("data/logs")).list_recent(limit=4, entry_type="operator-action")
        self.assertEqual(recent[0]["action"], "Disconnect Apple Account")
        self.assertEqual(recent[0]["related_kind"], "settings-account")

    def test_save_apple_connector_controls_records_activity_and_focus(self) -> None:
        runtime = _StubRuntime()
        result = _save_apple_settings_connector(
            runtime,
            "acct-google-1",
            {
                "service_scope": "calendar",
                "status": "watch",
                "notes": "Calendar still needs OAuth repair before mail is re-enabled.",
            },
            actor_name="chris",
        )

        self.assertEqual(result["account"]["service_scope"], "calendar")
        self.assertEqual(result["account"]["status"], "watch")
        self.assertEqual(result["account"]["notes"], "Calendar still needs OAuth repair before mail is re-enabled.")

        focus_summary = ProgressFocusStore(Path("data/logs")).summary(limit=4)
        self.assertEqual(focus_summary["latest"]["module"], "Settings")

        recent = AuditLog(Path("data/logs")).list_recent(limit=4, entry_type="operator-action")
        self.assertEqual(recent[0]["action"], "Save Apple Connector Controls")
        self.assertEqual(recent[0]["related_kind"], "settings-connector")

    def test_save_apple_family_identity_records_activity_and_focus(self) -> None:
        runtime = _StubRuntime()
        result = _save_apple_settings_family_member(
            runtime,
            "chris",
            {
                "role": "operator",
                "permissions": "household-admin",
                "trust_level": "trusted",
                "preferred_tone": "warm and direct",
                "notes": "Primary morning and launch owner.",
            },
            actor_name="chris",
        )

        self.assertEqual(result["member"]["role"], "operator")
        self.assertEqual(result["member"]["permissions"], "household-admin")
        self.assertEqual(result["member"]["preferred_tone"], "warm and direct")

        focus_summary = ProgressFocusStore(Path("data/logs")).summary(limit=4)
        self.assertEqual(focus_summary["latest"]["module"], "Settings")

        recent = AuditLog(Path("data/logs")).list_recent(limit=4, entry_type="operator-action")
        self.assertEqual(recent[0]["action"], "Save Apple Family Identity")
        self.assertEqual(recent[0]["related_kind"], "settings-family-identity")
