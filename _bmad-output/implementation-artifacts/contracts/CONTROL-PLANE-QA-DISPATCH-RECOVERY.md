# Frozen Architect Contract: Control-Plane QA Dispatch Recovery

Status: **FROZEN**

Contract version: **1.0.0**

Risk: **high**

Mission under recovery: `bo-d0-1-deployment-secret-hygiene-and-configuration-9b3b2df3`

Scope: **Build Office control plane only; no JARVIS product behavior**

## Invariants

1. QA remains independent and read-only. A QA dispatch may inspect and test the immutable Build target but may not modify it, repair it, merge it, push it, or change the frozen product contract.
2. The immutable D0.1 review target remains commit `44185456511efdb07e4cd43e04cd4f651f2818d3` with target fingerprint `b53c182f7e883473825fdb4e3992e24a80622f6bcf66936a1dd641ded7537dbc`. Recovery must not substitute another commit or recompute away a mismatch.
3. Installed-tool compatibility is authoritative. The installed Codex CLI supports neither `-a` nor `--ask-for-approval` for `codex exec`; neither option may appear in a generated Codex command. QA dispatch must use a command shape accepted by the installed CLI and must preserve read-only execution.
4. Scope validation distinguishes the immutable target diff from mutations made by the reviewing process. Files in the Build target are validated against the mission's owned and forbidden paths. A valid target-owned file is not a violation merely because the assignment is non-writable. Any file mutation attributable to QA is always a blocking violation.
5. Review recovery is a first-class, authorized state transition. A failed, blocked, leased, or running non-writable review assignment can be closed or reset only through the control-plane API/CLI, with an identified actor and durable event. Direct edits to `mission.json` are forbidden.
6. Recovery is append-only with respect to evidence. Current `evidence`, all `evidence_history`, lease acquisition data, failure output, actor, reason, and transition timestamps remain auditable. Resetting for retry may move current evidence into bounded history but may not discard or overwrite it.
7. Recovery does not alter Build evidence, the baseline, contract reference, target commit, target fingerprint, approvals, or product acceptance criteria. A retry reviews the same immutable target.
8. The uncommitted changes presently in `jarvis/build_office.py` and `tests/test_build_office.py` are untrusted evidence/input from the archived rogue Orchestration task. Build may inspect and assess their diff but must implement independently in an isolated worktree from the contract baseline. Those dirty files must not be staged, committed, reset, cleaned, or treated as approved code by Architect or Orchestration.
9. No recovery operation grants release approval. D0.1 remains blocked until a newly dispatched independent QA review submits a complete verdict against the immutable target.
10. All state transitions are lock-protected, deterministic, and idempotent: repeating an already completed recovery cannot duplicate evidence, erase history, or move an assignment into a less truthful state.

## Owned Paths

The downstream Build assignment may modify only:

- `jarvis/build_office.py`
- `scripts/jarvis_build_office.py`
- `tests/test_build_office.py`
- `docs/BUILD-OFFICE-AUTOMATION.md`

The Build implementation must occur in a newly provisioned isolated worktree. The two dirty files in the main checkout are evidence only and are not the Build workspace.

## Forbidden Paths

The downstream Build assignment must not modify:

- `.env.example`
- `deploy/docker-compose.yml`
- `scripts/verify_deploy_config.py`
- `tests/test_deploy_config.py`
- `_bmad-output/implementation-artifacts/contracts/**`
- `_bmad-output/build-office-runs/**`
- `data/**`
- `.git/**`
- `.github/**`
- `jarvis/office_charters.py`
- `docs/OFFICE-CHARTERS.md`
- any product runtime, application behavior, deployment configuration, secret, credential, release artifact, or mission-state file

Build and QA must not stage, reset, clean, or otherwise mutate unrelated dirty files in the main checkout.

## Acceptance Criteria

### AC1 — Installed Codex command compatibility

- A dry-run Codex QA dispatch generates a command accepted by the installed CLI's documented parser.
- The generated command contains neither `-a` nor `--ask-for-approval`.
- The generated command selects the exact immutable review commit and supplies the frozen QA instructions without shell interpolation.
- Automated tests prove the command shape without making a paid/model/network call.

### AC2 — Read-only QA execution

- QA dispatch is non-writable by construction and runs against the intended review worktree/repository.
- The dispatcher refuses a missing or wrong review target rather than falling back to the main checkout or another commit.
- A test proves that a QA process mutation is detected and blocks completion.

### AC3 — Correct target-scope validation

