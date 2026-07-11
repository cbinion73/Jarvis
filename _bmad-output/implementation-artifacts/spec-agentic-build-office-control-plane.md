---
title: 'Agentic Build Office Control Plane'
type: 'feature'
created: '2026-07-10'
status: 'done'
baseline_commit: 'df73198769cf7c592fa7ba2368883148caa6cebc'
review_loop_iteration: 0
context:
  - '{project-root}/docs/archive/2026-07-doc-consolidation/BUILD-OFFICE-PROTOCOL.md'
  - '{project-root}/docs/archive/2026-07-doc-consolidation/ARCHITECTURE-OFFICE-PROTOCOL.md'
  - '{project-root}/data/missions/jarvis_mission_model.v1.json'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Claude, Codex, and BMAD can all contribute to JARVIS, but simultaneous work in one checkout can overwrite files, alter the Git index, switch branches, or clean another agent's work. There is no executable office-level control plane that assigns bounded work, enforces isolated worktrees, gates expensive cross-review, and produces a truthful release record.

**Approach:** Add a repo-native Build Office pilot that turns one bounded request into a durable BMAD-backed mission, assigns Claude and Codex explicit duties, creates one branch/worktree per writable assignment, rejects overlapping leases, records evidence and handoffs, applies risk-based review routing, and prepares—but never silently performs—a main-branch release. Use the installed Claude and Codex CLIs through bounded adapters so the same workflow can progress from intake through implementation and independent review.

## Boundaries & Constraints

**Always:** Reuse `_bmad-output` and existing JARVIS mission/workflow concepts; keep runtime state out of Git; make all state transitions atomic and auditable; require unique worktrees and branches for writable assignments; declare owned and forbidden path globs; detect overlap before dispatch; cap model cost and runtime; capture command, exit status, commit, changed files, test evidence, and reviewer identity; keep the main checkout read-only except during an explicit release operation; treat the supplied Claude/Codex capability matrix as initial routing priors whose accuracy is measured and can be revised from evidence.

**Ask First:** Any push, merge, deletion of an occupied worktree, force operation, destructive cleanup, unbounded model permission, external side effect, or release with failed/missing evidence requires Chris's approval.

**Never:** Allow Claude and Codex to write in the same worktree; let an implementer self-approve; trust prose summaries without repository evidence; create a parallel `.ai/` framework; store secrets or full model transcripts in tracked artifacts; automatically push to `main`; treat fixed model roles as permanent capability truth.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| New mission | Bounded request, risk and budget | Mission record, office assignments, isolated worktrees, dispatch plan | Reject invalid repository, dirty main, missing CLI, or incomplete contract |
| Safe parallel work | Non-overlapping path leases | Claude and Codex may run in separate worktrees | Persist leases before either process starts |
| Collision | Overlapping owned paths or reused worktree | No dispatch occurs | Record blocked state and collision evidence |
| Model failure | Timeout, non-zero exit, or budget exhaustion | Mission remains resumable with captured evidence | Release leases safely; never mark complete |
| Review gate | Risk requires cross-review | Non-implementing model receives diff plus acceptance contract | Block release until review evidence exists |
| Release request | Passing tests and accepted review | Produce exact merge/push plan | Require explicit human approval before mutation |

</frozen-after-approval>

## Code Map

- `jarvis/build_office.py` -- Durable mission, assignment, lease, evidence, and transition model.
- `scripts/jarvis_build_office.py` -- Operator CLI for intake, dispatch, status, review, release planning, and cleanup.
- `_bmad/scripts/memlog.py` -- Existing append-only BMAD decision memory reused by each mission.
- `jarvis/workflow_runs.py` -- Existing runtime-run vocabulary and evidence conventions to align with.
- `tests/test_build_office.py` -- State-machine, collision, worktree, routing, failure, and release-gate coverage.
- `docs/BUILD-OFFICE-AUTOMATION.md` -- Claude/Codex duties, commands, safety boundaries, and first-pilot procedure.

## Tasks & Acceptance

**Execution:**
- [x] `jarvis/build_office.py` -- implement atomic mission storage, risk routing, scoped leases, collision detection, evidence manifests, and guarded transitions.
- [x] `scripts/jarvis_build_office.py` -- implement safe CLI commands plus bounded Claude/Codex subprocess adapters and dry-run support.
- [x] `tests/test_build_office.py` -- test happy path and every matrix failure boundary without calling paid models.
- [x] `docs/BUILD-OFFICE-AUTOMATION.md` -- publish the office charter, Claude's initial instructions, operator workflow, costs, closure, and recovery.
- [x] `.gitignore` -- ignore only generated Build Office runtime/run state while retaining specs and documentation.

