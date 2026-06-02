# Agent Work-State And Handoff Fabric

This document captures the durable backend contract added for branch `codex/agent-workstate-and-handoffs`.

It is intentionally scoped to:

- per-agent durable work state
- cross-agent handoffs
- delegation records
- escalation records
- duplicate-work suppression
- safe ownership transfer
- resumable partial work

It is intentionally not a scheduler rewrite, frontend redesign, device integration pass, or broad runtime-kernel expansion.

## Why This Exists

JARVIS cannot behave like a coordinated staff if agents only appear as labels on a mission dossier.

Each participating agent needs durable local operating memory inside the mission:

- inbox
- outbox
- active tasks
- blocked tasks
- pending reviews
- recent decisions
- current hypotheses

Without that, handoffs collapse into vague notes and partial work disappears when ownership changes.

## Durable Mission Additions

Each `MissionDossier` now carries:

- `agent_work_states`
- `handoffs`
- `delegations`
- `escalations`
- `ownership_transfers`
- `duplicate_suppressions`

This makes mission state the durable source of truth for cross-agent coordination.

## Agent Work-State Model

Each `AgentWorkState` records:

- `agent_id`
- `mission_id`
- `role`
- `status`
- `ownership_mode`
- `current_focus`
- `inbox`
- `outbox`
- `active_tasks`
- `blocked_tasks`
- `pending_reviews`
- `recent_decisions`
- `current_hypotheses`
- `last_handoff_at`
- `updated_at`

This is the contract later supervision and observability work should read from first.

## Handoff And Delegation Rules

### 1. Handoffs are explicit records

Every cross-agent pass creates a durable `AgentHandoffRecord` plus a `AgentDelegationRecord`.

The record preserves:

- who sent the work
- who received it
- what task moved
- what partial work already exists
- what context the receiver needs
- whether acceptance is required

### 2. Ownership transfer is not implicit

If a handoff requests ownership transfer:

- the sender keeps a blocked `awaiting-transfer-acceptance` task
- the receiver gets a pending review item
- ownership is not released until the receiver acknowledges

This is the key safe-transfer rule for resumable partial work.

### 3. Delegation and ownership are separate

An agent can delegate work without relinquishing ownership.

That means:

- outbound delegation can coexist with sender active ownership
- the receiver can support execution without becoming the lead
- later branches can use this to model review chains and bounded specialist assistance

### 4. Escalations are durable too

Escalations are not just comments. They create a durable escalation record and a receiver-side review obligation.

### 5. Duplicate suppression is first-class

When two agents are about to work the same problem:

- one agent is recorded as the winner
- the other receives a blocked duplicate-suppression task
- the mission retains the rationale

That gives later observability branches a real ledger of wasted-work avoidance.

## Ownership Conflict Patterns This Model Handles

The current fabric is designed around these conflict patterns:

- two agents both think they own the same task
- a sender drops partial work before the receiver accepts it
- a receiver starts duplicate work before reading existing context
- a review request is sent but not surfaced in durable state
- an escalation disappears into chat text instead of a tracked queue
- a task-agent supports a mission but leaves no resumable trail behind

## API Surface Added

The backend now exposes:

- `GET /api/missions/{mission_id}/work-state`
- `POST /api/missions/{mission_id}/agents/{agent_id}/work-state`
- `POST /api/missions/{mission_id}/handoffs`
- `POST /api/missions/{mission_id}/handoffs/{handoff_id}/acknowledge`
- `POST /api/missions/{mission_id}/escalations`
- `POST /api/missions/{mission_id}/duplicate-suppressions`

These are backend-facing orchestration primitives, not polished operator UX yet.

## What Later Branches Still Need To Add

Later branches should build on this by adding:

- supervision policies that inspect the new ledgers
- command-center surfaces that visualize agent work-state and conflict posture
- observability counters and stale-handoff alerts
- scheduler hooks that fire from durable handoff and review state
- doctrine that can auto-classify safe vs unsafe transfer patterns
- budget/arbitration rules that use blocked and duplicate signals to reduce waste

## Validation Intent

The validation target for this branch is not a full runtime battery.

The important proof is:

- mission creation initializes per-agent durable workspaces
- handoffs persist partial-work context
- ownership transfer requires acknowledgment before release
- duplicate suppression records the losing lane
- mission-level summaries expose blocked, pending review, and pending handoff counts
