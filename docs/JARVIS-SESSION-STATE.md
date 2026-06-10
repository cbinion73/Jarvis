# JARVIS Session State

This file is the persistent working state for the Level-9 advancement
program. Every autonomous session reads it first and updates it before
ending. It records honest, code-verified status — never doc claims.

Last updated: 2026-06-10 (Phase 0 truth report landed; master plan active)

## Current Maturity Placement

This section is now the placement of record until replaced by a later
code-verified true-up.

| Level | Current realistic state | Target for Level 9 program |
|---|---:|---:|
| Level 1: Tool Bundle | Retired | Retired |
| Level 2: Unified Command Product | >95% | Maintain >95% |
| Level 3: Household Operating System | ~90% | >95% |
| Level 4: Governed Intelligence System | ~90% | >95% |
| Level 5: Ambient Household Intelligence | ~70% | >95% |
| Level 6: Memory and Continuity Engine | ~45% | >95% |
| Level 7: Formation and Stewardship Platform | ~45% | >95% |
| Level 8: Bounded Autonomous Operator | ~50% | >95% |
| Level 9: Family Civilization Layer | ~20% | >95% |

Overall placement: solid Level 4, partial Level 5. The next program is not a
new mockup pass. It is a runtime integration, real-provider, hardware, memory,
formation, autonomy, proof, and docs-truth program.

## Level 9 Completion Contract

No row below is DONE because a module exists, an API returns 200, a doc says it
is designed, or a test uses only isolated stores. A row is DONE only when all
applicable proof exists:

- Code path: the runtime/client/server behavior exists in the real app.
- UI/API path: a household user or operator can reach it without debug steps.
- Persistence: state survives restart and deploy.
- Governance: actor, authority, policy, audit, rollback, and child/privacy rules
  apply wherever the action is consequential.
- Negative tests: unauthorized, stale, missing, unsafe, invalid, and external
  failure paths are proven blocked or truthfully unavailable.
- Runtime proof: at least one integration/e2e/smoke proof shows downstream
  behavior actually changes because of the feature.
- Truth labels: live, stale, cached, inferred, unavailable, blocked, and
  externally-blocked are not blurred together.
- Production proof: hosted Hetzner/Cloudflare deployment is verified when the
  feature is meant to be live.
- Docs last: maturity claims are updated only after the proof exists.

Target: every maturity level from 2 through 9 must clear >95% by this standard.

## Autonomous Execution Contract

This contract governs all future autonomous Codex runs.

### Source of Truth

`JARVIS-SESSION-STATE.md` is the authoritative execution document.

If roadmap docs, maturity docs, checklists, prompts, comments, or prior
reports conflict with this file, this file wins.

Read this file before any work begins.

### Unattended Execution

Chris may be unavailable.

Do not stop to ask questions.

Do not wait for clarification.

Make the best safe engineering decision from the codebase, tests,
architecture, and documentation.

If work requires:

- credentials
- provider access
- hardware
- entitlement approval
- production approval
- destructive migration
- mature-live consent

then:

1. mark `EXTERNALLY BLOCKED`
2. record exact dependency
3. add setup path if appropriate
4. add truthful unavailable state
5. add tests where possible
6. continue other work

### Completion Contract

A row is NOT complete because:

- an API exists
- a store exists
- a route exists
- a document exists
- a mock works
- a unit test passes

A row IS complete only when applicable proof exists:

- code path
- UI/API path
- persistence
- governance
- negative tests
- runtime proof
- truthful states
- production proof (when applicable)

Runtime behavior must actually change.

### Execution Loop

For every task:

`evaluate -> inspect code -> implement -> test -> integration proof -> fix ->
retest -> commit -> docs last`

Never update maturity claims before proof exists.

### Safety Rules

Never:

- hard-code secrets
- fake providers
- fake hardware
- fake production state
- fake integrations
- fake maturity

Truthful unavailable states are preferred over simulated success.

### Git Rules

Check `git status` first.

Do not discard user work.

Commit passing work frequently.

Use coherent commit messages.

Avoid large uncommitted diffs.

Before stopping:

- commit passing work
- update session state
- record resume point

### Deployment Rules

For low-risk completed work:

1. commit
2. push
3. allow deployment pipeline to run
4. verify deployment
5. verify affected routes
6. record proof

