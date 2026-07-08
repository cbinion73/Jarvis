"""Routing and escalation-ladder tests for the LLM gateway.

OpenAI-only gateway — no Ollama, no Groq. Covers the converse-floor routing
(conversation reaches the full non-mini OpenAI model instead of the mini
tier) and the escalation ladder (mini -> full -> gpt-5.4-thinking ->
gpt-5.5-thinking, tier-5 stays at the top).
"""

from __future__ import annotations

import json
import os
import unittest
from unittest import mock

from jarvis.llm_gateway import LLMGateway, LLMMessage, OpenAIBackend


class _StubBackend:
    def __init__(self, available: bool = True) -> None:
        self._available = available

    def is_available(self) -> bool:
        return self._available


def _gateway(openai_available: bool = True) -> LLMGateway:
    return LLMGateway(openai=_StubBackend(available=openai_available))


_ENV = {
    "JARVIS_OPENAI_MODEL": "gpt-5-mini",
    "JARVIS_CONVERSE_MODEL": "",
}


class ConverseFloorRoutingTests(unittest.TestCase):
    def test_converse_routes_to_full_openai_model(self) -> None:
        # Chris's explicit call: everyday conversation runs on ChatGPT-grade
        # quality — the full non-mini sibling of the configured OpenAI model.
        with mock.patch.dict(os.environ, _ENV):
            model = _gateway()._resolve_model("converse")
        self.assertEqual(model, "gpt-5")

    def test_converse_without_openai_falls_back_to_mini(self) -> None:
        with mock.patch.dict(os.environ, _ENV):
            model = _gateway(openai_available=False)._resolve_model("converse")
        self.assertEqual(model, "gpt-5-mini")

    def test_full_model_derivation_handles_versioned_names(self) -> None:
        env = dict(_ENV, JARVIS_OPENAI_MODEL="gpt-5.4-mini")
        with mock.patch.dict(os.environ, env):
            model = _gateway()._resolve_model("converse")
        self.assertEqual(model, "gpt-5.4")

    def test_full_gpt_models_route_to_openai_backend(self) -> None:
        with mock.patch.dict(os.environ, _ENV):
            self.assertEqual(_gateway()._backend_for("gpt-5"), "openai")

    def test_explicit_converse_model_override_wins(self) -> None:
        env = dict(_ENV, JARVIS_CONVERSE_MODEL="gpt-5.4-thinking")
        with mock.patch.dict(os.environ, env):
            model = _gateway()._resolve_model("converse")
        self.assertEqual(model, "gpt-5.4-thinking")

    def test_force_model_still_wins_over_converse_floor(self) -> None:
        with mock.patch.dict(os.environ, _ENV):
            model = _gateway()._resolve_model("converse", force_model="gpt-4o")
        self.assertEqual(model, "gpt-4o")

    def test_interactive_substantive_tasks_stay_on_mini(self) -> None:
        # draft/plan/analyze/reason resolve to the mini tier — there is no
        # local option anymore, everything routes to OpenAI.
        with mock.patch.dict(os.environ, _ENV):
            gw = _gateway()
            for task in ("draft", "plan", "analyze", "reason"):
                self.assertEqual(gw._resolve_model(task), "gpt-5-mini", task)


class TaskRoutingTests(unittest.TestCase):
    """Every task type resolves to an OpenAI model — no local or Groq tier."""

    def test_classify_and_background_tasks_use_mini(self) -> None:
        with mock.patch.dict(os.environ, _ENV):
            gw = _gateway()
            for task in ("classify", "route", "tag", "detect", "check"):
                self.assertEqual(gw._resolve_model(task), "gpt-5-mini", task)
            for task in ("summarize", "extract", "format", "briefing"):
                self.assertEqual(gw._resolve_model(task), "gpt-5-mini", task)
            self.assertEqual(gw._resolve_model("agent_work"), "gpt-5-mini")

    def test_conversation_and_strategy_diverge(self) -> None:
        with mock.patch.dict(os.environ, _ENV):
            gw = _gateway()
            self.assertEqual(gw._resolve_model("converse"), "gpt-5")
            self.assertEqual(gw._resolve_model("strategy"), "gpt-5-mini")


