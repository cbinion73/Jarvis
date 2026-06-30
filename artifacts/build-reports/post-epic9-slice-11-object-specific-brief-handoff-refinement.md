# Post-Epic 9 Slice 11: Object-Specific Brief Handoff Refinement

## Scope Reviewed
- `jarvis/morning_brief_pipeline.py`
- `tests/test_morning_brief_pipeline.py`
- Existing repo-truth review routes inspected:
  - `/mission-board/delegation-report/{mission_id}/{report_id}`
  - `/mission-board/research-tasks/{task_id}`
  - `/mission-board/artifact-outcome/{target_kind}/{target_id}`
  - `/mission-board/autonomy-states/{autonomy_id}`

## Handoff Precision Gaps Found
- The `Next Honest Step` catch-up recommendation always routed to the family-level `/activity-center` surface, even when a real stored review object could already be opened directly.
- The current catch-up seam already had access to persisted identifiers in some cases:
  - delegation `mission_id` + `report_id`
  - research `task_id`
  - outcome `target_kind` + `target_id` (+ `mission_id` when needed)
  - autonomy `autonomy_id`
- The brief needed to deepen only when those ids were actually present and a matching readable route already existed.

## Bounded Repairs Made
- Added bounded object-specific catch-up handoff selection inside `jarvis/morning_brief_pipeline.py`.
- Refined mission catch-up gathering so recent delegation reports carry `mission_id` alongside `report_id`.
- `recommendation_action` for the recorded catch-up branch now prefers, in order:
  1. delegation report review route
  2. research-task review route
  3. artifact outcome review route
  4. autonomy-state review route
  5. existing `/activity-center` family-level fallback
- Added `return_to=/briefing-center` continuity on the object-specific review links.
- Left all non-id-backed recommendation branches unchanged.

## Truth Guarantees Preserved
- Object-specific routes are only used when a real current id exists and the readable route already exists in repo truth.
- The family-level route remains the fallback whenever precision would be guessed rather than proven.
- No fake object-open claim was introduced.
- No new persistence system, synthetic ids, or new route family was added.
- Conversation remains primary; this is a precision refinement, not a CTA expansion.

## Tests / Validation

### Compile check

```bash
python3 -m py_compile jarvis/morning_brief_pipeline.py tests/test_morning_brief_pipeline.py
```

Result:

- passed

### Focused regression battery

```bash
python3 -m pytest -q tests/test_morning_brief_pipeline.py
```

Result:

- `28 passed in 14.69s`

### Current live brief probe

```bash
python3 - <<'PY'
from jarvis.morning_brief_pipeline import generate_morning_brief
brief = generate_morning_brief('Chris')
print('recommendation=', brief.recommendation)
print('recommendation_action=', brief.recommendation_action)
PY
```

Observed result:

- Current repo truth recommendation remains:
  - `Start by reviewing the 6 degraded agents — they may be blocking overnight work.`
- Current action remains the already truthful family-level direct route:
  - route: `/agent-ops-center`
- No fake object-specific deep link was introduced for the live current path.

## Blockers / Residual Risks
- Current live repo truth still does not surface a stored delegation report, research synthesis object, outcome record, or autonomy proof as the top recommendation, so the new deep-link precision is primarily proven through focused regression rather than current live selection.
- The refinement is intentionally limited to the catch-up recommendation branch; open-loop and signal-composite branches still truthfully remain family-level.

## Recommendation
- Ready for Architect Office review.
- The handoff is now more precise where real saved-object identifiers already exist, and it still falls back honestly everywhere else.
