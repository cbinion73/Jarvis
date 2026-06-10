# JARVIS Session State

This file is the persistent working state for the Level-9 advancement
program. Every autonomous session reads it first and updates it before
ending. It records honest, code-verified status — never doc claims.

Last updated: 2026-06-10 (TRUE-UP CORRECTION — honest placement is Level 4
solid / Level 5 partial; Level 9 roadmap added as Phases G–O; 1042 tests passing)

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
### TRUE-UP CORRECTION (2026-06-10)

A second code-verified audit found the prior "Level 9 COMPLETE" claim does not
meet this program's own completion standard ("a row is complete only when the
behavior has code, persistence, governance, tests, RUNTIME PROOF, and honest
user-facing state"). The Phase E/F modules are well-built, well-tested DATA
CONTRACTS that are NOT wired into the runtime.

KEY EVIDENCE: ConstitutionEngine, Level9ModeManager, ValueSimulationEngine,
LegacyArchiveStore, LongHorizonStore, HouseholdAdminStore, and ContinuityStore
are referenced ONLY in service.py route handlers. Zero references in runtime.py,
scheduler.py, apple_api.py, or any agent code. Setting mode="crisis" writes a
JSON field but does NOT suspend an agent, change TTS, or reroute a notification.
constitution_engine.cite() has zero production callers. There are TWO unrelated
mode systems (family_profiles.build_household_modes time-of-day + Level9ModeManager
situation) that do not talk to each other.

HONEST PLACEMENT (code-verified 2026-06-10):

- Level 2 (Unified Command Product): COMPLETE
- Level 3 (Household OS): COMPLETE* (*home/safety blocked on HA credentials)
- Level 4 (Governed Intelligence): COMPLETE — trust zones, supervision,
  promotion, fail-closed, hard policy rails all wired into real decisions
- Level 5 (Ambient): ~70% — event fabric/presence/interruption real; voice
  full-duplex, noise-learning feedback, proactive orchestration partial
- Level 6 (Memory/Continuity): ~45% — viewer enforcement real; situational
  retrieval is keyword-match, provenance/correction/Chronicle-narrative not built
- Level 7 (Formation): ~45% — health/faith STORES exist + season wired to Three
  Moves; per-person/per-mode dynamic adaptation not driving real cards
- Level 8 (Bounded Autonomy): ~50% — sandbox + foundry proposal/approve real;
  agent GENERATION, real end-to-end automation, rollback-before-exec not running
- Level 9 (Family Civilization): ~20% — data contracts + API surface exist;
  ~zero runtime integration; no household-facing UI for legacy/admin/reviews

OVERALL: solid Level 4, partial Level 5. The path to Level 9 is dominated by
INTEGRATION (wiring existing modules into real decision paths), not new modules.
See "Level 9 Completion Roadmap (Phases G–O)" below.

## Current Phase

PHASE G — Level 9 Runtime Integration. The unblocker phase: make existing
modes/constitution/value-sim actually drive behavior. See roadmap below.

---

# Level 9 Completion Roadmap (Phases G–O)

Goal: every maturity level ≥90% complete, code+test+RUNTIME-PROOF verified,
culminating in Level 9. Each row follows the existing Completion Standard
(code path, UI/API path, persistence, governance, negative tests, runtime
proof, truth labels, docs-last). A row is DONE only when a real decision,
notification, agent action, or rendered surface CHANGES because of it — not
when a store persists or an API returns 200.

## The Integration Doctrine (why G–O differ from A–F)

Phases A–F built data contracts and API surfaces. They are the right
foundation. But the modules sit beside the runtime, not inside it. Phases G–O
are dominated by WIRING those modules into real decision paths
(runtime.assess_action_boundary, scheduler._tick, apple_api delivery routing,
memory.py write/read paths, briefing/Three-Moves composition) plus the genuine
net-new work for Levels 5–8. "Wire X into Y" means Y reads X and Y's output
provably changes; prove it with an integration test that asserts the downstream
effect, not the store contents.

## Dependency ordering

- G is the unblocker (runtime wiring) — MUST come first; everything leans on it.
- H, I, J, K parallelize after G lands.
- L (civilization layer) depends on G + I.
- M (household UX) depends on G–L surfaces existing.
- N (infra/hardware) partially blocked on Chris (HA creds, devices).
- O (scenario proofs) is the final exit gate; runs against the integrated stack.

---

## Phase G — Level 9 Runtime Integration  [unblocker; lifts L9 20%→55%]

- [ ] G1  scheduler reads current mode; agents in `suspended_agents` are actually
      paused and `required_agents` actually run. Proof: set crisis → scheduler
      tick shows workshop-copilot paused; integration test asserts paused state.
- [ ] G2  notification routing honors mode `notification_level` + `alert_domains`
      + `suppress_domains`. Proof: sabbath → non-critical item routed to suppress;
      test asserts delivery decision changes vs normal mode.
