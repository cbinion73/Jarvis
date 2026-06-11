# JARVIS iPhone Mobile Command System

This document defines the iPhone/mobile command system for JARVIS so future phone work does not drift back toward a tiny desktop, a chat shell, or a voice-first assistant.

Use this with:

- `docs/jarvis-canonical-operating-model.md`
- `docs/ios-phone-parity-matrix.md`
- `artifacts/mockups/jarvis-iphone-command-system.html`

## Purpose

The phone is not where JARVIS exposes every domain equally.

The phone is where JARVIS helps me operate the system in real life when I:

- cannot speak
- have only a few seconds
- am moving
- need confidence before context
- need to approve, redirect, defer, or resume without opening a deep workspace

JARVIS on iPhone should feel like:

- a calm pocket command layer
- a fast decision and action surface
- a continuity-aware daily operating interface

## Core Position

Desktop is for supervision depth, workspace breadth, and longer operating sessions.

iPhone is for:

- seeing what matters now
- clearing urgent decisions fast
- resuming the exact thread or workflow already in motion
- steering focus and household posture
- handling commute and movement context
- capturing lightweight input silently

Voice remains available, but the mobile assumption is silent-first touch interaction.

## Mobile Command Model

The iPhone command system should be organized around five primary command surfaces plus one persistent continuity layer.

### 1. Today

The default landing surface.

Its job is to answer:

- What changed while I was away?
- What matters in the next few hours?
- What is blocked on me?
- What is already being handled?

Today is not a generic dashboard. It is a ranked command brief with:

- urgency strip
- brief timeline
- approvals waiting
- focus posture
- family/household changes
- active navigation context when relevant
- resume cards for unfinished threads

### 2. Focus

The personal operating surface.

Its job is to let me steer:

- today’s priorities
- interruption posture
- what JARVIS should hold, escalate, or suppress
- which missions are actively in focus

Focus combines intent, priority, and routing. It should feel like changing operating mode, not editing settings.

### 3. Family

The household command surface.

Its job is to surface:

- home posture
- family logistics
- pickup/dropoff timing
- safety or presence changes
- household tasks that need a human decision

This is the mobile expression of “real life operations,” not a smart-home control gallery.

### 4. Decisions

The approval and triage surface.

Its job is to let me:

- approve
- deny
- defer
- ask for one more detail
- batch clear low-risk items

This screen should prioritize fast confidence:

- short rationale
- clear consequence
- time sensitivity
- one-tap action

### 5. Navigate

The movement and commute surface.

Its job is to help JARVIS operate around movement:

- where I am going
- what timing changed
- route risk
- stop opportunities
- what needs review before arrival

Navigate should merge route intelligence with operational continuity. It is not just directions.

### Persistent Layer: Resume

Resume is not a tab. It is a system layer that appears across surfaces.

Its job is to preserve continuity for:

- unfinished agent work
- interrupted conversations
- pending reviews
- route sessions
- household flows in progress

Every primary surface can emit a resume card. Resume is the connective tissue that makes JARVIS feel always-on.

## Recommended iPhone Information Architecture

Primary bottom navigation should be reduced to the surfaces that matter most when mobile and silent:

1. Today
2. Focus
3. Decisions
4. Family
5. Navigate

Secondary capabilities should move behind these primary surfaces as drill-ins, drawers, or stack pushes:

- Health
- Weather
- Home details
- Huddle / Agents
- Chronicle
- Publish
- Forge
- Systems
- Voice

Those areas still exist, but they are not the main mobile mental model.

## Surface Structure

### Today Surface

Required blocks:

- top urgency strip
- “while you were away” delta summary
- next 3 horizon cards
- approvals due soon
- active agent progress
- resume stack
- optional voice entry button

Default action rules:

- tap card opens a focused detail sheet, not a sprawling destination
- swipe right clears or acknowledges only when reversible
- swipe left defers, snoozes, or pins to Focus

### Focus Surface

Required blocks:

- current operating posture
- top three priorities
- what JARVIS is suppressing
- what JARVIS will still interrupt for
- quick mode changes
- one-tap “protect next 2 hours” action

### Family Surface

Required blocks:

- household state at a glance
- pickup/dropoff timeline
- family needs requiring action
- presence changes
- home exceptions and errands

### Decisions Surface

Required blocks:

- urgent decisions first
- confidence + consequence labels
- expires soon grouping
- low-risk quick clear lane
- “need one more detail” action

### Navigate Surface

Required blocks:

