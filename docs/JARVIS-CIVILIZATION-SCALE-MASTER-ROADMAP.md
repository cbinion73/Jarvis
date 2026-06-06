# JARVIS Civilization-Scale Master Roadmap

## Purpose

This document connects present-day JARVIS to the full civilization-scale
vision.

It exists to answer five questions clearly:

1. What is JARVIS ultimately becoming?
2. What is already real?
3. What is still missing?
4. What order must the work happen in?
5. How do we avoid drifting back into "assistant" thinking?

This roadmap should be read after:

- `docs/jarvis-canonical-operating-model.md`
- `docs/always-on-agent-backend-blueprint.md`
- `docs/JARVIS-MATURITY-MODEL.md`

If another roadmap or planning document conflicts with this one, this document
wins unless deliberately revised.

## Canonical Frame

JARVIS is not a chat interface, dashboard, or smart-home wrapper.

JARVIS is an always-on orchestrator composed of specialized agents operating on
behalf of a household across time.

Direct interaction is only one operating mode inside a continuously running
system.

The household should experience:

- one governed intelligence layer
- one continuity engine across time
- one institutional memory system
- one command-and-oversight surface for live steering
- one background society of agents doing bounded delegated work

The final category is not "assistant software."

The final category is civilization software for a human life.

## North Star

At civilization scale, JARVIS becomes a governed household intelligence that:

- helps a family close the gap between stated values and lived reality
- preserves institutional memory across years, not sessions
- earns authority through evidence instead of assuming it
- remains inspectable, overridable, and household-operable
- compounds wisdom, continuity, and stewardship across generations

The deepest promise is not convenience.

The deepest promise is:

**you're not carrying this alone**

## Roadmap Doctrine

Everything below this point should obey six non-negotiables.

### 1. Always-on beats reactive

JARVIS must continue useful work when no one is actively using an interface.

### 2. Oversight beats chat

The core user experience is:

- what changed
- what matters
- what is underway
- what needs approval
- what should be redirected

### 3. Governance beats raw autonomy

No expansion of agent authority should outrun supervision, auditability,
rollback posture, or trust boundaries.

### 4. Event truth beats opaque mutable state

Where practical, the event log should become the system ground truth, with
state derived from typed, versioned, replayable history.

### 5. Household-operable beats builder-dependent

The long-term target is not "Chris can operate everything."

It is "the household can benefit from JARVIS directly, at the right level of
responsibility and complexity."

### 6. Earned authority beats assumed authority

The promotion engine is a core civilization primitive.

JARVIS should eventually earn the right to do more by:

- generating evidence
- demonstrating repeatability
- passing review
- crossing explicit consent boundaries

## Load-Bearing Systems

Civilization scale does not come from more features.

It comes from a small set of load-bearing systems becoming real.

### 1. Always-on runtime kernel

JARVIS needs durable agent lifecycle control:

- wake
- run
- pause
- resume
- interrupt
- escalate
- retire

### 2. Event-grounded system truth

JARVIS needs append-only, typed, versioned history for:

- state change
- agent action
- human override
- escalation
- promotion
- failure

### 3. Governed agent society

JARVIS needs a real supervision plane for:

- trust zones
- authority stages
- sandbox vs live execution
- review and escalation
- rollback posture
- doctrine formation

### 4. Institutional memory and continuity

JARVIS needs memory that compounds and is actually used:

- people
- patterns
- rituals
- commitments
- lessons learned
- prior resolutions

### 5. Household command and participation

JARVIS needs product surfaces that make the society visible and steerable:

- command center
- silent-first phone operation
- approvals
- continuity surfaces
- household-safe controls
- role-aware participation

### 6. Promotion and earned authority

JARVIS needs the mechanism that converts track record into bounded authority.

This is the bridge from "sandbox intelligence" to "governed real work."

## Where We Are Now

JARVIS is no longer just a speculative architecture.

It is in the transition from a multi-surface intelligent product to a real
always-on household operating system.

### Already real

- live production stack on Hetzner behind Cloudflare
- deployed Apple contract layer through `/api/apple/*`
- production iPhone app targeting the live hosted environment
- real command surfaces across the major household tabs
- recurring runtime verification discipline
- doctrine for trust zones, sandboxing, staged authority, and governed action
- canonical docs that define JARVIS as an always-on orchestrator
- backend foundations for registry, runtime, routing, supervision, and work
  state

### Emerging but not yet complete

- live shared-state and notification coherence across all surfaces
- full trust-zone control plane implementation
- event-grounded system truth as a first-class primitive
- durable agent-local work state with safe concurrency guarantees
- promotion engine and earned-authority pipeline
- fully household-operable governance and participation
- ambient orchestration that is helpful without becoming noisy

### Current maturity statement

JARVIS today is best described as:

**an emerging household command OS with real doctrine, real runtime truth, and
early agent-society foundations, but not yet a full civilization-scale governed
intelligence environment**

## Phase Map

The phases below are intentionally ordered.

Each phase should make the next one more truthful, not merely more ambitious.

### Phase 0: Unified Runtime

Goal:
Make web, backend, and iPhone behave like one system.

Includes:

- shared truth across surfaces
- Apple contract stability
- deploy and verification discipline
- elimination of split-brain behavior

Current status:

- largely achieved

Exit gate:

- core household flows behave consistently across web and phone

### Phase 1: Household Command OS

