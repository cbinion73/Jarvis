# JARVIS Build Office Automation

This control plane lets Claude, Codex, and BMAD contribute to one JARVIS mission without sharing a writable checkout. It extends the existing Build Office and Architecture Office protocols; it does not create a second planning framework.

## Non-negotiable invariant

No two writable assignments may use the same worktree or overlapping path lease. `main` is an integration surface, not an agent workspace. An agent may inspect another branch, but it may not edit another office's worktree, switch its branch, stage its files, clean its state, merge it, or push it.

## Initial routing priors

The supplied capability matrix is treated as a starting hypothesis:

- Claude is initially favored for large-codebase understanding, architecture, explanation, and long-context analysis.
- Codex is initially favored for implementation, tests/debugging, multi-file refactoring, Git/PR work, and autonomous execution.
- Either model may write first drafts.

These are not fixed lanes. Assignment outcomes capture exit status, commits, changed files, test evidence, review findings, time, and budget so later routing can follow observed results.

## Risk and cost policy

| Risk | Default route |
|---|---|
| Low | One implementation office; local evidence |
| Medium | One implementation office; other model reviews |
| High | Claude analysis; Codex implementation; Claude review |
| Critical | Same as high, with human gates before dispatch and release |

Every model process receives a timeout and declared dollar budget. Claude's CLI enforces the budget as a hard dollar cap. The installed Codex CLI exposes no equivalent dollar-cap flag, so Build Office applies a budget-derived shorter timeout and records this as a time proxy rather than falsely claiming hard cost enforcement. The system must not spend two-model review cost on low-risk work unless Chris requests it.

## Office duties

The binding, versioned role definitions and separation-of-duty matrix live in [OFFICE-CHARTERS.md](OFFICE-CHARTERS.md). Teach a persistent office with `office-brief` when it is created and whenever the charter version changes. Every generated mission assignment also records and injects the applicable charter version.

### JARVIS control plane

- Own mission state, revisions, assignments, leases, and release gates.
- Provision immutable branch/worktree pairs for writable assignments.
- Block scope or worktree collisions before starting a model process.
- Preserve append-only events and repository evidence.
- Reject linked-worktree control-plane invocation, stale revisions, branch reuse, symlink-rooted scopes, missing assignment worktrees, and changed files outside a lease.
- Prepare release and cleanup plans without silently mutating Git.

### Codex implementation office

- Work only in its assigned `build-office/.../codex-implementation` branch and worktree.
- Implement the frozen contract and run acceptance checks.
- Report exact changed files, commit, tests, failures, and remaining risk.
- Never approve its own implementation or touch `main`.

### Claude analysis and review offices

- Analysis is read-only and produces constraints, risks, and acceptance guidance.
- Review is independent and reads the frozen contract plus Codex's diff/evidence.
- Claude must not repair the implementation during review or convert review into a second writable lane.
- Review must distinguish blocking defects from optional improvements.

### Chris

- Owns product intent and frozen contract changes.
- Approves destructive cleanup, external side effects, and release mutations.
- Resolves genuine scope conflicts that cannot be safely re-sliced.

## Claude's first instruction

Claude should remain read-only in `/Users/chris/Desktop/CODE/JARVIS` while Codex builds the pilot in `/Users/chris/Desktop/CODE/JARVIS-codex-build-office` on `codex/agentic-build-office`.

Claude's first assignment is:

> Review `_bmad-output/implementation-artifacts/spec-agentic-build-office-control-plane.md` and the eventual branch diff against the existing BMAD, Build Office, and Architecture Office contracts. Do not edit files, switch branches, clean the checkout, stage, commit, merge, or push. Report only contract violations, collision risks, missing lifecycle controls, unsafe CLI permissions, and release-gate gaps, with exact file/line evidence. Wait for a provisioned Build Office assignment before performing any writable work.

## Operator commands

Run from the repository root:

