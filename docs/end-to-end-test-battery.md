# JARVIS Base Platform End-to-End Test Battery

This is the standing QA battery for the JARVIS base platform. It is meant to validate the shell, modal system, platform settings, Catalyst workspace integration, and the most important local control seams before we build more features on top.

## Goal

Make sure the base platform remains trustworthy in four areas:

1. The shell loads and stays interactive.
2. Core platform controls behave correctly.
3. Modal workspaces do not break the chamber experience.
4. Local state changes persist and reflect in the UI.

## Test Layers

### 1. Automated API smoke

These checks should return `200 OK` and the expected shape:

- `/`
- `/api/dashboard`
- `/api/mode`
- `/api/location-settings`
- `/api/voice-settings`
- `/api/voice-options`
- `/api/agents`
- `/api/agent-registry`
- `/api/memory-curator`
- `/api/accounts`
- `/api/catalyst-overview`
- `/catalyst/view/home`

Expected result:

- no refused connections
- no malformed JSON
- key fields present in the response body

### 2. Automated shell interaction

The Playwright battery verifies:

1. Home shell renders.
2. Packet rail expands.
3. Settings modal opens.
4. Household mode can be changed.
5. Saved locations persist.
6. Catalyst opens as a modal workspace.
7. Modal state hides the packet rail and shrinks the core stage.
8. Talk control remains interactive and does not leave the shell blank.

Expected result:

- no uncaught browser exceptions
- no dead buttons
- no broken modal state
- no lost local persistence for mode or locations

### 3. Manual audio and browser capability checks

These are still manual because they depend on device/browser support, permissions, and live providers.

#### Microphone flow

Procedure:

1. Open the shell.
2. Click `Talk`.
3. Allow microphone permission if prompted.
4. Speak a short command.

Expected result:

- state changes to listening or gracefully falls back
- the shell remains responsive
- no hard failure or blank UI

#### TTS playback

Procedure:

1. Send a text command.
2. Wait for spoken response.

Expected result:

- one voice path activates
- state returns to idle after playback
- no visible orb jitter or major UI shake during speech

#### Geolocation permission

Procedure:

1. Open `Settings`.
2. Use `Use Device Location`.
3. Allow location permission.

Expected result:

- location saves or a clear permission error appears
- no modal lockup

#### Google login handoff

Procedure:

1. Open `Settings`.
2. Save Google client JSON.
3. Click `Open Google Login`.

Expected result:

- browser redirects to Google cleanly
- callback returns to JARVIS without local server failure

## How To Run

Start JARVIS first:

```bash
/Users/chris/Desktop/CODE/JARVIS/.venv/bin/python -m jarvis serve --host 127.0.0.1 --port 8787
```

Run the automated battery:

```bash
NODE_PATH=/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
/Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-platform.e2e.cjs
```

Artifacts:

- JSON report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-platform-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-platform-report.json)
- screenshots: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/screenshots](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/screenshots)
- provider-layer companion: [live-provider-test-battery.md](/Users/chris/Desktop/CODE/JARVIS/docs/live-provider-test-battery.md)

## Pass Criteria

The base platform is healthy when:

- all automated checks pass
- no endpoint returns connection refused
- modal transitions preserve shell integrity
- settings changes persist
- Catalyst opens and routes within JARVIS
- manual microphone and speech checks do not destabilize the shell

## Failure Handling

When the battery fails:

1. Fix hard platform failures first:
   - app not reachable
   - settings modal broken
   - modal-open state broken
   - local persistence broken
2. Fix navigation and layout regressions next.
3. Tackle provider-specific issues after the shell is stable.