For risky changes involving:

- credentials
- identity
- finances
- provider writes
- destructive migrations

stop at tested commits and mark blocked.

### Testing Requirements

Add:

- integration tests
- negative tests
- restart-survival tests
- permission tests
- governance tests

Run the broadest feasible suite.

Fix regressions before proceeding.

### Maturity Scoring

Optimize for honest maturity percentage, not checklist count.

Priority:

1. Truth/Baseline
2. Memory & Continuity
3. Bounded Autonomy
4. Civilization Layer
5. Ambient Intelligence
6. Formation & Stewardship
7. Providers
8. Proof Systems

### Stop Condition

Stop only when:

- blocked by external dependency
- blocked by failing tests
- blocked by context limits

Before stopping:

- commit passing work
- update session state
- leave exact resume point

Format:

`Resume from LEVEL __ TASK __ using JARVIS-SESSION-STATE.md`

## External Blockers

These do not count as product-complete until connected, but they may be marked
EXTERNALLY BLOCKED if JARVIS provides a safe adapter, a precise unavailable
state, tests, and an operator-facing setup path.

Scoring rule: if a dependency is not yet procured, connected, or consented,
and JARVIS already exposes a truthful unavailable/setup state, it stays in the
plan but is excluded from the maturity denominator until the household decides
to bring it into scope.

- Home Assistant: future integration hub if the household adopts it. Keep in
  the plan, but exclude from maturity scoring until Chris chooses Home
  Assistant or another unified home-control authority for JARVIS.
- Perception: requires real camera/presence/audio hardware and privacy rollout.
  Keep in the plan; exclude from maturity scoring until the hardware exists.
- Workshop: requires reachable Bambu/Cricut/workshop device network access.
  Keep in the plan; exclude from maturity scoring until the devices exist.
- Always-on household footprint: Hetzner currently satisfies the real hosted
  always-on requirement. A future local host/NAS/UPS/network footprint remains
  in the plan as a local-first resilience upgrade, not a current maturity blocker.
- CarPlay navigation depth: may require entitlement approval for deeper
  route/navigation behavior.
- Provider credentials: Google, Microsoft, Dexcom, Plaid, KDP, Weather, and
  other providers must be configured with real tokens; missing tokens must not
  produce fake data.

# Master Level 9 Completion Plan

## Phase 0: Truth, Baseline, And Program Control

Goal: remove contradiction from status claims and create one living execution
view for getting all levels above 95%.

- [x] T0.1 Replace stale "Level 9 complete" language with this master plan.
- [x] T0.2 Create a machine-readable level scorecard artifact with level,
      percent, evidence links, open blockers, last verification date, and owner.
- [x] T0.3 Add a verification command that reports local, GitHub, deployed,
      Cloudflare, Docker, data-volume, and provider truth separately.
- [x] T0.4 Add a docs-truth check that fails when session state, maturity model,
      roadmap, Level 9 checklist, and exit reports conflict on current level.
- [x] T0.5 Add a "no fake data" audit command for connectors, local caches,
      rendered summaries, fixtures, and development-only fallbacks.
- [x] T0.6 Establish the current proof ledger: tests run, e2e status, live
      provider status, production revision, and unresolved failures.
- [x] T0.7 Define the rule that any future autonomous run updates this file only
      after code/test/runtime proof changes.

Proof landed 2026-06-10:

- `python3 scripts/verify_level9_truth.py --output artifacts/qa/level9-truth-report.json`
- `python3 scripts/verify_docs_truth.py`
- Artifact: `artifacts/qa/level9-truth-report.json`
- Tests:
  - `python3 -m pytest tests/test_verify_level9_truth.py tests/test_truthful_seed_filtering.py tests/test_data_connectors.py -q`
  - `python3 -m pytest tests/test_verify_docs_truth.py tests/test_verify_level9_truth.py -q`
- Current unresolved truth findings from the artifact:
  - provider battery is now classified as `environment-limited` rather than a
    product failure when the local report only shows a runner fetch error
    against `127.0.0.1:8787` with zero executed checks
  - no-fake-data audit now reports `warn`, not `fail`: zero runtime-exposed
    seeded findings, with remaining seeded/QA records classified as
    filtered-at-read backing data
  - proof ledger unresolved failures are now empty in the local truth artifact
  - live deployed / Cloudflare truth remains explicitly unverified in local sandbox runs