Goal:
Make JARVIS indispensable in ordinary family life.

Includes:

- daily brief and command posture
- approvals and staged action
- home-state coordination
- calendar, weather, route, and household posture integration
- systems visibility and sync truth

Current status:

- actively real

Exit gate:

- JARVIS runs a real household day better than the current mix of disconnected
  tools

### Phase 2: Behavioral Depth and Surface Credibility

Goal:
Make the major surfaces behaviorally credible, not just connected.

Includes:

- deeper `Needs`
- richer `Health`
- credible `Chronicle`
- stronger `Navigation`
- broader admin and systems reliability

Current status:

- materially underway

Exit gate:

- the primary phone and web surfaces are believable enough for daily trust, not
  just demos

### Phase 3: Shared-State Intelligence Surfaces

Goal:
Expose the shared-state spine that makes JARVIS feel like one ambient system.

Includes:

- notification workflow
- deeper calendar and reminders state
- focus and interruption posture
- sound and vision histories
- richer systems and admin truth
- inspectable cross-surface continuity

Current status:

- beginning

Exit gate:

- foreground and background state can be surfaced coherently as one running
  system

### Phase 4: Trust-Zone Control Plane

Goal:
Turn doctrine into live execution truth.

Includes:

- trust-zone registry
- authority-stage enforcement
- promotion and demotion actions
- explainability
- audit trails
- escalation boundaries
- bounded rollback posture

Current status:

- doctrine is ahead of implementation

Exit gate:

- every consequential action has explicit authority, scope, escalation, and
  review semantics in code

### Phase 5: Agent Runtime and Event Spine

Goal:
Make the always-on society real in the backend, not just conceptual in docs.

Includes:

- durable runtime kernel
- wake conditions and scheduler fabric
- event bus and event log discipline
- agent inbox, outbox, and worklog state
- cross-agent handoff
- concurrency-safe persistence

Current status:

- foundations exist, but this remains the major structural buildout lane

Exit gate:

- JARVIS can run persistent delegated work safely, explainably, and without
  brittle shared-state corruption

### Phase 6: Ambient JARVIS

Goal:
Make JARVIS proactively useful without becoming intrusive.

Includes:

- watch, phone, car, and home routing
- presence-aware prompts
- quiet warnings
- room-aware and mode-aware delivery
- interruption discipline
- background-to-foreground escalation rules

Exit gate:

- JARVIS helps before being asked while still preserving peace, quiet, and
  trust

### Phase 7: Memory and Continuity Engine

Goal:
Turn JARVIS into the household's second mind.

Includes:

- event-grounded institutional memory
- Chronicle as narrative interface
- retrieval by situation
- lessons learned
- prior resolution recall
- longitudinal household continuity

Exit gate:

- current decisions and long-running work materially improve because JARVIS
  remembers what the household has already lived

### Phase 8: Promotion Engine and Sandbox Agency

Goal:
Let JARVIS earn bounded authority through evidence.

Includes:

- sandbox execution arenas
- proposer and candidate-agent path
- promotion records
- evidence thresholds
- human consent boundaries
- rollback and pause controls

Exit gate:

- JARVIS can independently complete real useful work under governance, with
  authority expanding only through earned track record

### Phase 9: Formation, Stewardship, and Legacy

Goal:
Help the family not just operate, but become.

Includes:

- parenting and growth scaffolding
- health protocol loops
- faith and ritual orchestration
- season-of-life detection
- overload and conflict-risk sensing
- legacy archive
- intergenerational memory bundles
- value-aligned decision simulation

Exit gate:

- JARVIS is helping shape what kind of family this is becoming across years,
  not just what happens this week

## Dependency Rules

The most important sequencing rules are:

1. Do not widen autonomy before the trust-zone control plane is real.
2. Do not trust background multi-agent work without concurrency-safe durable
   state.
3. Do not claim "civilization layer" progress if the household cannot inspect
   and steer the system.
4. Do not let memory become a write-only archive.
5. Do not expand ambient behavior before interruption discipline is solid.
6. Do not confuse surface breadth with civilization depth.

## Immediate Program From Here

The next practical build order should be:

1. finish command-surface credibility and shared-state truth
2. complete the trust-zone control plane
3. complete the agent runtime, event spine, and safe persistence layer
4. make the promotion engine real enough to govern sandbox-to-live progression
5. then broaden ambient and household-operable participation

In concrete terms, the highest-value near-term work is:

- stable shared-state surfaces across phone and web
- permission and governance ownership in real product flows
- live backend contract truth
- concurrency-safe agent state
- event-grounded runtime history
- promotion-engine scaffolding

## What To Avoid

The most common failure modes from here are:

- drifting back into reactive assistant thinking
- shipping ambient behavior before governance
- adding more tabs instead of strengthening shared state
- building autonomy theater without runtime enforcement
- accumulating memory without retrieval or explanation
- letting the product remain builder-operated instead of becoming
  household-operable

## Summary

The build order is deliberate:

1. unify the runtime
2. prove the household command OS
3. deepen the behavioral credibility
4. surface the shared-state spine
5. implement governance as code
6. complete the agent runtime and event spine
7. add ambient intelligence
8. add real memory and continuity
9. add earned authority and sandbox agency
10. become a formation, stewardship, and legacy system

That is the path from "strong household product" to "civilization-scale
intelligence environment."
