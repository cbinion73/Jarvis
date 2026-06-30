# Epic 8 Slice 6: Research Task Lane Closeout Validation

## Scope

- Rechecked the full bounded Epic 8 research-task lane together:
  - task creation
  - queue view
  - readable review view
  - task update/status editing
  - evidence capture
  - attached-evidence-only synthesis
- Verified that the lane still stays inside explicit research-task truth boundaries.
- Made one small closeout repair for synthesis-flow precondition clarity on the readable review page.

## Closeout Validation Scope

- Store/runtime seam:
  - `ResearchTaskStore`
  - `JarvisRuntime` research-task helpers
- Service/API seam:
  - `/api/research-tasks`
  - `/api/research-tasks/{task_id}`
  - `/api/research-tasks/{task_id}/evidence`
  - `/api/research-tasks/{task_id}/synthesis`
- Readable page seam:
  - queue view
  - task review page
  - authoring/update forms
  - evidence rendering
  - synthesis rendering
- Validation seam:
  - targeted research-task tests
  - full command-center service surface test file

## Defects Found and Repairs Made

- Found one small closeout defect:
  - the readable synthesis lane was truthful after use, but it did not plainly state up front that synthesis requires at least one attached evidence item first
- Repair made:
  - tightened the review-page synthesis wording so the precondition is explicit before the user triggers the action
  - tightened the empty-synthesis state so it tells the user to attach evidence first, then generate a task-scoped synthesis from attached evidence only
  - added assertion coverage for this wording in the service-surface tests

## Truth / Research-Boundary Guarantees Confirmed

- No fake source discovery claims.
- No invisible or autonomous background research claims.
- No implication that task capture means research happened.
- No implication that evidence capture means research is complete.
- No implication that evidence-backed synthesis means research is complete.
- No implication of external validation unless explicitly recorded.
- Synthesis remains explicitly limited to evidence already attached to the task in the current runtime path.

## Tests Run

- `python3 -m compileall jarvis/research_tasks.py jarvis/runtime.py jarvis/service.py jarvis/render_pages.py tests/test_research_tasks.py tests/test_command_center_service_surface.py`
- `python3 -m pytest -q tests/test_research_tasks.py tests/test_command_center_service_surface.py -k "research_task"`
  - `21 passed, 79 deselected`
- `python3 -m pytest -q tests/test_command_center_service_surface.py`
  - `93 passed, 106 warnings`

## Residual Notes

- Existing broader-suite deprecation warnings remain outside the bounded Epic 8 lane.
- No broader research dashboard, autonomous discovery, or recommendation behavior was added in this closeout pass.

## Recommendation

Epic 8 appears procedurally ready for Architect Office closeout review from current repo truth.
