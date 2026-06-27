# JARVIS Glass Theme UX Specification

## Purpose

This document defines how JARVIS doctrine becomes visible through the Glass
theme.

It is not a style guide first.

It is not a palette document first.

It is not a component library first.

It is the visual and behavioral specification for expressing:

- the Life Operating Officer vision
- the arrival and conversation workspace doctrine
- the object posture representation doctrine

Glass is not merely a style.

Glass is a behavior.

The purpose of Glass is to make JARVIS feel:

- continuously operating
- permeable rather than page-like
- alive rather than loaded
- transient where needed
- stable where trust is required

Read this after:

- `docs/JARVIS-LIFE-OPERATING-OFFICER.md`
- `docs/jarvis-canonical-operating-model.md`
- `docs/JARVIS-ARRIVAL-AND-CONVERSATION-WORKSPACE-DOCTRINE.md`
- `docs/JARVIS-OBJECT-POSTURE-REPRESENTATION-DOCTRINE.md`

If this document conflicts with higher-order doctrine, higher-order doctrine
wins.

## Core Visual Principle

The UI should feel alive, not loaded.

Most software behaves like this:

`Loading -> Loaded`

JARVIS should feel like this:

`Listening -> Thinking -> Emerging -> Transforming -> Monitoring`

That means:

- fewer hard transitions
- fewer page cuts
- fewer permanent panels
- more gradual emergence
- more visual permeability
- more environmental continuity

## Why Glass

Glass is appropriate because it visually reinforces doctrine.

Solid panels imply:

`I am a page.`

Glass layers imply:

`I am a moment.`

This is important for Law 6:

`Every transient layer should disappear once its purpose is fulfilled.`

Glass should therefore be used to communicate:

- temporary handoff layers
- posture-specific overlays
- decision comparisons
- brief narrative summaries
- dynamic workspace transitions

Glass should not be used to create decorative clutter.

## Environmental Layer

The environmental layer is the always-present substrate of JARVIS.

It should feel infrastructural rather than widgetized.

It should not read like a dashboard.

### It should communicate:

- presence
- continuity
- readiness
- ambient operation

### It should contain:

- Conversation Presence
- Continuity Spine
- Ambient Intelligence
- Mission Gravity

### It should not contain:

- calendars
- metric boards
- large cards
- data grids
- charts
- detailed mission summaries
- launcher tiles

The environmental layer should feel etched into the space rather than floating
like app cards.

Think:

`Workshop HUD`

not

`Dashboard`

## Material System

Glass in JARVIS should be specified as a behavioral material system.

### Material characteristics

- translucent, not transparent
- layered, not stacked like windows
- luminous at edges, quiet at center
- soft blur for depth separation
- variable opacity based on posture and importance
- low-noise by default

### Material roles

#### Infrastructure Glass

Used for the permanent operating layer.

Should feel stable, quiet, and nearly architectural.

#### Ritual Glass

Used for the Operational Handoff.

Should feel narratively present, but transient.

Should dissolve when the ritual is complete.

#### Workspace Glass

Used for dynamic workspaces and posture-driven surfaces.

Should feel materialized in response to intent.

Should transform rather than cut.

#### Peripheral Glass

Used for Steward posture, ambient watches, and delegated monitoring.

Should feel quiet, receding, and non-demanding.

## Workspace Materialization Rules

Workspaces do not open.

Workspaces materialize.

This distinction is essential.

### A workspace should feel like it:

- emerges from the environment
- is summoned by intent
- inherits current continuity
- transforms from prior context where possible

### A workspace should not feel like it:

- routed to a page
- launched an app
- replaced the product shell
- loaded a module

### Materialization sequence

1. intent is recognized
2. relevant object is selected
3. posture stack is inferred
4. representation is composed
5. workspace emerges

### Dissolution sequence

When the context changes:

- the old transient layer should recede
- the new workspace should emerge
- persistent environmental elements should remain stable

## Posture Physics

Each posture should have its own visual physics.

Not merely different content.

Different motion, density, spatial behavior, and emphasis.

### Builder

Feels:

- expansive
- generative
- relational
- future-facing

Visual physics:

- space opens
- relationships become visible
- new structures branch outward
- composition feels unfinished in a productive way

### Operator

Feels:

- directional
- aligned
- active
- execution-oriented

Visual physics:

- density increases slightly
- task-relevant surfaces align
- blockers and next steps move closer to the center
- momentum is emphasized over exploration

### Advisor

Feels:

- comparative
- analytical
- confidence-building

Visual physics:

- surfaces split
- options sit side by side
- tradeoff structures become legible
- recommendation line becomes visually clear

### Chief of Staff

Feels:

- calm
- compressed
- synthesized
- orienting

Visual physics:

- noise collapses
- summary rises
- details recede until asked for
- motion is minimal

### Steward

Feels:

- quiet
- delegated
- reassuring

Visual physics:

- information moves peripheral
- active monitoring becomes subtle
- exceptions are emphasized only when necessary
- the main effect is relief, not stimulation

### Companion

Feels:

- relational
- fluid
- reflective
- present

Visual physics:

- layout softens
- narrative surfaces can appear
- memory and meaning can emerge without becoming reports
- conversation stays dominant

## Transition Doctrine

Transitions should communicate continuity, not navigation.

### Important transitions to define

#### Operational Handoff -> Conversation

- handoff can be interrupted at any moment
- the handoff should collapse immediately when Chris speaks
- no residue should remain unless it is explicitly recalled

#### Conversation -> Workspace

- workspace should emerge from the current object and posture context
- conversation remains the stable anchor
- the user should not feel transported elsewhere

#### Workspace -> Workspace

- reuse spatial continuity where possible
- transform rather than replace
- preserve the sense that JARVIS is still the same operation

#### Workspace -> Steward

- when active work becomes monitoring, the UI should recede
- the result should feel like burden removal

#### Recommendation -> Decision -> Action

- comparison becomes recommendation
- recommendation becomes commitment
- commitment becomes operational next step

This chain should feel guided, not mechanical.

## Motion Doctrine

Motion in JARVIS should:

- reveal continuity
- signal posture changes
- communicate emergence and recession
- support attention

Motion should not:

- perform for its own sake
- feel decorative
- delay interaction
- create theatrical friction

The correct motion philosophy is:

`subtle environmental responsiveness`

not

`cinematic UI spectacle`

## Typography and Hierarchy Principles

Typography should reinforce cognitive load reduction.

### Requirements

- hierarchy must be obvious at a glance
- recommendation lines should be unmistakable
- summaries should be compact and legible
- ambient layers should remain quiet
- transient ritual text should read as spoken handoff, not report copy

Type should help JARVIS feel:

- composed
- confident
- selective
- intelligent

Never:

- overloaded
- glossy
- corporate
- hyper-technical by default

## Color and Light Principles

Color should encode trust, continuity, attention, and posture.

### Baseline

- dark field for depth and calm
- cool luminous accents for live system presence
- restrained warm accents only where relational or high-meaning context matters

### Usage

- cool light for active operation and presence
- warmer tonal shifts for companion or reflective contexts
- alert hues only for true attention shifts

Color should support emotional posture without becoming gimmicky.

## MUI X Role Inside Glass

MUI X is a structural toolkit inside dynamic workspaces.

It is not the visible philosophy of JARVIS.

### Appropriate use

- Data Grid for comparison, evidence, operations, and readiness truth
- Tree View for object relationships and graph traversal
- Charts for trends, telemetry, and forecasting
- Panels for dynamic workspace composition

### Misuse

- surfacing MUI structures as permanent navigation
- letting grids become the default interface
- turning every workspace into enterprise software

MUI X should appear when the posture and object demand detail.

It should disappear back into the environment when the moment passes.

## Anti-Patterns

Do not create:

- Home screens
- widget walls
- dashboard dumps
- app launchers
- tab-first flows
- visible information architecture
- permanent mission cards everywhere
- floating chrome for its own sake
- hard loading mentality

Do not mistake:

- blue holograms
- transparent panels
- glowing edges

for actual JARVIS behavior.

The visual goal is not:

`look like Iron Man`

The visual goal is:

`feel like a continuously operating intelligence that reorganizes around intent`

## Ultimate Test

When making any visual decision, ask:

1. Which doctrine is this serving?
2. Is this reinforcing presence or merely adding information?
3. Is this layer permanent or transient?
4. Is this workspace emerging from intent or imitating an app?
5. Does this posture feel behaviorally distinct?
6. Does this reduce cognitive load?

If a visual decision does not reinforce doctrine, it is probably drift.
