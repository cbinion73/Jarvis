# Post-Epic 9 Slice 21: Morning Brief Live-Signal Usefulness Hardening

## A. Files Changed
- `jarvis/morning_brief_pipeline.py`
- `tests/test_morning_brief_pipeline.py`
- `tests/test_command_center_service_surface.py`
- `artifacts/build-reports/post-epic9-slice-21-morning-brief-live-signal-usefulness-hardening.md`

## B. Scope Reviewed
- `jarvis/morning_brief_pipeline.py`
- `jarvis/render_pages.py`
- `jarvis/service.py`
- `tests/test_morning_brief_pipeline.py`
- `tests/test_command_center_service_surface.py`

## C. Brief Weakness Found
- The Morning Brief already had truthful live/support posture for Google Calendar, but it underused that signal in the actual companion operating picture.
- Specifically, when `GoogleWorkspaceSupport` returned a real `upcoming_event_count`, the brief exposed that only through truth labels and indirect forgotten-context notes.
- `What Matters Today` still surfaced family-calendar event counts, but it did not give equivalent count-level planning value for live Google Calendar results.
- That made the brief less practically useful than current repo truth allowed, even though the supporting signal was already present and truthful.

## D. Bounded Repairs Made
- Added one bounded planning line in `What Matters Today` when live Google Calendar events are present:
  - `Calendar pressure: connected Google Calendar returned N upcoming events for planning. This is count-level context, not event interpretation.`
- Kept the family-calendar planning line as the fallback only when Google Calendar does not have live event count data.
- Preserved the no-bluff boundary by staying at count-level planning context only:
  - no event-title synthesis
  - no schedule interpretation
  - no fake calendar understanding
- Added focused pipeline coverage for:
  - dynamic live Google signal posture now feeding `what_matters`
  - Google Calendar count-level planning signal winning over family-calendar fallback when a real Google count exists
- Added one route/render proof test showing `/briefing-center` renders the new planning signal when the current brief payload contains it.

## E. Truth Guarantees Preserved
- The slice uses only existing repo-truth signal fields already produced by the Google Workspace support seam.
- The new line is explicitly count-level and says it is not event interpretation.
- No new retrieval, no new Google integration behavior, and no new hidden-memory behavior was introduced.
- The brief remains companion-shaped: one stronger planning cue, not a broader widget/dashboard expansion.

## F. Tests / Validation
Commands run:

```bash
python3 -m py_compile jarvis/morning_brief_pipeline.py tests/test_morning_brief_pipeline.py
```

Result:

```text
passed
```

```bash
python3 -m pytest -q tests/test_morning_brief_pipeline.py -k "dynamic_support_posture or family_calendar_live_signal_surfaces_without_google_events or google_calendar_live_signal_surfaces_in_what_matters or recommendation_action_stays_narrative_when_no_single_truthful_surface_exists"
```

Result:

```text
....                                                                     [100%]
4 passed, 25 deselected in 0.37s
```

```bash
python3 -m py_compile jarvis/morning_brief_pipeline.py tests/test_morning_brief_pipeline.py tests/test_command_center_service_surface.py
```

Result:

```text
passed
```

```bash
python3 -m pytest -q tests/test_morning_brief_pipeline.py tests/test_command_center_service_surface.py -k "dynamic_support_posture or family_calendar_live_signal_surfaces_without_google_events or google_calendar_live_signal_surfaces_in_what_matters or briefing_center_renders_google_calendar_count_level_planning_signal"
```

Result:

```text
....                                                                     [100%]
4 passed, 139 deselected in 0.41s
```

Compact repo-truth proof:
- Pipeline change in `jarvis/morning_brief_pipeline.py:1015-1023`
- Focused pipeline assertions in `tests/test_morning_brief_pipeline.py:210-219` and `tests/test_morning_brief_pipeline.py:395-449`
- Route/render proof in `tests/test_command_center_service_surface.py:1963-2011`

## G. Blockers / Residual Risks
- This slice does not synthesize or interpret actual event content; it only lifts existing count-level live calendar usefulness.
- If Google Calendar is connected-but-empty or degraded, the brief still stays limited to those truthful postures.
- Broader Morning Brief prioritization logic could still be refined later, but that would be a separate lane from this bounded usefulness hardening.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-21-morning-brief-live-signal-usefulness-hardening.md`

## I. Recommendation
- Ready for Architect Office review: yes
