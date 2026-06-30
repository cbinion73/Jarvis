# Epic 8 Slice 1: Research Task Capture and Inspectable Queue

## Scope

- Added one bounded persisted research-task primitive.
- Kept the slice limited to explicit task capture and inspection only.
- Did not add automatic research, source discovery, synthesis, or background execution.

## Research Task Surface Added

- Added `ResearchTaskStore` in `jarvis/research_tasks.py`.
- Added runtime seams:
  - `create_research_task(...)`
  - `research_task_snapshot(...)`
  - `research_task_queue_snapshot(...)`
- Added service routes:
  - `POST /api/research-tasks`
  - `GET /api/research-tasks`
  - `GET /api/research-tasks/{task_id}`
  - `GET /mission-board/research-tasks`
- Added a readable queue page that exposes:
  - topic/title
  - question
  - desired scope
  - status
  - constraints
  - source expectations
  - created time
  - plain research-state boundary

## Truth / Research-Boundary Guarantees

- Capturing a research task does not claim that research has already happened.
- The queue page explicitly says that queued intent is not completed research.
- No fake source discovery is implied.
- No autonomous background execution is implied.
- Each stored task records `research_performed = False`, `source_discovery_performed = False`, and `autonomous_execution = False` by default.

## Tests Run

- `python3 -m compileall jarvis/research_tasks.py jarvis/runtime.py jarvis/render_pages.py jarvis/service.py tests/test_research_tasks.py tests/test_command_center_service_surface.py`
- `python3 -m pytest -q tests/test_research_tasks.py`
  - `3 passed`
- `python3 -m pytest -q tests/test_command_center_service_surface.py -k "research_task"`
  - `4 passed, 79 deselected`
- `python3 -m pytest -q tests/test_command_center_service_surface.py`
  - `83 passed, 106 warnings`

## Open Defects / Blockers

- No research-task lane blockers were found in this bounded slice.
- Existing broader-suite deprecation warnings remain outside Epic 8 slice 1 scope.

## Recommendation

Epic 8 slice 1 appears ready for Architect Office review.
