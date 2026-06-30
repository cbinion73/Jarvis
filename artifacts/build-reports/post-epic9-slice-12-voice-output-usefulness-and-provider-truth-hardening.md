# Post-Epic 9 Slice 12: Voice Output Usefulness and Provider-Truth Hardening

## Scope Reviewed
- `jarvis/speech.py`
- `jarvis/settings.py`
- `jarvis/service.py`
- `tests/test_speech_fish_provider.py`

## Voice-Output Gaps Found
1. `voice_stack_status()` exposed provider order and a few booleans, but it did not explain why a provider was unavailable or degraded.
2. Auto/provider selection did not surface a truthful effective spoken-output note such as which provider would actually be used right now.
3. System fallback readiness was implicit rather than inspectable.
4. Focused regression coverage did not yet protect unavailable and degraded provider states or truthful fallback notes.

## Bounded Repairs Made
1. Added a compact `tts_provider_statuses` matrix to `voice_stack_status()` with per-provider:
   - `provider`
   - `label`
   - `ready`
   - `state`
   - `reason`
   - `selected`
   - `fallback_rank`
2. Added top-level spoken-output truth fields:
   - `selected_tts_provider_ready`
   - `selected_tts_provider_state`
   - `selected_tts_provider_reason`
   - `effective_tts_provider`
   - `effective_tts_provider_state`
   - `effective_tts_provider_reason`
   - `effective_tts_note`
   - `system_ready`
3. Kept the change inside the existing settings/options seam so the improved truth surface now rides through the current `/api/voice-settings` and `/api/voice-options` payloads without new routes or UI expansion.
4. Added focused regression coverage for:
   - Fish ready posture
   - Fish unavailable with truthful system fallback note
   - LocalAI configured-but-unhealthy degraded posture with truthful fallback note

## Truth Guarantees Preserved
- No provider is marked ready unless the current runtime seam can actually use it.
- Auto mode reports which current provider would be used; it does not imply broader quality or live success.
- Degraded providers stay explicitly degraded instead of being treated as ready.
- Fallback notes describe current local fallback order only; they do not claim playback success or voice quality.
- No new provider, STT expansion, or speech-stack rewrite was introduced.

## Tests Run
1. `python3 -m py_compile jarvis/speech.py tests/test_speech_fish_provider.py`
   - Result: passed
2. `python3 -m pytest -q tests/test_speech_fish_provider.py`
   - Result: `4 passed in 0.05s`
3. Local repo-truth probe:
   - Command: `python3 - <<'PY' ... voice_stack_status(AppConfig.from_env()) ... PY`
   - Result:
     - selected provider: `auto`
     - selected provider state: `ready`
     - effective provider: `elevenlabs`
     - effective note: `Auto mode will use elevenlabs in the current runtime.`
     - provider matrix showed:
       - `kokoro` unavailable
       - `piper` unavailable
       - `localai` degraded
       - `elevenlabs` ready
       - `fish` ready
       - `system` ready

## Residual Risks
1. This slice hardens provider-truth and inspectability, not end-to-end playback proof.
2. Provider readiness still depends on live credentials, local binaries, and service health at runtime.
3. ElevenLabs and Fish readiness here remain credential/config-backed posture; this slice does not claim subjective voice quality or successful audio playback on every device path.

## Recommendation
Ready for Architect Office review as a bounded truth/usefulness hardening slice. The voice-output seam is now more inspectable and more honest about provider readiness, degradation, and fallback posture without broadening the speech stack.
