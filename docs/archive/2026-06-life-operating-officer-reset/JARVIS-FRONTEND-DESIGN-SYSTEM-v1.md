# JARVIS Frontend Design System v1

## Purpose

This document defines the shared frontend system for JARVIS across iPhone and desktop.

It exists to prevent drift toward:

- generic dashboards
- chat-shell-first layouts
- feature-menu navigation
- voice-led assumptions
- disconnected mobile and desktop metaphors

This system inherits from:

- `docs/jarvis-canonical-operating-model.md`
- `docs/JARVIS-INTERACTION-BIBLE-v1.md`
- `docs/JARVIS-CHAMBER-v1-UI-SPEC.md`
- `artifacts/mockups/jarvis-numbered-outline-checklist.html`

If a future mockup or implementation conflicts with this document, this document wins unless deliberately revised.

## Canonical Product Frame

JARVIS is:

- an always-on orchestrator
- an oversight surface
- a continuity engine
- a command center for real life domains
- voice-first, conversation-first

The frontend is therefore not:

- a generic app dashboard
- a chat app with extra tabs
- a control room of equal-weight panels
- a feature catalog

The interface must help Chris do five things quickly:

1. orient to what matters now
2. see what changed while away
3. understand what JARVIS is already carrying
4. take one decisive next action
5. drop into conversation or voice when useful

## Core Design Principles

### 1. Briefing before browsing

The default surface must answer reality before it offers navigation.

The first read should clarify:

- what matters
- what changed
- what JARVIS prepared
- what requires a decision
- what JARVIS recommends next

### 2. Silent-first by default

Every core flow must be excellent with no speech at all.

The system should assume the user may need to:

- scan
- triage
- approve
- defer
- redirect
- resume work

without speaking.

### 3. Voice as acceleration, not dependence

Voice should:

- speed up capture
- reduce friction while moving
- support hands-free continuation
- provide a fast lane into command or conversation

Voice should not:

- own the primary navigation model
- be required to complete important tasks
- consume the default home hierarchy

### 4. One coherent presence

JARVIS may orchestrate many systems underneath, but the UI should feel like one disciplined operating presence.

Avoid visible fragmentation into:

- agent personalities
- competing panes
- subsystem branding
- equal-weight feature silos

### 5. Command over exploration

Navigation should support steering an active system, not wandering around a product tree.

Primary interaction modes should be:

- review
- decide
- redirect
- command
- inspect
- resume

## Shared Visual Direction

### Emotional blend

The shared design language should feel like:

`Warm study surface. Quiet reactor underneath.`

Target blend:

- trusted study
- chief-of-staff desk
- mission console
- family stewardship surface

### Surface rules

- Use a dark or warm-neutral base with restrained cyan, amber, green, and steel-blue accents.
- Favor layered atmosphere over flat fills.
- Use glow sparingly as a trust or readiness signal, not decoration.
- Surfaces should feel like instruments, not cards in a dashboard grid.
- Typography should carry hierarchy more than color does.

### Anti-patterns

- neon sci-fi cosplay
- cheerful productivity-app chrome
- bright chat bubbles as primary identity
- giant icon walls
- crowded status badges
- visual noise pretending to be intelligence

## Core Primitives

These primitives must exist in both iPhone and desktop implementations.

### 1. Posture Strip

A thin global orientation band.

Contains:

- current phase or day posture
- one environmental context signal
- one system-trust signal if needed
- one quiet route into settings or system state

Must not contain:

- dense filters
- provider jargon
- multiple alert stacks

### 2. Briefing Field

The center of gravity.

Contains:

- one greeting or posture line
- one state sentence
- 3 to 5 ordered briefing items
- one explicit recommended next move

Rules:

- this is always the visually dominant region
- it should read in under 10 seconds
- it should compress complexity rather than summarize everything

### 3. Decision Lane

The lane for approvals, redirects, and bounded actions.

Rules:

- every item needs a clear verb
- every item needs a consequence-aware priority
- every item should resolve with one tap or one short drill-in
- maximum 3 visible by default before expansion

### 4. Stewardship Lane

Quiet evidence that JARVIS is already carrying work.

Rules:

- phrase items as outcomes in progress
- show preparation, not machinery
- default to 2 or 3 visible items

### 5. Drift / Risk Lane

Material deviations from priorities or commitments.

Rules:

- calm tone
- no shame language
- only show meaningful drift
- use escalation color only when consequence justifies it

### 6. Command Dock

The stable entry for typed command, lightweight conversation, and optional voice.

Contains:

- text field
- send / commit affordance
- optional microphone affordance
- optional attachment affordance

Rules:

- this is a dock, not a giant chat stage
- it must feel always available
- it should not visually overpower the briefing

### 7. Workstream Panels

Domain-specific surfaces such as health, household, forge, publishing, or chronicle.

Rules:

- inherit the same shell, spacing, and tone
- lead with posture and recommended action
- avoid raw data walls
- expose depth through progressive disclosure

## Navigation Model

### Canonical structure

Navigation should move from domain sprawl to mission structure.

Primary level:

- Home
- Decisions
- Workstreams
- Chronicle
- Command
- Systems

Secondary level under Workstreams:

- Household
- Health
- Briefings
- Catalyst
- Forge
- Publish
- Navigate
- Faith
- Huddle
- Weather

### Navigation rules

- The first level should be small and stable.
- High-frequency destinations should not exceed 5 to 6 top-level choices.
- Domain proliferation belongs inside grouped workstreams, not on the root shell.
- Root navigation should answer "what kind of interaction am I here for?" rather than "which feature am I opening?"

### iPhone navigation rule

Do not place a long horizontal strip of equal-weight domains at the root.

Prefer:

- 4 or 5 persistent root destinations
- one command affordance that is always near reach
- drill-in stacks for workstream detail

### Desktop navigation rule

Prefer a left rail or split shell with:

- posture and root navigation at top
- workstream groups in the middle
- account and system tools at bottom

Do not recreate the phone tab bar on desktop.

## Information Hierarchy

### Shared order of importance

1. what matters now
2. what needs a decision
3. what JARVIS is already carrying
4. what is drifting
5. deeper workstream detail
6. system internals

### Hierarchy rules

- recommendation beats recency
- consequence beats chronology
- continuity beats novelty
- actionability beats completeness

### Compression rules

- default surfaces show the smallest useful truth
- detail expands inline before it navigates away when possible
- dense lists should summarize count, urgency, and recommended action before full content

## Density Rules

### iPhone

- optimize for thumb-reachable review and one-tap action
- keep visible sections short and decisive
- default to one dominant column
- collapse stewardship and drift when they are not urgent
- maintain persistent access to command without consuming excessive height

### Desktop

- use width for simultaneous orientation, command, and context
- allow briefing plus decision plus command to coexist
- use side columns for support lanes, not as competing primary canvases
- let deep workstream tools open in stable subviews, drawers, or secondary panes

### Shared density limits

- no more than one visually dominant hero region per screen
- avoid more than three urgency colors in a single viewport
- avoid more than three visible action buttons per card
- default sections should rarely exceed 5 rows before summarizing

## Interaction Rules

### One-tap action

Important items should allow:

- approve
- defer
- open context
- redirect

with minimal friction.

### Review before compose

JARVIS should more often present prepared choices than ask the user to compose from scratch.

### Progressive disclosure

Show in layers:

1. summary
2. recommendation
3. rationale
4. source detail

Do not start at layer 4.

### Command-center behavior

The command model should support three kinds of input:

- direct commands
- short questions
- review-and-act confirmations

Suggested command prompts:

- `Stage replies for the two urgent threads`
- `Show me what changed since lunch`
- `Hold anything non-urgent until tomorrow`

Avoid default prompt copy such as:

- Ask me anything
- Type a message
- How can I help

## Silent-First Rules

### Must be possible silently

- daily orientation
- approval review
- workstream triage
- task redirection
- reading prepared recommendations
- resuming prior threads
- inspecting what changed

### Silent interaction cues

- ordered lists over chat chronology
- explicit verbs over abstract labels
- state chips that imply actionability
- continuity markers such as `Updated 12m ago` or `Held for your approval`

### Notification philosophy

Notifications should pull the user into an already-prepared state, not into a blank input.

## Voice-Enabled Rules

### Voice belongs in three places

- launch or capture
- command dock escalation
- active conversation session

### Voice should feel optional

- microphone affordances should be clear but not oversized
- speaking should enhance the same command model as typing
- voice session UI should preserve continuity with the rest of the shell

### Voice should not create a second product

The voice surface should look like a focused mode of the same system, not a separate assistant app.

## Component Rules

### Recommendation Card

Must include:

- title
- why it matters
- primary action
- optional alternate action

### Decision Row

Must include:

- consequence-aware label
- short supporting context
- one primary verb
- one quiet secondary route

### Stewardship Item

Must read as active work in progress, such as:

- Preparing Friday follow-up draft
- Reviewing school-week timing conflicts

Not:

- Agent active
- Sync running

### Drift Item

Must state:

- what is drifting
- why it matters
- whether action is needed now

### Command Dock

Must support:

- typed entry
- submission
- optional voice trigger
- carry-forward context

### Section Header

Should usually include:

- section title
- short purpose cue
- count or posture badge only if it changes decisions

## Motion Rules

- Use motion to signal readiness, refresh, reveal, completion, or escalation.
- Keep transitions short and calm.
- Prefer opacity, blur, and position shifts over dramatic transforms.
- Do not animate decorative loops continuously on primary screens.

## Copy Rules

- calm
- concise
- consequence-aware
- non-corporate
- non-performative

Prefer:

- Three things matter.
- I held this for your review.
- I prepared the first pass.
- This can wait.

Avoid:

- maximize productivity
- assistant phrasing
- overexplaining labels
- playful filler in urgent contexts

## Desktop vs iPhone Behavior

### Shared invariant

Both platforms must express the same operating model:

- briefing first
- decisions visible
- command always near
- voice optional
- machinery mostly hidden

### Desktop should emphasize

- parallel visibility
- multi-lane oversight
- stable command dock
- quiet right-rail or side-pane conversation
- deeper contextual inspection without losing home posture

### iPhone should emphasize

- rapid orientation
- one-thumb decisions
- compressed support lanes
- resumable drill-in flows
- command and voice within reach, but never as the only path

### Things that must differ

- density
- pane count
- expansion behavior
- location of command dock

### Things that must not differ

- terminology
- color meaning
- posture hierarchy
- decision semantics
- action verbs
- recommendation framing

## Standardization Targets For Future UI Work

Standardize next:

1. root navigation vocabulary
2. posture strip tokens and states
3. recommendation and decision components
4. command dock behavior across phone and desktop
5. stewardship and drift lane content model
6. shared spacing, corner radius, and elevation tokens
7. motion tokens for refresh, reveal, and completion

## Implementation Guidance

When shaping future screens, evaluate them with these checks:

1. Does the first screen orient me before asking me to interact?
2. Can I handle the important path silently?
3. Is command available without becoming the whole screen?
4. Does this feel like one operating presence rather than many tools?
5. Is the recommendation clearer than the data behind it?
6. Would the same concept make sense on both iPhone and desktop?

## Related Artifact

Use this design-system mockup as the visual reference companion:

- `artifacts/mockups/jarvis-command-center-unified.html`
