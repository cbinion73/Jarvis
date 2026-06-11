# JARVIS Stewardship Lanes v1

## Purpose

This document turns the Interaction Bible into a build-facing first-lane plan.

The full future agent universe remains part of doctrine.

This spec answers a narrower question:

Which stewardship lanes must be alive in v1 so the chamber feels real?

## Core Rule

We are not deleting the future agent universe.

We are sequencing it.

The doctrine keeps the whole horizon visible.
The v1 lane spec defines the first meaningful implementation slice.

## v1 Goal

The first build should prove:

- JARVIS notices meaningful life movement
- JARVIS prepares useful work
- JARVIS surfaces clear decisions
- JARVIS protects household good
- JARVIS feels like one coherent presence

That means v1 should focus on lanes that produce high-value briefings with minimal gimmick risk.

## Lane Selection Principles

A lane belongs in v1 if it satisfies most of these:

- high frequency of relevance
- high leverage on daily burden
- low ambiguity about value
- strong potential for useful preparation
- clear permission boundaries
- visible contribution to the living briefing

## v1 First-Class Stewardship Lanes

### 1. Family Stewardship Lane

Purpose:

- protect household peace
- detect schedule friction
- support dinner, logistics, shared rhythm, and relationship tone

Primary agents inside the lane:

- Pepper
- Family Steward
- Family Chief

v1 responsibilities:

- detect family scheduling friction
- detect dinner-risk windows
- stage family logistics summaries
- stage conversation prep when tone matters
- surface school / pickup / household conflicts

v1 home outputs:

- Family item in the briefing
- one `Needs You` decision when relevant
- one `Drift / Risk` entry when household rhythm is threatened

### 2. Executive and Calendar Lane

Purpose:

- help Chris operate clearly and credibly in work
- reduce meeting friction
- prepare decision frames

Primary agents:

- Herald
- Executive Counsel

v1 responsibilities:

- detect important meetings
- prepare meeting context
- stage decision frames
- draft follow-up posture
- identify overloaded work blocks

v1 home outputs:

- Work item in the briefing
- `Already Working` entry for meeting or deck preparation
- decision entry when a draft needs review

### 3. Watcher and Continuity Lane

Purpose:

- preserve continuity
- detect recurring drift
- hold standing preferences
- connect current work to prior patterns

Primary agents:

- Watcher
- Memory Curator

v1 responsibilities:

- capture durable lessons
- detect repeated friction
- detect unresolved pattern recurrence
- support while-you-were-away summaries
- help the chamber feel like it remembers what matters

v1 home outputs:

- continuity-informed briefing lines
- `Drift / Risk` items
- while-you-were-away report support

### 4. Wealth and Opportunity Lane

Purpose:

- support stewardship of money, opportunity, risk, and passive-income thinking

Primary agents:

- Black Panther
- Opportunity Scout

v1 responsibilities:

- stage passive-income and opportunity briefs
- prepare diligence summaries
- identify risk posture mismatches
- surface household-impact concerns before excitement becomes commitment

v1 home outputs:

- one finance / opportunity item when relevant
- `Needs You` item for approval-gated financial decisions
- occasional `Already Working` item for diligence preparation

### 5. Chamber Operations Lane

Purpose:

- keep JARVIS itself reliable, quiet, and improving without dominating the chamber

Primary agents:

- System Steward
- Autoforge

v1 responsibilities:

- background self-improvement
- runtime health awareness
- quiet completion reporting
- surfacing only meaningful blocked or completed system work

v1 home outputs:

- minimal `Already Working` item when a meaningful maintenance task is active
- quiet completion note when low-risk work was completed
- decision item only when review or approval is genuinely needed

## Secondary v1.5 Lanes

These should remain visible in doctrine but not be treated as first-wave blockers:

- Health Stewardship
- Spiritual Formation
- Creator Commerce
- Builder / Forge
- Scout Operations
- Travel and Adventure

They can exist partially in code, but they should not be required for the first chamber to feel alive.

## Future Universe Preservation Rule

The future agent universe must be preserved in three ways:

1. The Interaction Bible remains canonical.
2. Every new lane should map back to the `What burden does this agent quietly help carry?` rule.
3. New agent ideas should be added through the Agent Discovery Rule, not by ad hoc UI clutter.

## Lane Contract

Every stewardship lane should define:

1. mission
2. primary burden relieved
3. primary agents
4. triggers
5. allowed data sources
6. home-screen output types
7. permission boundaries
8. reporting cadence
9. escalation rules

## Common Output Types

Each lane should emit only a small set of normalized outcomes to the chamber:

- `briefing_item`
- `prepared_work`
- `decision_needed`
- `drift_signal`
- `quiet_completion`
- `blocked_work`

The chamber should render those normalized outcomes, not raw agent payloads.

## While-You-Were-Away Requirements

At least three v1 lanes should contribute to a real `While You Were Away` report:

- Family Stewardship
- Executive and Calendar
- Watcher and Continuity

Optional fourth:

- Chamber Operations

This report should become one of the signature chamber surfaces.

## Council View Requirements

The council view should exist in v1 only as a secondary surfaced mode.

It should support:

- who worked on this
- what each lane noticed
- what each lane prepared
- what is blocked
- what JARVIS recommends after hearing the lanes

It should not become the default home surface.

## Runtime Mapping

Likely existing runtime surfaces to align with these lanes:

- family and household snapshots in [jarvis/runtime.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/runtime.py)
- `merged_calendar_events()`
- `today_board()`
- `unified_open_loops()`
- `assistant_notifications()`
- `work_lifecycle_snapshot()`
- `self_improvement_snapshot()`
- Catalyst opportunity and plan surfaces

## Data Discipline

We should avoid lane-specific one-off UI objects where possible.

Each lane should contribute through shared chamber primitives.

That means:

- briefing lines
- prepared-work cards
- decision cards
- drift cards
- report summaries

This is how we preserve one visible JARVIS presence instead of a visible swarm.

## v1 Success Test

The lane spec is working when:

- Chris opens JARVIS and can see that more than one part of life was being carried
- the home screen feels coherent, not fragmented by domain
- the agents feel real when summoned, not noisy when hidden
- the chamber can produce a convincing `While You Were Away` report
- at least one useful prepared artifact is usually waiting
- at least one recommendation feels wise, not generic

## Next-Lane Expansion Order

After v1, expand in this order:

1. Health Stewardship
2. Spiritual Formation
3. Creator Commerce
4. Builder / Forge
5. Scout Operations
6. Travel and Adventure

That order preserves the chamber’s life-carrying identity before broadening into more specialized capability theater.
