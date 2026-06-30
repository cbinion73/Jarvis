from __future__ import annotations

import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.speech import AudioPayload, record_voice_runtime_status, synthesize_speech, voice_stack_status


class _ConfigStub:
    def __init__(self) -> None:
        self.tts_provider = "fish"
        self.tts_fallbacks = ()
        self.stt_provider = "openai"
        self.stt_fallbacks = ()
        self.elevenlabs_voice = ""
        self.elevenlabs_api_key = ""
        self.fish_api_key = "fish-test-key"
        self.fish_model = "s2.1-pro"
        self.fish_reference_id = "612b878b113047d9a770c069c8b4fdfe"
        self.localai_base_url = ""
        self.localai_api_key = ""
        self.localai_tts_model = ""
        self.localai_tts_backend = ""
        self.localai_stt_model = ""
        self.piper_binary = "piper"
        self.piper_model_path = None
        self.piper_speaker = ""
        self.openai_api_key = "openai-test"


class _UrlOpenResponse:
    def __init__(self, body: bytes, content_type: str = "audio/mpeg") -> None:
        self._body = body
        self.headers = {"Content-Type": content_type}

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FishSpeechTests(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self._fish_env = patch.dict(
            os.environ,
            {
                "FISH_API_KEY": "",
                "FISH_REFERENCE_ID": "",
            },
            clear=False,
        )
        self._fish_env.start()
        self.addCleanup(self._fish_env.stop)

    def test_synthesize_speech_uses_fish_provider(self) -> None:
        config = _ConfigStub()

        with patch("jarvis.speech.request.urlopen", return_value=_UrlOpenResponse(b"fish-audio")) as mocked:
            payload = synthesize_speech(config, "Hello from Jarvis.")

        self.assertIsInstance(payload, AudioPayload)
        self.assertEqual(payload.provider, "fish")
        self.assertEqual(payload.data, b"fish-audio")
        request_obj = mocked.call_args.args[0]
        headers = dict(request_obj.header_items())
        self.assertEqual(request_obj.full_url, "https://api.fish.audio/v1/tts")
        self.assertEqual(headers["Model"], "s2.1-pro")
        self.assertEqual(headers["Authorization"], "Bearer fish-test-key")
        self.assertIn(b"612b878b113047d9a770c069c8b4fdfe", request_obj.data)

    def test_voice_stack_status_reports_fish_ready(self) -> None:
        config = _ConfigStub()
        status = voice_stack_status(config, {"tts_provider": "fish"})
        self.assertTrue(status["fish_ready"])
        self.assertEqual(status["fish_model"], "s2.1-pro")
        self.assertEqual(status["fish_reference_id"], "612b878b113047d9a770c069c8b4fdfe")
        self.assertTrue(status["selected_tts_provider_ready"])
        self.assertEqual(status["selected_tts_provider_state"], "ready")
        self.assertEqual(status["effective_tts_provider"], "fish")
        fish_status = next(item for item in status["tts_provider_statuses"] if item["provider"] == "fish")
        self.assertTrue(fish_status["ready"])
        self.assertEqual(fish_status["state"], "ready")
        self.assertIn("reference voice id", fish_status["reason"])

    def test_voice_stack_status_reports_fish_unavailable_with_system_fallback(self) -> None:
        config = _ConfigStub()
        config.fish_api_key = ""
        config.fish_reference_id = ""
        config.tts_fallbacks = ("system",)

        def _which(binary: str) -> str | None:
            if binary == "say":
                return "/usr/bin/say"
            return None

        with patch("jarvis.speech.shutil.which", side_effect=_which):
            status = voice_stack_status(config, {"tts_provider": "fish"})

        self.assertFalse(status["selected_tts_provider_ready"])
        self.assertEqual(status["selected_tts_provider_state"], "unavailable")
        self.assertIn("FISH_API_KEY is missing.", status["selected_tts_provider_reason"])
        self.assertEqual(status["effective_tts_provider"], "system")
        self.assertIn("fallback can use system", status["effective_tts_note"])
        fish_status = next(item for item in status["tts_provider_statuses"] if item["provider"] == "fish")
        self.assertEqual(fish_status["state"], "unavailable")

    def test_voice_stack_status_reports_degraded_localai_selection(self) -> None:
        config = _ConfigStub()
        config.tts_provider = "localai"
        config.tts_fallbacks = ("system",)
        config.localai_base_url = "http://127.0.0.1:8080"

        def _which(binary: str) -> str | None:
            if binary == "say":
                return "/usr/bin/say"
            return None

        with patch("jarvis.speech._localai_healthcheck", return_value=False), patch(
            "jarvis.speech.shutil.which",
            side_effect=_which,
        ):
            status = voice_stack_status(config, {"tts_provider": "localai"})

        self.assertFalse(status["selected_tts_provider_ready"])
        self.assertEqual(status["selected_tts_provider_state"], "degraded")
        self.assertIn("/readyz healthcheck did not succeed", status["selected_tts_provider_reason"])
        self.assertEqual(status["effective_tts_provider"], "system")
        self.assertIn("fallback can use system", status["effective_tts_note"])
        localai_status = next(item for item in status["tts_provider_statuses"] if item["provider"] == "localai")
        self.assertEqual(localai_status["state"], "degraded")

    def test_voice_stack_status_surfaces_last_known_ssl_blocker_for_fish(self) -> None:
        config = _ConfigStub()
        config.tts_fallbacks = ("system",)

        with tempfile.TemporaryDirectory() as tmp:
            runtime_status_path = Path(tmp) / "voice_runtime_status.json"
            record_voice_runtime_status(
                AudioPayload(
                    data=b"system-bytes",
                    content_type="audio/wav",
                    extension=".wav",
                    provider="system",
                    requested_provider="fish",
                    attempted_providers=("fish", "piper", "localai", "elevenlabs", "system"),
                    provider_failures=(
                        "fish: Fish Audio request failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)",
                    ),
                ),
                path=runtime_status_path,
            )

            def _which(binary: str) -> str | None:
                if binary == "say":
                    return "/usr/bin/say"
                return None

            with patch("jarvis.speech.VOICE_RUNTIME_STATUS_PATH", runtime_status_path), patch(
                "jarvis.speech.shutil.which",
                side_effect=_which,
            ):
                status = voice_stack_status(config, {"tts_provider": "fish"})

        self.assertTrue(status["selected_tts_provider_ready"])
        self.assertFalse(status["selected_tts_provider_live_ready"])
        self.assertEqual(status["selected_tts_provider_live_state"], "ssl_transport_blocked")
        self.assertIn("certificate verify failed", status["selected_tts_provider_live_reason"].lower())
        self.assertEqual(status["last_live_effective_tts_provider"], "system")
        self.assertIn("last live request was ssl_transport_blocked", status["effective_tts_note"])
        self.assertIn("last live fallback reached system", status["effective_tts_note"])
        fish_status = next(item for item in status["tts_provider_statuses"] if item["provider"] == "fish")
        self.assertTrue(fish_status["ready"])
        self.assertFalse(fish_status["live_ready"])
        self.assertEqual(fish_status["last_runtime_state"], "ssl_transport_blocked")
        self.assertIn("certificate verify failed", fish_status["last_runtime_reason"].lower())


if __name__ == "__main__":
    unittest.main()
