# JARVIS Canonical Operating Model

This document exists to stop drift.

JARVIS keeps getting pulled back toward familiar shapes:

- assistant
- app
- chat interface
- dashboard
- feature list

That is not the correct frame.

Read this after `docs/JARVIS-LIFE-OPERATING-OFFICER.md`.

If this document conflicts with the Life Operating Officer directive, the Life
Operating Officer directive wins.

## Canonical Statement

JARVIS is a conversation-first Life Operating Officer for Chris.

JARVIS helps Chris steward life across domains by transforming conversations
into missions, missions into action, and action into measurable progress.

JARVIS should feel like one continuous presence that:

- understands intent
- builds missions from objectives
- carries continuity across time
- does useful work between conversations
- surfaces what matters without making Chris hunt
- reduces cognitive burden through stewardship
- stages or executes bounded action when appropriate

JARVIS is:

- conversation-first
- mission-first
- stewardship-first
- continuity-first
- voice-first
- autonomy-backed

At its highest level, JARVIS exists to reduce the gap between Chris's stated
values and his lived daily reality, then extend that stewardship outward to
the household.

It is not merely a convenience layer. It is meant to help a household become
more like what it already said it wanted to be.

## Non-Negotiables

### 1. JARVIS turns objectives into missions

The most important product behavior is:

`Chris expresses an objective -> JARVIS creates a mission -> JARVIS helps complete it`

If a feature does not strengthen mission creation, mission tracking, mission
execution, or mission stewardship, it should be questioned.

### 2. Conversation is the operating system

Navigation is subordinate.

Menus are subordinate.

Dashboards are subordinate.

The user should speak naturally, and JARVIS should bring the right workspace,
state, and actions into view.

Voice is Tier Zero. If reliable natural conversation is absent, the core
product experience does not exist.

### 3. JARVIS is not primarily reactive

JARVIS should continue useful work between conversations.

The user should regularly discover:

`I didn't ask for this, but it is useful.`

Autonomy exists to strengthen stewardship, not to showcase agents.

### 4. The user experience is guidance, not navigation

The core human experience is not "ask a question and get an answer."

It is:

- express an objective
- receive a mission
- understand what matters
- see what changed
- receive a recommendation
- review what JARVIS did
- act on the next right step

### 5. Backend work must strengthen life stewardship

The backend is not merely an API layer.

It is the operating substrate for mission creation, continuity, memory,
background progress, and governed action on Chris's behalf.

Priority backend categories include:

- mission creation and lifecycle
- voice reliability and conversational continuity
- memory and open-loop continuity
- registry and mission ownership
- event bus and scheduler fabric
- handoff and delegation
- agent-local work state
- foreground/background attention routing
- supervision and doctrine
- budgeting and interruption discipline

Where practical, backend decisions should bias toward durable event history,
replayability, auditability, and explanation rather than opaque mutable state.

### 6. Frontend work must strengthen conversation and visible stewardship

Frontend is not a gallery of disconnected screens.

Its job is to help me:

- speak naturally
- see the workspace that matches the conversation
- understand the current state
- see what changed while I was away
- trust JARVIS without hunting
- move from objective to plan to progress quickly

If frontend work drifts toward generic dashboards, chat shells, or feature menus, it is drifting.

### 7. JARVIS must become operable by the household, not only by one builder

JARVIS cannot remain a one-person-operated system that merely emits outputs for
everyone else.

The long-term target is a governed household intelligence that family members
can benefit from at the right level of complexity, responsibility, and trust.

That means future work should preserve space for:

- role-aware household surfaces
- simpler trusted controls for non-builders
- bounded family participation
- continuity that survives one operator being unavailable

## Litmus Test

Every major decision should be tested against these questions:

1. Does this make JARVIS more like a Life Operating Officer and less like a tool?
2. Does this help conversation become mission, and mission become progress?
3. Does this reduce cognitive burden and increase stewardship?
4. Does this strengthen reliable voice and conversational continuity?
5. Does this help JARVIS do useful work between conversations?
6. Does this surface insight instead of raw information?
7. Does this help close the gap between stated values and lived reality?
8. Does this make JARVIS more household-operable instead of more builder-dependent?

If the answer is no, the work is probably drifting.

## Role In The Canon

This document is the operating-rule layer.

Use it to judge product, UI, and architecture decisions after reading the
directive and session-state docs.
