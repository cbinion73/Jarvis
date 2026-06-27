# Jarvis Phase 0A Runtime Health Stabilization + Cloud-Light Model Mode

## Snapshot

- Captured at: `2026-06-27T03:15:55Z`
- Repo path: `/Users/chris/Desktop/CODE/JARVIS`
- Branch: `main`
- HEAD: `994d281e0ff7a9a04919f1255d09d2f0c1b8e401`
- Baseline commit label: `994d281 Ignore generated runtime state artifacts`

## Scope Guardrails

- Implemented Phase 0A only.
- Did not refactor product behavior.
- Did not change conversation posture or conversation logic.
- Did not merge Monday code.
- Did not alter local data formats.
- Preserved oversized logs in place.

## Start-State Git Reality

### Dirty modified files present before and during this pass

```text
.env.example
jarvis/apple_api.py
jarvis/config.py
jarvis/dining.py
jarvis/drift_detection.py
jarvis/longevity_council.py
jarvis/nav_bridge.py
jarvis/quarterly_review.py
jarvis/render_pages.py
jarvis/runtime.py
jarvis/service.py
jarvis/voice_ui.py
tests/test_command_center_service_surface.py
tests/test_event_log_wiring_phase3.py
tests/test_voice_ui_conversation_posture.py
```

### Untracked files present before and during this pass

```text
_bmad-output/brainstorming/
artifacts/jarvis-consolidation-phase-0-snapshot.md
artifacts/jarvis-understanding-audit-2026-06-26.md
artifacts/mockups/.qlpreview/
artifacts/mockups/jarvis-chamber-mission-preview.html
artifacts/mockups/jarvis-glass-mui-ooux-proposal.html
artifacts/mockups/jarvis-glass-mui-ooux-review.md
artifacts/mockups/jarvis-life-officer-mcu-notes.md
artifacts/mockups/jarvis-life-officer-mcu-proposal.html
docs/JARVIS-ARRIVAL-AND-CONVERSATION-WORKSPACE-DOCTRINE.md
docs/JARVIS-GLASS-THEME-UX-SPECIFICATION.md
docs/JARVIS-OBJECT-POSTURE-REPRESENTATION-DOCTRINE.md
docs/JARVIS-REJOIN-OPERATION-IMPLEMENTATION-PLAN.md
docs/JARVIS-REJOIN-OPERATION-MILESTONE.md
jarvis/state_log_utils.py
tests/test_runtime_mission_followup.py
```

## Observed Runtime Health Problem

- Existing Jarvis listener observed on `8787`: PID `53808` earlier in this pass, about `2.5 GB` RSS before stop.
- After that heavy Jarvis process exited, `memory_pressure` free percentage moved from `35%` to `85%`.
- Existing Ollama process remained small and was not the primary memory culprit.
- Existing live listener later reappeared on `8787`: PID `78733`, about `842 MB` RSS at observation time.

## Oversized / Sensitive State Files Preserved In Place

```text
data/settings/assistant_core_log.jsonl         13G
data/settings/assistant_core_state_log.jsonl   13G
data/logs/llm_usage_state_log.jsonl            47M
data/agents/event_bus_state_log.jsonl          33M
```

- No oversized logs were deleted.
- No archive move was performed in this pass.

## What Changed In Phase 0A

### New stabilization utility

- Added `jarvis/state_log_utils.py`
- Provides bounded tail readers for JSONL/text logs.
- Provides byte-tail trimming used for safe rotation without full-file reads.

### Whole-file startup/state readers replaced with bounded tail reads

- `jarvis/assistant_core.py`
- `jarvis/memory.py`
- `jarvis/adaptation.py`
- `jarvis/user_profile.py`
- `jarvis/event_fabric.py`
- `jarvis/approvals.py`
- `jarvis/audit.py`
- `jarvis/runtime.py` guardian-event snapshot path

### Persistence safety

- `jarvis/persistence.py` rotation no longer reads an entire oversized JSONL file into memory before trimming.

### LLM usage log stabilization

- `jarvis/llm_gateway.py`
- Usage writes now append to `llm_usage.jsonl` instead of rebuilding the entire file on every write.
- Usage state snapshots are kept bounded with `JARVIS_USAGE_STATE_RECORD_LIMIT`.
- Usage reads now use bounded tail reads.

### Cloud-light model mode

- `jarvis/config.py`
- `jarvis/main.py`
- `jarvis/llm_gateway.py`
- Added env-driven mode support:
  - `JARVIS_MODEL_MODE=cloud_light`
  - `JARVIS_ENABLE_OLLAMA`
  - `JARVIS_SKIP_MODEL_WARMUP`
  - `JARVIS_STATE_LOG_TAIL_BYTES`
  - `JARVIS_STATE_LOG_TAIL_LINES`
  - `JARVIS_USAGE_STATE_RECORD_LIMIT`
- In `cloud_light` mode:
  - second-brain is disabled by default
  - Ollama auto-start is skipped
  - gateway default fast/reasoning/escalation selectors point to cloud model defaults instead of local Ollama defaults

## Commands Run

### Git / state inspection

```bash
git branch --show-current
git rev-parse HEAD
git log -1 --oneline
git status --short
```

### Runtime diagnosis

```bash
ps -p <pid> -o pid=,rss=,etime=,command=
memory_pressure
ls -lh data/logs/llm_usage_state_log.jsonl data/settings/assistant_core_log.jsonl data/settings/assistant_core_state_log.jsonl data/agents/event_bus_state_log.jsonl
```

### Safe validation