```bash
python3 scripts/jarvis_build_office.py doctor
python3 scripts/jarvis_build_office.py office-brief all
python3 scripts/jarvis_build_office.py init "Implement the bounded request" --contract-ref '_bmad-output/implementation-artifacts/spec-example.md' --risk medium --implementer codex --scope 'jarvis/**' --scope 'tests/**'
python3 scripts/jarvis_build_office.py status MISSION_ID
python3 scripts/jarvis_build_office.py inbox claude
python3 scripts/jarvis_build_office.py claim MISSION_ID ASSIGNMENT_ID --by "Claude QA Office"
python3 scripts/jarvis_build_office.py approve-dispatch MISSION_ID --by Chris
python3 scripts/jarvis_build_office.py reclaim-lease MISSION_ID ASSIGNMENT_ID --by Chris
python3 scripts/jarvis_build_office.py retry MISSION_ID ASSIGNMENT_ID --by Chris
python3 scripts/jarvis_build_office.py dispatch MISSION_ID codex-implementation --dry-run
python3 scripts/jarvis_build_office.py dispatch MISSION_ID claude-review --dry-run
python3 scripts/jarvis_build_office.py submit-result MISSION_ID ASSIGNMENT_ID --by "Claude QA Office" --status completed --summary "No blocking findings." --finding "Optional improvement"
python3 scripts/jarvis_build_office.py release-plan MISSION_ID
python3 scripts/jarvis_build_office.py cleanup-plan MISSION_ID
```

`dispatch` without `--dry-run` invokes the installed CLI with the mission budget posture, timeout, worktree, scope, forbidden paths, and main-branch prohibition. Claude also receives explicit dangerous-Git tool denials. Codex runs under its workspace sandbox; because its CLI has no equivalent command denylist or dollar cap, post-run path/ref evidence and the budget-derived timeout remain mandatory compensating controls. Redacted output tails and Git evidence are persisted under `_bmad-output/build-office-runs/`, which is ignored by Git.

## Lifecycle

1. `doctor` verifies Git, both CLIs, and checkout cleanliness.
2. `init` records a bounded mission and its frozen Architect contract reference, then provisions writable worktrees. Implementation remains blocked when the contract reference is missing.
3. `dispatch` atomically acquires a lease, checks all active leases, and only then launches a model.
4. Completion records process and Git evidence and releases the lease.
5. Medium or higher risk remains blocked until the other provider completes review.
6. `release-plan` reports whether the mission is blocked or ready for human approval; it never merges or pushes.
7. `cleanup-plan` distinguishes clean removable worktrees from dirty or active worktrees. Removal remains an explicit approved operation.

## Heartbeat pickup

Heartbeat pickup is file-backed, not magical cross-vendor RPC. The Build Office exposes a shared inbox from mission state, and each office polls it on a timer.

1. Orchestration or Build Office initializes the mission.
2. The Claude office heartbeat runs `python3 scripts/jarvis_build_office.py inbox claude`.
3. If a ready assignment appears, Claude claims it with `claim`, performs the read-only analysis or review, then records structured feedback with `submit-result`.
4. The Codex side can use the same flow with `inbox codex` for manual office pickup, or continue to use `dispatch` for ephemeral CLI execution.
5. `release-plan` reads the resulting assignment state and evidence instead of relying on trusted chat summaries.

This gives Claude a durable pickup signal and a durable return path without requiring shared writable branches or direct Codex-to-Claude messaging.

## Recovery

- A timeout or non-zero exit marks the assignment failed and preserves evidence.
- A named human may retry failed writable work in its original isolated worktree; prior evidence remains in bounded history.
- A collision marks the second assignment blocked before a model starts.
- An expired writable lease remains blocking until Chris explicitly reclaims it.
- A dirty main checkout blocks intake or release planning.
- Dirty agent worktrees are never proposed for automatic removal.
- Append-only events plus mission revisions make interrupted work resumable and auditable.

## Pilot success measures

Track wall-clock time, model spend, test pass rate, review findings, escaped defects, collision blocks, retries, and human interventions. The system succeeds when it reduces rework and collisions enough to justify its coordination cost; it should not be retained merely because multi-agent execution looks sophisticated.
