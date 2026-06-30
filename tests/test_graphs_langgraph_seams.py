from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from jarvis.graphs import run_response_graph
from jarvis.openai_tasks import OpenAIResult


class GraphLangGraphSeamTests(unittest.TestCase):
    def test_response_graph_keeps_per_call_continuity_context_isolated(self) -> None:
        runtime = SimpleNamespace(
            storm_weather_summary=lambda: {"available": False},
            family_calendar=SimpleNamespace(summary=lambda: {"events": []}),
            openviking_support=SimpleNamespace(enabled=False),
            get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
        )
        plan = SimpleNamespace(
            actor="Chris",
            room="office",
            request="Help me think.",
            context_lane="default",
        )

        def _fake_turn(_runtime, _actor, _room, _request, *, plan, continuity_context: str = "") -> OpenAIResult:
            return OpenAIResult(
                provider="test",
                model="test",
                output_text=continuity_context,
            )

        with patch("jarvis.graphs.run_companion_turn", _fake_turn):
            first = run_response_graph(runtime, plan, continuity_context="first-context")
            second = run_response_graph(runtime, plan, continuity_context="second-context")

        self.assertTrue(first.output_text.endswith("first-context"))
        self.assertTrue(second.output_text.endswith("second-context"))


if __name__ == "__main__":
    unittest.main()
