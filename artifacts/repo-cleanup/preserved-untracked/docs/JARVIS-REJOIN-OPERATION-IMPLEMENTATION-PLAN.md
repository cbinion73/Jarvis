# JARVIS Rejoin Operation Implementation Plan

## Purpose

This document translates the Rejoin Operation milestone into engineering
assessment and execution slices.

It does not redefine doctrine.

It does not add new philosophy.

It answers one question:

`What code already exists that gets us to Rejoin Operation in the fewest weeks?`

Read this after:

- `docs/JARVIS-REJOIN-OPERATION-MILESTONE.md`
- `docs/JARVIS-ARRIVAL-AND-CONVERSATION-WORKSPACE-DOCTRINE.md`
- `docs/JARVIS-OBJECT-POSTURE-REPRESENTATION-DOCTRINE.md`
- `docs/JARVIS-GLASS-THEME-UX-SPECIFICATION.md`

## Assessment Summary

The current repository already contains substantial backend value:

- conversation persistence
- voice session state
- mission creation and mission state
- approvals and trust boundaries
- memory and continuity stores
- agent and orchestration substrate
- event and runtime infrastructure
- existing Glass theme shell

The biggest gap is not backend capability.

The biggest gap is that the current UI shell is still module-first and
navigation-first.

The implementation strategy should therefore be:

- keep the current repo
- keep the backend substrate
- build a new operating-layer shell inside the repo
- treat the current shell as legacy interface, not legacy product

## Repo Assessment

### Existing substrate with high reuse value

#### Conversation system

- `jarvis/conversation.py`
- `jarvis/runtime.py`
- `jarvis/service.py`

What exists:

- persistent conversation threads
- active conversation snapshots
- recent conversation listing
- conversation turn append/update flow
- `/api/chat-state`
- `/api/conversations/{conversation_id}`

Assessment:

- strong reuse candidate for Conversation Presence
- likely sufficient for MVP text conversation rail

#### Voice infrastructure

- `jarvis/voice_session.py`
- `jarvis/voice.py`
- `jarvis/voice_pipeline.py`
- `jarvis/service.py` voice endpoints

What exists:

- voice session state machine
- voice settings and voice status APIs
- synthesis and greeting endpoints

Assessment:

- enough for MVP presence and voice affordance
- audio UX polish can wait

#### Mission system

- `jarvis/missions.py`
- `jarvis/runtime.py`
- `jarvis/service.py`

What exists:

- mission creation
- mission dossier persistence
- mission work state
- mission control summary
- mission routes
- mission updates and handoffs
- approvals tied to mission flow

Assessment:

- highest-value existing substrate
- should be reused rather than rewritten
- Summer Camp can be modeled as mission immediately

#### Memory and continuity

- `jarvis/memory.py`
- `jarvis/continuity.py`
- `jarvis/runtime.py`

What exists:

- memory store and support
- continuity event system
- memory signals inside chat state

Assessment:

- enough to support future Companion and continuity work
- not required to be fully surfaced in Sprint 1

#### Agent and orchestration substrate

- `jarvis/agentic.py`
- `jarvis/runtime_kernel.py`
- `jarvis/event_fabric.py`
- `jarvis/supervision.py`
- `jarvis/runtime.py`

What exists:

- background scheduler
- agent registry
- runtime kernel
- supervision support
- event fabric

Assessment:

- strong substrate for Ambient Intelligence
- should remain mostly hidden in MVP

#### Existing Glass shell

- `jarvis/jarvis_theme_glass.py`
- `jarvis/service.py`

What exists:

- theme rendering entrypoint
- styling system
- substantial client-side shell logic

Assessment:

- useful as a visual/material reference
- poor fit as the direct shell for Rejoin Operation because it is heavily
  view-switched and module-first

### Existing code that is likely legacy-shell baggage

#### Module-first navigation shell

- `jarvis/jarvis_theme_glass.py`
- `jarvis/service.py`

Evidence:

- `switchView('overview')`, `switchView('health')`, `switchView('home')`,
  `switchView('calendar')`, `switchView('email')`, etc.
