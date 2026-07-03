"""Routing and escalation-ladder tests for the LLM gateway.

Covers the converse-floor routing (conversation should reach Groq's free
70B in cloud_light mode instead of the collapsed mini tier) and the
unified escalation ladder (alias-safe across cloud_light's tier collapse,
free Groq rungs before paid OpenAI, tier-5 stays at the top).
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from jarvis.llm_gateway import LLMGateway


class _StubBackend:
    def __init__(self, available: bool = True) -> None:
        self._available = available

    def is_available(self) -> bool:
        return self._available


def _gateway(groq_available: bool = True) -> LLMGateway:
    return LLMGateway(
        ollama=_StubBackend(),
        openai=_StubBackend(),
        groq=_StubBackend(available=groq_available),
    )


_CLOUD_LIGHT_ENV = {
    "JARVIS_MODEL_MODE": "cloud_light",
    "JARVIS_OPENAI_MODEL": "gpt-5-mini",
    "JARVIS_GROQ_MODEL": "llama-3.3-70b-versatile",
    "JARVIS_GROQ_REASONING_MODEL": "openai/gpt-oss-120b",
    "JARVIS_CONVERSE_MODEL": "",
}

_LOCAL_ENV = {
    "JARVIS_MODEL_MODE": "standard",
    "JARVIS_OPENAI_MODEL": "gpt-5-mini",
    "JARVIS_GROQ_MODEL": "llama-3.3-70b-versatile",
    "JARVIS_GROQ_REASONING_MODEL": "openai/gpt-oss-120b",
    "JARVIS_OLLAMA_FAST_MODEL": "phi3.5",
    "JARVIS_OLLAMA_SUBSTANTIVE_MODEL": "qwen2.5:14b",
    "JARVIS_OLLAMA_BACKGROUND_MODEL": "qwen2.5:7b",
    "JARVIS_CONVERSE_MODEL": "",
}


class ConverseFloorRoutingTests(unittest.TestCase):
    def test_cloud_light_converse_routes_to_free_groq(self) -> None:
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            model = _gateway()._resolve_model("converse")
        self.assertEqual(model, "llama-3.3-70b-versatile")

    def test_cloud_light_converse_without_groq_keeps_prior_behavior(self) -> None:
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            model = _gateway(groq_available=False)._resolve_model("converse")
        self.assertEqual(model, "gpt-5-mini")

    def test_local_mode_converse_unchanged(self) -> None:
        with mock.patch.dict(os.environ, _LOCAL_ENV):
            model = _gateway()._resolve_model("converse")
        self.assertEqual(model, "qwen2.5:14b")

    def test_explicit_converse_model_override_wins(self) -> None:
        env = dict(_CLOUD_LIGHT_ENV, JARVIS_CONVERSE_MODEL="gpt-5.4-thinking")
        with mock.patch.dict(os.environ, env):
            model = _gateway()._resolve_model("converse")
        self.assertEqual(model, "gpt-5.4-thinking")

    def test_force_model_still_wins_over_converse_floor(self) -> None:
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            model = _gateway()._resolve_model("converse", force_model="qwen2.5:14b")
        self.assertEqual(model, "qwen2.5:14b")

    def test_other_substantive_tasks_keep_mini_floor_in_cloud_light(self) -> None:
        # Cost control: only conversation gets the Groq floor; internal
        # work (agent_work/draft/plan) stays on the collapsed mini tier.
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            gw = _gateway()
            for task in ("agent_work", "draft", "plan", "analyze", "reason"):
                self.assertEqual(gw._resolve_model(task), "gpt-5-mini", task)


class EscalationLadderTests(unittest.TestCase):
    def test_cloud_light_ladder_dedupes_collapsed_tiers(self) -> None:
        # fast/substantive/openai all collapse to gpt-5-mini in cloud_light;
        # escalation must still make progress instead of dead-ending.
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            gw = _gateway()
            self.assertEqual(gw._escalate_model("gpt-5-mini"), "llama-3.3-70b-versatile")
            self.assertEqual(gw._escalate_model("llama-3.3-70b-versatile"), "openai/gpt-oss-120b")
            self.assertEqual(gw._escalate_model("openai/gpt-oss-120b"), "gpt-5.4-thinking")
            self.assertEqual(gw._escalate_model("gpt-5.4-thinking"), "gpt-5.5-thinking")
            self.assertIsNone(gw._escalate_model("gpt-5.5-thinking"))

    def test_local_ladder_preserves_free_rungs_before_paid(self) -> None:
        with mock.patch.dict(os.environ, _LOCAL_ENV):
            gw = _gateway()
            self.assertEqual(gw._escalate_model("phi3.5"), "qwen2.5:14b")
            self.assertEqual(gw._escalate_model("qwen2.5:7b"), "qwen2.5:14b")
            self.assertEqual(gw._escalate_model("qwen2.5:14b"), "llama-3.3-70b-versatile")
            self.assertEqual(gw._escalate_model("llama-3.3-70b-versatile"), "openai/gpt-oss-120b")
            self.assertEqual(gw._escalate_model("openai/gpt-oss-120b"), "gpt-5-mini")
            self.assertEqual(gw._escalate_model("gpt-5-mini"), "gpt-5.4-thinking")

    def test_unknown_model_does_not_escalate(self) -> None:
        with mock.patch.dict(os.environ, _LOCAL_ENV):
            self.assertIsNone(_gateway()._escalate_model("some-custom-model"))

    def test_single_escalate_model_definition(self) -> None:
        # A second def used to shadow the real ladder, silently disabling
        # the thinking tiers and tier-5 approval gating.
        import inspect
        import jarvis.llm_gateway as gw_module

        source = inspect.getsource(gw_module.LLMGateway)
        self.assertEqual(source.count("def _escalate_model"), 1)


if __name__ == "__main__":
    unittest.main()
