# Epic 12 Slice 2: What Is Waiting

## Scope reviewed

- `jarvis/morning_brief_pipeline.py`
- `jarvis/service.py`
- `jarvis/render_pages.py`
- `tests/test_morning_brief_pipeline.py`
- `tests/test_command_center_service_surface.py`

## Waiting-state gaps found

1. The Morning Brief had no dedicated layer answering what is currently waiting on Chris.
2. Existing repo-truth waiting seams already existed, but were not composed together:
   - Gmail unread count posture from the Google Workspace support seam
   - recorded open-loop pressure from the existing Morning Brief open-loop gatherer
3. `/briefing-center` only rendered four Morning Brief lists, so a new waiting layer would not have been visible without a small surface update.
4. The module fallback payload in `jarvis/service.py` did not have a slot for a waiting section.

## Bounded repairs made

1. Added a compact `what_is_waiting` field to `MorningBriefResult`.
2. Added a bounded waiting-layer builder that uses only existing repo-truth seams:
   - inbox pressure from connected Gmail unread-count posture
   - system pressure from recorded open loops
   - plain limitation wording when the inbox seam is only support-ready or degraded
3. Kept the waiting layer sparse and explicit:
   - no fake sender summaries
   - no fake due dates
   - no fake commitment or thread understanding
4. Added a small recommendation uplift so high unread inbox pressure can become the recommendation only when higher-priority live pressure is not already present.
5. Wired the new section through:
   - Morning Brief service fallback payload
   - `/briefing-center` readable surface
   - client-side brief re-render path

## Truth guarantees preserved

- Unread Gmail counts are described as inbox pressure, not as proof that each item is truly waiting on Chris.
- Open-loop counts are described as recorded system pressure, not as complete obligation understanding.
- Support-ready or degraded inbox posture stays explicit when live unread counts are not truly retrievable.
- No inbox summarization, email drafting, calendar synthesis, or autonomy expansion was added.
- Conversation remains primary; this is one compact operating-picture section, not a dashboard rewrite.

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

- `24 passed, 42 warnings in 9.45s`

Warnings observed:

- Existing deprecation warnings from `jarvis/drift_detection.py` and `jarvis/longevity_council.py`
- No new failures or warning classes introduced by this slice

### Live repo-truth probe

```bash
python3 - <<'PY'
from jarvis.morning_brief_pipeline import generate_morning_brief
result = generate_morning_brief('Chris')
print('WHAT_IS_WAITING')
for item in result.what_is_waiting:
    print('-', item)
print('RECOMMENDATION', result.recommendation)
PY
```

Observed result:

- `Inbox pressure: connected Gmail returned 6 unread items. This is waiting pressure, not thread understanding.`
- `System pressure: 48 recorded open loops need follow-through. Top recorded item: "Approval needed · Build the first passive-income shortlist".`
- Recommendation remained correctly dominated by a higher-priority live signal:
  - `Start by reviewing the 6 degraded agents — they may be blocking overnight work.`

## Blockers / residual risks

1. Inbox pressure remains count-based only in this slice; it does not and should not imply sender meaning, due dates, or thread urgency.
2. Open-loop pressure is only as complete as the existing recorded local seams.
3. Existing unrelated deprecation warnings remain in the focused service-surface test path.

## Recommendation

Epic 12 Slice 2 is ready for Architect Office review. The Morning Brief now includes a truthful `What Is Waiting` layer grounded in existing Gmail posture and recorded open-loop seams, and the `/briefing-center` surface shows it without overstating what the underlying signals actually prove.
