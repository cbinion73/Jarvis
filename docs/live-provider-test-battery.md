# JARVIS Live Provider Layer Test Battery

This battery sits above the base platform checks. Its job is to verify the live edge systems that make JARVIS feel connected to the real world:

- speech providers
- Google account linking
- real integration readiness
- live home-provider behavior when available

## Goal

Keep provider-layer failures from being mistaken for shell failures.

The base platform battery proves that the chamber, modal system, settings shell, and workspace routing are stable. This provider battery tells us whether the external systems attached to that shell are genuinely usable.

## What This Battery Covers

### Automated speech checks

1. `GET /api/voice-options`
2. `POST /api/tts`

Expected result:

- provider lists are present
- STT and TTS order are visible
- provider readiness is reported
- TTS returns an actual audio payload
- `X-Jarvis-Tts-Provider` is present

### Automated Google provider checks

1. `GET /api/google/status`
2. `GET /api/accounts`
3. `GET /api/google/account/<account_id>` for configured Google accounts
4. `GET /accounts/<account_id>/connect` with redirect handling

Expected result:

- Google status shape is valid
- configured accounts have complete records
- connected accounts expose usable snapshots
- connect routes exist

Warnings this battery should surface:

- malformed `login_hint`
- connected account but Gmail API disabled
- connected account but Calendar API disabled
- connected per-account token but stale default Google integration status

### Automated integration readiness checks

1. `GET /api/status`
2. Conditional live checks when Home Assistant is actually ready

Expected result:

- integrations clearly report ready vs blocked
- provider-specific failures are explicit
- live home checks only run when the dependency is truly available

## Manual Procedures

### 1. Browser microphone flow

Procedure:

1. Open the JARVIS shell.
2. Click `Talk`.
3. Grant microphone permission if prompted.
4. Speak a short command.

Expected result:

- state changes to listening
- transcript is captured or graceful fallback appears
- shell remains stable

### 2. Audible TTS validation

Procedure:

1. Send a short typed command.
2. Listen for provider playback.
3. Repeat once after changing voice provider in `Settings`.

Expected result:

- selected or fallback provider speaks
- voice returns to idle cleanly
- no orb jitter or layout disruption during speech

### 3. Google OAuth handoff

Procedure:

1. Open `Settings`.
2. Save Google client JSON if needed.
3. Open the account-specific Google connect path.
4. Complete Google consent.
5. Return to JARVIS.

Expected result:

- redirect starts from the correct account
- callback returns to the local app
- token is stored
- Gmail and Calendar summaries stop reporting auth or API configuration errors

### 4. Enable Gmail and Calendar APIs

Procedure:

1. Open the Google Cloud project used by JARVIS.
2. Enable:
   - Gmail API
   - Google Calendar API
3. Wait for propagation.
4. Re-run the provider battery.

Expected result:

- `gmail_error` disappears
- `calendar_error` disappears
- summaries start returning real data

### 5. Live Home Assistant hardening

Procedure:

1. Set `HOME_ASSISTANT_URL`
2. Set `HOME_ASSISTANT_TOKEN`
3. Restart JARVIS
4. Re-run the provider battery

Expected result:

- `home-assistant` moves from blocked to ready
- `/api/home-overview` reflects live data
- home action seams stop being profile-only

## How To Run

Start JARVIS first:

```bash
/Users/chris/Desktop/JARVIS/.venv/bin/python -m jarvis serve --host 127.0.0.1 --port 8787
```

Run the provider battery:

```bash
NODE_PATH=/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
/Users/chris/Desktop/JARVIS/tests/e2e/jarvis-provider-layer.e2e.cjs
```

Artifacts:

- JSON report: [/Users/chris/Desktop/JARVIS/artifacts/qa/jarvis-provider-layer-report.json](/Users/chris/Desktop/JARVIS/artifacts/qa/jarvis-provider-layer-report.json)
- screenshots: [/Users/chris/Desktop/JARVIS/artifacts/qa/screenshots](/Users/chris/Desktop/JARVIS/artifacts/qa/screenshots)

## Status Semantics

- `passed`: the live provider path behaved as expected
- `warning`: the provider path is partially wired but not truly usable yet
- `skipped`: the dependency is not configured, so we did not pretend to test it
- `failed`: the path should work now and did not
- `environment-limited`: the local runtime was unreachable before the provider
  battery could exercise any provider paths, so the artifact records truthful
  preflight unavailability instead of a fake provider failure

## Current Likely Failure Modes

The battery is designed to catch these early:

- TTS provider configured but not producing audio
- Google account connected but Gmail API disabled
- Google account connected but Calendar API disabled
- bad Google account metadata such as a malformed `login_hint`
- integration status reporting stale or contradictory state
- Home Assistant checks running before credentials exist
