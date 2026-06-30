# Post-Epic 9 Slice 17: Premium-Provider Preview and Probe Honesty

## A. Files Changed
- `jarvis/voice_ui.py`
- `tests/test_voice_ui_conversation_posture.py`

## B. Scope Reviewed
- Existing shell voice preview path in `jarvis/voice_ui.py`
  - `#preview-voice-settings`
  - `speakText(...)`
  - `#voice-settings-status`
- Existing route-level truth seam already established in prior slices
  - `/api/voice/synthesize`
  - `/api/tts`
  - existing fallback/provider headers
- Existing focused route proof already present in repo truth
  - `tests/test_command_center_service_surface.py`

## C. Preview / Probe Gaps Found
- The current preview button already used the truthful synth route, but it discarded the returned provider/fallback headers.
- A premium provider preview could fall back to `system` and still leave the shell status copy sounding like the configured provider preview simply worked.
- When the route returned a failure body, the shell preview path reduced that to a generic `Voice output unavailable (...)` message instead of surfacing the truthful route detail.

## D. Bounded Repairs Made
- Added a tiny preview-result summarizer in `jarvis/voice_ui.py` that reads the existing route headers only:
  - requested provider
  - effective provider
  - fallback reason / live blocker when present
- Added a tiny error-detail reader so preview failures can surface route detail rather than only HTTP status.
- Kept the existing `Save + Preview` path, but changed it from:
  - save settings
  - call `await speakText(previewText)`
  to:
  - save settings
  - show `Running preview through the current voice route...`
  - call `await speakText(previewText, { onResult, onError })`
  - render concise truthful preview copy into `#voice-settings-status`
- Example user-visible outcomes now supported by the same current seam:
  - `Preview requested fish and played with fish.`
  - `Preview requested fish, but playback used system. Live blocker: ...`
  - `Preview failed: ...`

## E. Truth Guarantees Preserved
- The preview surface no longer implies the configured premium provider succeeded when the route actually fell back.
- Requested provider and effective provider remain clearly distinct.
- Live blocker wording is only shown when the current route headers actually provide it.
- No new route family, no new voice stack behavior, no TLS repair, and no provider expansion were introduced.

## F. Tests / Validation
Commands run:

```bash
python3 -m py_compile jarvis/voice_ui.py tests/test_voice_ui_conversation_posture.py
```

Result:

```text
passed
```

```bash
python3 -m pytest -q tests/test_voice_ui_conversation_posture.py tests/test_command_center_service_surface.py -k "voice_preview or voice_synthesize or voice_settings_surface"
```

Result:

```text
5 passed, 112 deselected in 0.21s
```

Focused proof used:
- Existing route-level tests already prove truthful provider/fallback headers:
  - explicit provider honored
  - fallback to `system` is exposed truthfully
- New UI source assertion now guards that the preview surface actually renders:
  - requested provider
  - effective provider
  - live blocker text
  - preview failure wording

## G. Blockers / Residual Risks
- This slice improves shell preview honesty only; it does not add a separate preview UI to `/settings-center`.
- Preview honesty still depends on the current route headers being truthful, which is intentional and already covered by prior slices.
- The shell status note is concise by design, so long raw transport failures are compacted rather than rendered verbatim.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-17-premium-provider-preview-and-probe-honesty.md`

## I. Recommendation
- Ready for Architect Office review: yes

## Compact Before / After Proof
- Before:
  - `jarvis/voice_ui.py` preview path saved settings and then called `await speakText(previewText);`
  - no preview-specific provider/fallback result was surfaced in `#voice-settings-status`
- After:
  - `jarvis/voice_ui.py:13263-13282` shows preview status wiring through the current voice route
  - `jarvis/voice_ui.py:16646-16719` shows header-based preview result summarization and truthful route-error extraction
