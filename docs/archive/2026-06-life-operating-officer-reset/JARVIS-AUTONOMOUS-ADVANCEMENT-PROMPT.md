# JARVIS Autonomous Advancement Prompt

Paste this entire prompt into a new Claude Code session to continue Level-9 advancement.
This prompt is self-contained. The agent does not need prior context.

---

## Mission

You are advancing JARVIS from its current state toward Level 9 maturity as quickly and
correctly as possible. JARVIS is a household intelligence platform for the Binion family.
You have full autonomy to read code, write code, commit, and push to main. Every push to
main deploys automatically to the Hetzner VPS via GitHub Actions.

Work continuously through the gap list below without stopping to ask for approval on
individual implementation decisions. Stop only if you hit a decision that is explicitly
marked AWAITING CHRIS, requires a secret or credential you don't have, or would violate
a security guardrail.

## Read First

Before writing any code, read these files in order:

1. `docs/JARVIS-SESSION-STATE.md` — current gap list, resolved items, verified facts
2. `docs/PHASE3-SHARED-STATE-INTELLIGENCE-SPEC.md` — Phase 3 subsystem spec
3. `docs/JARVIS-MATURITY-MODEL.md` — level definitions

Do not re-audit anything marked REAL or RESOLVED in the session state. Trust it.

## Repo and Deployment Facts

- Repo: `/Users/chris/Desktop/JARVIS`
- Production: Hetzner VPS. Push to `main` → GitHub Actions → `docker compose up --build jarvis`
- Stack: FastAPI (`jarvis/service.py` + `jarvis/main.py`) + Docker (`deploy/docker-compose.yml`)
- iPhone/macOS client: `JarvisApple/` (Swift, `swift test` for verification)
- All `/api/apple/*` routes registered in `jarvis/apple_api.py:_register_apple_api`
- Data volume: `jarvis_data` Docker volume mounted at `/app/data` on Hetzner

## Absolute Security Guardrails (never violate)

- No automatic external messaging without approval
- No remote unlock from voice alone
- No deceptive homework completion for kids
- No cloud archive of raw household video
- No bedroom/bathroom cameras
- No hazardous workshop automation without manual control
- Never present mock data as real
- Never silently widen authority — promotion requires recorded evidence
- No UX redesigns; preserve the existing design language

## Work Order

Work through this list in priority order. Do not skip ahead. Complete each item fully
(code + tests + session state update) before starting the next.

Batch related items into a single commit where sensible. Push to main after each
meaningful batch — do not accumulate uncommitted work across more than 3 gaps.

### Priority 1 — Commit what is already done (do this first)

The following changes are complete but not yet committed or pushed:

- `jarvis/scheduler.py` — GAP-2: `_tick()` now calls `background_cycle()` every 60s
- `jarvis/approvals.py` — GAP-3: fail-closed supervision at staging and execution
- `tests/test_scheduler_fabric_tick.py` — 4 tests for GAP-2
- `tests/test_approval_guard_fail_closed.py` — 5 tests for GAP-3
- `docs/JARVIS-SESSION-STATE.md` — updated with GAP-2/GAP-3 resolutions

Run `python3 -m pytest tests/test_scheduler_fabric_tick.py tests/test_approval_guard_fail_closed.py tests/test_approval_guard_supervision.py` to confirm all pass,
then commit and push.

### Priority 2 — GAP-5: Governance endpoint authentication

File: `jarvis/service.py`, `jarvis/apple_api.py`

`GET /api/learning/proposals/{id}` takes no viewer parameter.
Governance write/approve paths (`/api/governance-proposals/{id}/promote`,
`/api/apple/governance-proposals/{id}/promote`, `/api/apple/governance-proposals/{id}/dismiss`)
trust a self-asserted viewer string with no enforcement.

Fix: require a `viewer` query param on the proposals read route and enforce it matches
`chris` or the known actor list. Mirror the same enforcement already applied to memory
read paths (`jarvis/memory.py:573–602`). Add a negative-path test.

### Priority 3 — GAP-6: Complete interruption posture engine

File: `jarvis/apple_api.py:2702` (`_compute_interruption_posture`)

Currently implements: `deliver_now`, `badge_only`, `quiet_store`, `hold_for_brief`.
Missing: `suppress`, `escalate`.

Rules to add:
- `suppress`: severity=low AND category in {memory, system} AND quiet_hours → suppress
- `escalate`: severity=critical AND category in {household, approval} regardless of focus/quiet → escalate

Also missing: delivery decision recording. Every call to `_choose_delivery_mode` should
append a record to `data/state/interruption_decisions.jsonl` with:
`{ts, item_id, category, severity, posture_mode, decision, decision_reason}`.

Add tests covering both new postures and the recording path.

### Priority 4 — Phase 3 Slice 1: Event write path

File: `jarvis/apple_api.py`, `jarvis/approvals.py`, `jarvis/service.py`

