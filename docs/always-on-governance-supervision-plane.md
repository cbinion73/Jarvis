# Always-On Governance and Supervision Plane

## Purpose

This document extends the trust-zone foundation into a real supervision model for an always-on society of agents.

It is not a general policy essay.

It answers six backend questions:

1. what agents may do without approval
2. what must be staged
3. what must be sandboxed
4. what must be escalated
5. how rollback posture is represented
6. how reviewed success becomes doctrine

## Canonical Runtime Objects

The supervision plane now has four persistent object types:

- stewardship lane contracts
- agent supervision contracts
- supervision decision traces
- supervision reviews

These sit on top of existing:

- trust zones
- resource arenas
- authority stages
- shared doctrine rules

## Governing Relationship

The relationship is:

1. stewardship lane defines mission, burden relieved, reporting cadence, and escalation owner
2. trust zone defines where action is legally bounded
3. authority stage defines maturity of the allowed action posture
4. agent supervision contract defines what a specific agent may do inside that lane and zone
5. supervision decision evaluates a requested action against all of the above
6. review outcome decides whether the pattern is safe enough to become doctrine

## Resolution Types

Every supervised action resolves into one of four shapes:

- `autonomous`
- `stage`
- `sandbox`
- `escalate`

`forbidden` is used when the action is outside the contract or zone.

## Bounded Autonomy Rules

### May operate without approval

Only actions that are:

- inside the agent's supervision contract
- inside the trust zone allowed-action list
- compatible with the current authority stage
- not marked as must-stage, must-sandbox, must-escalate, or forbidden
- not crossing zones
- not missing a reversal posture for external mutation

### Must be staged

An action is staged when any of these are true:

- the agent contract says it must be staged
- the authority stage is `observe`, `draft`, or `stage_alert`
- the action is not in the standing autonomous allowance set
- doctrine says the pattern must remain human-reviewed
- the action is externally mutating but not safely reversible

### Must be sandboxed

An action is sandboxed when:

- the agent contract says it must be sandboxed
- the trust zone is live enough for sandbox operation
- the action remains inside the zone and the sandbox class

Sandbox is a bounded rehearsal or ring-fenced execution posture, not unrestricted live authority.

### Must be escalated

An action is escalated when:

- it crosses trust zones
- it is marked must-escalate by contract
- it is outside the trust zone
- the agent contract is inactive
- the trust zone is inactive
- doctrine forces a stricter posture

## Rollback Posture

Every decision trace carries rollback posture:

- `reversible`
- `full`
- `manual-only`
- `none-known`

This is not cosmetic metadata. It is part of the autonomy boundary.

If an externally mutating action has no declared reversal path, the system cannot treat it as ordinary autonomous work.

## Doctrine Formation

Doctrine is not hand-written first.

It is synthesized from repeated reviewed success.

A pattern becomes a doctrine candidate only when:

- it repeats in the same agent, lane, zone, action, and resolution shape
- it meets minimum reviewed-success counts
- it meets minimum approval success rate
- it stays under rollback/reversal limits

Candidates are merged into `shared_doctrine.json` with source `supervision`.

This means doctrine becomes a compression of reviewed operational truth, not generic aspiration.

## Traceability and Audit

Every supervision decision writes:

- decision id
- agent id
- lane id
- trust zone id
- action type
- requested outcome
- resolution
- authority stage
- reasons
- doctrine rules applied
- rollback posture
- context trace

Every review writes:

- review id
- decision id
- reviewer
- outcome
- rollback executed flag
- doctrine-ready flag

This gives later command-center work a durable audit spine for:

- why an agent acted
- why it was blocked
- what rule governed it
- whether the pattern is becoming trusted doctrine

## Initial Lane Coverage

The first supervision foundation ships lane contracts for:

- family stewardship
- executive and calendar
- watcher and continuity
- wealth and opportunity
- chamber operations

The first agent contracts cover:

- Pepper
- Herald
- Watcher
- Black Panther
- System Steward

This is intentionally a foundation layer, not a complete final registry.

## Next Branch Expectations

Later branches should add:

- richer resource and token budgeting
- operator-facing supervision dashboards
- runtime-triggered sampling and demotion loops
- deeper agent registry integration across the full agent society
- execution adapters that consume supervision decisions directly before acting
