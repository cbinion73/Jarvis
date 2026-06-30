# Epic 8 Slice 5: Evidence-Backed Research Synthesis With Explicit Uncertainty

## Scope

- Added one bounded persisted synthesis object on a real research task.
- Kept the synthesis derived only from evidence items already attached to that task.
- Added one bounded synthesis flow on the readable research-task review surface.
- Kept attached evidence, synthesis, and research completion as separate concepts.
- Did not add autonomous discovery, background research, final recommendation generation, or broad synthesis orchestration.

## Evidence-Backed Synthesis Surface Added

- Added persisted synthesis support inside `ResearchTaskStore`.
- Added runtime seam:
  - `generate_research_task_synthesis(...)`
- Added service route:
  - `POST /api/research-tasks/{task_id}/synthesis`
- Extended the readable task page to:
  - render the latest synthesis object when present
  - show supported points, uncertainty, and missing-information notes
  - expose a compact `Generate Evidence-Backed Synthesis` action
  - reload back into the readable task state after successful synthesis generation

## Synthesis Contract

Each generated synthesis now stores explicit inspectable fields including:

- `synthesis_id`
- `generated_at`
- `synthesis_mode`
- `evidence_ids_used`
- `evidence_count`
- `summary`
- `supported_points`
- `uncertainties`
- `missing_information`
- `externally_validated`
- `autonomous_discovery_used`
- `research_completed_inferred`

For this slice, synthesis is explicitly constrained as:

- `synthesis_mode = attached_evidence_only`
- derived only from currently attached task evidence
- `externally_validated = False`
- `autonomous_discovery_used = False`
- `research_completed_inferred = False`

## Truth / Research-Boundary Guarantees

- Generating a synthesis does not imply completed research.
- Generating a synthesis does not imply autonomous discovery or search beyond the attached evidence set.
- Generating a synthesis does not imply external validation.
- Sparse evidence remains sparse: the synthesis explicitly records uncertainty and missing information.
- Manual evidence capture remains plainly manual in the resulting synthesis posture.

## Tests Run

- `python3 -m compileall jarvis/research_tasks.py jarvis/runtime.py jarvis/service.py jarvis/render_pages.py tests/test_research_tasks.py tests/test_command_center_service_surface.py`
- `python3 -m pytest -q tests/test_research_tasks.py tests/test_command_center_service_surface.py -k "research_task"`
  - `21 passed, 79 deselected`
- `python3 -m pytest -q tests/test_research_tasks.py`
  - `7 passed`
- `python3 -m pytest -q tests/test_command_center_service_surface.py`
  - `93 passed, 106 warnings`

## Open Defects / Blockers

- No slice-blocking defects found in the bounded synthesis path.
- Existing broader-suite deprecation warnings remain outside Epic 8 slice 5 scope.

## Recommendation

Epic 8 slice 5 appears ready for Architect Office review.
