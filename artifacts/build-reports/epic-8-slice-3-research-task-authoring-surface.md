# Epic 8 Slice 3: Research Task Authoring Continuity and Status Control

## Scope

- Added one bounded authoring/update flow on the readable research-task review surface.
- Kept the slice limited to task-field edits and explicit bounded status control.
- Did not add research synthesis, evidence gathering, source discovery, or autonomous execution.

## Research Task Authoring Surface Added

- Added persisted update support in `ResearchTaskStore`.
- Added runtime update seam:
  - `update_research_task(...)`
- Added service update route:
  - `POST /api/research-tasks/{task_id}`
- Extended the readable review page at `GET /mission-board/research-tasks/{task_id}` with a small edit/update form.
- Supported bounded updates for:
  - title
  - research question
  - desired scope
  - status
  - constraints
  - source expectations

## Status Control Contract

- Allowed statuses remain:
  - `queued`
  - `in_progress`
  - `blocked`
  - `completed`
- Changing task status does not imply:
  - completed research
  - discovered sources
  - autonomous background execution
- The readable page explicitly states that status alone is not proof that research output or sources exist.

## Truth / Research Boundary Guarantees

- The update route returns explicit wording that task changes do not imply research, source discovery, or autonomous execution already happened.
- The readable page continues to state that research has not yet been performed when no work artifacts exist.
- No fake source discovery or hidden research activity was introduced by the authoring flow.

## Tests Run

- `python3 -m compileall jarvis/research_tasks.py jarvis/runtime.py jarvis/render_pages.py jarvis/service.py tests/test_research_tasks.py tests/test_command_center_service_surface.py`
- `python3 -m pytest -q tests/test_research_tasks.py tests/test_command_center_service_surface.py -k "research_task"`
  - `12 passed, 79 deselected`
- `python3 -m pytest -q tests/test_command_center_service_surface.py`
  - `87 passed, 106 warnings`

## Open Defects / Blockers

- No slice-blocking defects found in the bounded task authoring/update path.
- Existing broader-suite deprecation warnings remain outside Epic 8 slice 3 scope.

## Recommendation

Epic 8 slice 3 appears ready for Architect Office review.
