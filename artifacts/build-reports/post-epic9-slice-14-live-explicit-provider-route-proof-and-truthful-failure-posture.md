# Post-Epic 9 Slice 14: Live Explicit-Provider Route Proof and Truthful Failure Posture

## Scope Reviewed
- `jarvis/settings.py`
- `jarvis/service.py`
- `jarvis/speech.py`
- `tests/test_command_center_service_surface.py`
- `tests/test_speech_fish_provider.py`
- `tests/test_settings_store.py`

## Voice-Selection / Live-Proof Gaps Found
1. The route seam already preserved requested versus effective provider posture, but when an explicitly selected premium provider fell through to a fallback provider, the route response did not expose why.
2. The live Fish route proof in current repo truth did not complete on Fish despite Fish showing configured-ready in static status posture.
3. Without fallback metadata, the successful `system` response could misleadingly look like the requested premium path had worked.

## Bounded Repairs Made
1. Extended `AudioPayload` metadata in `jarvis/speech.py` so synthesis can carry:
   - `requested_provider`
   - `attempted_providers`
   - `provider_failures`
2. Preserved the existing synthesis behavior while attaching truthful metadata when a later provider succeeds after earlier failures.
3. Added compact route-level fallback proof headers in `jarvis/service.py` for `/api/tts` and `/api/voice/synthesize`:
   - `X-Jarvis-Voice-Fallback-From`
   - `X-Jarvis-Voice-Attempted-Providers`
   - `X-Jarvis-Voice-Fallback-Count`
   - `X-Jarvis-Voice-Fallback-Reason`
4. Added focused route tests covering:
   - explicit selected provider path
   - explicit selected provider fallback with truthful route headers
   - auto-mode pipeline continuity

## Truth Guarantees Preserved
- No claim is made that Fish completed successfully live in this environment.
- The route now distinguishes:
   - requested provider
   - effective provider
   - attempted providers
   - first fallback reason
- No new provider, new route family, or voice-stack redesign was introduced.
- The route still returns successful audio only when a real provider actually returns audio.

## Tests / Validation
1. `python3 -m py_compile jarvis/speech.py jarvis/service.py tests/test_command_center_service_surface.py tests/test_speech_fish_provider.py`
   - Result: passed
2. `python3 -m pytest -q tests/test_command_center_service_surface.py -k "voice_synthesize or settings_mutations_persist_into_settings_and_activity"`
   - Result: `4 passed, 107 deselected in 0.46s`
3. `python3 -m pytest -q tests/test_speech_fish_provider.py tests/test_settings_store.py`
   - Result: `8 passed in 0.07s`

### Exact Live Proof Command
```bash
python3 - <<'PY'
import asyncio
from jarvis.runtime import JarvisRuntime
from jarvis.service import build_app

runtime = JarvisRuntime.from_env()
app = build_app(runtime)

def route(path, method):
    for r in app.router.routes:
        if getattr(r, 'path', None) == path and method in getattr(r, 'methods', set()):
            return r.endpoint
    raise RuntimeError(f'missing route {method} {path}')

async def main():
    save = route('/api/voice-settings', 'POST')
    synth = route('/api/voice/synthesize', 'POST')
    saved = await save({
        'actor': 'Chris',
        'tts_provider': 'fish',
        'elevenlabs_voice': '',
        'piper_model_path': '',
        'piper_speaker': '0',
    })
    response = await synth({'text': 'Fish provider route proof from Jarvis.'})
    print({
        'save_status': getattr(saved, 'status_code', None),
        'synth_status': getattr(response, 'status_code', None),
        'headers': dict(getattr(response, 'headers', {})),
        'body_size': len(getattr(response, 'body', b'')),
        'media_type': getattr(response, 'media_type', None),
    })

asyncio.run(main())
PY
```

### Live Proof Result
- Save voice settings: succeeded (`200`)
- `/api/voice/synthesize`: succeeded (`200`)
- Requested provider: `fish`
- Effective provider: `system`
- Selection mode: `explicit`
- Attempted providers: `fish,piper,localai,elevenlabs,system`
- Fallback count: `4`
- First fallback reason:
  - `fish: Fish Audio request failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)`
- Content type: `audio/wav`
- Payload size: `109700` bytes

## Blockers / Residual Risks
1. Fish remains configured in repo truth, but live route proof is blocked in this environment by TLS certificate validation on the Fish request path.
2. This slice does not attempt certificate-store repair or network-stack recovery; it only makes the failure posture inspectable and truthful.
3. Later fallback providers are still attempted in current configured order, which is why the route succeeds with local audio rather than failing closed.

## Ready for Architect Office review
- yes