- For D0.1, the exact target file set `.env.example`, `deploy/docker-compose.yml`, `scripts/verify_deploy_config.py`, and `tests/test_deploy_config.py` produces no scope violation for the read-only review assignment.
- A target containing a file outside the assignment's owned paths produces a blocking scope violation.
- A target containing a forbidden path produces a blocking scope violation even if another owned pattern would match it.
- Dotfile paths such as `.env.example` retain their leading dot during normalization.
- Tests reproduce the historical false-positive path and prove it closed.

### AC4 — Supported non-writable review recovery

- A named CLI/API operation can recover a non-writable review assignment in `failed`, `blocked`, `leased`, or `running` state after a dispatch failure.
- Recovery requires a non-empty actor and reason, records a durable recovery event, releases/closes any active lease, and moves the assignment to its defined retry-ready state.
- The operation refuses writable assignments, completed successful reviews, unknown assignments, and invalid source states.
- Repeating the same recovery is safe and does not duplicate or erase evidence.
- No manual edit to a mission file is required.

### AC5 — Evidence-history preservation

- Before retry, current failure evidence is retained in `evidence_history` with its original exit code, stderr, changed-files snapshot, target commit/fingerprint, and timestamps where present.
- Existing history for the original AC7 rejection and both unsupported-option failures remains intact and ordered.
- Lease holder/acquisition/release or recovery metadata remains auditable.
- Recovery does not change the implementation assignment evidence for commit `44185456511efdb07e4cd43e04cd4f651f2818d3`.

### AC6 — Immutable retry target

- After recovery, readiness and dry-run dispatch resolve to commit `44185456511efdb07e4cd43e04cd4f651f2818d3` and fingerprint `b53c182f7e883473825fdb4e3992e24a80622f6bcf66936a1dd641ded7537dbc`.
- If the commit, fingerprint, baseline, or target diff no longer matches durable Build evidence, dispatch or release planning blocks with a precise reason.

### AC7 — Rogue-diff preservation and assessment

- Build evidence explicitly states whether each pre-existing dirty hunk in `jarvis/build_office.py` and `tests/test_build_office.py` was adopted, replaced, or rejected and why.
- The downstream implementation commit is produced from the isolated Build worktree and contains only the owned paths needed for this contract.
- The main-checkout dirty files remain untouched throughout Build and QA.

### AC8 — Regression suite and durable handoff evidence

Build must provide all of the following with exit code and output summary:

```bash
python3 -m pytest -q tests/test_build_office.py
python3 scripts/jarvis_build_office.py doctor
python3 scripts/jarvis_build_office.py dispatch <recovery-test-mission> codex-review --dry-run
git diff --check <baseline>..<implementation-commit>
git diff --name-only <baseline>..<implementation-commit>
```

The test suite must include explicit regressions for unsupported CLI options, valid read-only target files, actual out-of-scope target files, QA-authored mutation, successful non-writable recovery, invalid recovery, idempotent recovery, and evidence-history preservation. Build must report the exact baseline, implementation commit, changed-file list, and target fingerprint. QA must independently rerun the suite and map a pass/fail result to every acceptance criterion.

### AC9 — D0.1 operational proof

After the control-plane implementation passes independent QA, Orchestration must use the supported recovery operation on `bo-d0-1-deployment-secret-hygiene-and-configuration-9b3b2df3`, then dry-run and dispatch `codex-review`. The resulting QA evidence must reference the immutable D0.1 target and contain no false scope violation. This operational proof is required before the control-plane recovery mission or D0.1 review can be considered closed.

## Build Order

1. Provision a clean isolated Build worktree from the contract ref; capture the main-checkout dirty diff as read-only input without changing it.
2. Add failing regression tests for installed Codex command compatibility, including explicit exclusion of `-a` and `--ask-for-approval`.
3. Add failing regression tests that separate immutable target-scope validation from QA-process mutation detection, including the D0.1 dotfile case.
4. Add failing lifecycle tests for authorized recovery of non-writable review assignments, invalid-state refusal, idempotency, lease closure, and append-only evidence history.
5. Implement the smallest control-plane changes necessary inside the owned paths. Add or update the CLI surface and operator documentation only as required by the tests.
6. Run the full acceptance command set, inspect the bounded diff, and commit only the owned implementation files in the isolated worktree.
7. Submit durable Build evidence including the dirty-hunk assessment, exact baseline/commit/fingerprint, changed files, tests, and residual risks.
8. Route the immutable implementation commit to independent QA. QA reruns every criterion read-only and issues approve or reject; it does not repair.
9. Only after QA approval, use the supported recovery path on the named D0.1 mission and perform AC9. Release remains gated by the resulting independent D0.1 QA verdict.
