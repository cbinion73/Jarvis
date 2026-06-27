# JARVIS Fact Base Map

Date: 2026-06-27
Repo: `/Users/chris/Desktop/CODE/JARVIS`
Branch: `phase-1-companion-spine`
HEAD: `458158c`

This is a repo-truth map, not a roadmap.

## 1. Current Build State

- primary repo is dirty
- current work includes:
  - Architect Office governance files
  - companion spine files
  - Obsidian retrieval files
  - runtime data churn under `data/`
- Epic 1 governance was isolated and procedurally approved in:
  - `/Users/chris/Desktop/JARVIS-epic1-governance-clone`

## 2. Core Runtime Spine

- service entry:
  - `jarvis/service.py`
- runtime orchestration:
  - `jarvis/runtime.py`
- companion seam:
  - `jarvis/companion_spine.py`
- shell/front-door behavior:
  - `jarvis/voice_ui.py`
- model client seam:
  - `jarvis/openai_tasks.py`

Observed flow:

`/api/respond` -> `JarvisRuntime.converse()` -> `run_companion_turn()` -> model client or fallback -> persisted conversation turn

## 3. Confirmed Runtime Surfaces

- `/health`
- `/api/respond`
- `/api/gateway/status`
- `/api/obsidian/status`

Observed repo fact:

- `jarvis/service.py` currently contains `846` API routes

Interpretation:

- JARVIS is already a very broad system
- review difficulty is high
- consolidation matters more than adding more breadth

## 4. Companion Mind State

Confirmed:

- a dedicated companion spine file exists
- the spine builds a compact context packet
- the spine carries voice standard, truth constraints, and fallback behavior
- `JarvisRuntime.converse()` routes ordinary conversation through that seam

Open concerns:

- this work is still mixed into the main repo instead of presented as a clean isolated slice
- the larger surrounding platform can still overpower the companion center
- Architect Office still needs canon/runtime reconciliation before treating the companion path as fully accepted product direction

## 5. Memory / Obsidian State

Confirmed in code:

- `jarvis/obsidian_context.py` exists
- local vault path and derived index path are configurable in `jarvis/config.py`
- runtime exposes `obsidian_status()`
- `/health` and `/api/obsidian/status` surface Obsidian state
- companion path can include retrieved Obsidian note context

Open concerns:

- active canon still says Obsidian is not live-integrated yet
- runtime truth appears ahead of canon
- this must be reconciled before further product approval

## 6. Domain Breadth

Large specialist/domain presence is evident in the service layer, including:

- health
- chronicle
- family / household
- dining
- navigation
- publishing / foundry
- workshop / forge
- growth
- scheduler
- memory
- identity

Architect Office interpretation:

- these may be real and valuable
- they should support the companion center, not replace it
- the breadth increases the risk of platform sprawl and dashboard-first behavior

## 7. Governance State

Confirmed:

- Canon Registry exists
- QA Team Protocol exists
- JARVIS Master Build Plan exists
- JARVIS Preservation Map exists
- Build Request template exists
- Architecture Review template exists
- Architect Office CLI review path exists

Open concern:

- `docs/CHRIS-INTENT-CANON.md` is still missing even though canon expects it

## 8. Best Current Product Loop

Most important currently protected loop:

`conversation -> mission -> visible workspace -> Daily Brief -> open loops -> follow-through`

Why it matters:

- this is the clearest current candidate for the real Jarvis center
- it fits the preservation map
- it fits the Chris context canon
- it gives Architect Office a concrete consolidation target

## 9. Main Risks

- mixed primary worktree
- missing Chris Intent canon
- Obsidian canon/runtime drift
- extremely broad service surface
- specialist/domain breadth outrunning companion consolidation

## 10. Recommended Next Sequence

1. resolve missing Chris Intent canon
2. reconcile Obsidian canon against runtime truth
3. continue a deeper fact-base map focused on the protected core loop
4. define the next bounded Build Office slice from that grounded baseline
