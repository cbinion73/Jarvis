# Phase 4: Always-On Runtime and Device Lock-In

Phase 4 makes JARVIS behave more like household infrastructure and less like a local dev app.

## What this phase adds

- Personal devices can resolve to their owner or default actor automatically.
- Shared devices can stay neutral until someone chooses who this session belongs to.
- The shell can show real runtime-service status from the local machine.
- A launchd install script can turn JARVIS and OpenViking into boot-time local services.

## Shared-device session override

Shared devices should not permanently become "Chris's iPad" just because Chris used them once.

To handle that, the Device Registry settings now support:

- `Shared-device actor for this session`
- `Use For This Session`
- `Clear Session Override`

The override is stored in local browser storage and sent back through the identity bind API. The device record stays shared; only the current session persona changes.

## Runtime service status

Settings now ask the runtime for live local service posture through:

- `GET /api/runtime-service`

That endpoint reports:

- current service-plan values
- launch agent install status
- launch agent loaded status
- LAN URL
- configured hostname

This is intentionally local and truth-based. It does not claim Bonjour, `jarvis.local`, or launchd state unless the machine actually reports it.

## Installing JARVIS as an always-on service

Run:

```bash
./ops/install_launchd_services.sh
```

That script:

- renders the launchd plist templates with the real repo path
- installs them into `~/Library/LaunchAgents`
- bootstraps both launch agents
- kickstarts them so they start immediately

It installs:

- `com.jarvis.runtime`
- `com.jarvis.openviking`

## Verification

After installation, check:

```bash
launchctl list | rg jarvis
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:1933/health
```

## What this phase does not claim yet

- automatic voice recognition by person
- face recognition
- guaranteed Bonjour `jarvis.local` advertising
- a separate watchdog daemon beyond launchd keepalive

Those can come later. Phase 4 is about truthful device lock-in and local always-on posture.
