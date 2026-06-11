# JARVIS Agent Runtime Kernel

This document defines the runtime kernel added for the always-on agent backend.

It is intentionally narrow:

- durable lifecycle control
- durable run state
- heartbeat and health posture
- supervision-friendly snapshots

It does **not** yet try to become:

- the event bus
- the scheduler fabric
- the foreground router
- a generic jobs system

Those layers should build on top of this kernel instead of being fused into it.

## Canonical Role

The runtime kernel is the control plane for persistent delegated workers.

It answers:

- what state is each agent in right now
- what state is it trying to reach
- what run is active
- is its heartbeat fresh, stale, or missed
- is it blocked, paused, interrupted, escalating, or retiring
- does supervision need to look at it

## Durable Files

The kernel persists under `data/agents/`:

- `runtime_kernel_state.json`
- `runtime_kernel_events.jsonl`

The existing `background_state.json` and `tick_log.jsonl` remain as compatibility surfaces for the current background-status path.

## Lifecycle States

The kernel currently supports these durable lifecycle states:

- `idle`
- `waking`
- `running`
- `paused`
- `interrupted`
- `blocked`
- `escalating`
- `retiring`
- `retired`

Supported control actions:

- `wake`
- `pause`
- `resume`
- `interrupt`
- `escalate`
- `retire`
- `retire-now`

## Runtime Record Shape

Each runtime entry keeps four main sections:

1. `contract`
   Captures the durable identity and operating boundary for the agent:
   lane owner, execution lane, mission, cadence, trust zone, sandbox class, escalation target.

2. `lifecycle`
   Captures the current and desired lifecycle state plus transition history and operator reasons.

3. `run`
   Captures the active run id, execution lane, cadence due-at timestamp, and lifecycle counters such as wake, resume, interrupt, and escalation counts.

4. `heartbeat`, `health`, and `supervision`
   Capture freshness, degraded posture, blocked dependencies, quiet-hours posture, and whether the operator should intervene.

## Health Model

Heartbeat status is derived as:

- `fresh`
- `stale`
- `missed`
- `unknown`

Health posture is derived from lifecycle state plus dependencies and heartbeat:

- `healthy`
- `starting`
- `standing-by`
- `quiet-hours`
- `paused`
- `blocked`
- `watch`
- `degraded`
- `attention`
- `retiring`
- `retired`

## Integration Points

Current integration points:

- `JarvisRuntime.agent_runtime_kernel`
- `JarvisRuntime.agent_runtime_snapshot()`
- `JarvisRuntime.control_agent_runtime(...)`
- `JarvisRuntime.record_agent_runtime_heartbeat(...)`
- `GET /api/agent-runtime`
- `POST /api/agent-runtime/control`
- `POST /api/agent-runtime/heartbeat`
- `python -m jarvis agent-runtime`
- `python -m jarvis agent-runtime-control ...`

The existing `BackgroundTaskScheduler` now layers on top of the runtime kernel and exposes a compatibility snapshot for `/api/agents` and `python -m jarvis agent-status`.

## Later Branches Should Add

- real scheduler wake sources and cadence execution
- event-bus based signal routing
- foreground/background attention routing
- richer per-agent inbox/outbox/worklog state
- run execution workers and acknowledgements
- supervision policies for automatic escalation and retirement completion
- budget arbitration across the agent society
