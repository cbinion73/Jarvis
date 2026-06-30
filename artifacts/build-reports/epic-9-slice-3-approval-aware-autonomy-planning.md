# Epic 9 Slice 3: Approval-Aware Autonomy Action Planning

Date: 2026-06-28T09:44:06Z
Repo: `/Users/chris/Desktop/CODE/JARVIS`

## Scope

- Extend the existing autonomy-state family with a bounded proposed-action planning seam.
- Keep proposed actions explicit, inspectable, approval-aware, and not-run by default.
- Expose the plan through the existing autonomy review lane rather than a new dashboard.

## Approval-Aware Autonomy Planning Surface Added

- Added persisted autonomy planning fields on the existing autonomy-state object:
  - `planning_note`
  - `proposed_actions`
  - `planned_action_count`
  - `has_proposed_plan`
- Added per-action plan structure with:
  - `action_id`
  - `title`
  - `rationale`
  - `approval_needed`
  - `approval_state`
  - `execution_status`
  - `sequence`
  - `planned_at`
- Added bounded plan-writing runtime/service seam:
  - `JarvisRuntime.add_autonomy_action_plan(...)`
  - `POST /api/autonomy-states/{autonomy_id}/plan`
- Extended the readable autonomy review page with a `Proposed Action Plan` section that renders:
  - planning note
  - each proposed action
  - explicit `proposed_not_run` execution status
  - approval dependence per action

## Truth / Autonomy-Boundary Guarantees

- Planned actions are stored as planning only, not execution.
- `execution_status` is restricted to `proposed_not_run` in this slice.
- The UI and API wording explicitly say the plan does not mean actions ran, approval exists, or autonomous follow-through happened.
- No background execution, fake agent progress, or approval bypass is implied.
- The slice reuses the existing autonomy-state record instead of inventing a parallel autonomy theater surface.

## Open Defects / Blockers Logged

- No new local blocker was found in this bounded slice.
- Broader autonomous execution, approval progression, and follow-through remain intentionally out of scope.

## Tests / Validation

- `python3 -m compileall jarvis/autonomy_state.py jarvis/runtime.py jarvis/service.py jarvis/render_pages.py tests/test_autonomy_state.py tests/test_command_center_service_surface.py`
- `python3 -m pytest -q tests/test_autonomy_state.py tests/test_command_center_service_surface.py -k "autonomy_state or autonomy_plan"`
  - `12 passed, 93 deselected`
- `python3 -m pytest -q tests/test_autonomy_state.py`
  - `6 passed`
- `python3 -m pytest -q tests/test_command_center_service_surface.py`
  - `99 passed, 106 warnings`

## Files Touched

- `jarvis/autonomy_state.py`
- `jarvis/runtime.py`
- `jarvis/service.py`
- `jarvis/render_pages.py`
- `tests/test_autonomy_state.py`
- `tests/test_command_center_service_surface.py`

## Recommendation

- Ready for Architect Office review as a bounded approval-aware planning seam.
- The lane now distinguishes stored initiation state from stored proposed actions, and stored proposed actions from any executed autonomy.
