# JARVIS V1 Execution Plan

## Purpose

This document turns the Life Operating Officer rescope into a concrete build
sequence.

It is not a long-horizon roadmap.

It is the shortest credible path to making JARVIS feel like a
conversation-first Life Operating Officer in the real product.

Read this after:

1. `docs/JARVIS-RESCOPE-ENTRYPOINT.md`
2. `docs/JARVIS-LIFE-OPERATING-OFFICER.md`
3. `docs/JARVIS-SESSION-STATE.md`

## V1 Product Standard

V1 succeeds if Chris can say something like:

`JARVIS, I want to improve my health.`

and the product reliably does four things:

1. understands the objective
2. creates a mission
3. shows a visible workspace with next actions, milestones, and accountability
4. continues useful work between conversations

If that loop is not real, V1 is not done.

## The First V1 Promise

JARVIS V1 is not "all life domains."

JARVIS V1 is:

`conversation -> mission -> visible workspace -> brief follow-through`

across a small number of high-feeling domains.

## V1 Scope

### In Scope

- voice-first and typed conversation entry
- mission creation from natural language
- visible mission workspace
- Daily Brief as the primary home experience
- "What Changed" and "What JARVIS Did"
- open loops and next actions
- background mission progress
- basic accountability follow-up
- real proof on web and iPhone surfaces

### Out Of Scope For V1

- broad household admin
- full smart-home orchestration
- agent creation/foundry expansion
- deep civilization-layer governance work
- generalized family multi-user complexity
- every life domain at once
- invisible infrastructure work with no felt user outcome

## V1 Domain Strategy

Do not launch V1 with ten equal domains.

Launch with the domains most likely to create the feeling fast:

1. Health and Longevity
2. Writing and Publishing
3. JARVIS Development
4. Scouting and Service

These domains already fit the current repo posture and are rich in missions,
follow-up, and pattern recognition.

Everything else can remain present in canon without being first-wave execution.

## Product Surface Strategy

### 1. Conversation Is The Front Door

Primary entry:

- voice shell
- typed conversation fallback

The product should open into a conversation-first surface, not a generic
dashboard.

### 2. Daily Brief Is The Home Experience

The home experience should answer:

1. What changed?
2. What matters?
3. What did JARVIS do?
4. What should I do next?

### 3. Mission Workspace Is The Core Work Surface

After mission creation, JARVIS should bring Chris into a mission workspace
that includes:

- mission objective
- current status
- milestones
- next actions
- momentum signal
- open loops
- accountability cadence
- prepared recommendations

## Current Repo Strengths To Reuse

These are already present enough to build on:

- mission API and mission board routes in `jarvis/service.py`
- mission lifecycle and status flows
- command-center and brief substrate
- voice shell rendering path in `jarvis/service.py`
- memory and known-facts substrate
- work-state and handoff endpoints for background progress

V1 should repurpose these into a tighter product loop rather than replacing
them wholesale.

## Current Repo Drift To Avoid

Avoid rebuilding JARVIS around:

- generic dashboards
- visible agent theater
- broad architecture programs with no user-facing effect
- domain sprawl before mission quality is high
- voice demos that do not create or advance real missions

## V1 Milestones

## Milestone 1: Mission Capture

Goal:

Turn natural-language objectives into structured missions reliably.

User outcome:

Chris states a goal and immediately gets a real mission instead of a generic
answer.

Build:

- define the V1 mission-creation prompt and schema
- support objective -> mission parsing for the first four domains
- create mission title, purpose, milestones, next actions, and cadence
- route successful creation into the mission workspace
- preserve typed and voice parity

Proof:

- web flow creates a mission from natural language
- iPhone flow creates a mission from natural language
- mission appears in mission APIs and visible UI
- at least 5 exemplar prompts per launch domain work end-to-end

## Milestone 2: Visible Mission Workspace

Goal:

Make the mission feel real, active, and stewarded.

User outcome:

Chris sees that JARVIS built something useful, not just saved text.

Build:

- tighten the mission workspace around one primary mission at a time
- show milestones, next action, blockers, recent progress, and momentum
- add one clear recommendation panel
- add one accountability panel
- remove or demote low-signal controls that feel builder-oriented

Proof:

- mission workspace is reachable immediately after creation
- the workspace reads clearly on web and iPhone
- one mission can be updated and advanced without leaving the flow

## Milestone 3: Daily Brief Home

Goal:

Replace dashboard energy with companion energy.

User outcome:

Opening JARVIS feels like entering a prepared operating picture.

Build:

- define the letter-format Daily Brief structure
- wire "What Changed" from live local/runtime signals
- wire "What JARVIS Did" from real activity/work-state sources
- wire "What Matters" and open loops from live mission pressure
- generate one recommendation and one "you can stop carrying this" signal

