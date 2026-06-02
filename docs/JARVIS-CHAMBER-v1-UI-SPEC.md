# JARVIS Chamber v1 UI Spec

## Purpose

This document turns the Interaction Bible into an implementation-facing product surface for the first real JARVIS chamber.

This is not a generic dashboard redesign.

This chamber spec inherits the shared shell, navigation, density, and component rules in `docs/JARVIS-FRONTEND-DESIGN-SYSTEM-v1.md`.

It is the visible expression of the doctrine:

- JARVIS is a private intelligence chamber
- the first experience is a living briefing
- conversation is always available
- machinery is mostly hidden
- the user should feel: `You’re not carrying this alone.`

## Scope

This spec defines:

- the primary home-screen layout
- the information hierarchy
- the visible interaction rules
- the relationship between briefing, conversation, and background work
- what belongs in v1
- what must be deferred or hidden

## North Star

When Chris opens JARVIS, the interface should feel like:

`Something has been faithfully watching over the mission while I was away.`

The chamber should not feel like:

- a blank prompt
- a dashboard wall
- a control room of floating panels
- a debug console
- a swarm of bots

## Primary Job of the Chamber

The chamber has one primary job:

- orient Chris quickly
- reduce cognitive burden
- show what matters
- show what JARVIS already prepared
- surface needed decisions
- offer one clear next move
- leave the door open for natural conversation

## Product Rule

The home surface is:

`briefing-first and conversation-centered`

That means:

- the first thing the user sees is not the chat prompt
- the user should still feel conversation is always close and always safe

## Information Hierarchy

### Tier 1: Briefing

This is the hero surface.

It should answer:

- what matters now
- what changed
- what JARVIS prepared
- what needs a decision
- what JARVIS recommends next

### Tier 2: Support Blocks

These support the briefing without replacing it.

They include:

- Already Working
- Needs You
- Drift / Risk

### Tier 3: Conversation

Conversation is persistent and available, but subordinate to the briefing on initial load.

### Tier 4: Deeper Systems

These are available on demand:

- Catalyst
- approvals detail
- memory review
- agent council
- logs
- system status
- packet surfaces
- diagnostics

## Chamber Layout

The v1 chamber should use a three-band layout.

### Band A: Top Posture Strip

A thin, quiet band.

Purpose:

- orient without demanding attention

Contains only:

- current time or phase
- one weather or context signal
- one system-trust signal if needed
- settings entry

Avoid:

- provider bragging
- model names as primary chrome
- too many badges
- debug vocabulary

### Band B: Briefing Field

This is the center of gravity.

It contains:

1. chamber greeting
2. state-of-the-day line
3. 3 to 5 priority briefing items
4. recommended next move

This area should visually dominate the home screen.

### Band C: Support and Conversation Field

This sits below or beside the main briefing depending on viewport.

It contains four zones:

1. Already Working
2. Needs You
3. Drift / Risk
4. Speak Freely

These should feel like elegant instruments, not miscellaneous cards.

## Five Home Zones

### 1. The Briefing

This is the primary narrative surface.

Rules:

- one short greeting
- one sentence of overall state
- 3 to 5 ordered items
- one explicit next move
- no more than ~120 to 180 words before the user chooses to expand

Preferred pattern:

1. greeting
2. state line
3. three things matter
4. I prepared...
5. recommendation

### 2. Already Working

This is the quiet proof of stewardship.

Rules:

- maximum 3 items visible by default
- each item should be phrased as active preparation, not raw agent status
- examples should read like outcomes, not system logs

Good:

- Preparing tomorrow’s meeting frame
- Reviewing family schedule friction
- Staging a diligence brief

Bad:

- Herald running
- Watcher active
- queue depth 6

### 3. Needs You

This is the decision lane.

Rules:

- decisions should be concrete
- each item should have a clear verb
- should be ordered by consequence, not by chronology
- no vague “review pending” filler

Good:

- Approve Thursday family calendar change
- Review and send draft follow-up
- Decide whether to continue passive-income diligence

### 4. Drift / Risk

This is the wisdom lane.

Rules:

- gentle but clear
- no shame language
- no over-alerting
- only show items that materially matter

Good:

- Health has no protected space this week
- Dinner is exposed twice this week
- The book project has gone quiet for 12 days

### 5. Speak Freely

This is the conversation lane.

Rules:

- always available
- visually welcoming
- not the first focal point on initial load
- should feel like an open door, not a demand for input

Label:

`Speak freely`

Avoid:

- Ask me anything
- What can I help with?
- Enter prompt here

## Desktop Layout

Desktop should favor:

- large central briefing field
- support blocks arranged with restraint
- conversation docked in a stable, elegant position

Recommended structure:

- center-left: briefing field
- right column: conversation
- lower or side support strip: Already Working / Needs You / Drift