- current destination or suggested next move
- leave-by / arrival confidence
- route disruption alerts
- smart stop options
- arrival-linked reminders, approvals, or handoffs

## Silent-First Interaction Rules

These rules are non-negotiable for mobile work.

### 1. Glance before read

Every top-level surface must communicate posture in under two seconds with:

- clear severity color
- one-line summaries
- counts
- deadlines
- action labels

### 2. Tap before type

The first useful action on mobile should usually be:

- approve
- defer
- pin
- route
- acknowledge
- resume
- message with a precomposed option

Typing is allowed, but should not be the default path.

### 3. Voice is an accelerant, not the foundation

Voice entry can appear as:

- optional capture on Today
- optional quick note in Family
- optional in-motion command in Navigate

No core mobile workflow should require speech.

### 4. Resume beats re-navigation

If I leave and come back, JARVIS should prefer:

- “Resume route review”
- “Resume household decision”
- “Resume morning brief”

not “go find the right tab again.”

### 5. One decision per card

Approval and triage cards should expose a single main question with a small number of bounded actions.

### 6. Detail is progressive

Mobile details should open in:

- bottom sheets
- compact push screens
- stacked drill-ins

not full desktop-style multi-panel layouts.

### 7. Motion changes priority

When movement context is active, Navigate and arrival-linked tasks can temporarily outrank other surfaces.

### 8. Silence is a product state

The UI must feel complete even with no speaking, no dictation, and no audio playback.

## How Mobile Differs From Desktop

Desktop should remain better for:

- deep supervision of agents
- broad workspace management
- longer review sessions
- doctrine and systems administration
- multi-panel inspection

Mobile should be better for:

- urgency triage
- one-tap approvals
- leave-now / commute decisions
- family logistics in motion
- quick focus changes
- absence recovery

If a feature is equally broad on both platforms, it probably is not yet shaped correctly for mobile.

## Mapping From Current iPhone Surfaces

Current app tabs are useful as implementation inventory, but not as the long-term command model.

Recommended remapping:

| Current surface | Mobile command role |
|---|---|
| `BriefingView.swift` | becomes the Today surface |
| `NeedsView.swift` | becomes the Decisions surface |
| `NavigateView.swift` | remains a primary surface |
| `HomeView.swift` + family posture portions of Brief | merge toward Family |
| focus controls in `BriefingView.swift` and `SettingsView.swift` | merge toward Focus |
| `VoiceView.swift` | becomes optional entry and resume utility, not a primary mobile anchor |
| `SettingsView.swift` and long-tail domain tabs | move to secondary drill-in and admin layers |

## What Future iPhone Work Should Add

### Product / UX

- a true Today landing view with urgency, change, and resume hierarchy
- a dedicated Focus surface instead of scattering focus controls
- a Family surface that unifies home posture and family logistics
- a Decisions queue optimized for confidence and expiry
- continuity cards shared across surfaces

### Interaction

- swipe actions for defer, pin, and acknowledge
- bounded action sheets for approvals
- richer resume affordances after interruptions
- better in-motion handling when Navigate becomes dominant

### IA cleanup

- reduce the primary tab count
- demote voice from primary navigation
- demote systems/admin from primary navigation
- shift long-tail domains to secondary stacks

## What Desktop Branches Still Need To Add

- stronger cross-domain continuity views so mobile resume cards can open into a coherent desktop destination
- better agent supervision summaries for handoff from phone triage to desktop review
- a consistent “what changed while you were away” model shared across platforms

## What Design-System Branches Still Need To Add

- reusable urgency strip component
- reusable resume card component
- reusable decision card with consequence and expiry states
- reusable focus posture chips and mode-action controls
- reusable household timeline / movement card patterns
- compact mobile sheet and stacked drill-in rules

## Unresolved Questions

- Should Family and Navigate remain separate primary tabs, or collapse into one “Life” surface when route context is inactive?
- Should Today contain the approvals queue inline, or only highlight the next few decisions and hand off to Decisions?
- What is the right mobile threshold for batch-clear actions without reducing trust?
- Which long-tail domains still deserve direct tabs on iPhone after the primary navigation is reduced?
- How should watch, notifications, and live activities mirror the Resume layer without creating a second command model?

## Implementation Guidance

When changing iPhone UI:

1. Start from these mobile command surfaces, not the existing tab list.
2. Preserve production-backed truth from the parity matrix.
3. Prefer silent-first action over decorative status.
4. Treat continuity and resume as first-class product behavior.
5. Keep voice available, but never required.
