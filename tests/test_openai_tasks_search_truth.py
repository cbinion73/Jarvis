from __future__ import annotations

import unittest
from types import SimpleNamespace

from jarvis.openai_tasks import JarvisOpenAIClient

from tests.test_companion_spine import _plan


class SearchTruthTests(unittest.TestCase):
    def _client(self) -> JarvisOpenAIClient:
        return JarvisOpenAIClient(SimpleNamespace())

    def test_browser_search_context_includes_search_proof(self) -> None:
        client = self._client()
        context = client._format_browser_search_context(
            "**Result A**\nhttps://example.com/a\nA snippet.\n\n**Result B**\nhttps://example.com/b\nB snippet."
        )
        self.assertIn("Search proof:", context)
        self.assertIn("Live browser web search ran for this request.", context)
        self.assertIn("2 web result summaries came back in this turn.", context)
        self.assertIn("Retrieved web context:", context)

    def test_system_prompt_adds_search_truth_rule_when_search_proof_present(self) -> None:
        client = self._client()
        prompt = client._system_prompt_with_context(
            _plan("What is the weather today?"),
            supplemental_context=(
                "Search proof:\n"
                "- Live browser web search ran for this request.\n"
                "- 1 web result summary came back in this turn.\n\n"
                "Retrieved web context:\n"
                "**Weather**\nSunny."
            ),
        )
        self.assertIn("Search and retrieval truth rule:", prompt)
        self.assertIn("do not say you searched, found, looked up, or retrieved live web results", prompt)

    def test_system_prompt_does_not_add_search_truth_rule_without_search_proof(self) -> None:
        client = self._client()
        prompt = client._system_prompt_with_context(
            _plan("Help me think this through."),
            supplemental_context="Known local context:\n- Chris prefers practical help.",
        )
        self.assertNotIn("Search and retrieval truth rule:", prompt)


if __name__ == "__main__":
    unittest.main()