- [ ] G3  `assess_action_boundary` caps requested stage at the active mode's
      `autonomy_ceiling`. Proof: sabbath (monitor) blocks a sandbox_live action
      that normal mode would allow; negative test proves the cap.
- [ ] G4  unify the two mode systems — `family_profiles` time-of-day modes and
      `Level9ModeManager` situation modes resolve through ONE precedence function
      (situation overrides time-of-day). No split-brain mode state anywhere.
- [ ] G5  mode drives TTS enablement + briefing posture (verbosity/briefing_style).
      Proof: sabbath sets tts_enabled=False and briefing=off in the real briefing
      composer, not just the contract.
- [ ] G6  `constitution_engine.cite()` wraps every significant recommendation
      produced in runtime (Three Moves, value-sim output, mission proposals,
      foundry approvals). Proof: a real recommendation response carries a
      constitutional_citation with principle + authority + override path.
- [ ] G7  `value_simulation` is invoked for real multi-option decisions and the
      recommendation/dissent/uncertainty surfaces in a response. Proof: a decision
      prompt returns ranked options with what-would-change-my-mind.
- [ ] G8  mode auto-exit triggers fire (max_duration_hours, location_home,
      time-based) via scheduler. Proof: crisis auto-expires after its window in a
      time-advanced test; transition audited.

## Phase H — Level 5 Ambient completion  [70%→≥90%]

- [ ] H1  voice full-duplex loop: wake → listen → speak → interrupt → resume,
      proven across browser + iPhone with clear fallback. Integration/e2e proof.
- [ ] H2  Siri / App Intents launch JARVIS conversation into the in-app engine
      with context continuity (Siri starts it, JARVIS owns the thread).
- [ ] H3  CarPlay driving-safe loop proven end-to-end: route-aware, constrained
      action set, no broad non-driving workflows. Safety negative tests.
- [ ] H4  noise-learning feedback: useful / noisy / wrong-time / wrong-surface /
      missed-urgency feedback recorded AND future routing adapts while safety
      overrides remain intact. Proof: feedback changes a later delivery decision.
- [ ] H5  proactive prompt orchestration: combine calendar+weather+route+home+
      health+approvals+presence+mode into one timely prompt with why-now,
      confidence, source facts, actions, snooze/dismiss, and an audit event.

## Phase I — Level 6 Memory completion  [45%→≥90%]

- [ ] I1  situational retrieval replaces keyword match: retrieve by person,
      domain, current task, unresolved loop, prior resolution, season,
      relationship, lesson — and explain WHY each memory was selected.
- [ ] I2  provenance on every durable memory: observed fact / instruction /
      inference / tentative pattern / approved belief / retired belief, plus
      source, owner, subject, sensitivity, access policy, review state.
- [ ] I3  correction loop wired into reasoning: correct / dispute / retire /
      supersede / "do-not-use-in-reasoning" — a corrected/retired memory is
      provably EXCLUDED from future decision context. Negative test required.
- [ ] I4  Chronicle becomes the narrative memory layer: explains patterns,
      rituals, decisions, milestones, and why JARVIS thinks they matter;
      inspectable with source + impact + correction options.
- [ ] I5  `chronicle_boundary` wired into memory.py WRITE path: faith-tagged
      content routes to Chronicle and is BLOCKED from JARVIS memory. Negative
      test proves a faith write to JARVIS memory is rejected.

## Phase J — Level 7 Formation completion  [45%→≥90%]

- [ ] J1  `health_loop` wired into morning briefing + Three Moves (check-in
      history actually shapes the day card and the moves).
- [ ] J2  `ritual_loop` wired into daily card + formation guidance; a prayer/
      study item is captured, resurfaced when stale, reviewed, and influences
      later guidance.
- [ ] J3  `AdaptationContextBuilder` drives real per-person / per-mode /
      per-season formation cards that DIFFER appropriately and cite their inputs.
- [ ] J4  parenting/tutoring child-safe loop with parent-review boundaries, wired
      so child-facing guidance obeys permissions and is inspectable/correctable.
- [ ] J5  doctor packet generated from real accumulated check-in history (not an
      empty/unavailable shell) once ≥N days of data exist.

## Phase K — Level 8 Autonomy completion  [50%→≥90%]

- [ ] K1  foundry agent GENERATION: an approved proposal at sandbox_live creates
      a real agent stub with role, mission, zone, arena, memory/tool scope, and
      authority — the GAP-8 newborn-agent attachment.
- [ ] K2  newborn-agent lifecycle: evaluate → promote or retire with audit;
      authority cannot expand without recorded evidence.
- [ ] K3  one REAL end-to-end automation runs under governance:
      research → synthesis → draft → review → approval → publish/stage, with
      evidence, approval gate, rollback, and a success record.