Exit gate: the team can answer "what level is JARVIS today?" from one artifact,
and that answer matches code, tests, deployment, and docs.

## Phase 1: Level 2 And Level 3 Final Closure (>95%)

Goal: keep the unified command product real while closing the remaining
household-day gaps and external-provider honesty gaps.

- [ ] L3.1 Verify every primary experience route still loads locally and on the
      hosted stack: Daily Brief, Command, Needs You, Legacy, Faith, Agents,
      Intel, Forge, Catalyst, Workshop, Publishing, Huddle, Health, Dining,
      Navigate, Journey, Vision, Foundry, Home, Calendar, Email, News, Social.
- [ ] L3.2 Replace any remaining cached/static/sample summaries with connector
      output or an honest unavailable state.
- [ ] L3.3 Make provider status visible per module: Google, Microsoft, Dexcom,
      Plaid, KDP, Weather, News, Home Assistant, Chronicle, Ghostwritr, HA.
- [ ] L3.4 Close calendar/email/news/social truth gaps so disconnected states
      never render as real household activity.
- [ ] L3.5 Connect Home Assistant when credentials and entity map are available;
      until then, keep home/safety explicitly unavailable with exact blocker.
- [ ] L3.6 Make all daily-operating actions round-trip through the activity
      spine: approvals, missions, health, calendar, email, navigation, home,
      provider sync, recovery, and agent work.
- [ ] L3.7 Add route/app launch checks for all primary experiences to the e2e
      battery with screenshots and console/network-noise assertions.
- [ ] L3.8 Prove a realistic household day: morning brief, calendar, weather,
      route, health check-in, approval, mission update, provider sync, evening
      review, restart, and recovery.
- [ ] L3.9 Update `JARVIS-LEVEL3-EXIT-REPORT.md` only after the above live proof.

Exit gate: JARVIS can run a normal household day without fake data, unexplained
fallback, missing state, or split-brain web/iPhone behavior.

## Phase 2: Level 4 Governance Final Closure (>95%)

Goal: make governance universal, understandable, and fail-closed across every
consequential action path.

- [ ] L4.1 Audit every mutation route, Apple contract mutation, agent action,
      connector write, sandbox job, home action, financial action, memory write,
      publishing action, and provider sync for trust-zone enforcement.
- [ ] L4.2 Route every consequential action through one action taxonomy with
      family, risk tier, minimum authority, reversibility, audit requirement,
      approval mode, and hard-boundary flag.
- [ ] L4.3 Make unknown, under-classified, unauthenticated, suspended-zone,
      paused-arena, and failed-policy cases fail closed everywhere.
- [ ] L4.4 Add negative-path tests for money, legal, identity, security,
      children, reputation, public publishing, home control, credentials, and
      system mutation.
- [ ] L4.5 Build household-readable governance views for capabilities,
      blocked attempts, pending approvals, authority changes, agent scope, and
      rollback posture.
- [ ] L4.6 Add child/privacy product flows: parent review, child-safe memory,
      tutoring boundaries, restricted faith/health/family data, and audit.
- [ ] L4.7 Add a governance coverage report that shows every route/action and
      its policy owner.
- [ ] L4.8 Prove governance survives restart, provider outage, invalid actor,
      stale token, and partial write failures.

Exit gate: every consequential action is policy-owned, auditable,
understandable, and fail-closed.

## Phase 3: Level 5 Ambient Intelligence (>95%)

Goal: JARVIS becomes present, helpful, and disciplined across surfaces without
becoming noisy or voice-only.

- [ ] L5.1 Build a stable full-duplex voice loop: wake phrase, listen, speak,
      interrupt, resume, timeout, retry, and graceful fallback.
- [ ] L5.2 Support both "Hey Jarvis" and "Jarvis" wake phrases where the active
      voice surface allows wake-word control.
- [ ] L5.3 Wire Siri/App Intents so Siri launches the session and JARVIS owns
      the conversation, context, follow-up, and transcript.
- [ ] L5.4 Complete browser, iPhone, and hosted voice-shell parity for typed,
      spoken, interrupted, and resumed conversation.
- [ ] L5.5 Prove driving-safe CarPlay behavior with constrained commands,
      route-aware context, no broad non-driving workflows, and safety tests.
