# JARVIS Session State

This file is the persistent working state for the Level-9 advancement
program. Every autonomous session reads it first and updates it before
ending. It records honest, code-verified status — never doc claims.

Last updated: 2026-06-09 (GAP-5 resolved; GAP-2+GAP-3 live on Hetzner)

## Honest Maturity Placement (code-verified 2026-06-09)

- Level 2 (Unified Command Product): COMPLETE
- Level 3 (Household OS): ~80% — all 23 experiences live-backed or honestly
  unavailable (audit of 2026-06-09, commit 6934a70); always-on operation is
  BROKEN on this machine (see GAP-1)
- Level 4 (Governed Intelligence): ~70% BUILT — far ahead of what
  JARVIS-MATURITY-MODEL.md claims. Trust zones, supervision plane,
  promotion engine, sandbox execution, email draft staging, agent registry
  contract all exist in code with enforcement at two choke points and
  negative-path tests
- Level 5 (Ambient): ~40% — event fabric + attention routing + interruption
  posture exist but the fabric only ticks when polled (GAP-2); 4 of 6
  delivery postures implemented (GAP-6)
- Level 6 (Memory/Continuity): ~60% — partitioned memory with enforced
  viewer access, memory genuinely read in chat/briefing context, learning
  review live; retrieval is keyword-match not situation retrieval (GAP-7)
- Level 7 (Formation): ~30% — faith and health loops real; season detection
  missing; daily stewardship loop not routed (GAP-9)
- Level 8 (Bounded Autonomy): ~50% — sandbox execution + promotion engine +
  draft-only email staging real; recursive foundry is a read-only dashboard
  (GAP-8)
- Level 9: not started (correctly blocked on lower layers)

## Current Phase

P2: GAP-1 DONE. Now wiring event fabric (GAP-2) + enforcement seams (GAP-3, GAP-5).

## Gap List (priority order)

### GAP-1 — Always-on assessment [REASSESSED 2026-06-09]
IMPORTANT: JARVIS does NOT run on the Mac. Production is a Hetzner VPS.
Push to main → GitHub Actions → SSH → docker compose up --build jarvis.
Stack: jarvis (FastAPI) + chronicle + ghostwritr + nginx + cloudflared +
postgres + redis. Data persisted in Docker volume jarvis_data at /app/data.
The local launchd fix done earlier this session was irrelevant to production.
Level 3 always-on gate: EVALUATE against Hetzner Docker stack, not local.
The Docker service has restart: unless-stopped — always-on is structurally
met. Actual health depends on the running container on Hetzner.

### GAP-2 — Event fabric is poll-driven, not autonomous [RESOLVED 2026-06-09]
Fixed: added background_cycle() call to AgentScheduler._tick()
(jarvis/scheduler.py:1646). Now every 60s the scheduler drives the event
fabric unattended. Verified: background_state.json, event_bus_events.json,
event_bus_log.jsonl, and runtime_kernel_state.json all updated without any
HTTP poll. 4 new tests in tests/test_scheduler_fabric_tick.py (all pass).
runtime_kernel_events.jsonl only writes on agent lifecycle transitions
(apply_control / record_heartbeat) — correct, not a gap.

### GAP-3 — Supervision is fail-open on exceptions [RESOLVED 2026-06-09]
Fixed approvals.py two sites:
- Staging (request_approval): exception in evaluate_action now raises
  RuntimeError — action is not queued without a ruling.
- Execution (_resolve_supervision_decision): exception falls back to stored
  decision only if stored has an explicit resolution; empty stored → degraded
  block dict (resolution=forbidden, degraded=True).
5 new tests in tests/test_approval_guard_fail_closed.py (all pass).

### GAP-4 — Enforcement is choke-point, not universal [P3]
Supervision/boundary gating happens in ApprovalManager.execute_approved and
~10 assess_action_boundary sites in apple_api.py. Other runtime code paths
are not wrapped. Also enqueue_self_improvement_sandbox_job does not
re-check arena pause status at enqueue time.

### GAP-5 — Governance endpoints lack authn [RESOLVED 2026-06-09]
Fixed three sites:
- GET /api/memory-proposals: requires viewer param, validated via get_actor (403 on unknown)
- POST /api/learning/proposals/{id}: requires viewer in body (422 if missing, 403 if unknown)
- POST /api/apple/governance-proposals/{id}/promote + /dismiss: actor validated via
  get_actor before any business logic (403 on unknown actor)
11 tests in tests/test_governance_authn.py (all pass).

### GAP-6 — Interruption postures incomplete [P4]
_compute_interruption_posture (apple_api.py:2702) implements deliver_now /
badge_only / quiet_store / hold_for_brief. Missing: suppress, escalate.

