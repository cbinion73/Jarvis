import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VoiceUiConversationPostureTests(unittest.TestCase):
    def test_wake_word_pattern_accepts_natural_friend_openers(self) -> None:
        text = (ROOT / "jarvis" / "voice_ui.py").read_text(encoding="utf-8")
        self.assertIn(
            r'return /^(?:hey[\\s,]+jarvis|hi[\\s,]+jarvis|ok(?:ay)?[\\s,]+jarvis|jarvis)\\b[\\s,.:;-]*/i;',
            text,
        )

    def test_spoken_replies_keep_conversation_window_open(self) -> None:
        text = (ROOT / "jarvis" / "voice_ui.py").read_text(encoding="utf-8")
        self.assertIn("followUpWindowMs: 120000", text)
        self.assertIn("function armImmediateReplyWindow(text) {{", text)
        self.assertIn("extendConversationWindow();", text)
        self.assertIn(
            "state.followUpUntil = Date.now() + Math.max(state.followUpWindowMs, 180000);",
            text,
        )
        self.assertNotIn(
            "function armImmediateReplyWindow(text) {{\n      if (isImmediateQuestion(text)) {{",
            text,
        )

    def test_event_stream_is_opt_in_to_avoid_console_noise(self) -> None:
        text = (ROOT / "jarvis" / "voice_ui.py").read_text(encoding="utf-8")
        self.assertIn('const SHELL_EVENT_STREAM_PATH = "/ws/events";', text)
        self.assertIn("function shellEventStreamEnabled() {{", text)
        self.assertIn("if (!shellEventStreamEnabled()) {{", text)
        self.assertIn('const socket = new WebSocket(`${{protocol}}://${{window.location.host}}${{SHELL_EVENT_STREAM_PATH}}`);', text)
        self.assertIn("if (shellEventStreamEnabled()) {{\n      connectEventStream();\n    }}", text)

    def test_voice_settings_surface_distinguishes_configured_and_live_posture(self) -> None:
        text = (ROOT / "jarvis" / "voice_ui.py").read_text(encoding="utf-8")
        self.assertIn("TTS Provider", text)
        self.assertIn("ElevenLabs Voice", text)
        self.assertIn("Piper Voice Model", text)
        self.assertIn("Piper Speaker", text)
        self.assertIn("Preview Phrase", text)
        self.assertIn("Save Voice Settings", text)
        self.assertIn("Configured source", text)
        self.assertIn("Configured readiness", text)
        self.assertIn("Last live readiness", text)
        self.assertIn("Last live blocker", text)
        self.assertIn("Last live fallback", text)
        self.assertIn("Saved. Configured voice source:", text)
        self.assertIn("Save voice settings here, then preview through the current voice route.", text)

    def test_voice_preview_surface_reports_requested_effective_and_live_blocker(self) -> None:
        text = (ROOT / "jarvis" / "voice_ui.py").read_text(encoding="utf-8")
        self.assertIn("function summarizeVoicePreviewResult(response) {{", text)
        self.assertIn("Preview requested ${{requested}}, but playback used ${{effective}}. Live blocker: ${{blocker}}", text)
        self.assertIn("Preview requested ${{requested}} and played with ${{effective}}.", text)
        self.assertIn("Configured voice source saved. Running preview through the current voice route", text)
        self.assertIn("Preview failed:", text)


if __name__ == "__main__":
    unittest.main()
