from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.accounts import AccountRegistry
from jarvis.models import HouseholdProfile, RoomProfile, UserProfile


class AccountRegistryStoreTests(unittest.TestCase):
    def _household(self) -> HouseholdProfile:
        return HouseholdProfile(
            household_name="Jarvis Home",
            location_label="Home",
            quiet_start="21:00",
            quiet_end="06:00",
            users={
                "chris": UserProfile(
                    user_id="chris",
                    display_name="Chris",
                    address_as="Chris",
                    role="parent",
                    permissions="full",
                )
            },
            rooms={"office": RoomProfile(room_id="office", mode_bias="focus")},
            modes=["ambient", "focus"],
        )

    def test_replays_accounts_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "accounts.json"
            registry = AccountRegistry(self._household(), path=path)
            saved = registry.save_account(
                {
                    "owner_user_id": "chris",
                    "provider": "google",
                    "service_scope": "mail_calendar",
                    "label": "Chris Google",
                    "login_hint": "chris@example.com",
                    "status": "active",
                }
            )

            path.write_text("", encoding="utf-8")
            registry.log_path.write_text("", encoding="utf-8")
            replayed = AccountRegistry(self._household(), path=path)
            accounts = replayed.list_accounts()

            self.assertEqual(len(accounts), 1)
            self.assertEqual(accounts[0].account_id, saved.account_id)
            self.assertEqual(accounts[0].login_hint, "chris@example.com")


if __name__ == "__main__":
    unittest.main()