- many dedicated route aliases in `jarvis/service.py` such as
  `/health-center`, `/calendar-center`, `/email-center`, `/workshop-center`

Assessment:

- this is the biggest architectural conflict with doctrine
- should not be incrementally extended
- should be bypassed with a new operating-layer shell

#### Dedicated app-module render surfaces

- `jarvis/render_pages.py`

What exists:

- many route-backed module pages and workspace pages
- mission board, health center, catalyst desktop, activity workspace, approval
  workspace, settings workspace, etc.

Assessment:

- useful as source material for future representations
- not suitable as the primary shell

## Rejoin Operation Gap Analysis

### 1. Conversation Presence

Status: `Partially Exists`

Already exists:

- conversation persistence and snapshots in `jarvis/conversation.py`
- active conversation state in `jarvis/runtime.py`
- `/api/chat-state` and conversation APIs in `jarvis/service.py`
- voice session state in `jarvis/voice_session.py`

Missing:

- doctrine-aligned permanent conversation presence shell
- always-visible conversation rail inside a new operating layer
- clean combined voice/text interaction entrypoint

Recommended approach:

- reuse current conversation APIs
- build a new minimal front-end conversation rail
- expose voice presence using existing voice status/state APIs

### 2. Continuity Spine

Status: `Partially Exists`

Already exists:

- mission control summary in `jarvis/missions.py`
- mission control snapshot in `jarvis/runtime.py`
- memory overview in chat state
- activity-like system data across mission/approval/agent subsystems

Missing:

- a continuity-specific aggregated surface for:
  - things changed
  - active watches
  - active missions
  - recommendations
- doctrine-aligned non-dashboard visual treatment

Recommended approach:

- derive first Continuity Spine payload from `mission_control_snapshot`,
  approvals, and lightweight summary counts
- create a dedicated API shape rather than reuse legacy dashboard payloads whole

### 3. Ambient Intelligence

Status: `Partially Exists`

Already exists:

- background scheduler
- agent registry
- supervision/runtime/event substrate
- mission and work-state summaries

Missing:

- user-facing lightweight ambient activity summary
- small set of stable monitoring labels for the permanent layer

Recommended approach:

- create a tiny ambient summary API that abstracts current agent/runtime
  complexity into a few user-facing watches

### 4. Mission Gravity

Status: `Missing`

Already exists:

- active missions in `mission_control_snapshot`
- recommendation and next-step signals in mission dossiers

Missing:

- doctrine-specific notion of gravity distinct from priorities/tasks
- API and selection rules for top 3-5 “forces” on life/work right now

Recommended approach:

- implement a temporary gravity heuristic on top of active missions:
  status, due proximity, blocked state, recommendation weight, family/workshop
  significance

### 5. Operational Handoff

Status: `Partially Exists`

Already exists:

- morning briefing endpoint in `jarvis/service.py`
- mission control snapshot
- various “while away” and summary concepts in docs and runtime surfaces
- voice greeting endpoint

Missing:

- transient operational handoff stack
- interruptible arrival sequence
- explicit reconnect/orient/prioritize/recommend flow

Recommended approach:

- build a new handoff payload and UI stack separate from existing briefing
  pages
- allow static/sample content initially if needed, but source it from live
  summaries where possible

### 6. Intent Router

Status: `Partially Exists`

Already exists:

- mission creation attempt in `jarvis/runtime.py`
- mission follow-up handling in `jarvis/runtime.py`
- response graph and planning path in `jarvis/runtime.py`

Missing:

- explicit lightweight classifier for:
  - Status Inquiry
  - Decision Request
  - Mission Update
- direct mapping from intent to posture selection for the Summer Camp mission

Recommended approach:

- add a small deterministic first-pass classifier before broader response logic
- keep it scoped to the Summer Camp MVP utterances

### 7. Mission Materialization

Status: `Partially Exists`

Already exists:

- mission dossiers
- mission board APIs
- mission work-state APIs
- conversation routes and workspace routes

Missing:

