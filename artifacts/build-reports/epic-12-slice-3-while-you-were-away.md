# Epic 12 Slice 3: While You Were Away

## Scope reviewed

- `jarvis/morning_brief_pipeline.py`
- `jarvis/service.py`
- `jarvis/render_pages.py`
- `tests/test_morning_brief_pipeline.py`
- `tests/test_command_center_service_surface.py`

Repo-truth seams inspected for catch-up state:

- audit/action traces via `jarvis/audit.py`
- mission dossier delegation and staged-output state via `data/missions/dossiers.json`
- research-task recorded state via `jarvis/research_tasks.py`
- artifact outcome recorded state via `jarvis/artifact_outcomes.py`
- autonomy recorded state via `jarvis/autonomy_state.py`

## Catch-up gaps found

1. The Morning Brief had no dedicated `What JARVIS Did While You Were Away` layer.
2. `/briefing-center` had no readable section for catch-up traces.
3. The service fallback payload had no field for a catch-up section.
4. Existing repo-truth recorded-state seams were available, but not composed together:
   - assistant activity traces
   - mission delegation/staging state
   - research-task evidence/synthesis state
   - artifact outcome records
   - autonomy local-proof or planned-only state

## Bounded repairs made

1. Added `while_you_were_away` to `MorningBriefResult`.
2. Added bounded catch-up gatherers for:
   - recent assistant activity traces
   - recent mission delegation/staging state
   - recent research-task state
   - recent artifact outcome state
   - recent autonomy recorded state
3. Added catch-up truth labels so the new section can distinguish:
   - `recorded`
   - `planned-only`
   - `empty`
   - `degraded`
4. Added a compact `What JARVIS Did While You Were Away` section on `/briefing-center`.
5. Kept the section sparse and explicit:
   - completed delegation/research/outcome/autonomy traces only when actually recorded
   - staged mission movement called out as staged, not completed
   - plain limitation line when those recorded traces are absent
6. Added a small recommendation uplift so real completed catch-up outputs can matter when stronger live pressure does not already outrank them.

## Truth guarantees preserved

- No fake hidden execution or agent accomplishment claims were added.
- Planned-only mission state is explicitly distinguished from completed execution.
- Missing research/outcome/autonomy stores are treated as no visible recorded trace in this runtime, not as silent success.
- The catch-up layer does not imply background intelligence beyond inspectable stored state.
- Conversation remains primary; this is a bounded catch-up seam, not an activity-center rewrite.

## Tests / validation

### Compile check

```bash
python3 -m py_compile jarvis/morning_brief_pipeline.py jarvis/service.py jarvis/render_pages.py tests/test_morning_brief_pipeline.py tests/test_command_center_service_surface.py
```

Result:

- Passed with no output.

### Focused test battery

```bash
python3 -m pytest -q tests/test_morning_brief_pipeline.py tests/test_command_center_service_surface.py::CommandCenterServiceSurfaceTests::test_served_routes_expose_command_center_index_and_snapshot
```

Result:

- `26 passed, 42 warnings in 13.71s`

Warnings observed:

- Existing deprecation warnings from `jarvis/drift_detection.py`
- Existing deprecation warnings from `jarvis/longevity_council.py`
- No new failure class introduced by this slice

### Live repo-truth probe

```bash
python3 - <<'PY'
from jarvis.morning_brief_pipeline import generate_morning_brief
result = generate_morning_brief('Chris')
print('WHILE_YOU_WERE_AWAY')
for item in result.while_you_were_away:
    print('-', item)
print('TRACE_LABELS', {k: result.truth_labels.get(k) for k in ['activity_trace','delegation_trace','research_trace','outcome_trace','autonomy_trace']})
print('RECOMMENDATION', result.recommendation)
PY
```

Observed result:

- `Mission staging: 2 mission workspaces refreshed with prepared next steps. This is staged work, not completed execution.`
- `No inspectable delegation, research, outcome, or autonomy traces were recorded in this runtime. Current catch-up is limited to staged mission state and other explicitly logged surfaces.`
- Trace posture:
  - `activity_trace`: `empty — no recent assistant-action traces are visible`
  - `delegation_trace`: `planned-only`
  - `research_trace`: `empty — no recent research-task traces are visible`
  - `outcome_trace`: `empty — no recent artifact outcome traces are visible`
  - `autonomy_trace`: `empty — no recent autonomy traces are visible`

## Blockers / residual risks

1. This checkout currently has no recorded research-task, artifact-outcome, or autonomy-state records, so the live catch-up section can only surface their absence truthfully.
2. Mission dossiers currently provide staged mission state but no recent delegation reports in repo truth.
3. Existing unrelated deprecation warnings remain in the focused service-surface test path.

## Recommendation

Epic 12 Slice 3 is ready for Architect Office review. The Morning Brief now includes a truthful `What JARVIS Did While You Were Away` layer grounded in existing repo traces, and it clearly separates staged mission movement from absent or unrecorded delegation/research/outcome/autonomy execution.
