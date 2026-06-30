from __future__ import annotations

import unittest
from types import SimpleNamespace

from jarvis.openai_tasks import JarvisOpenAIClient

from tests.test_companion_spine import _plan


class DegradedModeHonestyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = JarvisOpenAIClient(SimpleNamespace())

    def test_manual_response_fallback_says_unavailable_plainly(self) -> None:
        text = self.client._manual_response_fallback(
            _plan("Search the web for the latest market news."),
            RuntimeError("OPENAI_API_KEY is missing."),
        )
        self.assertIn("unavailable right now", text)
        self.assertIn("I can still help in a reduced way", text)
        self.assertNotIn("I searched", text)
        self.assertNotIn("I found", text)

    def test_manual_prompt_fallback_says_partially_wired_plainly(self) -> None:
        text = self.client._manual_prompt_fallback(
            "Research mode",
            "Put together the evidence.",
            RuntimeError("Local scaffold only; live retrieval path is partially wired."),
        )
        self.assertIn("only partially wired right now", text)
        self.assertIn("I can still help with a local fallback", text)
        self.assertNotIn("completed live tool path", text.replace("not treating this as a completed live tool path", ""))

    def test_manual_image_fallback_says_blocked_or_degraded_plainly(self) -> None:
        text = self.client._manual_image_fallback(RuntimeError("Unexpected upstream gateway failure."))
        self.assertIn("blocked or degraded right now", text)
        self.assertIn("I cannot honestly claim image analysis succeeded", text)
        self.assertIn("vision model path is unavailable right now", text)


if __name__ == "__main__":
    unittest.main()
