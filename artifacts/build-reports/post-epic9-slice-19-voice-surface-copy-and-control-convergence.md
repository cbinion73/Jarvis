# Post-Epic 9 Slice 19: Voice-Surface Copy and Control Convergence

## A. Files Changed
- `jarvis/voice_ui.py`
- `jarvis/render_pages.py`
- `tests/test_voice_ui_conversation_posture.py`
- `tests/test_command_center_service_surface.py`

## B. Scope Reviewed
- Shell voice controls in `jarvis/voice_ui.py`
- Dedicated settings-center voice controls in `jarvis/render_pages.py`
- Existing preview/result semantics already established in slices 12-18

## C. Remaining Drift Found
- Shell used `Preferred voice source` while settings-center used `TTS Provider`.
- Shell used a short `Save` control while settings-center used `Save Voice Settings`.
- Shell used sentence-case field labels (`ElevenLabs voice`, `Piper voice`, `Preview phrase`) while settings-center used title-case labels.
- Shell preview-start wording said `Saved configured voice source...` while settings-center said `Configured voice source saved...`.
- Shell default helper note was still `Pick a source, save it, and preview the result here.` while settings-center already used route-truth wording.
- Settings-center save success note still defaulted to generic `Voice settings updated.` instead of the converged configured-source wording.

## D. Bounded Repairs Made
- Normalized the shell voice form labels to match the dedicated settings route:
  - `TTS Provider`
  - `ElevenLabs Voice`
  - `Piper Voice Model`
  - `Piper Speaker`
  - `Preview Phrase`
- Renamed the shell save button from `Save` to `Save Voice Settings`.
- Updated the shell default helper note to:
  - `Save voice settings here, then preview through the current voice route.`
- Updated the shell preview-start copy to match settings-center:
  - `Configured voice source saved. Running preview through the current voice route…`
- Updated settings-center save-success copy to converge on:
  - `Saved. Configured voice source: ...`

## E. Truth Guarantees Preserved
- This slice only converged wording and small control names; it did not change the synth route, provider selection, fallback logic, or diagnostics model.
- Shell and settings-center now describe the same voice truth seam with materially aligned vocabulary.
- Legitimate layout/context differences remain intact:
  - shell still presents voice inside the packet-style surface
  - settings-center still presents voice inside the dedicated module route

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
python3 -m pytest -q tests/test_voice_ui_conversation_posture.py tests/test_command_center_service_surface.py -k "voice_preview or voice_settings_surface or settings_center_voice_controls_surface"
```

Result:

```text
4 passed, 114 deselected in 0.36s
```

## G. Compact Before / After Proof
- Before:
  - shell label: `Preferred voice source`
  - shell save button: `Save`
  - shell default note: `Pick a source, save it, and preview the result here.`
  - shell preview start: `Saved configured voice source...`
  - settings-center save note: `Voice settings updated.`
- After:
  - shell labels/control copy in `jarvis/voice_ui.py:14642-14672` match settings-center terminology
  - shell preview-start copy in `jarvis/voice_ui.py:13263-13267` matches settings-center
  - settings-center save-success wording in `jarvis/render_pages.py:11191-11194` now converges on `Saved. Configured voice source: ...`

## H. Recommendation
- Ready for Architect Office review: yes
