# Jarvis Consolidation Phase 0 Snapshot

Date/time: 2026-06-26 22:57:58 EDT
Repo path: `/Users/chris/Desktop/CODE/JARVIS`

Purpose: establish a stabilization and truth snapshot before any consolidation work.

Consolidation decision:

> Jarvis is the runtime body. The future product must be rebuilt around one primary companion interaction spine: a smart, loyal friend with tools.

Note: the git status recorded below was captured before this snapshot artifact was created.

## Git state

Branch:

- `main`

HEAD commit:

- `994d281e0ff7a9a04919f1255d09d2f0c1b8e401`
- `994d281 Ignore generated runtime state artifacts`

Modified files:

- `.env.example`
- `jarvis/apple_api.py`
- `jarvis/config.py`
- `jarvis/dining.py`
- `jarvis/drift_detection.py`
- `jarvis/longevity_council.py`
- `jarvis/nav_bridge.py`
- `jarvis/quarterly_review.py`
- `jarvis/render_pages.py`
- `jarvis/runtime.py`
- `jarvis/service.py`
- `jarvis/voice_ui.py`
- `tests/test_command_center_service_surface.py`
- `tests/test_event_log_wiring_phase3.py`
- `tests/test_voice_ui_conversation_posture.py`

Untracked files and directories:

- `_bmad-output/brainstorming/`
- `artifacts/jarvis-understanding-audit-2026-06-26.md`
- `artifacts/mockups/.qlpreview/`
- `artifacts/mockups/jarvis-chamber-mission-preview.html`
- `artifacts/mockups/jarvis-glass-mui-ooux-proposal.html`
- `artifacts/mockups/jarvis-glass-mui-ooux-review.md`
- `artifacts/mockups/jarvis-life-officer-mcu-notes.md`
- `artifacts/mockups/jarvis-life-officer-mcu-proposal.html`
- `docs/JARVIS-ARRIVAL-AND-CONVERSATION-WORKSPACE-DOCTRINE.md`
- `docs/JARVIS-GLASS-THEME-UX-SPECIFICATION.md`
- `docs/JARVIS-OBJECT-POSTURE-REPRESENTATION-DOCTRINE.md`
- `docs/JARVIS-REJOIN-OPERATION-IMPLEMENTATION-PLAN.md`
- `docs/JARVIS-REJOIN-OPERATION-MILESTONE.md`
- `tests/test_runtime_mission_followup.py`

## Run command

Primary run command from `README.md`:

```bash
python -m jarvis serve --host 0.0.0.0 --port 8787
```

Expected local port:

- `8787`

## Known test commands

Safe targeted commands used for this Phase 0 pass:

```bash
python -m compileall jarvis
python scripts/verify.py
pytest -q tests/test_voice_ui_conversation_posture.py
pytest -q tests/test_command_center_service_surface.py
pytest -q tests/test_event_log_wiring_phase3.py
```

Supplemental low-risk diagnostics used to separate environment issues from repo issues:

```bash
python3 -m compileall jarvis
python3 -m pytest -q tests/test_command_center_service_surface.py
python3 -m pytest -q tests/test_event_log_wiring_phase3.py
```

## Runtime versions observed

- Python `3.14.4` via `python3`
- Node `v24.14.1`
- npm `11.11.0`

Environment note:

- `python` is not available on `PATH` in this shell.
- `python3` is available.

## Critical state directories

Primary local state roots:

- `data/`
- `data/agents/`
- `data/approvals/`
- `data/catalyst/`
- `data/chronicle/`
- `data/conversations/`
- `data/health/`
- `data/logs/`
- `data/memory/`
- `data/missions/`
- `data/perception/`
- `data/settings/`
- `data/state/`
- `data/supervision/`
- `data/system/`
- `data/trust/`
- `data/workshop/`
- `data/workstreams/`

Additional local state outside repo:

- `~/.jarvis/health/health.db` is part of the known runtime shape from current repo docs and code.

## Known external services