- [ ] K4  `executive_workflow` routes real Catalyst work (strategy/writing/
      pipeline/publishing/growth) with inspectable state, approvals, handoffs.
- [ ] K5  `sandbox_rollback` wired BEFORE sandbox job execution: a rollback packet
      (pre-state + reverse instructions) is captured pre-run and is replayable.

## Phase L — Level 9 Civilization completion  [55%→≥90%]  (needs G + I)

- [ ] L1  `long_horizon` reviews auto-triggered by scheduler (monthly/seasonal/
      yearly); arc summary surfaces and demonstrably shows how prior lessons
      changed current guidance.
- [ ] L2  `legacy_archive` household-browsable: a family member can add, view,
      and correct legacy entries through a real surface (not raw API), with
      permission gating enforced in the UI.
- [ ] L3  `continuity` workflow steps EXECUTE real effects (create profile, set
      permission, revoke token, migrate memory) — not string-shuffling. Restricted
      memory provably not exposed during a role/device change.
- [ ] L4  `household_admin` household-facing control panel: pause/approve/demote/
      revoke agents, modes, permissions, devices, integrations — no file edits,
      JSON, or scripts.
- [ ] L5  long-arc guidance proof: a recommendation THIS period visibly differs
      because of a lesson recorded in a PRIOR review (end-to-end, not unit-mocked).

## Phase M — Household UX layer  [non-developer operability]  (needs G–L)

- [ ] M1  mode switcher UI (set/inspect/auto-exit visibility).
- [ ] M2  decision-citation surface: "why did JARVIS recommend this" shows the
      constitutional principle, authority basis, uncertainty, override path.
- [ ] M3  value-simulation comparison UI (options ranked, dissent, change-my-mind).
- [ ] M4  legacy / admin / continuity / long-horizon-review surfaces usable by
      a non-developer household member.
- [ ] M5  plain-language control panel: what JARVIS can do, what it did and why,
      and a one-tap pause — household-operable safety.

## Phase N — Infrastructure + Hardware  [partially BLOCKED on Chris]

- [ ] N1  Home Assistant: real credentials + garage/climate/light/lock/leak entity
      map → home/safety/modes live with audit + no voice-only unlock.
      **BLOCKED on HOME_ASSISTANT_URL / HOME_ASSISTANT_TOKEN + entity map.**
- [ ] N2  SQLite / hybrid index for active state (GAP-10): queryable, concurrency-
      safe, migratable, while raw audit/artifact JSONL is preserved.
- [ ] N3  perception feeds (porch/garage/room presence/phone arrival) + privacy
      governance. **BLOCKED on perception hardware.**
- [ ] N4  workshop devices (Bambu/resin/Cricut): device status, job staging,
      safety checks, handoff. **BLOCKED on device network access.**
- [ ] N5  always-on host / NAS / UPS / segmented network / voice+perception edges.
      **BLOCKED on hardware procurement.**

## Phase O — End-to-end Level 9 scenario proofs  [final exit gate]

Each scenario must pass END-TO-END (UI → API → memory → governance → event →
audit → restart), not as an isolated store unit test:

- [ ] O1  crisis day — mode flips, autonomy drops, only critical breaks through,
      everything audited, survives restart.
- [ ] O2  travel week — travel mode, location-aware routing, home monitoring
      reduced, auto-exit on return.
- [ ] O3  child formation — child-safe tutoring/ritual with parent review,
      permission-gated, correctable.
- [ ] O4  health recovery — value-sim routes toward rest, health loop drives
      briefing, demands reduced.
- [ ] O5  legacy recall — permissioned legacy bundle browsable/exportable; child
      blocked from adults_only content end-to-end.
- [ ] O6  automation — one real automation completes under governance with
      evidence + approval + rollback.
- [ ] O7  correction — a wrong memory is corrected and provably excluded from a
      later decision.
- [ ] O8  governance pause — household pauses an agent mid-run; state recovers
      cleanly with audit, no corruption.

## Level 9 EXIT GATE (all must be TRUE before any "Level 9" claim)

1. Every level ≥90% with code + test + runtime proof (not store/API-only).
2. Active mode provably changes scheduler, notifications, autonomy ceiling, TTS.
3. constitution_engine cites REAL recommendations in the runtime.
4. Situational memory retrieval live; corrected memories excluded from reasoning.
5. At least one real automation completes end-to-end under governance.
6. Household-operable UI for modes, admin, legacy, reviews (non-developer).
7. Phase O scenario suite passes end-to-end WITH restart survival.
8. Docs updated ONLY after proof (docs-last rule honored).

---

## Legacy Current-Phase note (pre-true-up)

P2: GAP-1 DONE. Event fabric (GAP-2), enforcement seams (GAP-3, GAP-5) resolved.

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
