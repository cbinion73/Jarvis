# JARVIS Operations Runbook

## Daily Operator View

Primary browser surface:

- [http://127.0.0.1:8787](http://127.0.0.1:8787)

Useful runtime checks:

```bash
python3 -m jarvis status
python3 -m jarvis runtime-posture
python3 scripts/verify_runtime_posture.py
python3 -m jarvis approvals
python3 -m jarvis overnight-review
python3 -m jarvis security-incidents --limit 10
```

Rollout discipline:

- Use [live-feature-rollout-checklist.md](/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/docs/live-feature-rollout-checklist.md:1) for any live feature change that touches the web app, Apple surfaces, or shared-state workflows.

## Start and Restart

Manual dashboard start:

```bash
python3 -m jarvis serve --host 127.0.0.1 --port 8787
```

Launchd-backed install:

```bash
/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/ops/install_launchd_services.sh
```

Manual launchd restart:

```bash
launchctl kickstart -k "gui/$(id -u)/com.jarvis.runtime"
launchctl kickstart -k "gui/$(id -u)/com.jarvis.assistant-autonomy"
launchctl kickstart -k "gui/$(id -u)/com.jarvis.guardian"
```

Runtime truth endpoints:

- [http://127.0.0.1:8787/health](http://127.0.0.1:8787/health)
- [http://127.0.0.1:8787/api/runtime/posture](http://127.0.0.1:8787/api/runtime/posture)
- [http://127.0.0.1:8787/api/guardian-status](http://127.0.0.1:8787/api/guardian-status)

## Log Paths

Runtime service logs:

- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/logs/jarvis-runtime.stdout.log`
- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/logs/jarvis-runtime.stderr.log`

Autonomy and guardian logs:

- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/logs/jarvis-assistant-autonomy.stdout.log`
- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/logs/jarvis-assistant-autonomy.stderr.log`
- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/logs/jarvis-guardian.stdout.log`
- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/logs/jarvis-guardian.stderr.log`

Runtime data roots:

- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/approvals`
- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/chronicle`
- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/family`
- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/logs`
- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/security`
- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/system`
- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/tutoring`
- `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS/data/workshop`

## Incident Handling

Package or motion event:

```bash
python3 -m jarvis security-event --actor Chris --category package --location "front porch" --detail "Package delivered near the rain-exposed edge of the porch." --severity watch
```

Hazard escalation:

```bash
python3 -m jarvis safety-alert --actor Chris --hazard leak --source "garage freezer area" --detail "Water pooling detected near the freezer line." --severity critical
```

Voice unlock policy check:

```bash
python3 -m jarvis unlock-policy --actor Chris --target "front door"
python3 -m jarvis unlock-policy --actor Chris --target "front door" --second-factor
```

## Backup Scope

Back up:

- `data/chronicle`
- `data/family`
- `data/security`
- `data/tutoring`
- `data/workshop`
- `docs`

Skip:

- `.venv`
- `__pycache__`

## Outage Posture

If power is unstable:

1. keep router, switch, Home Assistant host, and JARVIS host on UPS
2. stop non-essential long-running tasks first
3. preserve logging and household state before convenience surfaces
4. perform graceful shutdown if remaining runtime falls below safe margin

If the runtime looks alive but trust is unclear:

1. run `python3 -m jarvis runtime-posture`
2. check whether guardian freshness is current
3. confirm `/api/runtime/posture` agrees with `/health`
4. treat stale integrations as stale instead of assuming they are live
