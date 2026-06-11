# JARVIS Desktop Command-Center Model

This document defines the desktop oversight experience for JARVIS.

It exists to keep desktop work aligned with the canonical operating model and to stop future frontend drift toward:

- chat shell thinking
- dashboard-wall thinking
- packet dumping
- decorative command-center cosplay without real supervision value

The governing anchors are:

- `docs/jarvis-canonical-operating-model.md`
- `artifacts/mockups/jarvis-numbered-outline-checklist.html`

## Desktop Job To Be Done

Desktop is where JARVIS becomes a command center for supervising an active agent society.

The desktop product job is not:

- talk to JARVIS like a chatbot
- browse a feature menu
- stare at ambient visuals

The desktop product job is:

- understand what changed while I was away
- see which agents are active, blocked, waiting, or drifting
- identify what needs my attention now
- inspect evidence before making a decision
- redirect agent work without losing continuity
- resume prior operating context quickly
- govern the system silently when speaking is inconvenient

## Core Desktop Thesis

Desktop should feel like:

- calm command center
- second-brain oversight surface
- continuity workspace
- operational cockpit for real life

Desktop is the supervision plane.

Mobile is the interruption, capture, and quick-action plane.

Voice is available on desktop, but it is not the organizing assumption.

## Primary Desktop Surfaces

Desktop should be organized around six persistent oversight surfaces.

### 1. Return Brief

The top of desktop should answer the question:

`What changed while I was away, and do I need to care yet?`

This surface should summarize:

- elapsed time since last active supervision
- completed agent work
- newly blocked work
- new decisions waiting
- notable drift or escalation
- continuity resumptions available

The Return Brief is not a timeline dump. It is a synthesized supervisory digest.

### 2. Attention Queue

This is the main triage lane for things that actually need human attention.

Every item here must be normalized into one of these classes:

- `approval`
- `decision`
- `blocked`
- `redirect`
- `review`
- `resume`

Each item should show:

- why it surfaced
- which agent or lane owns it
- what happens if I do nothing
- the smallest next supervisory action

### 3. Agent Society Board

Desktop needs a persistent board that makes the active agent society legible.

The board should expose:

- which agents are active
- what each agent is trying to accomplish
- lane ownership
- current run state
- confidence or risk posture
- whether the agent is autonomous, waiting, blocked, or escalating

This should feel like supervising a staff, not reading logs.

### 4. Decision Queue

Approvals and bounded decisions need their own dedicated surface.

Each queue item should include:

- agent source
- action requested
- why now
- evidence packet
- scope and blast radius
- approve / defer / deny / redirect options

Approval UX should help the user decide, not force the user to open a separate world.

### 5. Resume Stack

Desktop must preserve continuity across interruptions.

The Resume Stack should hold suspended contexts such as:

- previously inspected agent lanes
- half-reviewed approvals
- unfinished triage sessions
- open investigation threads
- paused steering actions

Resuming should recover:

- scope
- selected lane
- current evidence slice
- pending next action

### 6. Command Dock

Desktop needs a silent-first steering surface for short supervisory actions.

This dock should prioritize verbs like:

- `Review`
- `Triage`
- `Inspect`
- `Redirect`
- `Approve`
- `Defer`
- `Resume`
- `Quiet`

The dock is not a prompt box disguised as command. It is a compact supervisory grammar.

## Command-Center Structure

The recommended desktop structure is:

1. `Return Brief` across the top
2. `Attention Queue` as the main working lane
3. `Agent Society Board` beside or beneath the queue
4. `Decision Queue` in a dedicated right-side rail
5. `Resume Stack` always visible in compact form
6. `Command Dock` anchored and always reachable
7. `Inspector Drawer` for evidence and deep lane review

This creates a desktop hierarchy of:

- summarize
- triage
- inspect
- decide
- redirect
- resume

## Interaction Rules

### Silent-First Rule

Every important desktop path must be operable without speech.

