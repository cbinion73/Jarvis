from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.models import HouseholdProfile, RoomProfile, UserProfile
from jarvis.settings import LocationSettingsStore, VoiceSettingsStore


class _ConfigStub:
    def __init__(self) -> None:
        self.tts_provider = "auto"
        self.elevenlabs_voice = "voice-default"
        self.piper_model_path = None
        self.piper_speaker = "0"
        self.elevenlabs_api_key = ""

    def load_household(self) -> HouseholdProfile:
        return HouseholdProfile(
            household_name="Jarvis Home",
            location_label="Home Base",
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


class SettingsStoreTests(unittest.TestCase):
    def test_replays_voice_settings_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.json"
            store = VoiceSettingsStore(_ConfigStub(), path=path)

            saved = store.save(
                {
                    "tts_provider": "system",
                    "elevenlabs_voice": "voice-alt",
                    "piper_model_path": "",
                    "piper_speaker": "2",
                }
            )

            path.write_text("", encoding="utf-8")
            replayed = VoiceSettingsStore(_ConfigStub(), path=path).load()

            self.assertEqual(replayed.tts_provider, "system")
            self.assertEqual(replayed.elevenlabs_voice, saved.elevenlabs_voice)
            self.assertEqual(replayed.piper_speaker, "2")

    def test_replays_location_settings_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "locations.json"
            store = LocationSettingsStore(_ConfigStub(), path=path)

            store.add_location(
                {
                    "label": "Office",
                    "geography": "Office",
                    "latitude": 1.23,
                    "longitude": 4.56,
                    "make_preferred": True,
                }
            )

            path.write_text("", encoding="utf-8")
            replayed = LocationSettingsStore(_ConfigStub(), path=path).load()

            self.assertEqual(replayed["preferred_location_id"], "office")
            self.assertEqual(len(replayed["saved_locations"]), 2)
            office = next(item for item in replayed["saved_locations"] if item["id"] == "office")
            self.assertEqual(office["latitude"], 1.23)
            self.assertEqual(office["longitude"], 4.56)

    def test_add_location_accepts_glass_address_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "locations.json"
            store = LocationSettingsStore(_ConfigStub(), path=path)

            saved = store.add_location(
                {
                    "label": "Home",
                    "address": "8384 Riley Rd",
                    "city": "Alexandria",
                    "state": "KY",
                    "zip": "41001",
                    "lat": "38.960475",
                    "lon": "-84.385347",
                    "notes": "Primary home.",
                }
            )

            home = next(item for item in saved["saved_locations"] if item["id"] == "home")
            self.assertEqual(home["geography"], "8384 Riley Rd, Alexandria, KY, 41001")
            self.assertEqual(home["address"], "8384 Riley Rd")
            self.assertEqual(home["city"], "Alexandria")
            self.assertEqual(home["state"], "KY")
            self.assertEqual(home["zip"], "41001")
            self.assertEqual(home["latitude"], 38.960475)
            self.assertEqual(home["longitude"], -84.385347)


if __name__ == "__main__":
    unittest.main()
