"""Companion conversation turns must route through the LLM gateway.

run_companion_turn -> openai_client.respond() used to call the OpenAI SDK
directly, bypassing the gateway entirely — so conversation never reached
the converse-floor model, confidence escalation, or Groq fallback. These
tests pin the new behavior: when a gateway is initialized, conversation
turns (the only respond() calls that set system_prompt_override) go
through it; when the gateway is missing or degraded, the pre-existing
path is used unchanged.
"""

from __future__ import annotations

import unittest
from unittest import mock

from jarvis.llm_gateway import LLMResponse
from jarvis.models import (
    ActionClass,
    PrivacyLevel,
    RequestPlan,
    RiskLevel,
    RoutingTier,
    TaskClass,
)
from jarvis.openai_tasks import JarvisOpenAIClient


def _plan(request: str = "What should I focus on this week?") -> RequestPlan:
    return RequestPlan(
        request_id="test-req",
        actor="chris",
        room="office",
        request=request,
        mode="normal",
        module="",
        workstream="",
        task_class=TaskClass.AMBIENT,
        preferred_provider="openai",
        context_lane="conversation",
        model="gpt-5-mini",
        routing_tier=RoutingTier.USER_FACING_DELIVERY,
        privacy_level=PrivacyLevel.LOCAL_ONLY,
        risk_level=list(RiskLevel)[0],
        action_class=list(ActionClass)[0],
        allowed=True,
        needs_approval=False,
        second_factor_required=False,
        rationale="",
    )


def _client() -> JarvisOpenAIClient:
    config = mock.Mock()
    config.openai_api_key = "sk-test"
    return JarvisOpenAIClient(config)


def _gateway_response(text: str = "Here's my read.", error: str = "") -> LLMResponse:
    return LLMResponse(
        text=text,
        model_used="llama-3.3-70b-versatile",
        backend="groq",
        task_type="converse",
        latency_ms=120,
        prompt_tokens=800,
        completion_tokens=150,
        confidence=0.9,
        escalated=False,
        error=error,
    )


class CompanionGatewayRoutingTests(unittest.TestCase):
    def test_companion_turn_uses_gateway_when_available(self) -> None:
        client = _client()
        gateway = mock.Mock()
        gateway.complete.return_value = _gateway_response()
        with mock.patch("jarvis.llm_gateway.get_gateway", return_value=gateway):
            result = client.respond(
                _plan(),
                supplemental_context="Companion context packet: {}",
                system_prompt_override="You are Jarvis, Chris's private AI companion.",
            )
        self.assertEqual(result.provider, "groq")
        self.assertEqual(result.model, "llama-3.3-70b-versatile")
        self.assertEqual(result.output_text, "Here's my read.")
        gateway.complete.assert_called_once()
        _, kwargs = gateway.complete.call_args
        self.assertEqual(kwargs.get("task_type"), "converse")

    def test_gateway_receives_system_prompt_and_user_message(self) -> None:
        client = _client()
        gateway = mock.Mock()
        gateway.complete.return_value = _gateway_response()
        with mock.patch("jarvis.llm_gateway.get_gateway", return_value=gateway):
            client.respond(
                _plan("Help me think through the book launch."),
                supplemental_context="",
                system_prompt_override="You are Jarvis.",
            )
        messages = gateway.complete.call_args[0][0]
        self.assertEqual(messages[0].role, "system")
        self.assertIn("You are Jarvis", messages[0].content)
        self.assertEqual(messages[1].role, "user")
        self.assertEqual(messages[1].content, "Help me think through the book launch.")

    def test_degraded_gateway_falls_through_to_sdk_path(self) -> None:
        client = _client()
        gateway = mock.Mock()
        gateway.complete.return_value = _gateway_response(text="", error="rate_limited")
        sdk_result = mock.Mock()
        with mock.patch("jarvis.llm_gateway.get_gateway", return_value=gateway), \
                mock.patch.object(client, "_build_response_payload", return_value={}), \
                mock.patch("openai.OpenAI") as sdk, \
                mock.patch.object(client, "_sdk_result_to_output", return_value=sdk_result):
            sdk.return_value.responses.create.return_value = object()
            result = client.respond(
                _plan(),
                system_prompt_override="You are Jarvis.",
            )
        self.assertIs(result, sdk_result)

    def test_no_gateway_falls_through_to_sdk_path(self) -> None:
        client = _client()
        sdk_result = mock.Mock()
        with mock.patch("jarvis.llm_gateway.get_gateway", return_value=None), \
                mock.patch.object(client, "_build_response_payload", return_value={}), \
                mock.patch("openai.OpenAI") as sdk, \
                mock.patch.object(client, "_sdk_result_to_output", return_value=sdk_result):
            sdk.return_value.responses.create.return_value = object()
            result = client.respond(
                _plan(),
                system_prompt_override="You are Jarvis.",
            )
        self.assertIs(result, sdk_result)

    def test_non_companion_calls_never_touch_gateway(self) -> None:
        # respond() without system_prompt_override (module/tool flows) must
        # not change behavior.
        client = _client()
        gateway = mock.Mock()
        sdk_result = mock.Mock()
        with mock.patch("jarvis.llm_gateway.get_gateway", return_value=gateway), \
                mock.patch.object(client, "_build_response_payload", return_value={}), \
                mock.patch("openai.OpenAI") as sdk, \
                mock.patch.object(client, "_sdk_result_to_output", return_value=sdk_result):
            sdk.return_value.responses.create.return_value = object()
            client.respond(_plan())
        gateway.complete.assert_not_called()

    def test_gateway_trace_recorded_in_execution_trace(self) -> None:
        client = _client()
        gateway = mock.Mock()
        gateway.complete.return_value = _gateway_response()
        with mock.patch("jarvis.llm_gateway.get_gateway", return_value=gateway):
            result = client.respond(
                _plan(),
                system_prompt_override="You are Jarvis.",
            )
        sources = [entry.get("source") for entry in result.execution_trace]
        self.assertIn("llm_gateway", sources)


if __name__ == "__main__":
    unittest.main()
