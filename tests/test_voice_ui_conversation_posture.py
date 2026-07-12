import unittest
from pathlib import Path

from jarvis.companion_spine import generate_companion_fallback, harden_companion_reply


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

    def test_browser_voice_listening_collects_conversational_turns(self) -> None:
        text = (ROOT / "jarvis" / "voice_ui.py").read_text(encoding="utf-8")
        self.assertIn("recognitionCommitTimer: null", text)
        self.assertIn("function conversationalPauseMs({{ wakeGuardMode = false, spoken = \"\" }} = {{}}) {{", text)
        self.assertIn("function scheduleSpeechTurnCommit(recognizer, options = {{}}) {{", text)
        self.assertIn("recognizer.continuous = true;", text)
        self.assertIn("for (let index = 0; index < event.results.length; index += 1) {{", text)
        self.assertIn("scheduleSpeechTurnCommit(recognizer, {{ wakeGuardMode, spoken }});", text)
        self.assertIn("clearRecognitionCommitTimer();", text)

    def test_conscious_persona_replies_remain_speakable(self) -> None:
        celebration = generate_companion_fallback(
            "We did it! The launch worked.",
            {"turn_posture": "celebration", "conversation_excerpt": ""},
        )
        hardened = harden_companion_reply(
            "Help me think this through.",
            "Absolutely! The simpler path is stronger. What is fixed? What can move?",
            {"turn_posture": "thinking-partner", "conversation_excerpt": ""},
        )
        for reply in (celebration, hardened):
            with self.subTest(reply=reply):
                self.assertNotIn("\n- ", reply)
                self.assertNotIn("**", reply)
                self.assertLessEqual(reply.count("?"), 1)

    def test_ios_speech_recognition_uses_conversation_friendly_hints(self) -> None:
        text = (
            ROOT
            / "JarvisApple/apps/ios/JarvisPhone/JarvisPhone/Speech/SpeechRecognitionManager.swift"
        ).read_text(encoding="utf-8")
        self.assertIn("req.taskHint                       = .dictation", text)
        self.assertIn("req.contextualStrings              = [", text)
        self.assertIn('"Hey Jarvis"', text)
        self.assertIn("func transcribe(duration: TimeInterval = 8) async -> String", text)
        self.assertIn("try? await Task.sleep(for: .seconds(1.8))", text)


if __name__ == "__main__":
    unittest.main()
