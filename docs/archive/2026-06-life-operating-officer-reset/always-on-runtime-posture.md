# JARVIS Always-On Runtime Posture

This document defines the real substrate that the always-on orchestrator is allowed to trust.

It is intentionally narrower than broad backend architecture work. It answers a simpler question:

What has to be true for JARVIS to keep working on purpose when nobody is staring at it?

## Core Posture

JARVIS runs as a local-first always-on orchestrator with four runtime truths:

1. `com.jarvis.runtime` is the primary FastAPI surface.
2. `com.jarvis.guardian` is the watchdog loop that records runtime truth and attempts bounded recovery.
3. `com.jarvis.assistant-autonomy` keeps delegated background work alive.
4. `com.jarvis.openviking` is optional support infrastructure, not the definition of liveness.

If the guardian is stale, the runtime is drifting, or launchd is missing, the branch should say so plainly.

## Operator Checks

Primary posture commands:

```bash
python3 -m jarvis runtime-posture
python3 scripts/verify_runtime_posture.py
curl http://127.0.0.1:8787/api/runtime/posture
curl http://127.0.0.1:8787/health
```

The posture snapshot is the operator-facing truth surface for:

- launchd installation state
- guardian freshness
- runtime build drift
- local and hosted health probes
- live calendar visibility
- reminder queue truth
- Home Assistant boundary health
- perception-feed freshness
- workshop profile freshness
- Apple Health sync freshness

## Integration Doctrine

JARVIS is not allowed to imply that an integration is live merely because a profile exists.

The branch now treats these as separate states:

- `ready`: configured and recent enough to trust operationally
- `watch`: modeled or partially wired, but not strong enough for blind delegation
- `blocked`: missing, stale, or untruthful enough that the orchestrator should not lean on it

Current source-of-truth rules:

- calendars: family ICS feed plus connected Google/Microsoft accounts when present
- reminders: persistent local queue until a real mirrored provider is explicitly wired
- home automation: Home Assistant is the actuator boundary
- perception: local event feeds with privacy constraints
- workshop: profile-backed hardware/safety truth until live adapters are complete
- health sync: Apple Health daily snapshots from the iPhone bridge

## Host Durability

The runtime profile at [jarvis_runtime_profile.example.json](/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/household/jarvis_runtime_profile.example.json:1) defines the expected durability floor:

- UPS-backed core runtime
- segmented network posture
- encrypted backup targets
- explicit recovery artifacts in `data/system/`
- a helper-clone push fallback when `git push` stalls in pack-objects or receive-pack

## Recovery Rules

When recovery is needed:

1. trust `guardian_state.json` and `/health` before optimistic assumptions
2. confirm the guardian repo root still matches the active checkout
3. confirm runtime drift is not hiding un-restarted code
4. restart through launchd, not ad-hoc background shells
5. if `git push` hangs with no progress, rebuild and push from `/tmp/jarvis-push-helper`

This is the floor for an orchestrator that is supposed to keep working while life keeps moving.