class EscalationLadderTests(unittest.TestCase):
    def test_ladder_progresses_mini_full_thinking_tiers(self) -> None:
        with mock.patch.dict(os.environ, _ENV):
            gw = _gateway()
            self.assertEqual(gw._escalate_model("gpt-5-mini"), "gpt-5")
            self.assertEqual(gw._escalate_model("gpt-5"), "gpt-5.4-thinking")
            self.assertEqual(gw._escalate_model("gpt-5.4-thinking"), "gpt-5.5-thinking")
            self.assertIsNone(gw._escalate_model("gpt-5.5-thinking"))

    def test_unknown_openai_model_does_not_escalate(self) -> None:
        # gpt-4o routes to the openai backend but is not a ladder rung.
        with mock.patch.dict(os.environ, _ENV):
            self.assertIsNone(_gateway()._escalate_model("gpt-4o"))

    def test_single_escalate_model_definition(self) -> None:
        # A second def used to shadow the real ladder, silently disabling
        # the thinking tiers and tier-5 approval gating.
        import inspect
        import jarvis.llm_gateway as gw_module

        source = inspect.getsource(gw_module.LLMGateway)
        self.assertEqual(source.count("def _escalate_model"), 1)


def _captured_payload(model: str, temperature: float = 0.7) -> dict:
    """Build the request payload OpenAIBackend.complete() would send, without
    a network call, by capturing what's passed to urllib.request.Request."""
    captured: dict = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "ok"}}], "usage": {}}
            ).encode("utf-8")

    def _fake_urlopen(req, timeout=60):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse()

    backend = OpenAIBackend(api_key="sk-test")
    with mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen):
        backend.complete(
            [LLMMessage(role="user", content="hi")],
            model=model,
            temperature=temperature,
        )
    return captured["body"]


class OpenAIPayloadShapeTests(unittest.TestCase):
    """Regression coverage for a real bug: gpt-5-family models were sent a
    custom 'temperature', which OpenAI's API hard-rejects (400) for any model
    using the new max_completion_tokens param family — silently breaking
    every OpenAI gateway call in cloud_light mode, including conversation."""

    def test_gpt5_full_model_omits_temperature(self) -> None:
        body = _captured_payload("gpt-5")
        self.assertNotIn("temperature", body)
        self.assertIn("max_completion_tokens", body)
        self.assertNotIn("max_tokens", body)

    def test_gpt5_mini_omits_temperature(self) -> None:
        body = _captured_payload("gpt-5-mini")
        self.assertNotIn("temperature", body)
        self.assertIn("max_completion_tokens", body)

    def test_gpt5_budget_includes_reasoning_headroom(self) -> None:
        # max_completion_tokens counts hidden reasoning tokens; without
        # headroom the model can spend the whole budget reasoning and
        # return an empty visible reply (observed live).
        from jarvis.llm_gateway import _REASONING_TOKEN_HEADROOM

        body = _captured_payload("gpt-5")
        self.assertGreaterEqual(
            body["max_completion_tokens"], 2048 + _REASONING_TOKEN_HEADROOM
        )

    def test_o_series_models_omit_temperature(self) -> None:
        for model in ("o1", "o1-mini", "o3"):
            with self.subTest(model=model):
                body = _captured_payload(model)
                self.assertNotIn("temperature", body)

    def test_legacy_model_keeps_temperature_and_max_tokens(self) -> None:
        body = _captured_payload("gpt-4o", temperature=0.4)
        self.assertEqual(body.get("temperature"), 0.4)
        self.assertIn("max_tokens", body)
        self.assertNotIn("max_completion_tokens", body)

    def test_thinking_model_uses_reasoning_effort_not_temperature(self) -> None:
        body = _captured_payload("gpt-5.4-thinking")
        self.assertNotIn("temperature", body)
        self.assertEqual(body.get("reasoning_effort"), "high")


if __name__ == "__main__":
    unittest.main()
