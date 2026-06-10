# JARVIS Maturity Model

## Purpose

This model shows where JARVIS is today and what maturity levels remain between the current product and the long-horizon vision.

## Level 1: Tool Bundle

Definition:
Separate features, useful in isolation, with limited shared intelligence.

Typical signs:

- tabs or tools that work independently
- little shared state
- little continuity across time
- mostly reactive behavior

JARVIS status:

- past this level

## Level 2: Unified Command Product

Definition:
One product with shared live state and a coherent daily operating surface.

Typical signs:

- one source of truth
- shared contracts across web and phone
- morning command center
- route, weather, home, and approvals coordinated
- core household flows live-backed

JARVIS status:

- >95% complete, but no longer the frontier. This level is maintained while the
  current frontier sits higher.

Evidence:

- production-backed web and iPhone app
- shared Apple contract layer
- live parity work across major tabs
- repeated live device verification

## Level 3: Household Operating System

Definition:
The family can run a real day through JARVIS with reduced need for external tool-hopping.

Typical signs:

- command surfaces are indispensable
- approvals, home, route, focus, reminders, and notifications work together
- daily orchestration is proactive, not only reactive
- the product helps decide what matters now
- background agent work is becoming real, even if still narrow and uneven

JARVIS status:

- ~90% complete, but not yet closed under the current Level 9 completion
  contract.

Gap to close:

- final Navigation parity
- deeper shared-state surfaces
- richer orchestration breadth

## Level 4: Governed Intelligence System

Definition:
JARVIS has real initiative, but it is formally bounded by trust zones, authority stages, and auditability.

Typical signs:

- explicit authority model
- sandbox execution
- explainable action posture
- promotion from draft to live
- escalation boundaries
- durable multi-agent background work with inspectable oversight

JARVIS status:

- ~90% complete and part of the current frontier, with additional closure work
  still required before it can be treated as >95%.

## Level 5: Ambient Household Intelligence

Definition:
JARVIS becomes present across surfaces and helps before being asked, without becoming noisy or invasive.

Typical signs:

- context-aware prompts
- route, weather, home, and household risk alerts
- quiet delivery to the right surface at the right time
- strong interruption discipline
- foreground and background agent focus shift cleanly based on engagement

JARVIS status:

- early signals exist
- not yet unified

## Level 6: Memory And Continuity Engine

Definition:
JARVIS remembers the family in a usable, structured, retrieval-ready way.

Typical signs:

- commitments, patterns, rituals, and lessons are preserved
- Chronicle feeds a broader memory layer
- prior context improves current decisions
- continuity compounds across months and years
- long-running agents work from institutional memory, not just local session state

JARVIS status:

- conceptual groundwork exists
- implementation is still ahead

## Level 7: Formation And Stewardship Platform

Definition:
JARVIS helps improve people and family culture, not only household operations.

Typical signs:

- adaptive tutoring
- parenting and ritual support
- health and formation loops
- values-based stewardship
- season-aware guidance

JARVIS status:

- future level

## Level 8: Bounded Autonomous Operator

Definition:
JARVIS safely executes real work inside governed arenas.

Typical signs:

- publishing operations
- research and synthesis
- draft generation and staging
- low-risk automations
- rollback and pause controls

JARVIS status:

- future level

## Level 9: Family Civilization Layer

Definition:
JARVIS becomes long-horizon infrastructure for identity, continuity, legacy, and flourishing.

Typical signs:

- family constitution in operating logic
- household modes and season detection
- intergenerational memory
- value-aligned decision simulation
- legacy preservation

JARVIS status:

- ~20% (TRUE-UP CORRECTION 2026-06-10). The line below was written before a
  second code-verified audit. HONEST status: the Phase F modules are unintegrated
  data contracts — referenced only in service.py route handlers, with zero
  callers in runtime.py / scheduler.py / apple_api.py / agent code. Setting a
  mode changes a JSON field but does not change runtime behavior. The path to
  real Level 9 is the integration roadmap (Phases G–O) in JARVIS-SESSION-STATE.md.
  Retained verbatim below for audit history:

- Phase F capstone (modules + tests, NOT runtime-integrated) delivered:
  - F1: Constitutional decision engine — every significant recommendation
    cites applicable principle, authority basis, uncertainty level, override path
  - F2: 9 situation-based household modes (normal/travel/crisis/sabbath/school/
    health_recovery/guest/sprint/emergency) — each drives a different behavior
    contract (autonomy ceiling, agents, rituals, alerts, tone, verbosity)
  - F3: Value simulation across 9 dimensions with weighted scoring, dissent,
    uncertainty, and what-would-change-recommendation
  - F4: Legacy archive — permission-gated (family/adults_only/chris_only),
    provenance-backed, correctable, disputable, exportable bundles
  - F5: Long-horizon reviews (monthly/seasonal/yearly) with arc summaries
    showing how prior lessons changed current guidance, persistent drift tracking
  - F6: Household-operable admin — devices, integrations, permissions, audit
    log; no developer tooling required for household members
  - F7: Personnel/device continuity — step-based onboarding/offboarding workflows
    with audit trail and restricted data isolation
  - 62 new tests + 5 scenario proofs (crisis_day, sabbath, child_formation,
    health_recovery, legacy_recall); 1042 total tests passing

## Current Placement

If plotted honestly (code-verified true-up, 2026-06-10 — see
`docs/JARVIS-SESSION-STATE.md` for evidence and the gap list):

- Level 2 solidly real
- Level 3 mostly real; blocked on always-on deployment health, not features
- Level 4 substantially built: trust zones, supervision plane, promotion
  engine, sandbox execution, and draft-only email staging exist in code
  with enforcement and negative-path tests
- Level 5 mostly real: event fabric autonomous, presence heartbeat with TTL,
  foreground escalation, attention routing across all 6 delivery postures
- Level 6 partially built: partitioned viewer-enforced memory genuinely read
  in chat/briefing flows; retrieval is keyword-based, not semantic
- Levels 7–8: faith and health loops real, formation loops live, foundry
  governed approve flow executable, catalyst/executive workflows built
- Level 9: ~20% — constitution engine, household modes, value simulation,
  legacy archive, long-horizon reviews, household admin, continuity workflows
  are implemented as TESTED DATA CONTRACTS but are NOT wired into the runtime
  (no callers outside service.py route handlers). Real Level 9 requires the
  integration roadmap (Phases G–O) in JARVIS-SESSION-STATE.md.

Honest overall placement: solid Level 4, partial Level 5. `docs/JARVIS-SESSION-STATE.md`
is the authoritative source for current percentages, active execution order,
and what is or is not closed today.

## What Must Happen Next

To move from Level 2/3 into Level 4 and beyond:

1. finish remaining parity and shared-state workflow depth
2. implement trust-zone control plane
3. add ambient presence carefully
4. build the memory engine
5. expand into formation and bounded autonomy

That sequence matters because a civilization-scale JARVIS built without governance, continuity, and trust would become powerful before it becomes legitimate.
