# JARVIS Session State

This file is the persistent working state for the Level-9 advancement
program. Every autonomous session reads it first and updates it before
ending. It records honest, code-verified status — never doc claims.

Last updated: 2026-06-10 (Phase F / Level 9 complete; 1042 tests passing)

## Honest Maturity Placement (code-verified 2026-06-09)

- Level 2 (Unified Command Product): COMPLETE
- Level 3 (Household OS): COMPLETE — Phase A all 10 rows done; home state returns
  source='unavailable' not mock; recovery lifecycle fields (owner/root_cause/
  prevention_note/closure_note); deployment context detects Docker vs local;
  mission audit on closure; lessons_learned field; /api/apple/command-center live;
  exit report at docs/JARVIS-LEVEL3-EXIT-REPORT.md; 687 tests passing
- Level 4 (Governed Intelligence): COMPLETE — Trust zones, supervision plane,
  promotion engine, sandbox execution, email draft staging, agent registry
  contract all exist; all 10 governed action types enforce sequence gating;
  negative-path tests cover deny/stage/allow across all bootstrapped zones;
  canonical action taxonomy (50+ actions, 14 families); fail-closed unknown
  actions; hard boundary families (money/legal/security/identity/children/
  reputation/system) always deny; plain-language household governance UI;
  child safety guard with homework coaching; 72 new B-phase tests; 760 total
- Level 4 runtime: C-phase runtime complete — fail/complete lifecycle states;
  queue idempotency/retry/backoff/dead-letter; zombie recovery on restart;
  scheduler observability (/api/scheduler/health); 52 new C-phase tests
- Level 5 (Ambient): ~90% — event fabric autonomous, all 6 delivery postures
  live, interruption decisions recorded; presence override store live with TTL
  (suppress/escalate/clear via POST /api/apple/presence-override); background→
  foreground push escalation via _maybe_fire_escalation_push() debounced 5 min;
  POST /api/apple/presence-heartbeat writes foreground_active=True with 5-min
  TTL — _choose_delivery_mode upgrades hold_for_brief → badge_only when user
  is actively watching; foreground_active in apple_status() response
- Level 6 (Memory/Continuity): ~60% — partitioned memory with enforced
  viewer access, memory genuinely read in chat/briefing context, learning
  review live; retrieval is keyword-match not situation retrieval (GAP-7)
- Level 7 (Formation): ~60% — faith and health loops real; season now wired
  into Three Moves (LLM prompt + seasonal fallback moves) and daily faith word
  prompt; season field in day card and daily_word result; GAP-9 resolved
- Level 8 (Bounded Autonomy): ~65% — sandbox execution + promotion engine +
  draft-only email staging real; foundry proposals live with governed approve;
  POST /api/trust-zones/{id}/consent-promote unlocks system_agent to sandbox_live;
  full foundry approve flow now executable after human consent promotion
- Level 9 (Capstone): COMPLETE — Phase E (Formation/Autonomy/Domains/Hardware/Infra)
  + Phase F (Level 9 capstone) both done. F1: runtime constitution engine with
  principle citations on every significant recommendation; F2: 9 Level 9 household
  modes (normal/travel/crisis/sabbath/school/health_recovery/guest/sprint/emergency)
  with full behavior contracts (autonomy ceiling, agents, rituals, alerts, tone);
  F3: value simulation across 9 dimensions (time/money/health/faith/family/risk/
  opportunity/reputation/long_term) with dissent/uncertainty/what-would-change-mind;
  F4: legacy archive with permission gating (family/adults_only/chris_only/archive),
  provenance, correction/dispute flow, exportable bundles; F5: long-horizon reviews
  (monthly/seasonal/yearly) with arc summary showing prior lessons changed guidance,
  persistent drift tracking, domain trends; F6: household-operable admin (devices,
  integrations, permissions, audit — no developer tooling required); F7: continuity
  step-based workflows for member/device/role changes with clean audit trail.
  62 new F-phase tests + 5 scenario proofs; 1042 total passing

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

### GAP-4 — Enforcement is choke-point, not universal [PARTIALLY RESOLVED 2026-06-09]
enqueue_self_improvement_sandbox_job now checks arena status at enqueue time.
Reads job.arena_id (falls back to "system.agent-sandbox"). If arena is paused
or suspended: returns accepted=False with arena_id, arena_status, message.
system.agent-sandbox arena bootstrapped in TrustSupport. 9 new tests (all pass).
REMAINING: broader assess_action_boundary coverage across non-apple_api paths
is a separate audit — deferred to Phase B work.

### GAP-5 — Governance endpoints lack authn [RESOLVED 2026-06-09]
Fixed three sites:
- GET /api/memory-proposals: requires viewer param, validated via get_actor (403 on unknown)
- POST /api/learning/proposals/{id}: requires viewer in body (422 if missing, 403 if unknown)
- POST /api/apple/governance-proposals/{id}/promote + /dismiss: actor validated via
  get_actor before any business logic (403 on unknown actor)