- [ ] L5.6 Add real presence inputs: phone heartbeat, foreground/background,
      focus state, driving, room, quiet hours, stale TTL, and manual override.
- [ ] L5.7 Add noise-learning feedback: useful, noisy, wrong time, wrong
      surface, missed urgency, and future routing changes based on feedback.
- [ ] L5.8 Build proactive orchestration across calendar, weather, route, home,
      health, approvals, provider status, mode, presence, and risk.
- [ ] L5.9 Every proactive prompt must include why-now, source facts,
      confidence, actions, snooze/dismiss, feedback, and audit event.
- [ ] L5.10 Add ambient e2e proofs for quiet morning, urgent alert, driving,
      family mode, sabbath/rest, crisis, and provider-down scenarios.

Exit gate: JARVIS notices what matters, chooses the right surface, speaks only
when useful, and records why it interrupted or stayed quiet.

## Phase 4: Level 6 Memory And Continuity (>95%)

Goal: memory becomes a trustworthy continuity engine, not keyword stuffing.

- [ ] L6.1 Replace keyword relevance with situation retrieval using person,
      domain, task, unresolved loop, prior resolution, season, relationship,
      lesson, location, mode, and current decision.
- [ ] L6.2 Add retrieval explanations so every memory included in reasoning
      says why it was selected.
- [ ] L6.3 Add provenance to every durable memory: observed fact, instruction,
      inference, tentative pattern, approved belief, retired belief, source,
      owner, subject, sensitivity, access policy, review state, and correction.
- [ ] L6.4 Wire correction states into reasoning: corrected, disputed, retired,
      superseded, and do-not-use must be excluded from future context.
- [ ] L6.5 Make Chronicle the narrative memory layer for patterns, rituals,
      faith records, decisions, milestones, lessons, and why they matter.
- [ ] L6.6 Enforce Chronicle/JARVIS memory boundaries so faith-tagged content
      routes to Chronicle or requires explicit sharing.
- [ ] L6.7 Add household memory review UI for inspect, correct, dispute, retire,
      export, forget, provenance, and impact.
- [ ] L6.8 Add Obsidian or equivalent human-facing publishing for approved
      long-form notes, Chronicle summaries, and executive memory.
- [ ] L6.9 Add memory restart, permission, correction, retrieval, export, and
      narrative e2e proofs.

Exit gate: JARVIS remembers in a way the household can inspect, correct, trust,
and benefit from across months.

## Phase 5: Level 7 Formation And Stewardship (>95%)

Goal: JARVIS helps the household become more aligned with its stated values,
not merely more efficient.

- [ ] L7.1 Wire health check-ins, readiness, Dexcom, sleep, movement, stress,
      objectives, and review history into morning brief and Three Moves.
- [ ] L7.2 Generate doctor packets from real accumulated health history once
      enough data exists, with unavailable states before then.
- [ ] L7.3 Wire faith/ritual loops into daily word, prayer capture, study
      review, follow-up, Chronicle records, and future guidance.
- [ ] L7.4 Make formation guidance change by person, season, household mode,
      calendar load, health posture, stress, faith rhythm, and family context.
- [ ] L7.5 Build child-safe tutoring and coaching with parent review, Socratic
      boundaries, memory limits, and inspectable transcripts.
- [ ] L7.6 Add parenting support loops: rituals, encouragement, correction
      review, child-sensitive privacy, and adult-only reflection.
- [ ] L7.7 Add "formation changed because..." citations so guidance names the
      input facts it used.
- [ ] L7.8 Prove formation loops across normal day, health recovery, school
      day, sabbath/rest, child tutoring, and stale-prayer follow-up scenarios.

Exit gate: daily guidance adapts truthfully to the person and season, and the
family can inspect why.

## Phase 6: Level 8 Bounded Autonomy (>95%)

Goal: JARVIS completes useful delegated work in governed arenas without outrunning
trust, rollback, or approval.

- [ ] L8.1 Complete Foundry agent generation with real agent stubs, registry
      entries, mission, trust zone, arena, tools, memory scope, and authority.
- [ ] L8.2 Add newborn-agent lifecycle: propose, approve, sandbox, evaluate,
      promote, demote, suspend, retire, and archive with audit.
- [ ] L8.3 Finish Catalyst executive workflow routing as a first-class bounded
      domain, not a generic workstream fallback.
