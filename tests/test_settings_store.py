from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.models import HouseholdProfile, RoomProfile, UserProfile
from jarvis.settings import LocationSettingsStore, VoiceSettingsStore
from jarvis.speech import AudioPayload, record_voice_runtime_status


class _ConfigStub:
    def __init__(self) -> None:
        self.tts_provider = "auto"
        self.elevenlabs_voice = "voice-default"
        self.fish_reference_id = "612b878b113047d9a770c069c8b4fdfe"
        self.piper_binary = "piper"
        self.piper_model_path = None
        self.piper_speaker = "0"
        self.elevenlabs_api_key = ""
        self.fish_api_key = ""
        self.tts_fallbacks = ()
        self.stt_provider = "openai"
        self.stt_fallbacks = ()
        self.openai_api_key = "openai-test"
        self.localai_base_url = ""
        self.localai_api_key = ""
        self.localai_tts_model = ""
        self.localai_tts_backend = ""
        self.localai_stt_model = ""
        self.fish_model = "s2.1-pro"

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

    def test_accepts_fish_as_a_valid_tts_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.json"
            store = VoiceSettingsStore(_ConfigStub(), path=path)

            saved = store.save(
                {
                    "tts_provider": "fish",
                    "elevenlabs_voice": "voice-alt",
                    "piper_model_path": "",
                    "piper_speaker": "2",
                }
            )

            self.assertEqual(saved.tts_provider, "fish")

    def test_voice_describe_surfaces_runtime_blocker_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.json"
            runtime_status_path = Path(tmp) / "voice_runtime_status.json"
            store = VoiceSettingsStore(_ConfigStub(), path=path)
            store.save(
                {
                    "tts_provider": "fish",
                    "elevenlabs_voice": "",
                    "piper_model_path": "",
                    "piper_speaker": "0",
                }
            )
            record_voice_runtime_status(
                AudioPayload(
                    data=b"system-bytes",
                    content_type="audio/wav",
                    extension=".wav",
                    provider="system",
                    requested_provider="fish",
                    attempted_providers=("fish", "system"),
                    provider_failures=(
                        "fish: Fish Audio request failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)",
                    ),
                ),
                path=runtime_status_path,
            )

            with patch("jarvis.speech.VOICE_RUNTIME_STATUS_PATH", runtime_status_path), patch(
                "jarvis.settings.PIPER_VOICE_ROOT",
                Path(tmp) / "missing-piper-voices",
            ):
                described = store.describe()
                options = store.voice_options()

            self.assertEqual(described["tts_provider"], "fish")
            self.assertFalse(described["stack_status"]["selected_tts_provider_live_ready"])
            self.assertEqual(described["stack_status"]["selected_tts_provider_live_state"], "ssl_transport_blocked")
            self.assertIn(
                "certificate verify failed",
                described["stack_status"]["selected_tts_provider_live_reason"].lower(),
            )
            self.assertEqual(described["stack_status"]["last_live_effective_tts_provider"], "system")
            self.assertIn("voice_runtime_diagnostics", described["stack_status"])
            self.assertIn("providers", described["stack_status"]["voice_runtime_diagnostics"])
            self.assertEqual(
                options["stack_status"]["voice_runtime_diagnostics"]["last_requested_provider"],
                "fish",
            )

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
