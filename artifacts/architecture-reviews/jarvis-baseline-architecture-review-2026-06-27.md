# JARVIS Baseline Architecture Review

Date: 2026-06-27
Repo: `/Users/chris/Desktop/CODE/JARVIS`
Branch: `phase-1-companion-spine`
HEAD: `458158c`

## Decision

- decision: Needs Rework
- scope: baseline Architecture Office review of the current primary JARVIS repo state
- reason: the repo contains meaningful capability, but the current primary worktree is mixed, canon is incomplete, and runtime truth has drifted ahead of canon in at least one important area

## Canon Sources Checked

- `docs/CANON-REGISTRY.md`
- `docs/PHASE-GATES.md`
- `docs/CHRIS-CONTEXT-CANON.md`
- `docs/JARVIS-MASTER-BUILD-PLAN.md`
- `docs/JARVIS-PRESERVATION-MAP.md`
- `docs/ARCHITECTURE-OFFICE-PROTOCOL.md`
- `docs/BUILD-OFFICE-PROTOCOL.md`

## Chris Canon Sources Checked

- `docs/CHRIS-CONTEXT-CANON.md`
- `docs/CHRIS-INTENT-CANON.md` missing

## Scope Checked

- active branch: `phase-1-companion-spine`
- HEAD commit: `458158c`
- current git status: dirty and mixed
- Epic 1 governance loop: procedurally approved in isolated review state, not yet merged as a clean primary repo slice
- product/runtime review target: current repo truth, including in-flight companion and Obsidian work

## Repo Facts

- FastAPI service exists in `jarvis/service.py`
- current endpoint count in `jarvis/service.py`: `846`
- key routes present:
  - `/health`
  - `/api/respond`
  - `/api/gateway/status`
  - `/api/obsidian/status`
- primary conversation path:
  - `jarvis/service.py` -> `/api/respond`
  - `jarvis/runtime.py` -> `JarvisRuntime.converse()`
  - `jarvis/companion_spine.py` -> `run_companion_turn()`
- test file count under `tests/`: `175`

## Current Strengths

- JARVIS is not empty. It already contains a large real system with a working runtime, persistent conversation loop, mission/workspace ideas, and many domain surfaces.
- The companion spine seam now exists in code and is routed through `JarvisRuntime.converse()`.
- The service exposes clear health and gateway endpoints, which supports runtime inspection.
- Obsidian retrieval infrastructure now exists in code with local vault/index handling and an exposed status endpoint.
- The repo has broad test coverage by count, including focused tests for the new Architect Office layer and companion/Obsidian slices.
- The preservation map correctly identifies the strongest current loop as:
  `conversation -> mission -> visible workspace -> Daily Brief -> open loops -> follow-through`

## Current Risks

- The main repo is still a mixed worktree. Governance changes, product/runtime changes, and runtime data churn are all present together.
- `docs/CHRIS-INTENT-CANON.md` is missing, so Architect Office cannot fully evaluate product fit against the intended authoritative Chris canon stack.
- Current canon still says `docs/CHRIS-INTENT-CANON.md` is binding, but the file is absent.
- Current canon and current runtime truth appear to be out of sync on Obsidian:
  - `docs/CHRIS-CONTEXT-CANON.md` says Obsidian is external and not live-integrated yet.
  - current code in `jarvis/obsidian_context.py`, `jarvis/runtime.py`, `jarvis/service.py`, and `jarvis/companion_spine.py` indicates a real local retrieval path is being wired and surfaced.
- `jarvis/service.py` is extremely broad. A service file with `846` routes is a maintainability and review-risk signal by itself.
- The repo appears to contain many strong specialist/domain surfaces. That is useful, but it increases the risk that JARVIS behaves like a broad platform before the companion center is fully consolidated.

## Product Drift Findings

- Companion drift risk:
  the companion path is present, but it is still surrounded by a much larger platform surface that can easily pull the product back toward dashboard or module sprawl.
- Canon drift risk:
  runtime capability has moved ahead of canon on Obsidian.
- Evaluation drift risk:
  without `docs/CHRIS-INTENT-CANON.md`, product-fit review remains partially blind.
- Surface drift risk:
  the core companion loop exists, but the repo still advertises and implements many non-core centers.

## Architecture Office Judgment

- Epic 1 governance setup is now strong enough to manage the next work properly.
- The current primary repo is not ready for broad new product expansion.
- The correct next step is not “build more features.”
- The correct next step is:
  1. complete the fact-base map of what is already real
  2. reconcile canon against runtime truth
  3. define the next narrow approved implementation slice from that grounded baseline

## Required Follow-Up

- create `docs/CHRIS-INTENT-CANON.md` or explicitly revise canon so Architect Office is not pointing at a missing binding source
- reconcile the Obsidian canon statement with current runtime reality
- complete a fact-base map of the strongest currently real product loop and surrounding major domains
- avoid approving broad product work directly from the current mixed main repo state
- define the next bounded Build Office slice only after the canon/runtime reconciliation step

## Final Judgment

- baseline procedural outcome: Needs Rework
- meaning: JARVIS has real substance, but the current repo state is not yet clean enough or canon-aligned enough for confident forward approval
