from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import jarvis.user_profile as user_profile_module
from jarvis.apple_api import _save_apple_settings_profile
from jarvis.audit import AuditLog, ProgressFocusStore


class _StubActor:
    def __init__(self, user_id: str = "chris") -> None:
        self.user_id = user_id


class _StubRuntime:
    def get_actor(self, actor_name: str) -> _StubActor:
        return _StubActor("chris")

    def _invalidate_snapshot_cache(self, *args, **kwargs) -> None:
        return None


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

