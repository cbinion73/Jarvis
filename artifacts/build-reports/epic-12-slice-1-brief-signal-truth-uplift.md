# Epic 12 Slice 1: Brief Signal Truth Uplift

## Scope reviewed

- `jarvis/morning_brief_pipeline.py`
- `tests/test_morning_brief_pipeline.py`
- Repo support seams inspected for Morning Brief truth posture:
  - `jarvis/google_workspace.py`
  - `jarvis/family_calendar.py`
  - `jarvis/obsidian_context.py`
  - `jarvis/accounts.py`
  - `jarvis/config.py`

## Stale signal assumptions found

1. Morning Brief still hardcoded `calendar` to `unavailable — Google Calendar not configured`.
2. Morning Brief still hardcoded `email` to `unavailable — Gmail not configured`.
3. `What May Have Been Forgotten` always said Google Calendar was not connected, even when repo truth showed connected calendar support.
4. The fallback recommendation always told Chris to connect Google Calendar and Gmail, even when the local repo truth already showed connected support posture.
5. Morning Brief did not surface Obsidian local-retrieval posture at all, despite that seam being available in repo truth.

## Bounded repairs made

1. Added bounded Morning Brief support gatherers for:
   - Google Workspace support posture
   - family calendar support posture
   - Obsidian local-retrieval posture
2. Replaced stale hardcoded email/calendar truth labels with computed labels that distinguish:
   - `live`
   - `connected-but-empty`
   - `degraded`
   - `support-ready`
   - `unavailable`
3. Added `obsidian_context` truth labeling so the brief can say when local note retrieval is actually available.
4. Updated the forgotten/reminder section to describe current calendar posture truthfully instead of always claiming no calendar connection.
5. Added a small `what matters` signal when family-calendar events are actually loaded.
6. Replaced the stale Google-connect fallback recommendation with posture-aware guidance:
   - use current live signals when already connected
   - otherwise give the smallest truthful recovery step, such as restoring `config/google_client_secret.json`

## Truth guarantees preserved

- The brief still does not invent inbox contents or calendar events beyond what current support seams actually return.
- Connected-but-empty posture is stated plainly rather than inflated into live signal claims.
- Obsidian is described as local retrieval support, not as live synced memory or hidden inference.
- Google support-ready posture is kept distinct from live retrieved Gmail/Calendar data.
- Health remains honestly unavailable in this local path.

## Tests run

### Compile check

```bash
python3 -m py_compile jarvis/morning_brief_pipeline.py tests/test_morning_brief_pipeline.py
```

Result:

- Passed with no output.

### Focused Morning Brief regression suite

```bash
python3 -m pytest -q tests/test_morning_brief_pipeline.py
```

Result:

- `22 passed in 9.11s`

### Local repo-truth probe

```bash
python3 - <<'PY'
from jarvis.morning_brief_pipeline import generate_morning_brief
result = generate_morning_brief('Chris')
print('TRUTH_LABELS', result.truth_labels)
print('MAY_HAVE_FORGOTTEN')
for item in result.may_have_forgotten:
    print('-', item)
print('RECOMMENDATION', result.recommendation)
PY
```

Observed result:

- `calendar`: `live — Google Calendar returned 2 upcoming events`
- `email`: `live — Gmail returned 6 unread items`
- `obsidian_context`: `local — Obsidian vault is available for local retrieval`
- Forgotten section no longer claims Google Calendar is not connected.
- Recommendation remained driven by a higher-priority real signal: degraded agents blocking overnight work.

## Residual risks

1. Morning Brief still depends on current local bridge/account state, so counts and labels can shift between runs as real inbox/calendar signals change.
2. This slice did not broaden into richer live inbox summarization or event synthesis, so the brief posture is now truthful but still intentionally sparse.
3. Google and family-calendar support are summarized from existing seams; this slice did not add new upstream credential flows or hosted-runtime proof.

## Recommendation

Epic 12 Slice 1 is ready for Architect Office review. The Morning Brief no longer hardcodes stale unavailable posture for Gmail/Calendar when repo truth shows support-ready or connected seams, and it stays honest about what was actually retrieved versus merely available.
