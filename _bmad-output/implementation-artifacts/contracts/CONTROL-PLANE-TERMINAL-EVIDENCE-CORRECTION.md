# Frozen Architect Contract: Control-Plane Terminal Evidence Correction

Status: **FROZEN**

Contract version: **1.0.0**

Risk: **medium**

Scope: **Build Office control plane only; no JARVIS product behavior**

Primary observed failures:

- Heartbeat repeatedly reports superseded failed assignments from recovery missions that already have committed replacement evidence.
- A Build assignment can become terminal with internally inconsistent evidence: non-empty changed files but `commit == baseline_commit`, while the isolated worktree contains a valid newer implementation commit.

## Invariants

1. Orchestration remains benched for this recovery path. Architect may classify and route directly to Build or Quality Office Jarvis.
2. Mission evidence remains append-only. Any correction must preserve the original failed or stale evidence in ordered history before replacing current evidence.
3. No direct manual edit to `mission.json` is allowed. Correction and closure must use supported CLI/API operations with actor, reason, timestamp, and durable event records.
4. QA must only review immutable implementation commits with internally consistent evidence: exact commit, baseline, changed-file list, target fingerprint, worktree, tests, and scope validation.
5. Superseded failed assignments must not continue to page Architect heartbeat once a durable superseding contract/evidence artifact identifies why they are closed.
6. A terminal assignment cannot be silently reopened, overwritten, or erased. Any amendment must be explicit, auditable, and restricted to stale/inconsistent evidence cases.
7. Cleanup planning may identify removable worktrees but must not remove, reset, push, merge, or mutate unrelated user files.
8. No product runtime, deployment behavior, secret, data file, or release artifact may change.

## Owned Paths

Build may modify only:

- `jarvis/build_office.py`
- `scripts/jarvis_build_office.py`
- `tests/test_build_office.py`
- `docs/BUILD-OFFICE-AUTOMATION.md`

Architect may add or update only durable contract/evidence artifacts under:

- `_bmad-output/implementation-artifacts/contracts/**`
- `_bmad-output/implementation-artifacts/evidence/**`

## Forbidden Paths

Build and QA must not modify:

- `.env`
- `.env.example`
- `deploy/**`
- `data/**`
- `.git/**`
- `.github/**`
- `_bmad-output/build-office-runs/**` except through supported Build Office CLI/API transitions
- product runtime/application behavior outside the owned control-plane files

## Acceptance Criteria

### AC1 — Terminal evidence amendment

Provide a supported CLI/API operation that can amend a terminal assignment only when all are true:

- assignment status is terminal,
- current evidence is internally inconsistent,
- the isolated assignment worktree exists,
- the worktree `HEAD` differs from mission baseline,
- changed files are non-empty and inside the assignment owned paths,
- actor and reason are supplied.

The operation must refuse non-terminal assignments, missing worktrees, dirty out-of-scope changes, forbidden paths, no-op commits, completed QA approvals, and missing actor/reason.

### AC2 — Evidence preservation

Before amendment, the prior current evidence must be copied into `evidence_history` with:

- original commit,
- baseline,
- changed files,
- stdout/stderr tails,
- timestamps,
- completion actor where present,
- correction actor,
- correction reason,
- correction timestamp.

The current evidence may then be replaced with the corrected worktree-derived evidence.

### AC3 — Review target correctness

After amendment, release planning and QA dispatch must resolve the implementation review target to the corrected implementation commit, not the baseline commit.

For the observed governance/handoff mission, the corrected target must be:

- mission: `bo-finish-the-governance-and-handoff-loop-for-the-j-1ea2b033`
- baseline: `a1b9c2b366cdb6e3f7a22704b04fab9184757868`
- implementation commit: `325f612`
- changed files:
  - `docs/BUILD-OFFICE-AUTOMATION.md`
  - `jarvis/build_office.py`
  - `tests/test_build_office.py`

### AC4 — Superseded action closure

Provide a supported CLI/API operation or heartbeat rule that marks failed assignments as superseded without erasing evidence when a newer committed evidence artifact proves the failure has been resolved elsewhere.

For the two repeated heartbeat actions, the closure must reference committed durable evidence:

- `bo-control-plane-qa-dispatch-recovery-8117af25` / `claude-analysis`
- `bo-control-plane-qa-dispatch-recovery-replacement-ac9d2a79` / `codex-implementation`
- superseding artifacts:
  - `_bmad-output/implementation-artifacts/evidence/CONTROL-PLANE-QA-DISPATCH-RECOVERY-AC7-AC9-EVIDENCE.md`
  - `_bmad-output/implementation-artifacts/evidence/D0-1-DEPLOYMENT-SECRET-HYGIENE-QA-REPAIR-APPROVAL.md`

After closure, `python3 scripts/jarvis_build_office.py heartbeat architect --cadence-seconds 300` must not report those superseded failures as active Architect actions.

### AC5 — Regression tests

Tests must cover:

- terminal evidence amendment success,
- amendment refusal for no-op baseline evidence with no newer worktree commit,
- amendment refusal for out-of-scope or forbidden changes,
- evidence-history preservation,
- corrected review target in `release-plan`,
- superseded failed assignment no longer appears in heartbeat actions,
- superseded assignment evidence remains inspectable.

### AC6 — Required verification

Build must provide command output for:

```bash
python3 -m pytest -q tests/test_build_office.py
python3 scripts/jarvis_build_office.py doctor
python3 scripts/jarvis_build_office.py heartbeat architect --cadence-seconds 300
git diff --check <baseline>..<implementation-commit>
git diff --name-only <baseline>..<implementation-commit>
```

QA must independently rerun the tests and verify the heartbeat no longer reports the two superseded recovery failures.

## Build Order

1. Add failing tests for terminal evidence amendment and superseded heartbeat closure.
2. Implement the smallest supported CLI/API additions in the Build Office control plane.
3. Document the new operations and their guardrails.
4. Run the full regression suite and commit only owned paths in an isolated worktree.
5. Amend the governance/handoff Build evidence to point at commit `325f612` through the supported path.
6. Close the two superseded recovery failures through the supported path or heartbeat rule.
7. Route the corrected governance/handoff implementation target to Quality Office Jarvis.

## Non-goals

- No product feature implementation.
- No release merge.
- No push.
- No manual mission JSON surgery.
- No cleanup of worktrees unless a later explicit cleanup mission authorizes it.
