# Event Bus, Scheduler Fabric, and Attention Routing

This branch implements the backend shape for checklist items `3.14` and `3.15` without replacing the runtime kernel.

## What Was Added

- A durable event fabric in `jarvis/event_fabric.py`
- Event persistence under `data/agents/`:
  - `event_bus_events.json`
  - `event_bus_dedupe.json`
  - `event_bus_log.jsonl`
- A scheduler tick that can ingest:
  - cadence wakes
  - state changes
  - general signals
  - threshold crossings
  - handoffs
  - direct human interruptions
- Attention routing that classifies work into:
  - `silent`
  - `staged`
  - `foreground`
  - `interrupt`

## Durable Event Model

Each event is stored as an `EventEnvelope` with:

- `trigger_type`
- `topic`
- `source`
- `lane`
- `urgency`
- `attention_hint`
- `dedupe_key`
- `target_agents`
- `payload`
- `status`
- `wake_summary`

This gives later branches a durable source of truth for why a wake happened and which agents were brought forward.

## Scheduler Fabric Shape

The scheduler fabric now does three jobs on every tick:

1. Materialize due cadence events for agents with elapsed background loops.
2. Ingest externally supplied wake events with durable dedupe.
3. Route pending events into wake decisions and attention buckets.

The active runtime-kernel path is preserved. The scheduler sits above it and adds durable wake and attention behavior rather than replacing lifecycle primitives.

## Attention Routing Model

Attention routing is based on:

- user presence state
- quiet hours
- event urgency
- per-agent foreground policy
- per-agent interruption level
- explicit event attention hints

The current presence states are:

- `away`
- `passive`
- `foreground`
- `do-not-disturb`

The current routing outcomes are:

- `silent`: continue background work without surfacing
- `staged`: prepare work for review or a later summary
- `foreground`: bring the agent into the live interaction set
- `interrupt`: break through because the event is urgent enough

## Current Agent Policy Defaults

Examples:

- `ambient-router` is the always-available front door when the user is engaged.
- `watchtower` can interrupt on urgent anomalies.
- `memory-curator` stays silent and curates in the background.
- `system-steward` stays in maintenance posture and avoids attention grabs.
- `storm` comes forward when risk or travel relevance is high.

## What Later Branches Should Add

- richer event producers from real perception, comms, and home subsystems
- agent inbox and outbox state tied to wake decisions
- supervision policy layered on wake outcomes
- command-center and operator-visible audit surfaces
- budget arbitration across simultaneous wake pressure
