# Post-Epic 9 Slice 18: Settings-Center Preview Parity

## A. Files Changed
- `jarvis/render_pages.py`
- `tests/test_command_center_service_surface.py`

## B. Scope Reviewed
- Existing dedicated settings module voice controls in `jarvis/render_pages.py`
- Existing `/settings-center` readable diagnostics and current voice controls
- Existing route-backed synth seam already in repo truth:
  - `/api/voice/synthesize`
  - `/api/voice-settings`
  - existing provider/fallback headers from prior slices

## C. Preview Parity Gaps Found
- `/settings-center` had no real preview action in the voice controls panel.
- The dedicated settings route already exposed configured-vs-live diagnostics, but it did not let Chris try the current provider path from that same surface.
- Because no preview action existed, settings-center lacked the same requested/effective/fallback honesty that the shell preview path now has.

## D. Bounded Repairs Made
- Added the smallest bounded preview parity surface directly inside the existing `Voice Controls` form:
  - `Preview Phrase` input
  - `Save + Preview` button
- Added a tiny route-header summarizer in the settings-center page script that uses the existing synth-route truth only:
  - requested provider
  - effective provider
  - live blocker when fallback happens
- Added a tiny route-error detail reader so preview failures surface truthful route detail instead of generic failure wording.
- Wired the new preview button to:
  1. save the current configured voice source through `/api/voice-settings`
  2. call `/api/voice/synthesize`
  3. render concise truthful preview copy into `#voice-note`
  4. play returned audio if the route succeeds

Compact before / after proof:

- Before:
  - `Voice Controls` only offered save semantics
  - no preview phrase field
  - no preview button
  - no requested/effective/blocker note in settings-center
- After:
  - `jarvis/render_pages.py:10668-10691` adds the preview phrase field and `Save + Preview`
  - `jarvis/render_pages.py:10846-10903` adds preview-result summarization and route-error detail handling
  - `jarvis/render_pages.py:10903-10939` adds the real preview flow using the current synth route
  - `jarvis/render_pages.py:11371-11376` wires the preview button into the existing module script

## E. Truth Guarantees Preserved
- The settings-center preview path now uses the same route-backed truth semantics as the shell preview path.
- A configured premium provider is not implied to have worked when fallback actually produced playback.
- Requested provider, effective provider, and live blocker stay clearly separated in user-visible result copy.
- No new route family, no provider expansion, and no transport/TLS repair were introduced.

## F. Tests / Validation
Commands run:

```bash
python3 -m py_compile jarvis/render_pages.py tests/test_command_center_service_surface.py
```

Result:

```text
passed
```

```bash
python3 -m pytest -q tests/test_command_center_service_surface.py -k "settings_center_voice_controls_surface or voice_synthesize or settings_mutations_persist_into_settings_and_activity"
```

Result:

```text
6 passed, 107 deselected in 0.50s
```

Focused proof added:
- `tests/test_command_center_service_surface.py:1844-1849`
  - asserts the dedicated settings route now includes `Save + Preview`
- `tests/test_command_center_service_surface.py:4690-4699`
  - asserts the route HTML includes:
    - preview input
    - preview handler
    - requested/effective/blocker preview copy
    - truthful failure wording

## G. Blockers / Residual Risks
- The parity surface is limited to `/settings-center`; it does not attempt to unify shared code between settings-center and the shell.
- The preview result depends on the existing synth-route headers remaining truthful, which is intentional and already covered by prior slices.
- Browser playback can still fail even after the route returns audio; the page now says that plainly rather than implying provider failure/success incorrectly.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-18-settings-center-preview-parity.md`

## I. Recommendation
- Ready for Architect Office review: yes
