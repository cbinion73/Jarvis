from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.identity import IdentityRegistry
from jarvis.models import HouseholdProfile, RoomProfile, UserProfile


def _household() -> HouseholdProfile:
    return HouseholdProfile(
        household_name="Wilson Family",
        location_label="Home",
        quiet_start="21:00",
        quiet_end="06:00",
        users={
            "chris": UserProfile(
                user_id="chris",
                display_name="Chris",
                address_as="Chris",
                role="dad",
                permissions="trusted",
                priorities=["family", "work"],
            ),
            "anna": UserProfile(
                user_id="anna",
                display_name="Anna",
                address_as="Anna",
                role="child",
                permissions="child-safe",
                priorities=["school"],
            ),
        },
        rooms={"kitchen": RoomProfile(room_id="kitchen", mode_bias="family")},
        modes=["family", "quiet"],
    )


class IdentityRegistryStoreTests(unittest.TestCase):
    def test_replays_identity_state_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "identity.json"
            registry = IdentityRegistry(_household(), path=path)

            registry.save_member(
                {
                    "user_id": "chris",
                    "display_name": "Chris Wilson",
                    "preferred_tone": "direct",
                }
            )
            registry.save_device(
                {
                    "device_id": "device-1",
                    "label": "Kitchen iPad",
                    "device_type": "tablet",
                    "owner_user_id": "chris",
                }
            )

            path.write_text("", encoding="utf-8")
            registry._log_path().write_text("", encoding="utf-8")
            loaded = registry.load()

            member = next(item for item in loaded["members"] if item.user_id == "chris")
            device = next(item for item in loaded["devices"] if item.device_id == "device-1")
            self.assertEqual(member.display_name, "Chris Wilson")
            self.assertEqual(member.preferred_tone, "direct")
            self.assertEqual(device.label, "Kitchen iPad")
            self.assertEqual(device.owner_user_id, "chris")

    def test_service_profile_defaults_include_hosted_deployment_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "identity.json"
            registry = IdentityRegistry(_household(), path=path)

            service = registry.load()["service"]

            self.assertEqual(service["host_type"], "desktop")
            self.assertEqual(service["deployment_mode"], "hybrid")
            self.assertEqual(service["hosted_provider"], "Hetzner")
            self.assertEqual(service["hosted_base_url"], "https://jarvis.teambinion.org")
            self.assertEqual(service["edge_provider"], "Cloudflare Tunnel")
            self.assertTrue(service["cloudflare_access_enabled"])
            self.assertTrue(service["tunnel_enabled"])
            self.assertEqual(service["compose_project"], "jarvis-family")


if __name__ == "__main__":
    unittest.main()
