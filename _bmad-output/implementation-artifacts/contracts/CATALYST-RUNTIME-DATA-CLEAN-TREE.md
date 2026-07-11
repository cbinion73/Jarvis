# Frozen Architect Contract: Catalyst Runtime Data Clean-Tree Hygiene

Status: **FROZEN**

Contract version: **1.0.0**

Risk: **medium**

Scope: **Catalyst runtime persistence hygiene only; no Catalyst product behavior redesign**

## Problem

The Architect heartbeat repeatedly finds the main checkout dirty because Catalyst proactive surfacing appends runtime records to:

- `data/catalyst/proactive_surfacing_runs.json`

That file is currently tracked by Git, so normal runtime activity blocks Build Office mission intake and release gates.

The repeated runtime changes have been preserved in stashes instead of discarded:

- `architect-heartbeat-preserve-catalyst-runtime-data-2026-07-11T11-01Z`
- `architect-heartbeat-preserve-catalyst-runtime-data-2026-07-11T11-06Z`
- `architect-heartbeat-preserve-catalyst-runtime-data-2026-07-11T11-12Z`
- `architect-heartbeat-preserve-catalyst-runtime-data-2026-07-11T11-17Z`
- `architect-heartbeat-preserve-catalyst-runtime-data-2026-07-11T11-22Z`
- `architect-heartbeat-preserve-catalyst-runtime-data-2026-07-11T11-27Z`

## Invariants

1. Runtime-generated Catalyst output must not dirty the source checkout during Build Office heartbeat, mission intake, QA review, or release planning.
2. No user runtime data may be discarded. Existing generated records must remain recoverable from the current stashes unless a later explicit migration/merge decision is made.
3. The fix must not change the semantics of Catalyst proactive surfacing output: same public API shape, same fields, same append/read behavior from the caller perspective.
4. Source-controlled examples, fixtures, and seed data may remain tracked, but live append targets must be outside tracked source files or explicitly ignored.
5. The Build Office control plane must continue to treat a dirty main checkout as a blocker. This contract fixes the runtime writer, not the release-gate invariant.
6. No Orchestration involvement.
7. No merge, push, production deployment, credential access, or destructive cleanup.

## Owned Paths

Build may modify only:

- `jarvis/catalyst.py`
- `jarvis/scheduler.py`
- `jarvis/service.py`
- `jarvis/main.py`
- `tests/**`
- `.gitignore`
- `docs/**`

If implementation proves only `jarvis/catalyst.py`, tests, `.gitignore`, and docs are needed, prefer that narrower path set.

## Forbidden Paths

Build must not modify:

- `.env`
- `.env.*`
- `deploy/**`
- `_bmad-output/build-office-runs/**` except through supported Build Office CLI/API transitions
- `_bmad-output/implementation-artifacts/contracts/CATALYST-RUNTIME-DATA-CLEAN-TREE.md`
- `data/catalyst/proactive_surfacing_runs.json` except if the implementation removes it from tracking through a clearly documented, reviewed migration step
- unrelated product/runtime files

## Acceptance Criteria

### AC1 — Runtime writes do not dirty main

Running Catalyst proactive surfacing from a clean main checkout must not modify any tracked file.

Required verification:

```bash
git status --short
python3 -m jarvis catalyst-proactive --actor Chris --horizon today --context "clean-tree regression"
git status --short
```

The final status must be clean except for files explicitly created in ignored runtime paths.

### AC2 — Runtime records are still persisted

The proactive surfacing run must still append a recoverable record with:

- `run_id`
- `actor`
- `horizon`
- `opportunities`
- `risks`
- `recommended_focus`
- `raw_output`
- `timestamp`

The record may be persisted in an ignored runtime/state location rather than the tracked source file.

### AC3 — Existing tracked sample/seed behavior is preserved

If `data/catalyst/proactive_surfacing_runs.json` remains in the repository as seed/sample history, reads must continue to work. Runtime appends must target the live runtime store, not mutate the tracked seed.

If the file is removed from tracking, Build must provide a migration note and tests proving callers still see expected records from the runtime location.

### AC4 — Git ignore/source hygiene

The live runtime path must be covered by `.gitignore` or an equivalent existing ignored location. Tests must prove the generated runtime file path is not a tracked source file.

### AC5 — Tests

Add focused regression coverage proving:

- Catalyst proactive surfacing writes to the runtime path, not the tracked seed path.
- A clean checkout remains clean after a proactive surfacing run.
- The returned API payload is unchanged.
- Existing seed/sample data can still be read when relevant.

### AC6 — Evidence and release gate

Build must provide:

```bash
python3 -m pytest -q <relevant tests>
python3 -m jarvis catalyst-proactive --actor Chris --horizon today --context "clean-tree regression"
git status --short
git diff --check <baseline>..<implementation-commit>
git diff --name-only <baseline>..<implementation-commit>
```

Quality must independently verify that `python3 scripts/jarvis_build_office.py heartbeat architect --cadence-seconds 300` no longer reports `main-checkout-dirty` after a Catalyst proactive surfacing run.

## Build Order

1. Add regression tests that reproduce the tracked-file dirtying behavior.
2. Introduce a runtime data location for Catalyst proactive surfacing appends.
3. Preserve caller-facing payload behavior.
4. Add ignore/source hygiene for the runtime location.
5. Run Catalyst proactive surfacing from a clean checkout and prove Git remains clean.
6. Commit only owned paths in an isolated worktree.
7. Route immutable Build evidence to Quality Office Jarvis.

## Non-goals

- No change to the content or intelligence of Catalyst recommendations.
- No calendar/email/bank integration.
- No migration of the preserved stash contents unless separately authorized.
- No release merge or push.
