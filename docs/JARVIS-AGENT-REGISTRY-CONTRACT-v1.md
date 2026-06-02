# JARVIS Agent Registry Contract v1

This document defines the canonical contract for `3.13` in the numbered outline: agent registry and mission model.

The goal is not to make a prettier agent gallery. The goal is to make the agent society governable.

## What This Contract Is

The registry is the machine-readable source of truth for:

- agent identity
- mission statement
- lane ownership
- baseline authority stage
- autonomy posture
- trust-zone placement
- stewardship ownership
- escalation routing

The mission model is the companion contract for:

- canonical system posture
- authority stages
- mission statuses
- ownership roles
- escalation reasons and targets
- lane taxonomy
- handoff kinds
- non-negotiable invariants

Together they let JARVIS behave like an always-on orchestrator instead of a reactive assistant with a loose list of personalities.

## Canonical Artifacts

- `data/agents/jarvis_agent_registry.v1.json`
- `data/missions/jarvis_mission_model.v1.json`
- `schemas/jarvis-agent-registry.v1.json`
- `schemas/jarvis-mission-model.v1.json`
- `jarvis/agent_registry_contract.py`
- `scripts/verify_agent_registry_contracts.py`

## Contract Rules

These are the main drift blockers:

1. The canonical posture is explicit and validated.
   `always-on-orchestrator`, `oversight-and-steering`, `voice-enabled-not-primary`, and `operational-contract` are enforced values.
2. Every active core agent must declare ownership.
   Each record names the human principal, the ownership role, and the steward agent.
3. Every active core agent must declare authority.
   Each record has a baseline `authority_stage`, `autonomy_posture`, and `trust_zone`.
4. Every active core agent must declare escalation.
   Each record names a supervisor, default escalation target, and machine-readable escalation reasons.
5. Lane ownership is part of identity.
   An agent cannot exist without a primary lane and a declared lane set.

## Validation Behavior

Validation is intentionally strict:

- missing files fail
- malformed JSON fails
- duplicate agent ids fail
- duplicate labels fail
- unknown authority stages fail
- unknown lane names fail
- unknown principal ids fail
- unknown escalation targets fail
- unknown escalation reasons fail
- missing steward or supervisor references fail

`jarvis.agentic.AgentRegistry` now loads from the canonical contract and raises on invalid data instead of silently drifting back to hardcoded defaults.

## How To Verify

Run:

```bash
python3 scripts/verify_agent_registry_contracts.py
```

If the command exits non-zero, the registry contract should be treated as broken until fixed.