- OpenAI Responses API
- Ollama
- LocalAI
- ElevenLabs
- Home Assistant
- OpenViking
- Google Workspace APIs
- Microsoft Graph
- Cozi
- Plaid
- Dexcom
- Omron
- Google Maps / geocoding
- Chronicle service
- Ghostwritr service
- PostgreSQL
- Redis
- Cloudflare Tunnel
- Playwright
- LiveKit
- Kasa devices
- KDP scraping flow

## Safe smoke checks

### Requested commands

1. `python -m compileall jarvis`

- Ran: yes
- Result: failed
- Failure summary: shell returned `python: command not found`
- Likely cause: this environment exposes `python3`, not `python`

2. `python scripts/verify.py`

- Ran: no
- Result: skipped
- Reason: script depends on a live local server and includes a POST to `/api/gateway/test`; Phase 0 avoids starting the app or issuing runtime requests that could write logs, touch state, or invoke configured integrations

3. `pytest -q tests/test_voice_ui_conversation_posture.py`

- Ran: yes
- Result: passed
- Summary: `5 passed`

4. `pytest -q tests/test_command_center_service_surface.py`

- Ran: yes
- Result: failed
- Failure summary: import-time `ModuleNotFoundError: No module named 'jarvis'`
- Likely cause: pytest invocation environment did not resolve the repo package correctly through the standalone `pytest` entrypoint

5. `pytest -q tests/test_event_log_wiring_phase3.py`

- Ran: yes
- Result: failed
- Failure summary: import-time `ModuleNotFoundError: No module named 'jarvis'`
- Likely cause: same invocation-path issue as the prior test

### Supplemental diagnostics

1. `python3 -m compileall jarvis`

- Ran: yes
- Result: passed

2. `python3 -m pytest -q tests/test_command_center_service_surface.py`

- Ran: yes
- Result: passed
- Summary: `59 passed`

3. `python3 -m pytest -q tests/test_event_log_wiring_phase3.py`

- Ran: yes
- Result: passed
- Summary: `10 passed`

Interpretation:

- The targeted code paths compiled cleanly under the available interpreter.
- The failing requested commands point to command-invocation environment mismatch, not an immediate repo regression in those two test files.

## Runtime check

Command considered:

```bash
python -m jarvis serve --host 0.0.0.0 --port 8787
```

Result:

- Ran: no
- Status: skipped

Reason:

- Starting the server in this dirty worktree is not a pure read-only check.
- The runtime is designed around persisted local state under `data/` and may write logs, state snapshots, cache files, conversation data, or startup traces.
- The service also has many optional connectors and integration paths. Even if some degrade safely, the launch is not cleanly non-mutating enough for this Phase 0 stabilization pass.

## Known risk areas

Dirty state risks:

- Core runtime files are already modified, including `jarvis/runtime.py`, `jarvis/service.py`, and `jarvis/voice_ui.py`.
- Three targeted tests are themselves dirty or newly added, which means smoke results are tied to a non-pristine local state.

External service risks:

- Many subsystems expect credentials or reachable services.
- `scripts/verify.py` is not a static verifier; it assumes a running local app and hits live endpoints.

Local data risks:

- The repo contains extensive live local state under `data/`.
- Running the app may create or mutate logs, state snapshots, conversation records, and integration traces.

Consolidation risks:

- Without parking current dirty work first, Phase 1 could mix baseline stabilization with behavior changes.
- There is already substantial doctrine and mockup churn in the tree, so product consolidation work could become hard to separate from ongoing local experiments.

## Baseline recommendation

Recommended baseline for consolidation planning:

- Branch: `main`
- Commit: `994d281e0ff7a9a04919f1255d09d2f0c1b8e401`
- Working tree state: preserve current dirty state as an explicit pre-consolidation snapshot, not an implicit one

Before Phase 1:

- Park or commit the current modified and untracked work in a way that preserves it intact.
- Standardize command usage around `python3` or an activated project environment before using `python` in automation prompts.
- Treat this artifact and the existing understanding audit as the read-only baseline record.