The current “floating chat + floating sidecar + floating packet rail” approach should be retired.

## Mobile / Narrow Layout

Narrow layouts should prioritize:

1. Briefing
2. Needs You
3. Speak Freely

Already Working and Drift / Risk can collapse behind expandable sections.

Conversation remains present, but screen height should not be consumed by chrome.

## Conversation Design

### Role of Conversation

Conversation is where Chris enters the chamber and where JARVIS answers naturally.

But conversation should not define the whole screen.

### Conversation Rules

- the thread should feel like talking to one trusted presence
- the composer should be visually simple
- helper copy should be minimal
- attachments should be present but quiet
- voice controls should not compete with send

### Composer Rules

Required:

- message field
- send button
- attachment affordance

Optional but subordinate:

- voice toggle
- mic entry

Avoid:

- crowded control clusters
- visible system jargon
- too many mini-buttons around the composer

## Visual Direction

### Desired Feel

`Walnut desk. Arc reactor underneath.`

The visual system should feel:

- premium
- private
- calm
- warm
- powerful

### Core Traits

- dark or warm-neutral base
- restrained glow
- subtle depth
- elegant typography
- quiet motion
- card surfaces that feel like instruments

### Avoid

- cartoonish AI iconography
- cluttered grids
- heavy sci-fi cosplay
- sterile enterprise SaaS
- “assistant toy” visuals

## Motion Rules

Motion should communicate:

- presence
- readiness
- state change

Motion should not communicate:

- novelty
- entertainment
- visual overconfidence

Use motion for:

- briefing refresh
- surfaced recommendation
- prepared work completion
- approval reveal

Avoid:

- constant particle distraction
- unnecessary idle animation
- dramatic transitions between ordinary states

## Hidden vs Visible Machinery

### Hidden by Default

- agent roster
- orchestration internals
- provider/model routing
- logs
- memory controls
- governance scaffolding
- packet sprawl

### Visible When Useful

- what JARVIS noticed
- what JARVIS prepared
- what was completed under standing permission
- what was held for approval
- why a recommendation exists
- which agent contributed, if that improves trust or accountability

## Field Reports and Council Visibility

Agent visibility should be optional and structured.

Default home behavior:

- unified JARVIS voice

Expandable or summoned behavior:

- field reports
- while-you-were-away report
- roundtable
- dissenting view

These should appear as:

- curated report surfaces
- not raw logs
- not multi-agent chatter

## Home Refresh Rules

The chamber should refresh around meaningful thresholds, not on constant visual churn.

Refresh triggers:

- new high-consequence decision
- meaningful prepared artifact ready
- major drift detected
- morning / midday / evening cycle change
- user return after time away

## State Model

The visible home should reflect one of these states:

### 1. Calm Ready

Low friction, no major decisions.

### 2. Active Stewardship

Work is being prepared; a few meaningful items matter.

### 3. Decision Required

One or more consequential choices need Chris.

### 4. Drift Warning

Reality is moving away from priorities.

### 5. Crisis / High Alert

Only for meaningful events.
Tone becomes brief, direct, calm.

## v1 Must Include

- living briefing
- Already Working
- Needs You
- Drift / Risk
- Speak Freely
- clear recommended next move
- one stable conversation pane
- one clean approval entry path
- support for while-you-were-away summaries

## v1 Must Not Include

- visible full agent map on home
- giant floating packet rail as primary nav
- dashboard wall of all subsystems
- raw system telemetry as primary content
- decorative panels without decision value

## File / Surface Mapping

Primary files likely affected:

- [jarvis/voice_ui.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/voice_ui.py)
- [jarvis/runtime.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/runtime.py)
- [jarvis/service.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/service.py)

Primary runtime surfaces to shape:

- `dashboard_snapshot()`
- `today_board()`
- `chat_state_snapshot()`
- `assistant_notifications()`
- `work_lifecycle_snapshot()`
- `self_improvement_snapshot()`

## Acceptance Criteria

The chamber spec is working when:

- opening JARVIS feels relieving, not demanding
- the first thing visible is meaning, not machinery
- the user can understand what matters in under 10 seconds
- the user can talk immediately without hunting for the input
- the user sees evidence that JARVIS has already been helping
- the user is never forced to parse a dashboard wall

## Shared Design-System References

Use these alongside this chamber spec:

- `docs/JARVIS-FRONTEND-DESIGN-SYSTEM-v1.md`
- `artifacts/mockups/jarvis-command-center-unified.html`
- `artifacts/mockups/jarvis-numbered-outline-checklist.html`

## Implementation Sequence

1. Replace the current shell hierarchy with briefing-first hierarchy.
2. Simplify or remove floating packet-first navigation.
3. Rebuild home around the five calm zones.
4. Tighten composer and thread into a stable conversation surface.
5. Introduce field reports and council views only as secondary layers.
