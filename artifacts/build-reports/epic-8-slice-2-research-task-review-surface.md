# Epic 8 Slice 2: Research Task Review Surface and Continuity

## Scope

- Added one bounded readable review surface for persisted research-task objects.
- Kept the slice limited to queue-to-review continuity and truthful inspection.
- Did not add research synthesis, source gathering, or background execution.

## Research Task Review Surface Added

- Added readable route:
  - `GET /mission-board/research-tasks/{task_id}`
- Added continuity from the queue page:
  - queue cards now link to the readable task review page
  - readable review page carries a local `return_to` path back to the queue
- The review page exposes real stored task data:
  - title
  - research question
  - desired scope
  - status
  - constraints
  - source expectations
  - created timestamp
  - truth mode
  - explicit not-yet-researched state

## Truth / Research Boundary Guarantees

- The readable review page explicitly says that research has not yet been performed for the task when no work exists.
- The page explicitly says it does not claim completed research, discovered sources, or autonomous background execution.
- Queue-to-review continuity does not add any new capability claims; it only exposes the real stored task object through a readable surface.

## Tests Run

- `python3 -m compileall jarvis/render_pages.py jarvis/service.py tests/test_command_center_service_surface.py`
- `python3 -m pytest -q tests/test_research_tasks.py tests/test_command_center_service_surface.py -k "research_task"`
  - `9 passed, 79 deselected`
- `python3 -m pytest -q tests/test_command_center_service_surface.py`
  - `85 passed, 106 warnings`

## Open Defects / Blockers

- No slice-blocking defects found in this readable review continuity path.
- Existing broader-suite deprecation warnings remain outside Epic 8 slice 2 scope.

## Recommendation

Epic 8 slice 2 appears ready for Architect Office review.