Proof:

- brief is generated from live data, not canned examples
- web home and iPhone home both show the same truth
- at least one overnight or between-session change appears correctly

## Milestone 4: Background Progress

Goal:

Make JARVIS appear active between conversations.

User outcome:

Chris discovers useful work already completed.

Build:

- define a narrow set of allowed background jobs for V1
- generate mission-support artifacts such as milestone proposals,
  follow-up suggestions, stalled-mission nudges, and domain-specific options
- record work in visible activity and mission history
- surface prepared outputs in Daily Brief and mission workspace

Proof:

- at least one mission receives background-prepared work
- prepared work is visible in both mission view and Daily Brief
- the system distinguishes suggestion, staged action, and completed action

## Milestone 5: Voice Tier Zero

Goal:

Make voice a real product path, not a wrapper around text UI.

User outcome:

Chris can speak naturally, create or advance a mission, and stay in flow.

Build:

- stabilize the voice loop for listen -> understand -> respond -> continue
- ensure voice can create and advance missions
- make interruption and resume graceful
- keep transcript and surfaced workspace synchronized
- preserve typed fallback without changing product logic

Proof:

- successful voice-created mission on web or hosted shell
- successful voice-created mission on iPhone
- follow-up utterance advances the same mission
- interrupted conversation recovers without losing state

## Milestone 6: Accountability Loop

Goal:

Make JARVIS follow up on what matters.

User outcome:

Chris feels supported and challenged, not merely informed.

Build:

- define mission check-in cadence rules
- detect stalled missions and missed commitments
- produce supportive follow-up language
- add visible trend and momentum status

Proof:

- at least one stalled-mission follow-up appears correctly
- at least one positive progress reinforcement appears correctly

## First Build Order

Build in this order:

1. mission capture
2. visible mission workspace
3. Daily Brief home
4. background progress
5. voice Tier Zero
6. accountability loop

This order matters.

Voice is top priority in product identity, but V1 should first guarantee that
voice lands on a strong mission system instead of a shallow conversational
surface.

## Codebase Execution Map

### Likely Primary Files

- `jarvis/service.py`
- `jarvis/runtime.py`
- `jarvis/missions.py`
- `jarvis/voice_ui.py`
- `jarvis/known_facts.py`
- relevant web and iPhone surface files for home, voice, and mission views

### Likely Existing Routes To Reuse

- `/api/missions`
- `/api/missions/{mission_id}`
- `/mission-board`
- `/api/mission-control`
- voice shell routes already rendered through `jarvis/service.py`

## V1 UI Rules

- one dominant conversational entry
- one dominant mission in focus
- one dominant recommendation at a time
- one brief that reads like stewardship, not analytics
- visible truth labels when data is inferred, stale, or unavailable

Avoid:

- dense operator dashboards
- too many equal modules
- agent-centric vocabulary in the main user experience
- implementation detail leaking into the primary surfaces

## V1 Data And Truth Rules

- live data beats mock data
- truthful unavailable states beat fake completeness
- mission activity must survive restart
- the same mission truth should appear across conversation, brief, and mission view
- background work must be attributable and inspectable

## V1 Verification Plan

### Manual Proofs

- create a health mission by voice
- create a writing mission by typed conversation
- reopen JARVIS and verify Daily Brief reflects mission reality
- verify "What JARVIS Did" shows real background work
- advance a mission and verify accountability updates

### Automated Proofs

- mission creation API tests
- mission workspace payload tests
- Daily Brief payload tests
- voice flow smoke tests
- restart-survival tests for active mission continuity

## What To Cut Or Ignore Immediately

- any surface whose main value is generic monitoring without stewardship
- any module that cannot support mission creation, mission progress, or Daily Brief truth
- any implementation slice that exists mainly to advertise agent complexity
- any new domain expansion before the first four domains feel excellent

## Definition Of Done For V1

V1 is done when all of the following are true:

1. Chris can state an objective naturally and JARVIS creates a useful mission.
2. JARVIS immediately presents a real workspace for that mission.
3. Opening JARVIS later shows what changed, what matters, and what JARVIS did.
4. JARVIS performs at least one useful background action on an active mission.
5. Voice can create and advance missions on real surfaces.
6. The product feels like stewardship, not navigation.

## Immediate Next Build Slice

The first implementation slice should be:

`Mission Capture + Mission Workspace + Daily Brief linkage`

That is the smallest slice that can produce the core feeling.

Specifically:

1. tighten mission creation from natural language
2. auto-route into a focused mission workspace
3. reflect the new mission in Daily Brief and "What Matters"
4. show one prepared next action and one accountability signal

If this slice feels right, the rest of V1 can compound from it.