- a doctrine-aligned mission materialization inside the new shell
- workspace generation from object + posture + context

Recommended approach:

- use one mission object only: Summer Camp
- hydrate from existing mission APIs where possible
- present through a new representation layer instead of mission board UI

### 8. Posture Engine

Status: `Missing`

Already exists:

- no clear posture engine for Builder/Operator/Advisor/Chief of Staff/etc.
- existing “posture” language in scattered domain surfaces is not the doctrine
  engine we need

Missing:

- posture model
- posture stack sequencing
- representation selection logic

Recommended approach:

- implement only three postures in Sprint 1:
  - Chief of Staff
  - Advisor
  - Operator
- keep posture logic front-end friendly and explicit

### 9. Representation Engine

Status: `Missing`

Already exists:

- many legacy pages with useful content fragments
- no shared representation doctrine engine in code yet

Missing:

- mapping from mission object + posture to visible representation
- transition behavior between posture manifestations

Recommended approach:

- do not build a full generic engine in Sprint 1
- implement one mission with three posture-specific representations
- prove the pattern before abstracting

## Technical Risks

### Risk 1: Legacy shell gravity

The current Glass shell has deep module/view switching baked into it.

Evidence:

- `switchView(...)` patterns across many named views in
  `jarvis/jarvis_theme_glass.py`
- dedicated module routes in `jarvis/service.py`

Mitigation:

- create a new operating-layer shell inside the repo
- do not retrofit Rejoin Operation directly into the old nav shell

### Risk 2: Over-generalizing too early

The repo already contains many domains and route-backed surfaces.

Mitigation:

- force Summer Camp mission only
- force only three intent types
- force only three postures

### Risk 3: Reusing dashboard payloads wholesale

The current summary APIs often come from module-era assumptions.

Mitigation:

- build thin new aggregation payloads for:
  - continuity spine
  - ambient intelligence
  - mission gravity
  - operational handoff

### Risk 4: Backend logic mixed with old surface semantics

Some mission and route fields currently point toward mission-board or
module-center routes.

Mitigation:

- reuse mission data
- ignore old route semantics for the new shell

## Sprint 1: Rejoin Operation

### Goal

Open JARVIS.

Receive Operational Handoff.

Ask about Summer Camp.

See mission materialize.

No navigation.

### Deliverables

#### D1. New Operating Layer shell

Build a new shell inside the current repo.

Requirements:

- no Home screen
- no module tabs
- no page launcher
- permanent operating layer only

#### D2. Conversation Presence

Requirements:

- text input always available
- voice affordance always visible
- lightweight conversation timeline

#### D3. Operational Handoff

Requirements:

- greeting
- what changed
- what matters
- recommendation
- invitation to act

Note:

- static or semi-static data is acceptable initially if the ritual works

#### D4. Summer Camp Mission object

Requirements:

- one mission only
- hardcoded bootstrap acceptable
- dynamic materialization required

#### D5. Three postures

- Chief of Staff
- Advisor
- Operator

#### D6. Primitive intent classifier

- Status Inquiry
- Decision Request
- Mission Update

## Recommended Build Order

1. new operating shell scaffold
2. continuity/handoff payload API
3. permanent operating layer UI
4. conversation rail integration
5. Summer Camp mission bootstrap
6. Chief of Staff representation
7. Advisor representation
8. Operator representation
9. intent routing and posture transitions

## Explicit Non-Goals For Sprint 1

Do not build:

- Health
- Finance
- Publishing
- Faith
- Family
- Workshop
- Home Automation

Do not build:

- generalized graph explorer
- full posture engine abstraction
- generic representation framework
- full agent visibility
- parity migration for old modules

## Completion Criteria

The milestone is complete when Chris can:

1. open JARVIS
2. receive Operational Handoff
3. ask about Summer Camp
4. see the mission materialize
5. request a decision
6. see posture transition
7. commit to action
8. see operator state emerge
9. be unable to explain where the Summer Camp mission "lives" except through conversation

without navigating anywhere.

If this works, the operating model is proven.
