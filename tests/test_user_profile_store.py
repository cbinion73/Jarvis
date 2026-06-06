from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import user_profile


class UserProfileStoreTests(unittest.TestCase):
    def test_replays_profile_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profiles_dir = Path(tmp) / "profiles"

            with patch.object(user_profile, "PROFILES_DIR", profiles_dir):
                saved = user_profile.save_profile(
                    "chris",
                    {
                        "greeting_name": "Chris",
                        "dashboard": {"show_finance": True},
                    },
                )

                user_profile._profile_path("chris").write_text("", encoding="utf-8")
                user_profile._profile_log_path("chris").write_text("", encoding="utf-8")
                replayed = user_profile.load_profile("chris")

                self.assertEqual(replayed["user_id"], "chris")
                self.assertEqual(replayed["greeting_name"], "Chris")
                self.assertTrue(replayed["dashboard"]["show_finance"])
                self.assertEqual(replayed["updated_at"], saved["updated_at"])


if __name__ == "__main__":
    unittest.main()
