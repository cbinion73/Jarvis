# Frozen Architect Contract: Codex Office Control-Plane Canonicalization

Status: **FROZEN**

Contract version: **1.0.0**

Risk: **high**

Scope: **Office control plane and active office documentation only; no JARVIS product behavior**

## Canonical Doctrine

1. The JARVIS office workflow has one execution platform: Codex.
2. The official independent review authority is **Quality Office Jarvis**.
3. **Orchestration Office Jarvis** routes missions and signals. **Architect Office Jarvis** freezes intent and dispositions. **Build Office Jarvis** implements. **Quality Office Jarvis** independently approves or rejects.
4. There is no alternate provider lane, fallback-provider mode, provider-selection option, or provider-branded office identity.
5. Quality independence is established by office duty, immutable review target, read-only execution, separate assignment/thread, and evidence—not by using a different model vendor.

## Invariants

1. Active control-plane source, CLI help, schemas, tests, prompts, charters, and operator documentation must contain no legacy provider name or `no-<provider>` routing concept.
2. Mission initialization creates Codex assignments for the required office duties without accepting an implementer-provider or route-provider choice.
3. High- and critical-risk missions retain Architect analysis and independent Quality review gates. Removing provider routing must not weaken risk gates.
4. The review office title and user-facing identity are exactly `Quality Office Jarvis`; `QA Office`, `JARVIS QA Office`, and provider-branded reviewer titles are not canonical.
5. Quality assignments remain non-writable and cannot implement, repair, merge, push, or revise the frozen contract.
6. Existing durable mission files, evidence history, Git history, archived documents, and unrelated product integrations are historical/external evidence and must not be rewritten solely to erase old terminology.
7. Current active missions are not manually mutated. Orchestration supersedes incompatible missions through supported transitions and preserves their evidence.

## Owned Paths

- `jarvis/build_office.py`
- `jarvis/office_charters.py`
- `scripts/jarvis_build_office.py`
- `tests/test_build_office.py`
- `tests/test_office_charters.py`
- `docs/BUILD-OFFICE-AUTOMATION.md`
- `docs/OFFICE-CHARTERS.md`

## Forbidden Paths

- `_bmad-output/build-office-runs/**`
- `_bmad-output/implementation-artifacts/contracts/**`
- `docs/archive/**`
- `.git/**`
- `.github/**`
- `data/**`
- `.env*`
- `deploy/**`
- `jarvis/mcp_server.py`
- all product runtime, deployment, secret, credential, release, and unrelated integration files

## Acceptance Criteria

1. `python3 scripts/jarvis_build_office.py init --help` exposes no provider implementer selection and no `no-<provider>` route mode.
2. `python3 scripts/jarvis_build_office.py inbox codex` is the single provider inbox; unsupported provider values fail clearly.
3. Default medium-risk routing produces Codex Build and Codex Quality assignments, with the Quality assignment titled and briefed as `Quality Office Jarvis` and marked non-writable.
4. High- and critical-risk routing includes a required Architect analysis assignment before Build and an independent Quality assignment after Build; all are Codex-backed.
5. Low-risk routing behavior remains explicitly defined and tested; no risk level silently loses a previously required independent gate.
6. Assignment identifiers are duty/office based and contain no legacy provider name. Existing historical mission identifiers remain readable for backward-compatible status and evidence inspection.
7. Dispatch uses only installed Codex CLI-compatible arguments and preserves the sandbox policy appropriate to each duty.
8. Release planning requires completed independent Quality evidence wherever cross-review is required and reports `Quality Office Jarvis` consistently.
9. Active control-plane files in Owned Paths pass a case-insensitive search proving removal of `claude`, `no-claude`, `QA Office`, and `JARVIS QA Office`.
10. Backward-compatible read/status/release inspection of existing mission evidence succeeds without rewriting historical mission JSON.
11. The full control-plane and charter test suites pass, including routing, readiness, scope, lease, evidence-history, independent-review, and release-gate regressions.
12. Build reports exact baseline, commit, changed files, test outputs, and any intentionally retained historical compatibility keys. Quality independently maps evidence to every criterion.

## Required Evidence Commands

```bash
python3 -m pytest -q tests/test_build_office.py tests/test_office_charters.py
python3 scripts/jarvis_build_office.py doctor
python3 scripts/jarvis_build_office.py init --help
python3 scripts/jarvis_build_office.py inbox codex
rg -n -i 'claude|no-claude|QA Office|JARVIS QA Office' jarvis/build_office.py jarvis/office_charters.py scripts/jarvis_build_office.py tests/test_build_office.py tests/test_office_charters.py docs/BUILD-OFFICE-AUTOMATION.md docs/OFFICE-CHARTERS.md
git diff --check <baseline>..<implementation-commit>
git diff --name-only <baseline>..<implementation-commit>
```

The `rg` acceptance command must return no matches. Tests may exercise legacy input compatibility without spelling the retired provider name in active source by using fixtures derived from historical mission evidence.

## Build Order

1. Add failing tests for canonical office names, Codex-only routing, high-risk analysis, independent Quality review, and historical mission readability.
2. Replace provider-based routing with duty/office-based Codex assignments and remove provider-selection CLI surfaces.
3. Rename the review charter and every active user-facing reference to `Quality Office Jarvis`.
4. Remove the fallback route concept and make the canonical route the only route.
5. Preserve read-only compatibility for historical missions without rewriting durable evidence.
6. Update active operator documentation and examples.
7. Run all required evidence commands and commit only Owned Paths from an isolated Build worktree.
8. Route the immutable implementation commit to Quality Office Jarvis for independent read-only review.
