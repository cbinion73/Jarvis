---
title: 'JARVIS Capability Maturity Ledger'
type: 'feature'
created: '2026-07-11'
status: 'done'
review_loop_iteration: 0
baseline_commit: '49ee92a21e53a51898c52c6e7245eeba243eb84c'
context:
  - '{project-root}/docs/README.md'
  - '{project-root}/docs/CHRIS-INTENT-CANON.md'
  - '{project-root}/docs/CHRIS-CONTEXT-CANON.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The repository contains broad capabilities but no current, evidence-backed view connecting the desired Jarvis behaviors to their actual implementation maturity. Existing route counts, historical checklists, and passing unit tests can overstate what works end to end.

**Approach:** Create one standalone interactive HTML capability ledger derived from the foundational Jarvis model. Score every item from 1–10 using code, route, test, integration, and live-runtime evidence; show the supporting evidence and missing condition; preserve user checklist state locally; then launch and visually verify the ledger.

## Boundaries & Constraints

**Always:** Keep the companion identity central; distinguish code presence from wired and functioning behavior; include exact evidence paths; disclose simulated, unavailable, stale, or unverified integrations; define the scoring rubric inside the interface; support filtering, search, expandable evidence, progress tracking, and local persistence; preserve unrelated work.

**Ask First:** Adding the dashboard to the production FastAPI navigation, changing capability implementations, pushing or deploying, or replacing an existing canonical document.

**Never:** Claim production or device functionality from route names alone; treat archived household doctrine as current authority; modify capability scores when the user checks an item; overwrite existing mockups; bundle unrelated source changes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Initial view | No saved browser state | All capability groups, evidence-based scores, rubric, gaps, and summary metrics render | Static baseline remains usable without network or backend |
| Progress tracking | User checks items or adds notes | Completion state and notes persist locally; maturity score remains evidence-derived | Invalid stored state is ignored and reset safely |
| Filtering | Search, domain, score, or completion filter | Matching capabilities and aggregate counts update immediately | Empty results show a clear reset path |
| Evidence inspection | User expands a capability | Exact files/routes/tests and score rationale appear | Missing live proof is labeled unverified rather than inferred |

</frozen-after-approval>

## Code Map

- `artifacts/mockups/jarvis-capability-maturity-ledger.html` -- new standalone, launchable capability checklist and maturity dashboard.
- `docs/README.md` -- current product scope, architecture truth, runtime state, and guardrails.
- `docs/CHRIS-INTENT-CANON.md` -- desired capability hierarchy and behavior contract.
- `docs/CHRIS-CONTEXT-CANON.md` -- relationship, voice, workbench, and acceptance expectations.
- `jarvis/service.py` -- real HTTP entrypoints and UI/API surface evidence.
- `jarvis/runtime.py` -- orchestration and capability wiring evidence.
- `tests/` -- behavioral and integration evidence used to calibrate scores.

## Tasks & Acceptance

**Execution:**
- [x] Audit current routes, runtime call paths, modules, tests, integration configuration, and live health for each foundational capability.
- [x] `artifacts/mockups/jarvis-capability-maturity-ledger.html` -- implement the complete evidence ledger with responsive layout, score summaries, filters, checklist persistence, notes, and expandable evidence.
- [x] Launch the HTML in the in-app browser and verify rendering, interaction, persistence, filtering, and responsive behavior.

**Acceptance Criteria:**
- Given the foundational Jarvis model, when the ledger opens, then every identified function, behavior, input, safety boundary, and operational capability appears exactly once in a clear domain.
- Given any maturity score, when its evidence is expanded, then the interface states what exists, what was verified, and what prevents the next maturity level.
- Given user progress changes, when the page reloads, then checked state and notes persist without changing evidence-based maturity.
- Given an unavailable or simulated external integration, when it is scored, then the limitation is explicit and the score does not imply live operation.

## Spec Change Log

## Design Notes

Use a dense Architect Office control surface rather than a decorative presentation. Maturity color should encode score bands, while checklist completion is a separate visual dimension. The overall score is descriptive, not a project completion percentage.

## Verification

**Commands:**
- `git diff --check` -- expected: no whitespace errors.
- Parse/extract the HTML with an available local parser -- expected: one document, unique capability IDs, valid embedded data, and no missing required fields.
- Serve locally and request the page -- expected: HTTP 200 with the intended title.

**Manual checks:**
- Open in the in-app browser; verify summary cards, filters, evidence expansion, checkboxes, notes persistence, and narrow viewport layout.

## Suggested Review Order

**Capability baseline**

- Start with the scored inventory, evidence, and explicit maturity gaps.
  [`jarvis-capability-maturity-ledger.html:22`](../../artifacts/mockups/jarvis-capability-maturity-ledger.html#L22)

- Review newly explicit Self-Research and life-context coverage.
  [`jarvis-capability-maturity-ledger.html:28`](../../artifacts/mockups/jarvis-capability-maturity-ledger.html#L28)

**Truth and presentation**

- Confirm repository configuration is distinguished from verified live production state.
  [`jarvis-capability-maturity-ledger.html:15`](../../artifacts/mockups/jarvis-capability-maturity-ledger.html#L15)

- Inspect responsive, accessible score-band presentation.
  [`jarvis-capability-maturity-ledger.html:8`](../../artifacts/mockups/jarvis-capability-maturity-ledger.html#L8)

**Interaction and persistence**

- Review validated local state, filtered metrics, and safe persistence behavior.
  [`jarvis-capability-maturity-ledger.html:90`](../../artifacts/mockups/jarvis-capability-maturity-ledger.html#L90)

- Verify filtering, evidence disclosure, tracking, notes, and cross-tab refresh.
  [`jarvis-capability-maturity-ledger.html:93`](../../artifacts/mockups/jarvis-capability-maturity-ledger.html#L93)
