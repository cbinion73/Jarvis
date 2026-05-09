from __future__ import annotations

import json
from dataclasses import asdict

from .models import InferredContext, OpenClawBridgeEnvelope, RequestPlan
from .openai_tasks import OpenAIResult


def build_openclaw_envelope(
    gateway_url: str,
    inferred: InferredContext,
    plan: RequestPlan,
    result: OpenAIResult | None = None,
) -> OpenClawBridgeEnvelope:
    return OpenClawBridgeEnvelope(
        gateway_url=gateway_url,
        actor=inferred.actor,
        room=inferred.room,
        raw_request=plan.request,
        cleaned_request=inferred.cleaned_request,
        wake_word_detected=inferred.wake_word_detected,
        module=plan.module,
        mode=plan.mode,
        model=plan.model,
        needs_approval=plan.needs_approval,
        second_factor_required=plan.second_factor_required,
        rationale=plan.rationale,
        output_text=result.output_text if result else "",
    )


def envelope_to_json(envelope: OpenClawBridgeEnvelope) -> str:
    return json.dumps(asdict(envelope), indent=2)