- [ ] L8.4 Ship one flagship automation: research -> synthesize -> draft ->
      review -> approval -> publish/stage, with evidence and rollback.
- [ ] L8.5 Add sandbox snapshots before every execution and rollback packets
      for every supported job type.
- [ ] L8.6 Add pause, cancel, resume, dead-letter, retry, timeout, and recovery
      controls to every autonomous job surface.
- [ ] L8.7 Add agent performance memory: success rate, boundary violations,
      operator feedback, promotion evidence, demotion cause, and doctrine impact.
- [ ] L8.8 Prove autonomous work in at least three domains: publishing, research,
      household admin, workshop planning, finance review, or health prep.

Exit gate: JARVIS can do real work while bounded, reviewable, reversible, and
interruptible.

## Phase 7: Level 9 Civilization Layer (>95%)

Goal: JARVIS becomes long-horizon household infrastructure for identity,
continuity, legacy, values, and flourishing.

- [ ] L9.1 Encode the household constitution into runtime decisions, not only
      docs: mandate, values, roles, hard boundaries, amendments, escalation.
- [ ] L9.2 Make significant recommendations cite principle, authority basis,
      uncertainty, dissent, override path, and what would change the answer.
- [ ] L9.3 Make household modes change real behavior: priorities, alerts,
      agents, rituals, autonomy ceiling, briefing posture, TTS, and UI posture.
- [ ] L9.4 Complete value simulation for decisions across time, money, health,
      faith, family, risk, opportunity, reputation, and long-term effects.
- [ ] L9.5 Build legacy archive as a household-facing product: stories,
      milestones, decisions, rituals, photos/media references, lessons,
      permission tiers, correction, export, and provenance.
- [ ] L9.6 Add monthly, seasonal, and yearly reviews across health, faith,
      family, work, finances, learning, identity, and household systems.
- [ ] L9.7 Show how prior lessons changed current guidance.
- [ ] L9.8 Build household-operable admin for modes, memory, devices, agents,
      integrations, permissions, autonomy, audits, backups, and emergency pause.
- [ ] L9.9 Add personnel/device continuity flows: new member, changed role,
      new device, lost device, offboarding, memory migration, permission update.
- [ ] L9.10 Add non-builder household views so family members can benefit from
      JARVIS directly at appropriate responsibility levels.
- [ ] L9.11 Prove crisis day, travel week, health recovery, child formation,
      legacy recall, automation, memory correction, governance pause, and
      provider outage as end-to-end scenarios with restart survival.

Exit gate: JARVIS is not just useful today; it compounds wisdom, memory,
values, governance, and continuity across time.

## Phase 8: Real-World Providers, Hardware, And Infrastructure

Goal: connect the household world honestly and safely.

- [ ] HW.1 Unified home-control authority chosen and wired. If Home Assistant
      is adopted, connect credentials/entity map with service-call safety rails.
      If another backbone is chosen, provide the equivalent governed adapter.
      Exclude from scoring until a whole-home authority is intentionally adopted.
- [ ] HW.2 Weather provider repaired or replaced; WeatherKit/OpenWeather status
      truth visible; no fake weather cards.
- [ ] HW.3 Google Gmail/Calendar and Microsoft Outlook status live, with token
      refresh, degraded states, and per-account diagnostics.
- [ ] HW.4 Dexcom live sync complete with clear "not worn recently" state.
- [ ] HW.5 Plaid finance connector configured, linked, synced, and governed.
- [ ] HW.6 KDP connector governed with credential safety, sync health, and no
      unsafe publishing action.
- [ ] HW.7 Perception feeds: porch, garage, room presence, phone arrival,
      privacy state, mute indicators, and event resolution. Keep in plan;
      exclude from scoring until perception hardware exists.
- [ ] HW.8 Workshop devices: Bambu/Cricut/printer telemetry, job staging,
      material context, safety checks, and device-unavailable states. Keep in
      plan; exclude from scoring until workshop devices exist.
- [ ] HW.9 Local-first resilience track: optional household host, NAS backup,
      UPS graceful shutdown, segmented network, and recovery runbook applied to
      the house. Hetzner already satisfies the current hosted always-on need.
- [ ] HW.10 Live provider battery distinguishes configured, connected, stale,
      blocked, permission-denied, and provider-error for every integration.

