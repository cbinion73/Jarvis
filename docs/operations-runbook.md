# JARVIS Operations Runbook

## Daily Operator View

Primary browser surface:

- [http://127.0.0.1:8787](http://127.0.0.1:8787)

Useful runtime checks:

```bash
python3 -m jarvis status
python3 -m jarvis approvals
python3 -m jarvis overnight-review
python3 -m jarvis security-incidents --limit 10
```

## Start and Restart

Manual dashboard start:

```bash
python3 -m jarvis serve --host 127.0.0.1 --port 8787
```

Launchd-backed install:

```bash
/Users/chris/Desktop/CODE/JARVIS/infra/scripts/install_launchd_services.sh
```

Manual launchd restart:

```bash
launchctl unload ~/Library/LaunchAgents/com.chris.jarvis.dashboard.plist
launchctl load ~/Library/LaunchAgents/com.chris.jarvis.dashboard.plist
```

## Log Paths

Dashboard service logs:

- `/Users/chris/Desktop/CODE/JARVIS/data/logs/jarvis-dashboard.stdout.log`
- `/Users/chris/Desktop/CODE/JARVIS/data/logs/jarvis-dashboard.stderr.log`

Voice shell logs:

- `/Users/chris/Desktop/CODE/JARVIS/data/logs/jarvis-voice.stdout.log`
- `/Users/chris/Desktop/CODE/JARVIS/data/logs/jarvis-voice.stderr.log`

Runtime data roots:

- `/Users/chris/Desktop/CODE/JARVIS/data/approvals`
- `/Users/chris/Desktop/CODE/JARVIS/data/chronicle`
- `/Users/chris/Desktop/CODE/JARVIS/data/family`
- `/Users/chris/Desktop/CODE/JARVIS/data/logs`
- `/Users/chris/Desktop/CODE/JARVIS/data/security`
- `/Users/chris/Desktop/CODE/JARVIS/data/tutoring`
- `/Users/chris/Desktop/CODE/JARVIS/data/workshop`

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