The default desktop actions should assume:

- scanning
- clicking
- keyboard steering
- deferred review

Voice can accelerate, but voice must never be required.

### Supervision Rule

Desktop should always show the user what the system is doing on their behalf.

If the interface hides agent work until the user asks for it, the desktop has become too reactive.

### Evidence Rule

Approvals, redirects, and escalations should always open into evidence-aware inspection rather than blind yes/no prompts.

### Continuity Rule

Leaving the desktop should not collapse operating context.

When the user returns, JARVIS should restore:

- what changed
- what is still waiting
- what was already under review
- what can be resumed immediately

### Calm Rule

Desktop should reward periodic supervision, not constant babysitting.

That means:

- compressed summaries
- limited top-level urgency
- stable layout
- no noisy feed behavior by default

### Lane Rule

The system should organize around stewardship lanes, mission lanes, and agent ownership rather than generic app sections.

### Inspect-Then-Steer Rule

For desktop, the preferred sequence is:

1. inspect
2. understand
3. redirect or approve

This is different from mobile, where rapid single-tap action often comes first.

## Surface Contracts

### Return Brief Contract

Must include:

- absence duration
- concise change summary
- surfaced decisions
- blockers
- resumable contexts

Must not include:

- full event stream
- raw telemetry wall
- multiple competing heroes

### Attention Queue Contract

Must include:

- priority ordering
- state class
- owner
- why it matters
- one-step action

Must not include:

- ambient informational clutter
- hidden approval consequences

### Agent Society Board Contract

Must include:

- active
- waiting
- blocked
- escalated
- stale

Must not include:

- vanity avatars without operational meaning
- lane-free agent lists

### Decision Queue Contract

Must include:

- evidence
- scope
- consequence
- redirect path

Must not include:

- unscoped yes/no prompts
- approvals with no source accountability

### Resume Stack Contract

Must include:

- last supervision target
- resumable investigation
- resumable queue item
- partial decision context

Must not include:

- generic recent history
- undifferentiated browsing breadcrumbs

## Desktop Versus Mobile

Desktop differs from mobile in purpose, not just size.

### Desktop Is For

- supervising multiple agents at once
- comparing parallel lanes
- inspecting evidence
- processing stacked decisions
- recovering continuity after time away
- redirecting work at lane level

### Mobile Is For

- quick interrupts
- urgent approvals
- capture and handoff
- heads-up awareness
- voice entry
- one-step defer, approve, or resume

Desktop should feel broader, calmer, and more supervisory.

Mobile should feel faster, narrower, and interruption-safe.

## Anti-Patterns

Desktop work is drifting if it becomes:

- a chatbot with decorative chrome
- a dashboard grid of unrelated cards
- a packet browser with no triage logic
- an ambient holo scene with weak operational density
- a mobile layout simply stretched wider
- a generic analytics admin console

## Defined Screens And States

The desktop command-center work should define at least these states:

1. `Overview / Return`
2. `While You Were Away`
3. `Decision Queue`
4. `Agent Society`
5. `Resume and Continuity`
6. `Inspect and Redirect`

These are not separate apps. They are modes within the same command-center workspace.

## Design-System Implications

The design system branch should support:

- lane-state badges
- approval-state patterns
- resumable context chips
- compact evidence blocks
- silent command dock controls
- agent-state clusters
- inspection drawer patterns

## Open Questions

The main unresolved product questions are:

- What is the exact normalization model for desktop attention items across lanes?
- How much agent detail should remain visible before the user opens inspection?
- What is the right density for the Agent Society Board on laptop-width layouts?
- Which desktop actions deserve keyboard-first shortcuts on day one?
- How should absence summaries distinguish true urgency from informative change?

## Required Follow-Through

Future frontend work should use this document to check whether a proposed surface strengthens:

- oversight
- continuity
- silent command
- supervisory confidence
- real multi-agent visibility

If it does not, it is probably not command-center work.