11 tests in tests/test_governance_authn.py (all pass).

### GAP-6 — Interruption postures incomplete [RESOLVED 2026-06-09]
Added suppress and escalate postures to _compute_interruption_posture
(apple_api.py:2702). suppress: fires on watch_status.suppress_interruptions=True;
routes non-critical to "suppress", critical to deliver_now. escalate: fires on
watch_status.escalate_interruptions=True OR alert_count >= 3; routes everything
to deliver_now. escalate takes priority over suppress. Added
_record_interruption_decision() helper — appends {ts, item_id, category,
severity, posture_mode, decision, decision_reason} to
data/state/interruption_decisions.jsonl. Wired into all 7 _choose_delivery_mode
call sites in _reconcile_shared_notifications. 16 new tests (all pass).

### GAP-7 — Memory retrieval is keyword-match [P4]
_relevant_profile_facts injects up to 4 facts by keyword relevance into
chat context. Roadmap Phase 7 requires retrieval-by-situation,
lessons-learned, prior-resolution recall.

### GAP-8 — Recursive foundry is read-only [PARTIALLY RESOLVED 2026-06-09]
POST /api/foundry/proposals, GET /api/foundry/proposals,
POST /api/foundry/proposals/{id}/approve all added. Proposals persisted to
data/foundry/proposals.json + proposals_log.jsonl. Approve governed by
assess_action_boundary against system_agent zone + system.agent-sandbox arena.
system_agent trust zone bootstrapped (resolves dangling arena linked_zone_id).
23 new tests all pass.
REMAINING: agent generation and newborn-agent zone attachment require a
Fable 5 architecture session — deferred.

### GAP-9 — Formation gaps [RESOLVED 2026-06-09]
Added GET /api/stewardship/daily (cached day card + season), POST
/api/stewardship/daily/morning (run_morning_checkin), POST
/api/stewardship/daily/complete (run_evening_review). Season derived from
current calendar month via _current_season() — winter/spring/summer/autumn.
16 new tests (all pass).

### GAP-10 — SQLite migration not started [P4, optional accelerant]
data/system/jarvis.db does not exist; all core persistence is JSON/JSONL
via jarvis/persistence.py (fcntl flock — proven safe under concurrency, see GAP-11).
JARVIS-DATA-ARCHITECTURE-v1 phases A–D unimplemented.

### GAP-11 — No concurrency/restart tests beyond kernel [RESOLVED 2026-06-09]
10 concurrency tests added for jarvis/persistence.py: concurrent appenders
(N*M data loss), atomic write correctness under contention, read-during-write
safety, stray .tmp recovery, lock file creation. All pass.

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

## Phase B Audit Findings (2026-06-09)

- All 4 trust levels enforced via assess_action_boundary sequence comparison. REAL.
- Negative paths (unknown zone, inactive zone, unknown/suspended arena) all deny. REAL.
- 8 restricted action types all stage correctly at observe level. REAL.
- Gap documented: action_type=stewardship_lane_review (runtime.py:8957) is NOT in the
  restricted set → allows at any stage level. Low risk for now (read-oriented lane metadata).
- 24 new tests in test_phase_b_trust_boundary_audit.py.

## Next 3 Work Items

1. Level 8 foundry agent generation: when a proposal is approved at sandbox_live,
   the foundry should create an agent stub (zone + supervision contract). This is
   the "newborn-agent zone attachment" described in GAP-8. Requires designing the
   minimal agent spec format and auto-bootstrap flow.
2. GAP-7 (blocked): Memory retrieval by situation — requires Fable 5 design session.
3. Level 5 delivery audit: verify that all 7 _choose_delivery_mode call sites in
   _reconcile_shared_notifications pass posture with foreground_active (they read
   posture from _compute_interruption_posture which now includes it — should be
   automatic, but worth an integration test).

## Phase C Completion Record (2026-06-10)

All 6 Phase C rows complete:
- C1 DONE: Agent lifecycle — added `fail` and `complete` states + control actions
  to runtime_kernel.py; both emit durable JSONL events; `fail_count`,
  `complete_count` tracked per agent; fail sets `requires_attention`; `fail` and
  `complete` in CONTROL_ACTIONS; health_summary handles both new states;
  `failed_agents` count in snapshot summary; 11 new lifecycle tests
- C2 DONE: Queue semantics — `AgentWorkItem` gains `dedupe_key`, `attempt_count`,
  `max_attempts`, `next_attempt_at`; `enqueue()` returns bool and checks item_id +
  dedupe_key idempotency; `dequeue_next()` respects `next_attempt_at` backoff;
  `mark_failed()` returns "retry"/"dead_letter" and implements exponential backoff
  (2^attempt*30s capped at 1h) or moves to `dead_letter` after max_attempts;
  `cancel()` cancels queued items; `get_dead_letter()`, `get_failed()`,
  `get_running()` added; 16 new queue tests
