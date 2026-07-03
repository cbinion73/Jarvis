"""Routing and escalation-ladder tests for the LLM gateway.

Covers the converse-floor routing (conversation should reach Groq's free
70B in cloud_light mode instead of the collapsed mini tier) and the
unified escalation ladder (alias-safe across cloud_light's tier collapse,
free Groq rungs before paid OpenAI, tier-5 stays at the top).
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
    def test_cloud_light_converse_routes_to_full_openai_model(self) -> None:
        # Chris's explicit call: everyday conversation runs on ChatGPT-grade
        # quality — the full non-mini sibling of the configured OpenAI model.
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            model = _gateway()._resolve_model("converse")
        self.assertEqual(model, "gpt-5")

    def test_cloud_light_converse_without_openai_keeps_prior_behavior(self) -> None:
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            gw = LLMGateway(
                ollama=_StubBackend(),
                openai=_StubBackend(available=False),
                groq=_StubBackend(),
            )
            model = gw._resolve_model("converse")
        self.assertEqual(model, "gpt-5-mini")

    def test_full_model_derivation_handles_versioned_names(self) -> None:
        env = dict(_CLOUD_LIGHT_ENV, JARVIS_OPENAI_MODEL="gpt-5.4-mini")
        with mock.patch.dict(os.environ, env):
            model = _gateway()._resolve_model("converse")
        self.assertEqual(model, "gpt-5.4")

    def test_full_gpt_models_route_to_openai_backend(self) -> None:
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            self.assertEqual(_gateway()._backend_for("gpt-5"), "openai")

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

    def test_interactive_substantive_tasks_keep_mini_floor_in_cloud_light(self) -> None:
        # Cost control: interactive module work (draft/plan/analyze/reason)
        # stays on the collapsed mini tier. agent_work is background-class
        # and prefers local — covered in BackgroundPreferLocalTests.
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            gw = _gateway()
            for task in ("draft", "plan", "analyze", "reason"):
                self.assertEqual(gw._resolve_model(task), "gpt-5-mini", task)


class BackgroundPreferLocalTests(unittest.TestCase):
    """Chris's cost policy: background/scheduled work runs on free local
    Ollama models when available — even in cloud_light — and can take all
    the time it wants. Cloud spend belongs to conversation and strategy."""

    def test_background_tasks_route_local_when_ollama_up(self) -> None:
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            gw = _gateway()
            for task in ("summarize", "extract", "format", "briefing"):
                self.assertEqual(gw._resolve_model(task), "qwen3:4b", task)
            for task in ("classify", "route", "tag", "detect", "check"):
                self.assertEqual(gw._resolve_model(task), "qwen3:4b", task)
            self.assertEqual(gw._resolve_model("agent_work"), "qwen3:14b")

    def test_conversation_and_strategy_stay_cloud(self) -> None:
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            gw = _gateway()
            self.assertEqual(gw._resolve_model("converse"), "gpt-5")
            self.assertEqual(gw._resolve_model("strategy"), "gpt-5-mini")
            # Unmapped/interactive substantive tasks also stay on the mini tier.
            self.assertEqual(gw._resolve_model("reason"), "gpt-5-mini")

    def test_ollama_down_falls_back_to_cloud(self) -> None:
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            gw = LLMGateway(
                ollama=_StubBackend(available=False),
                openai=_StubBackend(),
                groq=_StubBackend(),
            )
            self.assertEqual(gw._resolve_model("summarize"), "gpt-5-mini")
            self.assertEqual(gw._resolve_model("agent_work"), "gpt-5-mini")

    def test_kill_switch_forces_cloud(self) -> None:
        env = dict(_CLOUD_LIGHT_ENV, JARVIS_BACKGROUND_PREFER_LOCAL="false")
        with mock.patch.dict(os.environ, env):
            gw = _gateway()
            self.assertEqual(gw._resolve_model("summarize"), "gpt-5-mini")

    def test_low_confidence_local_reply_escalates_to_free_groq(self) -> None:
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            gw = _gateway()
            self.assertEqual(gw._escalate_model("qwen3:14b"), "llama-3.3-70b-versatile")

    def test_local_escalation_skips_groq_without_key(self) -> None:
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            gw = LLMGateway(
                ollama=_StubBackend(),
                openai=_StubBackend(),
                groq=_StubBackend(available=False),
            )
            self.assertEqual(gw._escalate_model("qwen3:14b"), "gpt-5-mini")


class EscalationLadderTests(unittest.TestCase):
    def test_cloud_light_ladder_dedupes_collapsed_tiers(self) -> None:
        # fast/substantive/openai all collapse to gpt-5-mini in cloud_light;
        # escalation must still make progress instead of dead-ending.
        with mock.patch.dict(os.environ, _CLOUD_LIGHT_ENV):
            gw = _gateway()
            self.assertEqual(gw._escalate_model("gpt-5-mini"), "llama-3.3-70b-versatile")
            self.assertEqual(gw._escalate_model("llama-3.3-70b-versatile"), "openai/gpt-oss-120b")
            self.assertEqual(gw._escalate_model("openai/gpt-oss-120b"), "gpt-5")
            self.assertEqual(gw._escalate_model("gpt-5"), "gpt-5.4-thinking")
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
            self.assertEqual(gw._escalate_model("gpt-5-mini"), "gpt-5")
            self.assertEqual(gw._escalate_model("gpt-5"), "gpt-5.4-thinking")

    def test_unknown_openai_model_does_not_escalate(self) -> None:
        # gpt-4o routes to the openai backend but is not a ladder rung.
        with mock.patch.dict(os.environ, _LOCAL_ENV):
            self.assertIsNone(_gateway()._escalate_model("gpt-4o"))

    def test_unknown_local_model_escalates_to_cloud(self) -> None:
        # Anything ollama-backed that is not in the ladder (e.g. a custom
        # local model from the background-prefer-local path) still escalates
        # to free Groq so low-confidence local output improves.
        with mock.patch.dict(os.environ, _LOCAL_ENV):
            self.assertEqual(
                _gateway()._escalate_model("some-custom-model"),
                "llama-3.3-70b-versatile",
            )

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
