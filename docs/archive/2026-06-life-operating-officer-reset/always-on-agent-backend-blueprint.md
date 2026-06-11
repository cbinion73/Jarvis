# Always-On Agent Backend Blueprint

## Operating Picture

JARVIS is not just an app server with agent features. It is becoming an always-on multi-agent operating system:

- around 60 specialist agents with more on the way
- each agent has a purpose, cadence, scope, and authority boundary
- agents keep working in the background on behalf of the household
- when the human engages directly, the right agents shift into foreground focus
- when the human disengages, those agents return to supervised background work

This is the core product shape, not a future embellishment.

Direct interaction is one operating mode inside a continuously running
orchestrator.

This changes the backend from a request router into a persistent orchestration core.

Two architectural consequences follow from this:

- the system should preserve a durable event history of what happened, why,
  and under whose authority
- the backend should gradually move toward event-grounded state derivation,
  replay, and explanation rather than trusting only mutable point-in-time state

## Target Backend Layers

### 1. Agent Runtime Kernel

The kernel owns agent lifecycle:

- wake
- pause
- resume
- interrupt
- escalate
- retire

Each agent needs durable run state, heartbeat state, and a known execution lane.

### 2. Agent Registry and Mission Model

Each agent needs a durable contract:

- agent id
- title
- role
- mission
- lane ownership
- authority boundary
- cadence
- trust zone
- sandbox class
- escalation target

This should become the canonical source of truth for the agent universe.

### 3. Event Bus and Scheduler Fabric

Agents should wake from:

- time
- state change
- signal arrival
- threshold crossing
- handoff from another agent
- direct human interruption

The backend needs durable event routing plus scheduled background loops.

In the stronger form of this architecture, the event log becomes a first-class
system primitive rather than a debug afterthought.

The event log should be treated as the system ground truth, with current state
derived as a projection over append-only, typed, versioned records.

### 4. Foreground and Background Attention Router

The backend must distinguish:

- background autonomous work
- foreground live interaction
- interruption handling
- return-to-background state

This router decides which agents come forward when the human is present.

### 5. Agent Inbox, Outbox, and Worklog State

Each agent needs:

- inbox
- outbox
- active tasks
- blocked tasks
- pending reviews
- recent decisions
- current hypotheses

This is the agent-local operating memory layer.

### 6. Cross-Agent Handoff and Delegation Fabric

Agents must be able to:

- delegate
- request review
- request data
- escalate
- merge or avoid duplicate work
- hand off partial work safely

This is where the system stops behaving like isolated tools and starts behaving like a coordinated staff.

### 7. Observability and Operator Health Plane

The operator needs to see:

- which agents are active
- which are blocked
- which are drifting
- which are waiting on review
- which lanes are overloaded
- which background runs are stale

This becomes product-visible operational telemetry.

Without this, an always-on society of 60-plus agents becomes opaque and
therefore untrustworthy.

### 8. Governance, Doctrine, and Supervision Loop

The backend must supervise:

- what agents may do
- where autonomy stops
- what gets staged
- what is sandboxed
- what is rolled back
- what becomes doctrine after repeated successful review

This extends the governance work already in progress into a true multi-agent supervision plane.

Implementation anchor:

- `docs/always-on-governance-supervision-plane.md`
- `jarvis/supervision.py`

This layer should eventually support earned authority progression:

- sandbox evidence
- promotion records
- explicit consent boundaries for higher authority stages
- rollback and review when behavior drifts

The promotion engine is the key mechanism that converts track record into
authority. Sandbox execution, review, and supervision should all feed this
earned-authority path rather than bypass it.

### 9. Budgeting and Resource Arbitration

Always-on agents compete for:

- tokens
- compute
- time
- user attention
- trust headroom

The backend needs budget policy and arbitration so the agent society does not become noisy or wasteful.

This matters more, not less, in an always-on orchestrator because background
initiative competes continuously for compute, tokens, trust headroom, and human
attention.

### 10. Presence and Interruption Engine

Presence, mode, room, device, urgency, and quiet hours need to inform:

- who can interrupt
- who must stay backgrounded
- which summary is shown
- which work should be paused
- which work may continue silently

This is the human-facing timing discipline for the whole system.

## Additional Pressure From The Vision

The long-term vision adds three important backend pressures that should shape
implementation choices now, even if they are not all immediate build targets:

1. household institutional memory should compound over years, not sessions
2. household operation should become less builder-dependent over time
3. authority should be earned through evidence and governance, not assumed by default

## What We Already Have

The following foundations are already real and should be treated as the base layer for this architecture:

- stewardship lanes
- trust zones and arenas
- governance review and rollout posture
- sandbox execution lanes
- durable memory graph
- reflective memory review
- while-you-were-away synthesis
- chamber and home shared aggregation
- deployment-aware runtime posture

## What This Means For Next Backend Work

The next backend expansion should move in this order:

1. real device integrations
2. agent runtime kernel
3. agent registry and mission model
4. event bus and scheduler fabric
5. foreground and background attention routing
6. agent inbox, outbox, and worklog state
7. cross-agent delegation and handoff
8. observability and supervision surfaces

## Checklist Translation

This blueprint maps into the numbered checklist as:

- `3.11` blueprint captured
- `3.12` agent runtime kernel
- `3.13` agent registry and mission model
- `3.14` event bus and scheduler fabric
- `3.15` foreground and background attention router
- `3.16` agent inbox, outbox, and worklog state
- `3.17` cross-agent handoff and delegation fabric
- `3.18` observability and operator health plane
- `3.19` governance, doctrine, and supervision loop
- `3.20` budgeting, arbitration, and interruption engine

Supporting branch doc:

- `docs/agent-workstate-and-handoffs.md`
