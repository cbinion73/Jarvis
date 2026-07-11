---
title: Control Plane QA Dispatch Recovery AC7/AC9 Evidence
status: recorded
owner: architect-office
recorded_at: 2026-07-11
---

# Control Plane QA Dispatch Recovery AC7/AC9 Evidence

## Scope

This evidence supplements the frozen control-plane recovery contract:

- `_bmad-output/implementation-artifacts/contracts/CONTROL-PLANE-QA-DISPATCH-RECOVERY.md`
- contract ref: `5d2241d7810edffc520167a6f3b7d54cbbb35627`
- Build implementation commit: `fe21788c6cbfe66896458d134f197d6bd21502b9`
- Integrated main commits:
  - `e405e39` - recover QA dispatch control plane
  - `41ac19c` - pipe Codex review prompt via stdin
  - `c346e39` - use commit-only Codex review dispatch

## AC7 Dirty-Hunk Attribution

Pre-existing dirty control-plane work from the archived rogue Orchestration task was preserved as evidence, not silently adopted as a writable source of truth.

- Main checkout dirty evidence was preserved before recovery as `stash@{0}: preserve archived rogue orchestration QA recovery evidence 2026-07-11`.
- Build assessed the archived input as evidence only from the isolated recovery worktree.
- Adopted design direction:
  - preserve dotfile owned-path handling so `.env.example` is not falsely stripped or rejected;
  - use the installed Codex `exec review` lane for immutable read-only review dispatch;
  - add durable non-writable review recovery that preserves evidence history.
- Replaced implementation details:
  - replaced unsupported `-a` / `--ask-for-approval` dispatch flags;
  - replaced false read-only scope validation with immutable target validation plus process-mutation checks;
  - replaced ad hoc recovery with `recover-review`.
- Rejected/kept out of the Build target:
  - no direct mission JSON edits from Build;
  - no merge, push, deployment, or external mutation;
  - no unrelated product-code changes.

The Build implementation diff from `5d2241d7810edffc520167a6f3b7d54cbbb35627` to `fe21788c6cbfe66896458d134f197d6bd21502b9` contained exactly:

- `docs/BUILD-OFFICE-AUTOMATION.md`
- `jarvis/build_office.py`
- `scripts/jarvis_build_office.py`
- `tests/test_build_office.py`

## AC9 Operational Proof

After integration onto current `main`, Architect executed the supported D0.1 recovery path directly, with Orchestration benched.

1. Integrated control-plane recovery:
   - `e405e39 Recover QA dispatch control plane`
   - tests: `python3 -m pytest -q tests/test_build_office.py` -> `53 passed`
2. Recovered D0.1 non-writable review assignment:
   - command: `python3 scripts/jarvis_build_office.py recover-review bo-d0-1-deployment-secret-hygiene-and-configuration-9b3b2df3 codex-review --by "Architect Office" --reason "..."`
   - result: `codex-review` reset to `planned`;
   - prior blocked evidence preserved in `evidence_history`.
3. Dry-runed D0.1 review dispatch:
   - command: `python3 scripts/jarvis_build_office.py dispatch bo-d0-1-deployment-secret-hygiene-and-configuration-9b3b2df3 codex-review --dry-run`
   - final compatible command shape: `codex exec --ephemeral --json -C /Users/chris/Desktop/CODE/JARVIS-codex-d0-1-deployment-secret-hygiene-and-configuration-9b3b2df3 -s read-only review --commit 44185456511efdb07e4cd43e04cd4f651f2818d3 --title 'bo-d0-1-deployment-secret-hygiene-and-configuration-9b3b2df3 immutable review'`
   - no `-a` flag;
   - no `--ask-for-approval` flag;
   - no false `.env.example` scope violation.
4. Ran live D0.1 Codex review dispatch:
   - command: `python3 scripts/jarvis_build_office.py dispatch bo-d0-1-deployment-secret-hygiene-and-configuration-9b3b2df3 codex-review`
   - exit code: `0`
   - target commit: `44185456511efdb07e4cd43e04cd4f651f2818d3`
   - target fingerprint: `b53c182f7e883473825fdb4e3992e24a80622f6bcf66936a1dd641ded7537dbc`
   - changed files:
     - `.env.example`
     - `deploy/docker-compose.yml`
     - `scripts/verify_deploy_config.py`
     - `tests/test_deploy_config.py`

The live review completed and produced product-side findings. Those findings are D0.1 implementation defects or contract repair inputs, not control-plane dispatch failures.

## Current Control-Plane Disposition

The control-plane recovery path is operational:

- unsupported Codex flags are no longer emitted;
- failed non-writable review lanes can be recovered while preserving evidence history;
- immutable D0.1 review dispatch runs through the installed Codex CLI;
- `.env.example` is no longer falsely rejected as an out-of-scope read-only QA change.

Remaining work is D0.1 product repair based on live review findings.
