# Post-Epic 9 Slice 3: Cross-Surface State-Label and Return-Path Continuity Hardening

## Surfaces Reviewed

- Delegation report review readable surface
- Artifact outcome review readable surface
- Research task queue readable surface
- Research task review readable surface
- Autonomy state review readable surface
- Adjacent mission-board return wording used by those readable surfaces

## Continuity Drifts Found

1. Several recorded-state review surfaces still used a generic `Return` action label even when the destination was a specific queue, summary, or mission-board surface.
2. The research queue hero heading still said `Inspectable Research Intent` even though Slice 2 normalized the body copy to `inspectable research task records`.
3. The generic return wording risked weakening the recorded-state vocabulary when moving between queue, review, and summary surfaces.

## Bounded Repairs Made

- Artifact outcome review now computes a truthful return label based on the actual safe return target:
  - `Return to Outcome Summary`
  - `Return to Delegation Review`
  - `Return to Mission Board`
  - fallback: `Return to Review Surface`
- Research task queue heading now reads `Inspectable Research Task Records`.
- Research task queue return link now reads `Return to Mission Board`.
- Research task review return link now reads `Return to Research Task Queue`.
- Autonomy state review return link now reads `Return to Autonomy State Queue`.
- Added focused regression assertions covering the new heading and return labels, including the dynamic outcome-summary return case.

## Truth Guarantees Preserved

- No surface now implies a broader action lane than the linked destination actually provides.
- Recorded-state pages still read as recorded-state pages when entering and leaving them.
- No new execution, agent, research, or autonomy capability was added.
- Return wording now stays aligned with the established `recorded-state / inspectable-output / bounded-proof` vocabulary from Slice 2.

## Tests / Validation

1. `python3 -m compileall jarvis/render_pages.py tests/test_command_center_service_surface.py`
   - Result: passed
2. `python3 -m pytest -q tests/test_command_center_service_surface.py -k "artifact_outcome_review_surface or artifact_outcome_summary_to_review_link_preserves_summary_return_path or names_summary_return_path_plainly or research_task_queue_surface or research_task_review_surface or autonomy_state_review_surface_renders_real_state_and_boundary or delegation_report_review_surface"`
   - Result: `17 passed, 91 deselected in 0.28s`

## Residual Risks

- A few older non-target surfaces outside this recorded-state family still use generic `Back` / `Return` phrasing, but they were outside this bounded slice and were not changed.
- If future slices add new review surfaces, they should follow the same specific return-label pattern rather than reintroducing generic `Return` wording.

## Recommendation

- Recommended next bounded Post-Epic 9 slice: a narrow shared-heading and adjacent action-label sweep for older non-recorded-state module pages only where they directly touch these approved review lanes, without broad navigation rewrite.
