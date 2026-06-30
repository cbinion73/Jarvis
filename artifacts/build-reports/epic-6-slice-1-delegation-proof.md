# Epic 6 Slice 1: Delegation Proof and Inspectable Agent Output Surface

## Scope reviewed
- Mission handoff and delegation lifecycle in `jarvis/missions.py`
- Thin runtime and service wrappers in `jarvis/runtime.py` and `jarvis/service.py`
- Existing mission-board proof surfaces and service tests

## Delegation surface added
- Added a bounded `delegation_reports` record lane inside the mission dossier.
- Added a narrow completion path: `POST /api/missions/{mission_id}/delegations/{delegation_id}/report`
- Added inspectable read surfaces:
  - `GET /api/missions/{mission_id}/delegation-reports`
  - `GET /api/missions/{mission_id}/delegation-reports/{report_id}`
- Added delegation proof fields to mission work-state snapshots so the runtime can distinguish:
  - `requested`
  - `completed-with-output`
  - `unavailable`

## Truth / inspectability guarantees
- Delegated work is only described as completed when a real `delegation_report` record exists.
- The producer is explicit through `producer_agent`, `delegate_agent`, and `delegator_agent`.
- The inspectable artifact is explicit through `report_id`, `output_id`, and `artifact_ref`.
- Rejected or unavailable delegations are surfaced as unavailable instead of implying work happened.
- The path does not claim background autonomy or invisible subordinate execution.

## Bounded fixes made
- Added `DelegationReportRecord` and persisted `delegation_reports` on the mission dossier.
- Added `MissionSupport.record_delegation_output(...)` to convert a live delegation into a completed inspectable output.
- Marked linked handoff/delegation status as `completed-with-output` when a report is recorded.
- Added mission work-state summary counts for requested, completed, and unavailable delegation proof states.
- Exposed delegation report proof paths in the mission-board module payload.

## Tests run
- `python3 -m pytest -q tests/test_agent_workstate.py`
- `python3 -m pytest -q tests/test_command_center_service_surface.py -k "mission_delegation_report_routes_expose_inspectable_output_surface or served_routes_expose_command_center_index_and_snapshot"`
- `python3 -m pytest -q tests/test_agent_workstate.py tests/test_command_center_service_surface.py`
- `python3 -m compileall jarvis/missions.py jarvis/runtime.py jarvis/service.py jarvis/models.py`

## Results
- `tests/test_agent_workstate.py`: `10 passed`
- Focused service/module proof run: `2 passed, 59 deselected`
- Full directly affected suites: `71 passed`
- Compile check completed without syntax errors.

## Residual risks
- This slice exposes the inspectable delegation proof through dossier/runtime/service surfaces, but it does not yet add a dedicated mission-board authoring control for delegation reports.
- The repo has unrelated dirty state outside this slice; this report reflects only the bounded Epic 6 delegation-proof work.

## Recommendation
- `Epic 6 slice 1 ready for Architect Office review`
