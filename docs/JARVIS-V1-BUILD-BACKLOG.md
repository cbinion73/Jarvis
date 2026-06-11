# JARVIS V1 Build Backlog

## Purpose

This document converts the V1 execution plan into an ordered implementation
backlog.

It is written for real build sequencing, not abstract roadmap discussion.

Read this after:

1. `docs/JARVIS-V1-EXECUTION-PLAN.md`
2. `docs/JARVIS-CANONICAL-MOMENTS.md`

## Planning Rules

- Build the feeling before the platform.
- Prefer reuse over replacement.
- Every epic must produce visible user value.
- No backlog item exists just to increase architecture sophistication.
- If an item does not improve `conversation -> mission -> visible workspace -> follow-through`, it is probably not V1 work.

## Backlog Order

Build in this order:

1. Epic A: Mission Capture
2. Epic B: Mission Workspace
3. Epic C: Daily Brief Linkage
4. Epic D: Background Progress
5. Epic E: Voice Tier Zero
6. Epic F: Accountability Loop

## Epic A: Mission Capture

Goal:

Turn natural-language intent into a useful mission reliably.

Definition of done:

Chris can state a goal by typed or spoken conversation and receive a mission
with title, brief, milestones, next actions, cadence, and domain routing.

### Story A1: Define V1 mission contract

Outcome:

One stable mission payload for the V1 experience.

Build:

- define required mission fields for V1
- define optional fields that can remain empty without breaking the experience
- define the minimal domain taxonomy for V1 launch domains
- define truth labels for inferred vs confirmed mission details

Likely files:

- `jarvis/missions.py`
- mission contract docs if needed

Proof:

- written V1 mission contract exists
- payload can represent all four launch domains cleanly

### Story A2: Tighten natural-language mission creation

Outcome:

Mission creation feels intentional rather than generic.

Build:

- improve objective parsing for Health, Writing, JARVIS Development, and Scouting
- generate better mission titles and briefs
- generate first-pass milestones and next actions
- ensure creation logic handles vague, specific, and multi-part requests gracefully

Likely files:

- `jarvis/missions.py`
- `jarvis/runtime.py`

Proof:

- 5 successful exemplar prompts per launch domain
- no generic fallback wording for normal prompts

### Story A3: Ensure conversation parity

Outcome:

Typed and voice entry create the same mission quality.

Build:

- route both typed and spoken intent through the same mission-creation logic
- ensure voice-specific wrappers do not degrade mission creation

Likely files:

- `jarvis/service.py`
- `jarvis/voice_ui.py`
- `jarvis/runtime.py`

Proof:

- same prompt by typed and voice produces materially similar mission output

### Story A4: Auto-route to mission workspace after creation

Outcome:

The user moves from intent to mission view without hunting.

Build:

- create post-create routing behavior
- ensure the mission workspace opens on successful mission creation

Likely files:

- `jarvis/service.py`
- mission surface files

Proof:

- web and iPhone flows land on the new mission immediately after creation

## Epic B: Mission Workspace

Goal:

Make the mission feel active, visible, and stewarded.

Definition of done:

The mission workspace clearly shows what the mission is, where it stands, and
what should happen next.

### Story B1: Define mission workspace information hierarchy

Outcome:

One clear hierarchy for the primary mission screen.

Build:

- define above-the-fold sections
- decide what is primary, secondary, and hidden
- remove builder-first clutter from the default view

Proof:

- one agreed workspace structure exists for web and iPhone

### Story B2: Add core mission sections

Outcome:

The workspace exposes the minimum useful mission truth.

Build:

- mission objective
- current status
- milestones
- next action
- blockers
- momentum signal
- open loops
- recommendation panel

Likely files:

- `jarvis/service.py`
- mission UI files

Proof:

- each section is populated from real mission state or truthfully unavailable

### Story B3: Add accountability panel

Outcome:

The mission reflects progress and follow-through expectations.

Build:

- show cadence
- show completion status against planned actions
- show supportive next follow-up

Proof:

- workspace displays at least one accountability signal for active missions

### Story B4: Tighten mission mutation flow

Outcome:

The mission can be advanced without breaking the feeling.

Build:

- refine update status flow
- refine detail edits
- ensure changes immediately reflect in workspace

Proof:

- one mission can be created, updated, and advanced end-to-end

## Epic C: Daily Brief Linkage

Goal:

Make the home experience feel like stewardship, not a dashboard.

Definition of done:

Opening JARVIS shows a live operating picture with `What Changed`, `What
Matters`, `What JARVIS Did`, and a recommendation.

### Story C1: Define Daily Brief structure

Outcome:

One stable format for the V1 brief.

Build:

- define section order
- define tone and brevity rules
- define what qualifies for each section

Likely files:

- `jarvis/service.py`
- brief generation code

Proof:

- written brief format is implemented in the product surface

### Story C2: Wire `What Changed`

Outcome:

The brief reflects meaningful change since the last session.

Build:

- use mission updates
- use recent activity
- use open-loop changes
- exclude noisy low-value events

Proof:

- at least one real between-session change appears correctly

### Story C3: Wire `What Matters`

Outcome:

The brief surfaces real current pressure.

Build:

- rank active missions
- rank blockers and open loops
- surface one top recommendation

Proof:

- brief top priorities match live mission state

### Story C4: Wire `What JARVIS Did`

Outcome:

The brief shows work done on Chris's behalf.

Build:

- pull from visible background work records
- distinguish observations, drafts, staged work, and completed work

Proof:

- at least one real background-prepared item appears in the brief

### Story C5: Link brief to mission workspace

Outcome:

The brief is not a dead end.

Build:

- each important brief item routes to the right mission or follow-up surface

Proof:

- click-through from brief to mission works for top items

## Epic D: Background Progress

Goal:

Make JARVIS feel active between conversations.

Definition of done:

At least one active mission receives useful background-prepared work that is
visible afterward.

### Story D1: Define V1 allowed background jobs

Outcome:

A narrow, safe, useful list of background behaviors.

Build:

- mission milestone proposals
- next-action suggestions
- stalled mission detection
- writing opportunity spotting
- scouting readiness preparation

Proof:

- one documented allowed-jobs list exists for V1

### Story D2: Record background work visibly

Outcome:

Prepared work leaves a readable trail.

Build:

- add activity records
- add mission history records
- classify suggestion vs staged vs completed work

Proof:

- background work appears in both brief and mission history

### Story D3: Surface prepared outputs in mission view

Outcome:

Prepared work is easy to discover and act on.

Build:

- add prepared recommendations section
- add staged output cards where appropriate

Proof:

- one mission displays useful prepared work in the workspace

## Epic E: Voice Tier Zero

Goal:

Make voice a true product path.

Definition of done:

Chris can speak naturally, create or advance a mission, receive a response,
and stay in flow without losing context.

### Story E1: Stabilize listen/respond loop

Outcome:

The voice path feels dependable.

Build:

- stabilize listen state
- stabilize response state
- improve interruption/resume handling
- reduce dead-air or confused state transitions

Likely files:

- `jarvis/voice_ui.py`
- `jarvis/service.py`

Proof:

- one uninterrupted voice mission-create flow works end-to-end

### Story E2: Sync voice and surfaced workspace

Outcome:

The UI follows the conversation.

Build:

- ensure created or advanced mission becomes visible immediately
- keep transcript and mission context aligned

Proof:

- voice-created mission opens in the correct workspace

### Story E3: Preserve typed fallback without divergence

Outcome:

Voice and typed paths remain one product, not two.

Build:

- ensure typed fallback uses the same core logic and surfaces

Proof:

- parity checks pass for key exemplar prompts

## Epic F: Accountability Loop

Goal:

Make JARVIS remember commitments and follow up.

Definition of done:

Active missions receive visible progress reinforcement or stalled-mission
nudges in a supportive tone.

### Story F1: Define mission cadence rules

Outcome:

JARVIS knows when to check in.

Build:

- define cadence defaults by mission type
- define stale thresholds
- define what counts as progress

Proof:

- cadence rules exist and are usable across launch domains

### Story F2: Add supportive follow-up generation

Outcome:

Follow-up feels like stewardship, not nagging.

Build:

- produce positive reinforcement
- produce stalled-mission prompts
- produce next best action suggestions

Proof:

- one positive and one stalled follow-up example are generated from live missions

### Story F3: Surface accountability in brief and workspace

Outcome:

Accountability is visible where Chris already looks.

Build:

- add accountability signals to mission workspace
- add mission progress signals to Daily Brief

Proof:

- accountability appears in both surfaces for at least one mission

## First Slice Backlog

This is the immediate implementation queue.

### Slice 1: Mission Capture + Mission Workspace + Daily Brief Linkage

1. Story A1: Define V1 mission contract
2. Story A2: Tighten natural-language mission creation
3. Story A4: Auto-route to mission workspace after creation
4. Story B1: Define mission workspace information hierarchy
5. Story B2: Add core mission sections
6. Story C1: Define Daily Brief structure
7. Story C3: Wire `What Matters`
8. Story C5: Link brief to mission workspace

This slice is the smallest credible path to the core feeling.

## Proof Checklist

Before calling V1 slice work done, verify:

- a typed prompt creates a useful mission
- a voice prompt creates a useful mission
- mission workspace opens automatically
- workspace shows milestones and next action
- Daily Brief reflects the new mission in `What Matters`
- at least one mission can be advanced without leaving the main flow

## Defer List

Keep these out of the first slice unless they directly unblock it:

- foundry/new agent generation
- deep trust-zone expansion
- household-wide admin experiences
- broad home-control integration
- legacy archive work
- major visual redesign unrelated to mission flow
- speculative platform work without immediate user-facing effect
