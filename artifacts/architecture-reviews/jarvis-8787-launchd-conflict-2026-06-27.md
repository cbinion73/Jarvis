# JARVIS 8787 Launchd Conflict

- date: `2026-06-27 02:00:36 EDT`
- repo: `/Users/chris/Desktop/CODE/JARVIS`
- branch: `phase-1-companion-spine`
- commit: `458158c7b5f61d0039598ba390f37f277e75fe0f`

## 1. Conflicting launch agents

- `com.chris.jarvis.dashboard`
- `com.jarvis.runtime`

## 2. Competing checkout paths

- `com.chris.jarvis.dashboard`
  - LaunchAgent path: `~/Library/LaunchAgents/com.chris.jarvis.dashboard.plist`
  - Working directory: `/Users/chris/Desktop/CODE/JARVIS`
  - Launcher script: `~/Library/Application Support/JARVIS/bin/start_jarvis_dashboard.sh`

- `com.jarvis.runtime`
  - LaunchAgent path: `~/Library/LaunchAgents/com.jarvis.runtime.plist`
  - Working directory: `/Users/chris/Desktop/JARVIS`
  - Program: `/Users/chris/Desktop/JARVIS/.venv/bin/python -m jarvis serve --host 0.0.0.0 --port 8787`

## 3. Observed failure mode on 8787

- `8787` was already occupied by a supervised `python -m jarvis serve --host 0.0.0.0 --port 8787` process.
- The listener could return `200` from `/health`, but the payload showed drift:
  - `startup_vs_disk: true`
- `api/respond` on that path produced stale startup behavior rather than current repo behavior.
- Killing the listener caused another supervised `8787` listener to return.

## 4. Evidence the blocker was external launchd supervision

- `ps` showed the original `8787` listener with `PPID 1`.
- `launchctl list` showed both:
  - `com.chris.jarvis.dashboard`
  - `com.jarvis.runtime`
- `launchctl print gui/$(id -u)/com.chris.jarvis.dashboard` showed:
  - `state = running`
  - `KeepAlive = true`
  - `RunAtLoad = true`
  - active `pid`
- `launchctl print gui/$(id -u)/com.jarvis.runtime` showed:
  - `state = spawn scheduled`
  - `last exit code = 78: EX_CONFIG`
  - same target port `8787`
- `~/Library/Application Support/JARVIS/bin/start_jarvis_dashboard.sh` explicitly launches:
  - `python -m jarvis serve --host 0.0.0.0 --port 8787`

## 5. Bounded recovery steps that restored trustworthy current-code behavior

1. Unload the conflicting second runtime job:
   - `launchctl bootout gui/$(id -u)/com.jarvis.runtime`
2. Restart the active dashboard job if needed:
   - `launchctl kickstart -k gui/$(id -u)/com.chris.jarvis.dashboard`
3. If `8787` still serves stale or hanging behavior, unload the remaining dashboard LaunchAgent:
   - `launchctl bootout gui/$(id -u)/com.chris.jarvis.dashboard`
4. Confirm `8787` is free:
   - `lsof -iTCP:8787 -sTCP:LISTEN -n -P`
5. Launch current repo directly on the expected path:
   - `python3 -m jarvis serve --host 0.0.0.0 --port 8787`
6. Verify trust on the expected path:
   - `curl --max-time 5 -sS http://127.0.0.1:8787/health`
   - `curl --max-time 5 -sS http://127.0.0.1:8787/api/gateway/status`

## 6. Residual risk

- The conflict will recur if either LaunchAgent is reloaded without normalizing the duplicated `8787` ownership.
- The highest recurrence risk is reloading both:
  - `com.chris.jarvis.dashboard`
  - `com.jarvis.runtime`
- The problem is operational duplication across two checkout paths, not a product-behavior bug.

## 7. Operator verification note before future live smokes

Before trusting `8787`, verify all of the following:

1. Only one intended listener owns `8787`:
   - `lsof -iTCP:8787 -sTCP:LISTEN -n -P`
2. `/health` returns quickly.
3. `/health` shows:
   - `startup_vs_disk: false`
   - `live_probe_vs_disk: false`
   - `live_probe_vs_startup: false`
4. `/api/gateway/status` returns quickly.
5. A small `api/respond` prompt such as `Hey Jarvis` behaves like the current repo, not a stale startup path.