- C3 DONE: Restart survival — zombie recovery on load resets "running" items to
  "queued" (started_at cleared, logged); existing test updated to reflect correct
  behavior; state-log fallback verified; dead-letter survives restart; 5 tests
- C4 DONE: Scheduler observability — `get_status()` now exposes: `last_tick_at`,
  `tick_count`, `running_count`, `dead_letter_count`, `stale_jobs` (items running
  >10min), `unhealthy_agents`, `next_due_work`, `workers_active`, `dead_letter`;
  `_tick()` writes `_last_tick_at` on every call; `GET /api/scheduler/health`
  endpoint with healthy flag; `DELETE /api/scheduler/queue/{item_id}` to cancel;
  `GET /api/scheduler/dead-letter`; 6 new observability tests
- C5 DONE: Data architecture — JSONL persistence round-trips new fields correctly;
  old format without new fields loads with safe defaults (unknown fields stripped);
  state-log fallback verified for both queue and kernel event log; 4 tests
- C6 DONE: Concurrency integrity — concurrent enqueue (N*M items), concurrent
  mark_completed (no double-dequeue), concurrent JSONL append (all valid lines),
  concurrent dedupe_key enqueue (exactly 1 accepted), concurrent mark_failed
  (exactly 1 dead_letter), concurrent kernel event append (all N lines valid);
  6 concurrency tests
New files: tests/test_phase_c_runtime.py (52 tests)
Modified: jarvis/runtime_kernel.py, jarvis/scheduler.py, jarvis/service.py,
          tests/test_scheduler_queue.py (zombie recovery semantics update)
Tests: 812 passing (was 760), no regressions

## Phase B Completion Record (2026-06-09)

All 7 Phase B rows complete:
- B1 DONE: Trust-zone coverage — negative paths for unknown/inactive zone,
  suspended arena, unknown action; 4 tests in TestTrustZoneCoverageNegativePaths
- B2 DONE: Canonical action taxonomy — jarvis/policy_rails.py with 50+ action
  types across 14 families; every entry has risk_tier, approval_mode, family,
  audit_required, reversible; discoverable via list_action_taxonomy()
- B3 DONE: Fail-closed posture — unknown action_type → deny regardless of zone
  stage; assess_action_boundary() passes through to policy_rails for unknown +
  hard boundary checks; original sequence logic preserved for known non-hard actions
- B4 DONE: Promotion engine evidence gating — 7 tests covering hold/promote/
  suspend/pending_consent; min_runs, success_rate, boundary_violations all gate
- B5 DONE: Plain-language governance UI — governance_plain_language_summary()
  returns plain_summary, active/inactive zone counts, per-zone plain labels,
  per-approval plain descriptions; capabilities assessment via assess_action_policy
- B6 DONE: Children/privacy boundaries — ChildInteractionHandler (CHILD_USER_IDS=
  {caleb, anna}); share_child_data + override_child_guardrail always deny;
  all child family actions have parent_review_required; homework coaching response
- B7 DONE: Hard policy rails — spend_money, sign_document, remote_unlock,
  post_social, create_account, change_credentials, submit_filing all deny at every
  authority stage; HARD_BOUNDARY_FAMILIES covers all 7 required families;
  all hard boundary actions have audit_required and reversible=False
New files: jarvis/policy_rails.py; tests/test_phase_b_level4_governance.py (72 tests)
Modified: jarvis/runtime.py (assess_action_boundary fail-closed);
          jarvis/service.py (8 governance routes); jarvis/policy_rails.py (create_account fix)
Tests: 760 passing (no regressions)

## Phase A Completion Record (2026-06-09)

All 10 Phase A rows complete or honestly blocked:
- A1 DONE: _build_deployment_context() in runtime_posture.py; deployment section added
- A2 DONE: Household OS coherence confirmed by prior session work
- A3 DONE: background_cycle() autonomous; event fabric writes every 60s
- A4 DONE: mission_lifecycle audit event on completed/blocked/abandoned; lessons_learned field
- A5 DONE: Agent registry contract passes; 9 lifecycle states; heartbeat/pause/resume/interrupt
- A6 DONE: recovery_cases.py: owner/root_cause/prevention_note/closure_note/close_case()
- A7 DONE: _unavailable_home_state() source='unavailable'; _mock_home_state() deprecated
- A8 DONE: GET /api/apple/command-center with Today/Focus/Family/Decisions/Navigate/Continuity
- A9 BLOCKED: HA code complete; blocked on HOME_ASSISTANT_URL + HOME_ASSISTANT_TOKEN from Chris
- A10 DONE: docs/JARVIS-LEVEL3-EXIT-REPORT.md created
Commits: d936b5ef (Phase A), bbfb3523 (L5 heartbeat), 69534b10 (foreground TTL)
