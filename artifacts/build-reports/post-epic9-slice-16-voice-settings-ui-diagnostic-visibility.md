# Post-Epic 9 Slice 16: Voice-Settings UI Diagnostic Visibility

## A. Files Changed
- `jarvis/voice_ui.py`
- `jarvis/render_pages.py`
- `tests/test_voice_ui_conversation_posture.py`
- `tests/test_command_center_service_surface.py`

## B. Scope Reviewed
- Existing shell voice settings surfaces in `jarvis/voice_ui.py`
  - scene settings posture block
  - settings packet `Current Selection`
  - saved settings confirmation copy
- Existing `/settings-center` voice controls surface in `jarvis/render_pages.py`
  - current voice controls panel
  - readable diagnostics adjacent to the current form
  - client refresh path after save
- Existing voice truth fields from slices 12-15
  - `selected_tts_provider_ready`
  - `selected_tts_provider_live_ready`
  - `selected_tts_provider_live_state`
  - `selected_tts_provider_live_reason`
  - `last_live_effective_tts_provider`
  - `effective_tts_note`

## C. UI Visibility Gaps Found
- The shell settings surface still read like configured selection and live availability were the same thing.
- The shell save confirmation still said `Current source`, which could over-imply live readiness instead of saved configuration.
- `/settings-center` exposed the live truth fields only through payload JSON, not through a concise readable diagnostics block beside the existing voice controls.
- The current voice controls UI did not plainly surface the last known live blocker or last live fallback outcome for a configured premium provider.

## D. Bounded Repairs Made
- Added shared shell labels in `jarvis/voice_ui.py` so the existing voice settings surfaces now distinguish:
  - `Configured source`
  - `Configured readiness`
  - `Last live readiness`
  - `Last live blocker`
  - `Last live fallback`
- Changed the shell save confirmation from `Saved. Current source: ...` to `Saved. Configured voice source: ...`.
- Added a bounded readable diagnostics list to the existing `/settings-center` voice controls surface.
  - Server-seeded the diagnostics list from current payload truth so the route source itself is reviewable.
  - Re-rendered the same diagnostics list client-side on refresh/save using the existing `voice.stack_status` / `voice_options.stack_status` fields.
- Kept the slice inside the existing settings route and existing shell settings packet only.

Compact before/after proof:

- Before:
  - shell scene posture showed `Voice source` and provider order/health only
  - shell `Current Selection` showed `Source`, `ElevenLabs`, `Piper`, `Order`
  - `/settings-center` voice panel ended at the save form plus a generic note
- After:
  - shell scene posture now shows `Configured source`, `Configured readiness`, `Last live readiness`, `Last live blocker`, `Last live fallback`
  - shell `Current Selection` now uses the same configured-vs-live vocabulary
  - `/settings-center` now renders a readable `voice-diagnostics-list` with configured posture, last live posture, live blocker, and last fallback outcome

Repo-truth references:
- `jarvis/voice_ui.py:8990-9040`
- `jarvis/voice_ui.py:14659-14668`
- `jarvis/voice_ui.py:13259`
- `jarvis/render_pages.py:10379-10436`
- `jarvis/render_pages.py:10662-10663`
- `jarvis/render_pages.py:10873-10915`

## E. Truth Guarantees Preserved
- Configured provider posture is now explicitly distinct from last-known live posture.
- A configured premium provider is not implied to be live just because it is selected or statically ready.
- Live blocker wording remains grounded in the stored runtime diagnostic fields already added in prior slices.
- Last fallback posture is shown only when a real prior runtime result exists.
- No new voice provider behavior, routing, fallback engine, or network workaround was introduced.

## F. Tests / Validation
Commands run:

```bash
python3 -m py_compile jarvis/voice_ui.py jarvis/render_pages.py tests/test_voice_ui_conversation_posture.py tests/test_command_center_service_surface.py
```

Result:

```text
passed
```

```bash
python3 -m pytest -q tests/test_voice_ui_conversation_posture.py tests/test_command_center_service_surface.py -k "voice or settings"
```

Result:

```text
12 passed, 104 deselected in 0.79s
```

Focused coverage added/updated:
- `tests/test_voice_ui_conversation_posture.py`
  - guards shell wording for configured-vs-live diagnostic labels
- `tests/test_command_center_service_surface.py`
  - guards `/settings-center` route copy for the new diagnostic labels
  - proves a blocked Fish route result surfaces readable live-blocker/fallback posture through the settings route family

## G. Blockers / Residual Risks
- Live readiness remains last-known runtime posture, not an active continuous health probe. This is intentional and truthful for the current seam.
- If no live synthesis has been attempted yet, the UI can only truthfully say `not checked yet`.
- This slice does not add browser-screenshot proof; validation is route/test-backed and kept bounded to repo truth.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-16-voice-settings-ui-diagnostic-visibility.md`

## I. Recommendation
- Ready for Architect Office review: yes
- Recommended next bounded move: only if needed, continue with a similarly small voice-surface continuity pass or stop and let Architect Office decide whether the current voice truth/readability lane is sufficient.
