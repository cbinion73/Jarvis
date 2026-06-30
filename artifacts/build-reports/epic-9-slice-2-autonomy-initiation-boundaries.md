# Epic 9 Slice 2: Explicit Autonomy Task Initiation Boundaries

## Scope

- Extended the existing `autonomy_state` object family with explicit initiation-boundary fields.
- Kept the slice limited to inspectable initiation scope, reason, approval posture, allowed boundary, and blocked posture.
- Reused the existing autonomy-state API and readable page family rather than adding a broader autonomy dashboard or execution control plane.

## Autonomy Initiation Boundary Surface Added

- Extended persisted autonomy-state records with:
  - `requested_scope`
  - `initiation_reason`
  - `approval_required`
  - `approval_state`
  - `allowed_action_boundary`
  - `blocked_reason`
- Extended runtime seam:
  - `create_autonomy_state(...)` now records explicit initiation boundaries
  - autonomy snapshot/queue payloads now expose allowed approval states
- Extended API route:
  - `POST /api/autonomy-states` now accepts explicit initiation-boundary fields
- Extended readable surfaces:
  - queue page now shows approval state, allowed boundary, requested scope, initiation reason, and blocked reason
  - review page now shows the full initiation-boundary contract directly on the readable state

## Truth / Autonomy-Boundary Guarantees

- Recording initiation does not mean autonomous execution has started.
- Approval state is stored explicitly and is not faked.
- Allowed action boundary is stored explicitly and shown back to the user.
- Blocked posture is stored explicitly when the record is not yet allowed to proceed.
- No invisible execution claims, no fake agents, and no implication that a recorded initiation can act beyond the stored boundary.

## Tests Run

- `python3 -m compileall jarvis/autonomy_state.py jarvis/runtime.py jarvis/service.py jarvis/render_pages.py tests/test_autonomy_state.py tests/test_command_center_service_surface.py`
- `python3 -m pytest -q tests/test_autonomy_state.py tests/test_command_center_service_surface.py -k "autonomy_state"`
  - `8 passed, 93 deselected`
- `python3 -m pytest -q tests/test_command_center_service_surface.py`
  - `97 passed, 106 warnings`

## Open Defects / Blockers Logged

- No slice-blocking defects found in the bounded autonomy initiation lane.
- Existing broader-suite deprecation warnings remain outside Epic 9 slice 2 scope.

## Recommendation

Epic 9 slice 2 appears ready for Architect Office review.