Exit gate: every external dependency is either genuinely live or precisely
blocked with a reversible setup path.

## Phase 9: Mobile, Web, And Household UX Consolidation

Goal: make JARVIS operable by the household without adding another pile of
equal-weight screens.

- [ ] UX.1 Keep web as full command/oversight surface, but remove fake or stale
      provider signals from every experience.
- [ ] UX.2 Reshape iPhone around Today, Focus, Family, Decisions, Navigate, and
      Continuity while preserving live `/api/apple/*` truth.
- [ ] UX.3 Add household-safe views for non-builder users with role-aware
      complexity and permissions.
- [ ] UX.4 Add settings paths for every connector and hardware dependency.
- [ ] UX.5 Add global unavailable/partial/stale/error/loading patterns that are
      consistent and truthful.
- [ ] UX.6 Add accessibility and responsive checks for all primary experiences.
- [ ] UX.7 Add manual verification scripts for web, iPhone, voice, and provider
      surfaces.

Exit gate: the product is not just technically wired; it is understandable,
reviewable, and steerable by the household.

## Phase 10: Proof, Release, And Maturity Advancement

Goal: advance maturity only when the evidence earns it.

- [ ] P.1 Build one Level 9 scenario suite covering Level 3 through Level 9
      behaviors in integrated flows, not isolated stores.
- [ ] P.2 Add production smoke tests for hosted API health, primary routes,
      connector status, auth boundaries, and key mutation paths.
- [ ] P.3 Add restart-survival tests for modes, agents, memory, missions,
      health, rituals, provider sync, approvals, automations, and legacy.
- [ ] P.4 Add browser e2e screenshots and console/network-noise checks for all
      primary experiences.
- [ ] P.5 Add Apple contract verification and Swift decode verification for
      every changed `/api/apple/*` payload.
- [ ] P.6 Add security and permission regression tests for every Level 4+ action.
- [ ] P.7 Require proof ledger update before any checkbox changes to DONE.
- [ ] P.8 Update maturity model, roadmap, exit reports, and this file only after
      integrated proof passes.

Exit gate: every level is >95%, all critical scenario proofs pass, production
truth is verified, and docs agree.

## First Execution Order

1. T0 truth/status tool and docs consistency check.
2. L3 no-fake-data/provider truth audit across all experiences.
3. Home Assistant setup path and entity map, if credentials are available.
4. L5 voice loop: "Hey Jarvis" conversational path, interrupt, resume.
5. L6 situational memory retrieval and correction exclusion.
6. L7 health/faith loops changing daily guidance.
7. L8 flagship governed automation.
8. L9 household modes, constitution citations, legacy/review UI.
9. Hardware/provider rollout.
10. End-to-end Level 9 proof suite and docs-last maturity update.

## Resume Point

Resume from LEVEL 3 TASK hosted/provider proof battery using `JARVIS-SESSION-STATE.md`.

Immediate next work:

1. Replace or refresh the stale local provider battery artifact with a real run
   against a live local or hosted JARVIS surface so provider truth can move
   from environment-limited to verified.
2. Re-run `python3 scripts/verify_level9_truth.py --output artifacts/qa/level9-truth-report.json`
   after each provider-truth seam to reduce unresolved failures honestly.
3. Keep `python3 scripts/verify_docs_truth.py` green as the planning docs evolve.

## Level 9 Exit Gate

JARVIS may be called Level 9 only when all of the following are true:

1. Levels 2 through 9 each score >95% against the completion contract above.
2. No primary experience presents mock, sample, cached, or inferred data as live.
3. Every consequential action is governed, auditable, reversible where possible,
   and fail-closed.
4. Ambient voice and proactive orchestration work across real user surfaces.
5. Memory retrieval is situational, provenance-backed, and correctable.
6. Formation loops actually change daily guidance and cite their inputs.
7. At least one useful autonomous workflow completes under governance.
8. Legacy, long-horizon review, household admin, and continuity are household
   usable, not developer-only APIs.
9. Real-world providers and hardware are live or explicitly externally blocked.
10. The Level 9 scenario suite passes with restart survival and production-like
    verification.

---

## Archived Historical Notes

The sections below preserve earlier audit and completion records. They may be
useful evidence, but this file's active plan is the master checklist above.

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
