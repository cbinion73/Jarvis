# Post-Epic 9 Slice 20: Voice-Surface End-to-End Acceptance Battery

## A. Files Changed
- `artifacts/build-reports/post-epic9-slice-20-voice-surface-end-to-end-acceptance-battery.md`

## B. Acceptance Scope
- Shell voice controls in `jarvis/voice_ui.py`
- Settings-center voice controls in `jarvis/render_pages.py`
- Existing route-backed voice settings and preview semantics already hardened in slices 12-19
- Focused truth checks for:
  - configured source save wording
  - configured vs last-live diagnostics visibility
  - preview start wording
  - requested vs effective provider wording when fallback happens
  - truthful failure wording when preview cannot complete

## C. Acceptance Battery Run
Commands run:

```bash
python3 -m py_compile jarvis/voice_ui.py jarvis/render_pages.py tests/test_voice_ui_conversation_posture.py tests/test_command_center_service_surface.py
```

Result:

```text
passed
```

```bash
python3 -m pytest -q tests/test_voice_ui_conversation_posture.py tests/test_command_center_service_surface.py -k "voice_preview or voice_settings_surface or settings_center_voice_controls_surface or voice_synthesize or settings_mutations_persist_into_settings_and_activity"
```

Result:

```text
........
8 passed, 110 deselected in 0.38s
```

Repo-truth acceptance points covered by the passing battery:
- shell and settings-center both expose aligned voice field labels and save controls
- both surfaces expose `Configured source`, `Configured readiness`, `Last live readiness`, `Last live blocker`, and `Last live fallback`
- both surfaces use aligned preview-start wording:
  - `Configured voice source saved. Running preview through the current voice route…`
- preview/result reporting stays truthful when requested and effective providers differ
- synth route behavior remains covered for fallback and truthful failure posture

## D. Failures or Gaps Found
- No new bounded defect was found in this slice's acceptance battery.
- No cross-surface wording drift was found beyond what slice 19 already repaired.
- No new route/render mismatch was found between shell voice controls and settings-center voice controls in the covered acceptance path.

## E. Bounded Repairs Made
- None required in this slice.
- This slice was completed as an acceptance-and-evidence pass rather than a feature or wording change pass.

## F. Truth Guarantees Preserved
- The acceptance battery confirms shell and settings-center remain materially aligned in truth language while preserving their legitimate layout differences.
- Configured posture is still kept distinct from last-known live posture.
- Preview results still distinguish requested provider from effective provider when fallback occurs.
- Failure posture remains explicit rather than implying premium-provider success when the live path is blocked.
- No new architecture, voice-stack expansion, TLS/network repair, or UI redesign was introduced.

## G. Residual Risks
- This slice did not attempt live TLS/network recovery for premium providers; prior known remote-request blockers remain out of scope.
- Acceptance evidence here is focused on repo-truth compile/test coverage rather than a new live premium-provider success proof.
- If future work changes the synth route or provider diagnostics model, this acceptance lane should be rerun.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-20-voice-surface-end-to-end-acceptance-battery.md`

## I. Recommendation
- Ready for Architect Office review: yes
