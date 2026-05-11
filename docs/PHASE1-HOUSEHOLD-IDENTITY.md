# Phase 1 Household Identity

Phase 1 gives JARVIS three durable foundations:

1. separate family-member profiles
2. device-to-person binding
3. always-on host/service planning

## What now exists

- `data/settings/identity.json`
  - family member profiles
  - device registry
  - always-on service plan
- `GET /api/identity`
- `POST /api/identity/member`
- `POST /api/identity/device`
- `POST /api/identity/session`
- `POST /api/identity/service`

## Family member profiles

Each person can now hold:

- trust level
- privacy boundary
- preferred tone
- briefing style
- anticipation style
- notes
- device bindings

This lets JARVIS learn each family member separately instead of flattening everyone into one household memory shape.

## Device registry

Each device can now be saved with:

- device id
- label
- type
- owner
- default actor
- trust level
- room
- shared vs personal
- always-available flag

The browser shell creates and reuses a persistent local device id, then binds it through `/api/identity/session`.

If a device is personal and has a default actor, JARVIS can automatically resolve the actor on startup.

## Always-on planning

The identity service section also stores:

- host label
- host type
- LAN URL
- preferred hostname
- always-on enabled
- launch-on-boot enabled
- watchdog enabled

This is the planning layer that ties the human identity model to the machine that should stay up.

## launchd templates

Templates live in:

- `ops/launchd/com.jarvis.runtime.plist.template`
- `ops/launchd/com.jarvis.openviking.plist.template`

To use them:

1. replace `/ABSOLUTE/PATH/TO/JARVIS` with the real repo path
2. create `data/logs/`
3. copy the filled templates into `~/Library/LaunchAgents/`
4. load them:

```bash
launchctl unload ~/Library/LaunchAgents/com.jarvis.runtime.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.jarvis.openviking.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.jarvis.runtime.plist
launchctl load ~/Library/LaunchAgents/com.jarvis.openviking.plist
```

Check status:

```bash
launchctl list | rg jarvis
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:1933/health
```

## Recommended host posture

- dedicated always-on Mac if possible
- `0.0.0.0:8787` for LAN serving
- local hostname goal: `jarvis.local`
- no public exposure
- VPN-only remote access later

## What Phase 1 does not do yet

- biometric identity
- voiceprint identity
- face recognition
- deep behavior modeling
- automatic digital-twin inference

Those belong in later phases. Phase 1 is the lock-in and separation layer.
