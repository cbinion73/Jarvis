from __future__ import annotations

import unittest
from dataclasses import dataclass

from jarvis.party_mode import PartyModeController


class _BridgeStub:
    def __init__(self) -> None:
        self.idea_calls: list[int] = []
        self.research_calls: list[str] = []

    def dream_passive_income_ideas(self, needed: int) -> list[dict[str, str]]:
        self.idea_calls.append(needed)
        return [{"title": "API Scorecards", "idea": "Recurring diagnostics for SaaS ops teams."}]

    def build_research_brief(self, *, title: str, idea: str, domain: str = "general") -> dict[str, str]:
        self.research_calls.append(title)
        return {
            "research_notes": "Validated demand, fragmented competition, clear wedge via reporting automation.",
            "proposal_text": "Pilot with three teams.",
            "first_action": "Interview three operators.",
        }


class _GatewayStub:
    def simple_complete(self, prompt: str, max_tokens: int = 0, task_type: str = "") -> str:
        raise AssertionError("Gateway fallback should not run when CrewAI succeeds")


@dataclass
class _WorkItem:
    work_id: str
    title: str
    idea: str
    domain: str = "passive-income"
    research: str = ""


class _StoreStub:
    def __init__(self) -> None:
        self.research_updates: list[tuple[str, str]] = []

    def advance_to_research(self, work_id: str, research_notes: str):
        self.research_updates.append((work_id, research_notes))
        return _WorkItem(
            work_id=work_id,
            title="API Scorecards",
            idea="Recurring diagnostics for SaaS ops teams.",
            research=research_notes,
        )


class PartyModeCrewAITests(unittest.TestCase):
    def test_generate_dream_ideas_prefers_crewai_bridge(self) -> None:
        bridge = _BridgeStub()
        controller = PartyModeController(crewai_bridge=bridge)

        ideas = controller._generate_dream_ideas(_GatewayStub(), 1, lambda _msg: None)

        self.assertEqual(bridge.idea_calls, [1])
        self.assertEqual(len(ideas), 1)
        self.assertEqual(ideas[0]["title"], "API Scorecards")

    def test_prime_work_item_with_crewai_brief_advances_research(self) -> None:
        bridge = _BridgeStub()
        controller = PartyModeController(crewai_bridge=bridge)
        store = _StoreStub()
        work_item = _WorkItem(
            work_id="work-1",
            title="API Scorecards",
            idea="Recurring diagnostics for SaaS ops teams.",
        )

        updated = controller._prime_work_item_with_crewai_brief(store, work_item, lambda _msg: None)

        self.assertEqual(bridge.research_calls, ["API Scorecards"])
        self.assertEqual(len(store.research_updates), 1)
        self.assertIn("fragmented competition", updated.research)


if __name__ == "__main__":
    unittest.main()
