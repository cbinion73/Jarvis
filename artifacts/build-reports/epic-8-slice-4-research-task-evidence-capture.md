# Epic 8 Slice 4: Research Task Evidence Capture Surface

## Scope

- Added one bounded persisted evidence-item structure attached to a real research task.
- Added one bounded evidence-capture flow on the readable research-task review surface.
- Kept the slice limited to explicit evidence capture and readable inspection only.
- Did not add synthesis, recommendation generation, autonomous discovery, or completed-research claims.

## Evidence Capture Surface Added

- Added persisted evidence-item support inside `ResearchTaskStore`.
- Added runtime seam:
  - `add_research_task_evidence(...)`
- Added service route:
  - `POST /api/research-tasks/{task_id}/evidence`
- Extended the readable task page to:
  - render attached evidence items
  - expose a compact evidence-capture form
  - reload back into the readable task state after successful capture

## Evidence Item Contract

Each evidence item now stores explicit inspectable fields including:

- `source_label`
- `source_locator`
- `evidence_note`
- `capture_status`
- `confidence_label`
- `capture_mode`
- `captured_at`
- `retrieval_used`
- `autonomous_discovery`

For this slice, captured evidence is explicitly marked as:

- `capture_mode = manual_entry`
- `retrieval_used = False`
- `autonomous_discovery = False`

## Truth / Research-Boundary Guarantees

- Attaching evidence does not imply that the research task is completed.
- Attaching evidence does not imply validated synthesis, final conclusions, or autonomous source discovery.
- The readable task page explicitly states that evidence items are attached inputs only.
- Task status and evidence presence remain distinct from completed research.

## Tests Run

- `python3 -m compileall jarvis/research_tasks.py jarvis/runtime.py jarvis/render_pages.py jarvis/service.py tests/test_research_tasks.py tests/test_command_center_service_surface.py`
- `python3 -m pytest -q tests/test_research_tasks.py tests/test_command_center_service_surface.py -k "research_task"`
  - `16 passed, 79 deselected`
- `python3 -m pytest -q tests/test_command_center_service_surface.py`
  - `90 passed, 106 warnings`

## Open Defects / Blockers

- No slice-blocking defects found in the bounded evidence-capture path.
- Existing broader-suite deprecation warnings remain outside Epic 8 slice 4 scope.

## Recommendation

Epic 8 slice 4 appears ready for Architect Office review.
