# Post-Epic 9 Slice 13: Voice Provider-Selection Continuity and Live Spoken-Output Proof

## Scope Reviewed
- `jarvis/settings.py`
- `jarvis/service.py`
- `jarvis/speech.py`
- `jarvis/voice_audio.py`
- `jarvis/voice_pipeline.py`
- `tests/test_command_center_service_surface.py`
- `tests/test_settings_store.py`
- `tests/test_speech_fish_provider.py`

## Voice-Selection / Live-Proof Gaps Found
1. Voice settings persistence already stored the selected provider, but the Friday `/api/voice/synthesize` path could bypass that saved choice whenever the voice pipeline was present.
2. The current routes did not expose a compact requested-versus-effective provider proof surface on synthesis responses.
3. The local FastAPI response stub in service-surface tests did not properly model binary/media-type responses, which made direct route proof for spoken-output continuity brittle.

## Bounded Repairs Made
1. Hardened `/api/voice/synthesize` so explicit saved provider selections now use the direct TTS path that already honors persisted voice settings.
   - `auto` still uses the Friday pipeline path.
   - explicit selections now stay explicit instead of being silently overridden by the pipeline cascade.
2. Added inspectable provider continuity headers to synthesis responses:
   - `X-Jarvis-Voice-Requested-Provider`
   - `X-Jarvis-Voice-Effective-Provider`
   - `X-Jarvis-Voice-Selection-Mode`
   - plus matching requested/effective headers on `/api/tts`
3. Tightened the service-surface test response stub so binary audio responses with `media_type` can be exercised truthfully in tests.
4. Added focused route tests proving:
   - explicit saved provider selection bypasses the pipeline and reaches direct synthesis
   - auto selection still uses the pipeline and reports that clearly

## Truth Guarantees Preserved
- No claim is made that provider selection persistence is stronger than the current stored settings path actually provides.
- No claim is made that any provider succeeded live unless it was directly exercised.
- Requested and effective provider posture stay clearly separated.
- Auto mode remains distinct from explicit provider selection.
- No broad voice-stack, STT, device, or mobile expansion was introduced.

## Tests / Validation
1. `python3 -m py_compile jarvis/service.py tests/test_command_center_service_surface.py tests/test_speech_fish_provider.py`
   - Result: passed
2. `python3 -m pytest -q tests/test_command_center_service_surface.py -k "voice_synthesize or settings_mutations_persist_into_settings_and_activity"`
   - Result: `3 passed, 107 deselected in 0.48s`
3. `python3 -m pytest -q tests/test_speech_fish_provider.py tests/test_settings_store.py`
   - Result: `8 passed in 0.07s`
4. Tiny local spoken-output proof:
   - Command used `synthesize_speech(AppConfig.from_env(), "Voice proof check.", voice_settings={"tts_provider": "system"})`
   - Result:
     - provider: `system`
     - content type: `audio/wav`
     - payload size: `49254` bytes
     - extension: `.wav`

## Blockers / Residual Risks
1. Friday pipeline auto mode still uses its own narrower cascade by design; this slice only prevents it from silently overriding explicit saved provider choices.
2. Live proof in this slice covers one local system-provider path only, not every configured provider.
3. Provider success at runtime still depends on credentials, local binaries, and service health.

## Recommendation
Ready for Architect Office review as a bounded continuity/proof hardening slice. The chosen provider path is now more dependable when explicitly selected, and the product exposes a clearer requested-versus-effective proof surface without broadening the voice stack.