**Acceptance Criteria:**
- Given a clean repository and bounded request, when a mission is initialized, then every writable office receives a distinct branch, worktree, scope, budget, and lease.
- Given overlapping writable scopes or a reused checkout, when dispatch is attempted, then execution is blocked before either model starts and the reason is persisted.
- Given a medium/high-risk implementation, when work completes, then the other model must review repository evidence before a release plan can become approval-ready.
- Given failed tests, missing review, expired lease, dirty main, or uncommitted agent work, when release planning runs, then it reports a blocked release without mutating Git.
- Given a completed pilot, when cleanup runs, then active leases close, removable worktrees are identified, durable evidence remains, and tracked source stays clean.

## Spec Change Log

## Design Notes

The pilot uses a single-writer state lock plus optimistic revision numbers. Assignments own explicit path globs and immutable worktree paths. Model adapters receive the frozen intent, assignment scope, forbidden paths, acceptance checks, evidence location, and a prohibition against main-branch operations. Risk routing chooses single-model, cross-review, or dual-analysis workflows. Initial priors favor Claude for large-codebase understanding, architecture, explanation, and long-context reasoning; they favor Codex for implementation, testing/debugging, multi-file refactoring, Git/PR workflow, and autonomous execution; first-draft work is treated as shared strength. Each completed assignment records outcome evidence so routing can change rather than hard-coding Claude as thinker and Codex as builder.

## Verification

**Commands:**
- `python3 -m pytest -q tests/test_build_office.py` -- all control-plane and collision tests pass without network/model calls.
- `python3 scripts/jarvis_build_office.py doctor` -- both CLIs and Git capabilities are reported truthfully.
- `python3 scripts/jarvis_build_office.py demo --dry-run` -- produces a complete mission, isolated assignment plan, cross-review gate, and cleanup plan without paid execution or main mutation.
- `git status --short` -- only intentional source/spec changes remain.

**Observed:** 21 focused tests passed; the complete JARVIS suite passed with 2,219 tests, 3 skipped, and 35 subtests; a clean temporary-repository demo produced both provider assignments, a blocked evidence gate, and `mutated_git: false`.

## Suggested Review Order

**Control-plane entry and mission truth**

- Start with the durable office state model and primary-checkout boundary.
  [`build_office.py:102`](../../jarvis/build_office.py#L102)

- Intake converts risk, budget, scopes, and routing into an auditable mission.
  [`build_office.py:264`](../../jarvis/build_office.py#L264)

**Isolation and collision safety**

- Provisioning rejects occupied paths, reused branches, and main-checkout execution.
  [`build_office.py:379`](../../jarvis/build_office.py#L379)

- Atomic leases conservatively block overlapping writable scopes across active missions.
  [`build_office.py:434`](../../jarvis/build_office.py#L434)

- Expired leases require named human reclamation instead of silent takeover.
  [`build_office.py:475`](../../jarvis/build_office.py#L475)

**Provider execution and evidence**

- Provider adapters encode budgets, sandboxes, Git denials, and independent roles.
  [`build_office.py:514`](../../jarvis/build_office.py#L514)

- Dispatch refuses missing worktrees and turns process results into verified evidence.
  [`build_office.py:549`](../../jarvis/build_office.py#L549)

- Changed files are checked against owned and forbidden path leases.
  [`build_office.py:615`](../../jarvis/build_office.py#L615)

**Release and lifecycle gates**

- Release readiness requires real changes, analysis, cross-review, and clean main state.
  [`build_office.py:663`](../../jarvis/build_office.py#L663)

- Cleanup reports safe removals without deleting dirty or active worktrees.
  [`build_office.py:708`](../../jarvis/build_office.py#L708)

**Operator surface and doctrine**

- The CLI exposes bounded lifecycle commands without an automatic push operation.
  [`jarvis_build_office.py:21`](../../scripts/jarvis_build_office.py#L21)

- The doctrine explains routing priors, cost asymmetry, duties, and Claude's assignment.
  [`BUILD-OFFICE-AUTOMATION.md:5`](../../docs/BUILD-OFFICE-AUTOMATION.md#L5)

**Regression evidence**

- Failure-focused tests prove no fallback, false completion, stale takeover, or lost update.
  [`test_build_office.py:119`](../../tests/test_build_office.py#L119)