The `_EventLogStore` and `data/state/event_log.jsonl` exist. The `_event_log.record()`
helper exists. But the major action handlers do not emit events. Wire event emission into:

- `ApprovalGuard.request_approval` → emit `kind=action_needed, domain=approvals`
- `ApprovalGuard.execute_approved` → emit `kind=resolved, domain=approvals`
- `/api/apple/home/command` handler → emit `kind=info or warning, domain=home`
- Navigation route record (`_record_navigation_route_history`) → emit `kind=info, domain=navigation`
- Any existing calls to `_notification_center.add()` → also emit a paired event

Each event must include `id`, `ts`, `actor`, `domain`, `kind`, `severity`, `title`,
`status=new`, `source`, `trust_zone` where available.

Spec: `docs/PHASE3-SHARED-STATE-INTELLIGENCE-SPEC.md` § Event Log.

Add `GET /api/apple/events` with `domain`, `status`, `severity`, `limit`, `before`, `after`
query params if it does not already exist (check first — `/api/apple/events/recent` exists).

Add tests verifying events are emitted after approval submission and home command.

### Priority 5 — Phase 3 Slice 2: Notification Center gaps

File: `jarvis/apple_api.py`

Check: does `POST /api/apple/notifications/{id}/escalate` exist? If not, add it.
Check: does `/api/apple/reminders/{id}/defer` and `/api/apple/reminders/{id}/stage` exist?
If not, add them following the existing snooze/complete pattern.

The notification center store and core routes already exist — do not rebuild them.

### Priority 6 — GAP-9: Formation — daily stewardship HTTP route

File: `jarvis/service.py`, `jarvis/daily_stewardship.py`

`daily_stewardship.py` exists but has no HTTP route — it is only callable via
`health_scheduler`. Add:

- `GET /api/stewardship/daily` — returns the current stewardship state (morning check-in,
  evening review, Three Moves)
- `POST /api/stewardship/daily/complete` — marks a move or review step complete

Wire season detection: read the current month to derive season
(Dec–Feb = winter, Mar–May = spring, Jun–Aug = summer, Sep–Nov = fall) and include it
in the stewardship payload. This satisfies the one-reflective-prompt gap without
requiring a full season-detection engine.

### Priority 7 — GAP-4: Enforce arena pause at enqueue time

File: `jarvis/service.py` or wherever `enqueue_self_improvement_sandbox_job` is defined.

`enqueue_self_improvement_sandbox_job` does not re-check arena pause status at enqueue
time. Add the check: if the arena is paused, return an error instead of enqueuing.

### Priority 8 — GAP-8: Foundry proposal pipeline (partial)

File: `jarvis/service.py`, new `jarvis/foundry.py` if needed.

The foundry dashboard (`GET /api/foundry/module`) exists and is read-only. Add:

- `POST /api/foundry/proposals` — submit a new module proposal (draft, no execution)
- `GET /api/foundry/proposals` — list proposals
- `POST /api/foundry/proposals/{id}/approve` — promote a proposal to sandbox-ready

Do NOT add agent generation or newborn-agent zone attachment yet — those require a Fable 5
design session (architectural decision on recursive foundry safety). Just close the
proposal pipeline gap.

### Priority 9 — GAP-11: Concurrency tests for persistence

File: `tests/test_persistence_concurrency.py` (new)

`jarvis/persistence.py` uses `fcntl.flock` for file locking but has no concurrency tests.
Add tests that spawn multiple threads writing to the same JSON file concurrently and assert
no corruption or data loss. Cover at least: concurrent writes, concurrent read+write,
recovery after a write interruption.

## After Each Gap

1. Run the relevant test suite: `python3 -m pytest tests/ -x -q`
2. Do a syntax check on any modified files: `python3 -c "import ast; ast.parse(open('jarvis/FILE.py').read())"`
3. Update `docs/JARVIS-SESSION-STATE.md` — mark the gap resolved with evidence
4. Commit with a clear message referencing the gap (e.g. `GAP-5: require viewer on governance endpoints`)
5. After every 2–3 gaps, push to main

## What Not To Do

- Do not rebuild or re-audit anything marked RESOLVED or REAL in the session state
- Do not redesign UI surfaces — add backend routes and data; the glass shell picks them up
- Do not add SQLite migration (GAP-10) — it is optional and lower priority than all the above
- Do not implement GAP-7 (situation-based memory retrieval) or the full GAP-8 recursive
  foundry without a Fable 5 design session — these are architecture decisions, not
  implementation gaps
- Do not mock data and call it live
- Do not widen trust-zone authority without the promotion engine recording evidence

## Session Hygiene

- Read `docs/JARVIS-SESSION-STATE.md` at the start of every session
- Update it before ending every session
- If you hit something unexpected (a broken import, a missing dependency, a schema
  mismatch), note it in the session state under a new GAP entry and move to the next item
- Never leave uncommitted changes at end of session