### GAP-7 — Memory retrieval is keyword-match [P4]
_relevant_profile_facts injects up to 4 facts by keyword relevance into
chat context. Roadmap Phase 7 requires retrieval-by-situation,
lessons-learned, prior-resolution recall.

### GAP-8 — Recursive foundry is read-only [P5]
Only GET /api/foundry/module (dashboard payload). No proposal pipeline,
agent generation, or newborn-agent zone attachment
(JARVIS-RECURSIVE-GROWTH-ARCHITECTURE.md sections 6, APIs /api/foundry/*).

### GAP-9 — Formation gaps [P5]
Season detection: missing entirely (one reflective prompt only).
daily_stewardship.py (morning check-in / evening review / Three Moves) is
wired only via health_scheduler, no HTTP route.

### GAP-10 — SQLite migration not started [P4, optional accelerant]
data/system/jarvis.db does not exist; all core persistence is JSON/JSONL
via jarvis/persistence.py (fcntl flock — real, but no concurrency tests).
JARVIS-DATA-ARCHITECTURE-v1 phases A–D unimplemented.

### GAP-11 — No concurrency/restart tests beyond kernel [P3]
Only runtime kernel has a state-log replay test. No tests for concurrent
writers or multi-process contention on persistence.py.

## Key Verified Facts (do not re-audit)

- Trust-zone registry: jarvis/trust.py (TrustStore/TrustSupport), schemas/
  trust-zone.v1.json + resource-arena + authority-stage; routes
  service.py:8929–8945. REAL.
- Supervision: jarvis/supervision.py evaluate_action:395; decision traces +
  reviews persisted; doctrine formation in jarvis/doctrine.py →
  shared_doctrine.json; consumed for real blocking in approvals.py:994–1031
  and runtime.assess_action_boundary (runtime.py:20081) at ~10 apple_api
  sites. Negative tests in test_approval_guard_supervision.py. REAL.
- Promotion engine: jarvis/promotion.py; routes /api/promotion-* in
  service.py:8949–8993; authority history via trust.py:891. REAL.
- Email staging: draft-only confirmed — Gmail drafts.create only, no send
  capability anywhere in jarvis/. REAL.
- Agent registry contract: verify script passes (exit 0). REAL.
- Runtime kernel: jarvis/runtime_kernel.py, 9 lifecycle states, routes +
  CLI + replay test. REAL (but no events ever fired — see GAP-2).
- Memory: viewer enforcement in memory.py:573–602 applied across review/
  forget/export/overview/profile_facts; personal/restricted excluded from
  cloud context (memory.py:342). Memory IS read in chat context
  (runtime.py:5069–5110). REAL.
- Stewardship lanes: 5 v1 lane contracts bootstrapped in
  supervision.py:160–245 with the 6 normalized output types; route
  /api/stewardship-lanes. REAL.
- While-You-Were-Away: runtime.py:9343, rendered web + apple. REAL.
- First Light: route + truth-posture per section (vocabulary: live/
  interpreted/mixed/connected-empty/unavailable/stale). REAL but barely
  exercised (first_light.json empty).
- web.py is legacy; service.py (FastAPI) is the real server via main.py.
- Stale doc paths: /Users/chris/Desktop/CODE/JARVIS and OneDrive
  CODE/CODE/JARVIS appear throughout docs and in INSTALLED launchd plists.
  Working repo: /Users/chris/Desktop/JARVIS.

## Decisions Made

- 2026-06-09: Maturity true-up performed via three parallel code audits;
  this file is now the placement of record. JARVIS-MATURITY-MODEL.md
  placement section should be revised in a future doc-update seam.

## AWAITING CHRIS

- Home Assistant credentials (HOME_ASSISTANT_URL / HOME_ASSISTANT_TOKEN) —
  blockers.md #1
- Live household entity map (garage/climate/lighting/lock/leak names) —
  blockers.md #3
- Hardware-dependent items: Bambu printer, wake-word/speaker models,
  perception devices, E14 host/NAS/UPS — blockers.md #5–8
- Home Assistant credentials (HOME_ASSISTANT_URL / HOME_ASSISTANT_TOKEN) —
  blockers.md #1 (still needed)
- Live household entity map (garage/climate/lighting/lock/leak names)

## Next 3 Work Items

1. GAP-6: add suppress + escalate postures to _compute_interruption_posture
   (apple_api.py:2702); add delivery decision recording to interruption_decisions.jsonl.
2. GAP-4: enqueue_self_improvement_sandbox_job must re-check arena pause status.
3. Phase 3 Slice 1: wire _event_log.record() into approvals, home commands, nav actions.
