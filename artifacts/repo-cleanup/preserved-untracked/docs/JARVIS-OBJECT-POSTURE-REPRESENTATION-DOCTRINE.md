# JARVIS Object Posture Representation Doctrine

## Purpose

JARVIS is not composed of pages.

JARVIS is not composed of applications.

JARVIS is not composed of screens.

JARVIS is composed of:

- objects
- postures
- representations
- workspaces

The purpose of this doctrine is to define how JARVIS dynamically generates user
experiences from those elements.

Read this after:

- `docs/JARVIS-LIFE-OPERATING-OFFICER.md`
- `docs/jarvis-canonical-operating-model.md`
- `docs/JARVIS-ARRIVAL-AND-CONVERSATION-WORKSPACE-DOCTRINE.md`
- `docs/JARVIS-SESSION-STATE.md`

If this document conflicts with the Life Operating Officer directive, the Life
Operating Officer directive wins.

## Core Principle

Traditional software:

`Object -> Screen`

JARVIS:

`Intent -> Object -> Posture -> Representation -> Workspace`

The object remains stable.

The posture changes.

The representation adapts.

The workspace emerges.

## Laws

### Law 7

Objects are persistent.

Representations are transient.

A Mission remains.

A Person remains.

A Relationship remains.

A Project remains.

The representation shown to Chris changes continuously.

### Law 8

The same object should reveal different truths under different postures.

Builder reveals possibility.

Operator reveals progress.

Advisor reveals tradeoffs.

Chief of Staff reveals state.

Steward reveals delegated responsibility.

Companion reveals meaning.

### Law 9

No object should require a dedicated application.

If an object requires its own permanent application, the doctrine has failed.

## Core Object Classes

These objects are examples of the stable substrate from which JARVIS generates
representations and workspaces.

### Person

Examples:

- Chris
- Rebekah
- Caleb
- Anna
- Jonathan

### Mission

Examples:

- Lose 40 Pounds
- Summer Camp
- Publish Book
- Retirement Planning

### Relationship

Examples:

- Marriage
- Parent Child
- Professional
- Friendship

### Project

Examples:

- JARVIS
- Workshop Expansion
- Thermo Fisher Initiative

### Asset

Examples:

- House
- Pool
- 3D Printer
- Vehicle
- Investment Account

### Place

Examples:

- Home
- Workshop
- Office
- Church

### Event

Examples:

- Summer Camp
- Meeting
- Vacation
- Appointment

### Goal

Examples:

- Weight Target
- Financial Target
- Spiritual Goal

### Document

Examples:

- Book Manuscript
- SOP
- Plan
- Research Notes

### Idea

Examples:

- Business Concept
- Product Concept
- Writing Concept

## Posture Definitions

Postures are not destinations.

Postures are lenses.

They determine how an object should reveal itself in the current moment.

### Builder

Question:

`What are we creating?`

Reveals:

- possibility
- structure
- planning
- relationships
- future state

Emotion:

- optimism
- expansion
- momentum

### Operator

Question:

`What must happen next?`

Reveals:

- tasks
- progress
- blockers
- execution
- dependencies

Emotion:

- movement

### Advisor

Question:

`What should I do?`

Reveals:

- comparisons
- tradeoffs
- recommendations
- risks
- forecasts

Emotion:

- clarity
- confidence

### Chief of Staff

Question:

`What do I need to know?`

Reveals:

- status
- readiness
- priorities
- opportunities
- risks

Emotion:

- orientation
- control

### Steward

Question:

`What can I stop thinking about?`

Reveals:

- monitoring
- delegated responsibility
- active watches
- exception handling

Emotion:

- relief
- trust

### Companion

Question:

`What does this mean?`

Reveals:

- narrative
- context
- memory
- reflection
- continuity

Emotion:

- presence
- relationship
- meaning

## Representation Rules

Every representation should answer the primary question of its posture.

Do not show Builder information in Advisor posture unless needed.

Do not show Operator information in Steward posture unless requested.

Representations should be posture-specific, not object-specific.

The same object may generate radically different representations without
becoming a new screen, new app, or new destination.

### Example: Summer Camp Mission

Builder representation:

- goals
- structure
- timeline
- people
- resources

Operator representation:

- tasks
- progress
- readiness
- blockers

Advisor representation:

- transportation options
- budget tradeoffs
- recommendations

Chief of Staff representation:

- readiness score
- risks
- upcoming deadlines

Steward representation:

- monitoring
- exceptions
- delegated activities

Companion representation:

- historical context
- lessons learned
- narrative summary

## Workspace Materialization

Workspaces do not exist permanently.

Workspaces emerge from:

`Object + Posture + Context`

The same object may generate different workspaces depending on the active
posture stack.

The workspace should feel materialized rather than navigated to.

Workspaces should exist because the conversation, recommendation, question, or
decision requires them.

They should not exist because a permanent product section has to be filled.

## Posture Stacking

A conversation may invoke multiple postures.

Example:

`Am I ready for summer camp and should I rent a trailer?`

Primary:

- Chief of Staff

Secondary:

- Advisor

Tertiary:

- Operator

The workspace should flow through those representations.

Do not force a hard posture switch.

Do not require a mode selector.

The user should feel the system moving through orientation, understanding,
decision, action, and stewardship naturally.

## Persistence Rules

Persistent:

- objects
- relationships
- memory
- mission state
- watches

Transient:

- representations
- workspace layouts
- recommendations
- comparisons
- operational views

The same underlying object should survive many conversations, many postures,
and many workspaces.

Only the manifestation should change.

## Anti-Patterns

Do not create:

- Health App
- Finance App
- Workshop App
- Publishing App
- Calendar App

These are object collections, not applications.

Do not create:

- posture-specific pages

Do not create:

- Builder Screen
- Advisor Screen
- Steward Screen

Postures influence representation.

They are not destinations.

If developers begin building permanent interfaces around domains or postures,
the doctrine has drifted.

## Ultimate Test

When a new feature is proposed, ask:

1. Is this a new object?
2. Is this a new posture?
3. Is this a new representation?
4. Or is it accidentally becoming a new application?

If it is becoming a new application, stop and redesign.

The goal is not to build apps.

The goal is to build a living operating system that continuously reshapes
itself around intent.

If Vision, Arrival Doctrine, and Object Posture Representation Doctrine are
correct, then the interaction model is defined.

After that, Glass Theme, MUI implementation, workspace engine, and agent
orchestration become implementation details rather than philosophical debates.
