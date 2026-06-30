# Epic 12 Slice 4: Recommendation to Action Surface

## Scope Reviewed
- `jarvis/morning_brief_pipeline.py`
- `jarvis/service.py`
- `jarvis/render_pages.py`
- `tests/test_morning_brief_pipeline.py`
- `tests/test_command_center_service_surface.py`

## Action-Surface Gaps Found
- Morning Brief recommendations ended at narrative text even when a real current repo surface already existed.
- The brief did not distinguish between:
  - a recommendation with a real direct route
  - a recommendation with only a bounded review/intake handoff
  - a recommendation that should stay narrative-only
- `/briefing-center` had a separate conversation-follow route, but no recommendation-specific action contract tied to the actual recommendation branch.

## Bounded Repairs Made
- Added `recommendation_action` to the Morning Brief result contract.
- Added three explicit handoff modes:
  - `direct_route`
  - `bounded_request`
  - `narrative_only`
- Mapped existing recommendation branches to truthful current repo destinations only:
  - degraded agents -> `/agent-ops-center`
  - repo review / progress -> `/progress-center`
  - open-loop pressure -> `/mission-board` as bounded handoff
  - recorded catch-up review -> `/activity-center`
  - inbox pressure -> `/email-center`
  - Google recovery posture -> `/settings-center`
  - composite live-signal guidance -> narrative-only
- Added a compact `Next Honest Step` surface to `/briefing-center`.
- Kept the action copy explicit that opening a route is not execution, completion, save, or hidden follow-through.
- Added service fallback behavior so error-state briefs still expose a truthful narrative-only handoff posture.

## Truth Guarantees Preserved
- Direct actions only point to real current repo routes.
- Bounded handoff wording stays explicit when there is no direct object-level open target.
- Narrative-only posture remains plain when no single truthful next surface exists.
- No fake launch, save, open-object, or completion claims were added.
- Recommendation quality remains primary; the action surface is compact and secondary.

## Tests / Validation
- `python3 -m py_compile jarvis/morning_brief_pipeline.py jarvis/render_pages.py jarvis/service.py`
  - passed
- `python3 -m pytest -q tests/test_morning_brief_pipeline.py tests/test_command_center_service_surface.py::CommandCenterServiceSurfaceTests::test_served_routes_expose_command_center_index_and_snapshot`
  - passed
  - result: `28 passed, 42 warnings in 18.22s`

## Blockers / Residual Risks
- The recommendation-to-action mapping is intentionally branch-level, not object-specific; some recommendations still only truthfully support family-route handoff rather than deep object handoff.
- Composite brief guidance remains narrative-only when a single precise next surface would overstate certainty.
- Existing deprecation warnings in unrelated drift/longevity code remain outside this slice.

## Recommendation
- Ready for Architect Office review.
- Next bounded move, if desired: tighten object-specific handoff only where the Morning Brief later gains real saved-object identifiers to target directly.
