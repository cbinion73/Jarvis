# JARVIS Branch Integration Rubric

Use this rubric whenever parallel branches return work to the canonical branch.

This document exists to prevent drift from re-entering through merge pressure.

## Purpose

Parallel branches are useful for speed.

They are dangerous when they:

- redefine the product implicitly
- sneak in conventional assistant assumptions
- optimize a local branch goal while weakening the whole system
- add attractive but non-canonical UI or backend patterns

This rubric defines what gets accepted, what gets rejected, and what must be revised before merge.

## Governing Order

All branch work is subordinate to:

1. `docs/jarvis-canonical-operating-model.md`
2. `docs/JARVIS-CIVILIZATION-SCALE-MASTER-ROADMAP.md`
3. `docs/always-on-agent-backend-blueprint.md`
4. `artifacts/mockups/jarvis-numbered-outline-checklist.html`

If a branch conflicts with those documents, the branch does not quietly win.

## First Pass Questions

Every returning branch must answer these before merge:

1. What exact problem did this branch solve?
2. Which numbered checklist item(s) did it advance?
3. How does this make JARVIS more like an always-on orchestrator?
4. How does this strengthen voice-first, conversation-first behavior?
5. What assumptions does this branch introduce?
6. What downstream branches are affected?

If those answers are vague, the branch is not ready.

## Hard Acceptance Criteria

Branch work should be accepted only if it:

- strengthens the always-on multi-agent operating model
- advances the civilization-scale phase order instead of bypassing it
- preserves oversight, continuity, and delegation as the core user experience
- does not centralize voice as the primary path
- makes ownership, routing, supervision, or command clearer
- adds truthful capability rather than decorative complexity
- keeps the system more governable, not less

## Automatic Rejection Triggers

A branch should be rejected or sent back for revision if it:

- reframes JARVIS as a reactive assistant
- assumes voice is the default path
- introduces generic dashboard UI without command/continuity value
- treats agents like flavor text rather than operational actors
- duplicates ownership across agents without resolving boundaries
- weakens supervision or traceability
- hides important product assumptions in implementation details
- adds complexity without improving command, continuity, or delegated work

## Backend Merge Checklist

For backend-heavy branches, verify:

- lifecycle is durable
- ownership is explicit
- supervision is preserved
- event truth is becoming stronger, not weaker
- escalation boundaries are clear
- work state is inspectable
- event routing is auditable
- resource and attention implications are understood
- the branch does not create silent uncontrolled autonomy

## Frontend Merge Checklist

For frontend-heavy branches, verify:

- the user can understand what changed
- the user can see what matters now
- the user can inspect or steer active work
- silent use is first-class
- voice remains optional and contextual
- the UI does not collapse into cards, tabs, or chat without command value
- desktop and mobile remain one system with different posture

## Branch-Specific Return Format

Every branch should report back in this format:

1. Branch name
2. Files changed
3. Summary of what was added or changed
4. Checklist item(s) affected
5. Assumptions introduced
6. Unresolved questions
7. Validation command(s)
8. Risks or possible drift points

If a branch does not return in this structure, ask for the missing pieces before merge.

## Conflict Resolution Rule

When two branches disagree:

- prefer the interpretation that better supports always-on orchestration
- prefer the interpretation that better preserves roadmap sequencing
- prefer silent-first over voice-first
- prefer explicit ownership over ambiguity
- prefer command/continuity over decorative UI
- prefer governed autonomy over convenience

If still unclear, update the canonical docs first, then merge implementation.

## Merge Order Rule

Prefer merging in this order:

1. canonical docs and operating model updates
2. schemas and registries
3. runtime primitives
4. routing and work-state layers
5. supervision/governance
6. design-system rules
7. desktop/mobile command surfaces
8. real-world integration and infrastructure hardening

## Final Question

Before merging any branch, ask:

Does this make JARVIS more like a governed society of persistent delegated workers acting under user authority?

If not, it is probably drift in disguise.
