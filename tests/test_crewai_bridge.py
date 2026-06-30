from __future__ import annotations

import unittest

from jarvis.crewai_bridge import CrewAIPartyModeBridge


class _StubBridge(CrewAIPartyModeBridge):
    def __init__(self, raw: str) -> None:
        super().__init__(llm="test-model")
        self._raw = raw

    def _run_idea_crew(self, needed: int):  # type: ignore[override]
        return type("Result", (), {"raw": self._raw})()

    def _run_research_crew(self, *, title: str, idea: str, domain: str):  # type: ignore[override]
        return type("Result", (), {"raw": self._raw})()


class CrewAIBridgeTests(unittest.TestCase):
    def test_dream_passive_income_ideas_parses_fenced_json(self) -> None:
        bridge = _StubBridge(
            """```json
            [
              {"title": "API Scorecards", "idea": "Sell automated scorecards for SaaS teams."},
              {"title": "Tiny SEO Monitor", "idea": "Monitor SEO regressions for niche sites."}
            ]
            ```"""
        )

        ideas = bridge.dream_passive_income_ideas(needed=2)

        self.assertEqual(len(ideas), 2)
        self.assertEqual(ideas[0]["title"], "API Scorecards")
        self.assertIn("SEO", ideas[1]["idea"])

    def test_build_research_brief_returns_structured_fields(self) -> None:
        bridge = _StubBridge(
            """{
              "research_notes": "Demand exists in SMB SaaS teams and competition is fragmented.",
              "proposal_text": "Stage a pilot for 3 SaaS operators and validate pricing.",
              "first_action": "Interview 5 target operators this week."
            }"""
        )

        brief = bridge.build_research_brief(
            title="API Scorecards",
            idea="Automated scorecards for SaaS teams.",
        )

        self.assertIn("fragmented", brief["research_notes"])
        self.assertTrue(brief["proposal_text"].startswith("Stage"))
        self.assertEqual(brief["first_action"], "Interview 5 target operators this week.")


if __name__ == "__main__":
    unittest.main()
