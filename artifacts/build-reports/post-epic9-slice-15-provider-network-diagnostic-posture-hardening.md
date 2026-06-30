# Post-Epic 9 Slice 15: Provider-Network Diagnostic Posture Hardening

## Scope Reviewed
- `jarvis/speech.py`
- `jarvis/service.py`
- `jarvis/settings.py`
- `tests/test_speech_fish_provider.py`
- `tests/test_settings_store.py`
- `tests/test_command_center_service_surface.py`

## Repo-Truth Evidence Used
The current repo-truth live Fish route proof still shows:
- requested provider: `fish`
- effective provider: `system`
- fallback reason:
  - `fish: Fish Audio request failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)`

That evidence came from the existing saved-settings plus `/api/voice/synthesize` seam and was then read back through `/api/voice-settings` and `/api/voice-options`.

## Visibility Gaps Found
1. The voice settings/options truth seam could say Fish was configured-ready, but it could not carry forward the last known remote-request or SSL blocker.
2. A route-level fallback reason existed only on the last synthesis response, so the next operator/status read did not preserve that knowledge.
3. The surfaces lacked an explicit distinction between:
   - configured/static readiness
   - last known live transport/request blocker
   - last live fallback outcome

## Bounded Repairs Made
1. Added a local inspectable runtime snapshot for spoken-output provider diagnostics in the existing voice seam.
2. Recorded synthesis-route failure metadata from the current `AudioPayload` when a fallback provider succeeds after earlier provider failures.
3. Surfaced the snapshot back through `voice_stack_status()` so the existing settings/options APIs now include:
   - `selected_tts_provider_live_ready`
   - `selected_tts_provider_live_state`
   - `selected_tts_provider_live_reason`
   - `last_live_requested_tts_provider`
   - `last_live_effective_tts_provider`
   - `last_live_attempted_tts_providers`
   - per-provider fields such as:
     - `live_ready`
     - `live_state`
     - `live_reason`
     - `last_runtime_blocked`
     - `last_runtime_state`
     - `last_runtime_reason`
     - `last_runtime_at`
4. Tightened the top-level note so the settings seam now says plainly when a provider is configured but the last live request was SSL-blocked and fallback reached another provider.

## Truth Guarantees Preserved
- No certificate-store repair, TLS bypass, or network-stack intervention was added.
- No provider is marked live-ready when the last real route attempt showed a transport blocker.
- Static configured posture remains visible alongside live-blocked posture instead of being overwritten.
- The new mechanism is local, inspectable, and limited to the current voice seam only.

## Tests / Validation
1. `python3 -m py_compile jarvis/speech.py jarvis/service.py tests/test_speech_fish_provider.py tests/test_settings_store.py`
   - Result: passed
2. `python3 -m pytest -q tests/test_speech_fish_provider.py tests/test_settings_store.py`
   - Result: `10 passed in 0.07s`
3. `python3 -m pytest -q tests/test_command_center_service_surface.py -k "voice_synthesize or settings_mutations_persist_into_settings_and_activity"`
   - Result: `4 passed, 107 deselected in 0.34s`

### Exact Live Proof / Readback Command
```bash
python3 - <<'PY'
import asyncio, json
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
    get_settings = route('/api/voice-settings', 'GET')
    get_options = route('/api/voice-options', 'GET')
    await save({
        'actor': 'Chris',
        'tts_provider': 'fish',
        'elevenlabs_voice': '',
        'piper_model_path': '',
        'piper_speaker': '0',
    })
    response = await synth({'text': 'Fish provider route proof from Jarvis.'})
    settings = await get_settings()
    options = await get_options()
    settings_payload = json.loads(settings.body.decode('utf-8'))
    options_payload = json.loads(options.body.decode('utf-8'))
    print(json.dumps({
        'synth': {
            'status': getattr(response, 'status_code', None),
            'headers': dict(getattr(response, 'headers', {})),
            'body_size': len(getattr(response, 'body', b'')),
            'media_type': getattr(response, 'media_type', None),
        },
        'settings_stack_excerpt': {
            'selected_tts_provider': settings_payload['stack_status'].get('selected_tts_provider'),
            'selected_tts_provider_ready': settings_payload['stack_status'].get('selected_tts_provider_ready'),
            'selected_tts_provider_live_ready': settings_payload['stack_status'].get('selected_tts_provider_live_ready'),
            'selected_tts_provider_live_state': settings_payload['stack_status'].get('selected_tts_provider_live_state'),
            'selected_tts_provider_live_reason': settings_payload['stack_status'].get('selected_tts_provider_live_reason'),
            'last_live_effective_tts_provider': settings_payload['stack_status'].get('last_live_effective_tts_provider'),
            'effective_tts_note': settings_payload['stack_status'].get('effective_tts_note'),
        },
        'options_stack_excerpt': {
            'last_live_requested_tts_provider': options_payload['stack_status'].get('last_live_requested_tts_provider'),
            'last_live_effective_tts_provider': options_payload['stack_status'].get('last_live_effective_tts_provider'),
            'fish_status': next((item for item in options_payload['stack_status'].get('tts_provider_statuses', []) if item.get('provider') == 'fish'), {}),
        }
    }, indent=2))

asyncio.run(main())
PY
```

### Live Proof / Readback Result
- `/api/voice/synthesize`
  - status: `200`
  - requested provider: `fish`
  - effective provider: `system`
  - fallback reason: TLS certificate validation failure on the Fish request path
- `/api/voice-settings`
  - `selected_tts_provider_ready`: `true`
  - `selected_tts_provider_live_ready`: `false`
  - `selected_tts_provider_live_state`: `ssl_transport_blocked`
  - `last_live_effective_tts_provider`: `system`
  - `effective_tts_note`: `fish is configured, but the last live request was ssl_transport_blocked; the last live fallback reached system.`
- `/api/voice-options`
  - `fish_status.ready`: `true`
  - `fish_status.live_ready`: `false`
  - `fish_status.last_runtime_state`: `ssl_transport_blocked`
  - `fish_status.last_runtime_reason`: TLS certificate validation failure text

## Blockers / Residual Risks
1. Fish remains configured but not live-proven in this environment because of TLS certificate validation failure.
2. The stored diagnostic is last-known posture, not a promise that every future call will fail the same way.
3. This slice intentionally does not attempt remediation beyond truthful visibility.

## Ready for Architect Office review
- yes