```bash
python3 -m compileall jarvis
python3 scripts/verify.py
python3 -m pytest -q tests/test_voice_ui_conversation_posture.py
python3 -m pytest -q tests/test_command_center_service_surface.py
python3 -m pytest -q tests/test_event_log_wiring_phase3.py
```

### Cloud-light runtime validation

```bash
JARVIS_MODEL_MODE=cloud_light \
JARVIS_ENABLE_OLLAMA=false \
JARVIS_SKIP_MODEL_WARMUP=true \
JARVIS_SERVE_MODE=light \
python3 -m jarvis serve --host 127.0.0.1 --port 8788
curl -sf http://127.0.0.1:8788/health
curl -sf http://127.0.0.1:8788/api/gateway/status
```

## Validation Results

### Compile

- `python3 -m compileall jarvis`
- Result: passed

### Targeted tests

- `python3 -m pytest -q tests/test_voice_ui_conversation_posture.py`
- Result: `5 passed`

- `python3 -m pytest -q tests/test_command_center_service_surface.py`
- Result: `10 passed`

- `python3 -m pytest -q tests/test_event_log_wiring_phase3.py`
- Result: `59 passed`

### Existing live `8787` verification

- `python3 scripts/verify.py`
- Result: partial pass against the already-running Jarvis listener on `http://localhost:8787`
- Observed:
  - `/health` passed
  - `/api/gateway/status` passed
  - `/api/gateway/test` returned `HTTP 502`
  - briefing payload returned warning-level empties
  - approvals and voice status passed

### Cloud-light runtime validation on isolated port

- Boot command: `JARVIS_MODEL_MODE=cloud_light JARVIS_ENABLE_OLLAMA=false JARVIS_SKIP_MODEL_WARMUP=true JARVIS_SERVE_MODE=light python3 -m jarvis serve --host 127.0.0.1 --port 8788`
- `/health` result: passed
- `/api/gateway/status` result: passed
- Observed:
  - runtime PID `64524`
  - runtime RSS about `160848 KB`
  - `brain_graph.second_brain_enabled=false`
  - gateway models reported `fast=gpt-5.4-mini`, `reasoning=gpt-5.4-mini`, `escalation=gpt-5.4-mini`
  - `ollama_available=true` remained visible because Ollama was already running on the machine, but Jarvis `cloud_light` did not require auto-start to come up

## Runtime Versions Observed

- Python: `3.14.4`
- Git: `2.53.0`
- Ollama: `0.30.11`

## Critical State Directories

- `data/settings/`
- `data/logs/`
- `data/agents/`
- `data/system/`
- `data/state/`
- `data/settings/profiles/`
- `~/.jarvis/approvals/`

## Known External / Optional Services

- Ollama
- OpenAI
- Groq
- OpenViking
- Home Assistant
- Google Workspace connectors
- Microsoft Graph connectors
- Catalyst / Postgres-backed components
- MCP / FastMCP-backed components

## External Jarvis Data-Root Readiness

- external Jarvis root checked: yes
- path: `/Volumes/Monday/JARVIS`
- exists: yes
- readable: yes
- approximate size at check time: `0B`
- status: external data root is available as a future derived-data location

## Known Risk Areas

- `jarvis/runtime.py` and `jarvis/service.py` were already dirty before this pass; future work must isolate Phase 0A changes from unrelated local edits.
- `assistant_core` state logs remain very large on disk even though startup hydration is now bounded.
- Existing `8787` runtime drifted from disk at one observation point; the live process should not be treated as canonical code truth.
- `scripts/verify.py` still shows gateway roundtrip failure on the existing live `8787` instance.
- Optional dependencies are still missing in this environment:
  - `psycopg2`
  - `openai`
  - `fastmcp`
- `cloud_light` now routes defaults to cloud models, but cloud success still depends on external credentials/providers being present.

## Obsidian Readiness

- vault exists: yes
- vault readable: yes
- approximate size: `392K`
- markdown file count: `68`
- config variable added/documented: yes
- documented vault variable: `JARVIS_OBSIDIAN_VAULT=/Volumes/Monday/Obsidian`
- index path planned: `/Volumes/Monday/JARVIS/indexes/obsidian`
- vault modified: no
- index built: no
- live conversation wired: no
- status: external source available, integration pending

### Phase 0A Obsidian boundary

- Jarvis does not currently have a completed Obsidian integration in this checkout.
- Phase 0A did not parse the vault.
- Phase 0A did not build a vector index.
- Phase 0A did not copy or modify the vault.
- Phase 0A only verified the external vault path and documented future configuration.
- No completed runtime path was found that wires Obsidian into live conversation.
- `.env.example` now documents that a missing Obsidian path must be treated as unavailable and must not trigger fake-vault creation.

## Phase 3: Obsidian / Memory Grounding

Future work should:

- read `JARVIS_OBSIDIAN_VAULT`
- build a derived index under `/Volumes/Monday/JARVIS/indexes/obsidian`
- retrieve small relevant note snippets per user message
- inject compact context into the conversation mind
- distinguish retrieved Obsidian context from Jarvis memory and inference
- never claim Obsidian knowledge unless retrieval returned actual notes

## Next Recommended Phase

- Phase 1 should start from this Phase 0A checkpoint only after unrelated dirty work is parked outside the baseline commit.
- Phase 1 should focus on consolidation around the stabilized runtime body, not new product behavior.

## Consolidation Truth

> Jarvis is the runtime body. The future product must be rebuilt around one primary companion interaction spine: a smart, loyal friend with tools.

## Commit State

- No commit was created in this pass.
