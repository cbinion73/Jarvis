# JARVIS Understanding Audit

Date: 2026-06-26
Repo: `/Users/chris/Desktop/CODE/JARVIS`
Mode: discovery only

This report is intentionally blunt. It describes the repository as it exists in this checkout. It does not assume that named features are complete just because they have routes, files, or UI shells.

## Executive read

JARVIS is real software, not just a deck, but it is not one coherent product yet.

What is real:

- A Python-first runtime with a very large FastAPI service surface.
- A persisted local state model under `data/` and `~/.jarvis/health`.
- A functioning conversation path that can route requests, call LLMs, persist turns, and inject some continuity context.
- A substantial amount of real subsystem code for health, home, missions, memory, approvals, Chronicle, workshop/forge, finance, scheduling, and Apple-facing APIs.
- A separate Swift package scaffold for Apple clients with shared models and contracts.

What is not true:

- This is not a cleanly unified “smart loyal friend with tools” product today.
- It is not one focused interaction model.
- It is not a small, legible architecture.
- It is not fully local.
- It is not mostly conversational in implementation. Much of it is a broad control surface over many stores and subsystem handlers.

The repo currently behaves more like:

- a large household/workbench platform,
- with a conversational layer on top,
- mixed with many aspirational surfaces,
- plus doctrine, mockups, and specialist-domain experiments,
- all living in one codebase.

The foundation is probably salvageable. The current shape is not clean enough to become the long-term foundation without synthesis and hard pruning.

## Start-state report

1. Repo path

- `/Users/chris/Desktop/CODE/JARVIS`

2. Current branch

- `main`

3. Latest commit hash and message

- `994d281e0ff7a9a04919f1255d09d2f0c1b8e401`
- `Ignore generated runtime state artifacts`

4. Git status

Dirty worktree. Existing uncommitted changes were not touched.

Modified:

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

Untracked:

- `_bmad-output/brainstorming/`
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

5. Runtime versions observed in this environment

- Python `3.14.4`
- Node `v24.14.1`
- npm `11.11.0`

6. Package manager

- Python/pip is the real package manager path.
- No top-level `package.json` was found.
- Swift Package Manager is used in `JarvisApple/Package.swift`.

7. Main run commands

From `README.md` and repo scripts:

- `bash scripts/setup.sh`
- `python -m jarvis serve --host 0.0.0.0 --port 8787`
- `python -m jarvis voice --text-loop`
- `python -m jarvis voice --realtime`
- `python scripts/verify.py`
- `swift test` from `JarvisApple/` is implied by the package layout

8. Main test commands

Implied, not centrally standardized:

- `pytest`
- targeted `pytest tests/test_...py`
- `node tests/e2e/run-all-e2e.cjs` for JS e2e scripts
- `swift test` in `JarvisApple/`

9. Environment variables required

Core:

- `OPENAI_API_KEY`
- `ELEVENLABS_API_KEY` for preferred cloud TTS
- `HOME_ASSISTANT_URL`
- `HOME_ASSISTANT_TOKEN`
- `OLLAMA_BASE_URL`
- `LOCALAI_BASE_URL`
- `OPENVIKING_*`

Common integrations:

- Google OAuth and tokens
- Microsoft Graph OAuth and tokens
- `COZI_*`
- `PLAID_*`
- `DEXCOM_*`
- `OMRON_*`
- `GOOGLE_MAPS_API_KEY` or equivalent
- `CLOUDFLARE_TUNNEL_TOKEN`
- `DB_*` and `CATALYST_DB_URL`
- `GHOSTWRITR_*`
- `LIVEKIT_*`
- `GROQ_API_KEY`
- `TAVILY_API_KEY`

10. Known external dependencies

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
- Ghostwritr service and database
- PostgreSQL
- Redis
- Cloudflare Tunnel
- Playwright
- LiveKit
- Kasa devices
- KDP scraping flow

## High-level repo map

### Primary runtime areas

- `jarvis/`
  - Main Python application.
  - Contains runtime, service, routes, stores, domain logic, voice, integrations, UI HTML renderers, and Apple route registration.

- `data/`
  - Real persisted local runtime state.
  - Large number of JSON, JSONL, lock, and state-log files.
  - This is not just fixture data. It is part of the active system shape.

- `household/`
  - Household config, example profiles, snapshots, and persona-related config inputs.

### Frontend / UI surfaces

- `jarvis/voice_ui.py`
  - Main web shell HTML/CSS/JS generator.
  - Very large embedded UI surface.

- `jarvis/render_pages.py`
  - Large server-rendered module pages and workspace pages.

- `jarvis/device_views.py`
  - Alternate device-specific views, including TV/mobile-style surfaces.

- `jarvis/jarvis_theme_glass.py`
- `jarvis/jarvis_theme_nexus.py`
  - Theme-heavy alternative shells and UI experiments.

### Backend / server

- `jarvis/service.py`
  - Main FastAPI app.
  - Extremely large.
  - 846 routes in this file alone by simple decorator count.

- `jarvis/apple_api.py`
  - Registers a second large Apple-specific route surface.
  - 137 `/api/apple/...` routes by simple decorator count.

- `jarvis/web.py`
  - Older/simple HTTP server path still exists.
  - Overlaps conceptually with FastAPI service responsibilities.

### Conversation / LLM / routing

- `jarvis/runtime.py`
- `jarvis/orchestrator.py`
- `jarvis/openai_tasks.py`
- `jarvis/graphs.py`
- `jarvis/persona.py`
- `jarvis/conversation.py`

### Memory / knowledge / continuity

- `jarvis/memory.py`
- `jarvis/known_facts.py`
- `jarvis/openviking_context.py`
- `jarvis/chronicle*.py`
- `data/memory/`
- `data/conversations/`

### Agents / autonomy / supervision

- `jarvis/agentic.py`
- `jarvis/agent.py`
- `jarvis/runtime_kernel.py`
- `jarvis/scheduler.py`
- `jarvis/event_fabric.py`
- `jarvis/supervision.py`
- `jarvis/trust.py`
- `jarvis/promotion.py`
- `data/agents/`
- `data/supervision/`
- `data/trust/`

### Domain systems

- Health: `jarvis/health_*.py`, `jarvis/longevity_*.py`, `jarvis/symptom_triage.py`
- Home: `jarvis/home*.py`, `jarvis/kasa_bridge.py`, `jarvis/ha_safety.py`
- Calendar/email/workflow: `jarvis/gmail_bridge.py`, `jarvis/gcal_bridge.py`, `jarvis/outlook_bridge.py`, `jarvis/unified_inbox.py`, `jarvis/home_projects.py`, `jarvis/signal_router.py`
- Workshop/forge: `jarvis/workshop*.py`, `jarvis/forge*.py`, `jarvis/wow_forge.py`
- Publishing/content: `jarvis/publishing_suite.py`, `jarvis/kdp_*.py`, `jarvis/book_launch.py`, `jarvis/social_engine.py`
- Finance/growth: `jarvis/financial_intelligence.py`, `jarvis/plaid_connector.py`, `jarvis/growth*.py`, `jarvis/wealth.py`

### Apple clients

- `JarvisApple/`
  - Swift package scaffold and shared client libraries.
  - Real package structure.
  - Still not a completed app workspace.

### Specs / doctrine / product docs

- `docs/`
  - Active canon, roadmap, interaction Bible, mission contract, UX doctrine.

- `docs/archive/`
  - Archived doctrine and older resets.

- `_bmad-output/planning-artifacts/`
  - Generated planning artifacts.

### Experimental / concept-heavy areas

- `artifacts/mockups/`
  - HTML mockups and concept surfaces.

- `jarvis/jarvis_theme_glass.py`
- `jarvis/jarvis_theme_nexus.py`
- multiple “center”, “command”, “storyboard”, “workspace”, and “theme” routes

### Tests

- `tests/`
  - 171 Python test files.

- `tests/e2e/`
  - 9 JS e2e files.

### Deployment / operations

- `Dockerfile`
- `deploy/`
- `infra/launchd/`
- `infra/scripts/`
- `ops/`
- `.github/workflows/`

### Old / deprecated / overlapping areas

- `jarvis/web.py` overlaps with `jarvis/service.py`
- `docs/archive/` indicates doctrine churn
- multiple UI theme systems coexist
- many routes and stores appear additive rather than consolidated

## Runtime architecture

### What process starts first

Nominally:

- `python -m jarvis serve --host 0.0.0.0 --port 8787`

In practice:

- `jarvis/main.py` builds `JarvisRuntime.from_env()`
- initializes a large set of optional subsystems
- then `jarvis/service.py` builds the FastAPI app
- `uvicorn` serves it

### What server(s) run

Primary local server:

- FastAPI via `jarvis/service.py` on port `8787`

Secondary/legacy server:

- `jarvis/web.py` provides a separate HTTP server implementation

Other expected local or sidecar services:

- Ollama
- LocalAI
- OpenViking
- optional Chronicle service
- optional Ghostwritr service
- Postgres and Redis in docker deploy mode
- Cloudflare/Nginx in deployed mode

### Ports used

Observed defaults:

- `8787` JARVIS FastAPI
- `8080` LocalAI
- `11434` Ollama
- `1933` OpenViking
- `5174` Chronicle in docker config
- `3000` Ghostwritr in docker config
- `5432` Postgres
- `80` Nginx in deploy compose
- `18789` OpenClaw gateway websocket default

### What UI opens

Primary:

- `/` renders the voice shell from `jarvis/voice_ui.py`

Also many alternate centers/pages:

- `/glass`
- `/nexus`
- `/health-center`
- `/home-center`
- `/agents-center`
- `/catalyst-center`
- `/forge-center`
- `/chronicle-center`
- many others

### What routes/endpoints exist

Large surface area:

- `846` routes in `jarvis/service.py`
- `137` routes in `jarvis/apple_api.py`

Representative categories in `service.py`:

- home: 53
- health: 51
- finance: 30
- forge: 30
- chronicle: 28
- publishing: 25
- foundry: 18
- growth: 15
- missions: 14

This breadth is real, but it is also a warning sign. The product surface is wider than the current coherence.

### What background workers start

Real background concepts exist:

- `BackgroundTaskScheduler`
- `AgentRuntimeKernel`
- assistant autonomy loops
- scheduler ticks
- event fabric
- supervision and promotion traces

But the always-on picture depends on environment and launch mode. The code supports a background organism more strongly than the deploy/readme path proves it is consistently running.

### What local services are expected

- Ollama
- LocalAI
- Home Assistant
- OpenViking
- optional Piper binary
- optional LiveKit
- optional browser/Playwright

### What databases/files are read/written

Files:

- extensive JSON/JSONL state in `data/`
- conversation threads in `data/conversations/`
- memory in `data/memory/`
- agent/runtime state in `data/agents/`
- logs in `data/logs/`

Databases:

- SQLite for health at `~/.jarvis/health/health.db`
- SQLite index at `jarvis/sqlite_index.py`
- Postgres for Catalyst / Ghostwritr paths in some deploy modes

### What external APIs are called

- OpenAI
- ElevenLabs
- Google APIs
- Microsoft Graph
- Dexcom
- Omron
- Plaid
- Home Assistant
- Google Maps / Nominatim
- NOAA / weather feeds
- Playwright-mediated browser search
- Cloudflare tunnel infrastructure

### What breaks if credentials are missing

Credentials are not uniformly optional. Missing credentials often degrade features silently or partially.

Examples:

- No `OPENAI_API_KEY`: cloud responses fail, some prompts fall back, some subsystems still work locally
- No Ollama/local brain: local-first plans degrade
- No Google/Microsoft auth: calendar/email connectors become disconnected
- No Home Assistant: home actions become not live
- No ElevenLabs/Piper/LocalAI voice components: speech output degrades
- No Dexcom/Omron/Plaid/etc.: those domain modules become mostly shells or disconnected views

### Architecture diagram

```text
CLI / launchd / docker
        |
        v
  jarvis.main
        |
        v
 JarvisRuntime.from_env()
        |
        +--> config + household profiles
        +--> stores under data/
        +--> orchestrator + permission engine
        +--> memory + Chronicle + missions + supervision
        +--> connectors (Google, Microsoft, Home Assistant, etc.)
        +--> local/cloud model clients
        |
        v
  jarvis.service FastAPI
        |
        +--> web shell routes
        +--> module pages
        +--> JSON APIs
        +--> websocket events
        +--> apple_api route registration
        |
        v
 UI surfaces / Apple clients / scripts

Conversation path:
user input
  -> runtime.plan_request()
  -> heuristic intercepts (mission/task/calendar/reminder in some paths)
  -> run_response_graph()
  -> live context + optional OpenViking context
  -> OpenAI or Ollama path
  -> persistence to conversation/audit/memory/catalyst
```

## UI / frontend audit

### Overall judgment

There are many UI surfaces. Too many.

This repo does not present one clear frontend. It presents:

- a main chamber/voice shell,
- multiple themed variants,
- many module centers,
- Apple-specific API clients,
- device-specific views,
- and mockup/proposal files.

That is breadth, not clarity.

### Primary shell

- File: `jarvis/voice_ui.py`
- Route: `/`
- Purpose: main interactive chamber shell
- Style: cinematic/glass/chamber aesthetic, heavy embedded HTML/CSS/JS
- Works: shell rendering, actor/room controls, conversation panel, packetized workspace feel
- Does not prove: overall product coherence or that every linked module is robust
- Backend link: `/api/shell-state`, `/api/chat-state`, many module APIs
- Usable today: yes, as the main shell concept

### Alternate themed shells

- Files: `jarvis/jarvis_theme_glass.py`, `jarvis/jarvis_theme_nexus.py`
- Routes: `/glass`, `/nexus`
- Purpose: alternate branded shell experiences
- Current state: visually ambitious, but contributes to fragmentation
- Usable today: partially, but they multiply surface-area debt

### Module centers

Examples:

- `/health-center`
- `/home-center`
- `/agents-center`
- `/forge-center`
- `/catalyst-center`
- `/chronicle-center`
- `/settings-center`

These are real route-backed surfaces, mostly rendered from `jarvis/render_pages.py`. They appear more like a large workstation/dashboard family than one intimate companion interface.

### Health UI

- Files: `jarvis/render_pages.py`, health modules, health chat JS inside theme files
- Routes: `/health-center`, `/api/health/...`, `/api/apple/health/...`
- Strength: substantial real backend and stored data model
- Weakness: voice/personality consistency is diluted by specialist-doctor chat patterns
- Usable today: more real than many other domains

### Chronicle / faith UI

- Files: `jarvis/render_pages.py`, `jarvis/chronicle_bridge.py`
- Routes: `/chronicle-center`, `/api/chronicle/...`, `/api/apple/chronicle/...`
- Status: real surface, but product identity drifts from core companion behavior into a specialized subsystem

### Catalyst / workbench UI

- Files: `jarvis/render_pages.py`
- Routes: `/catalyst/view/{page}`, `/catalyst-center`, `/api/apple/catalyst/...`
- Status: real and broad, but feels more like an operations workspace than a single companion

### Forge / workshop UI

- Files: `jarvis/render_pages.py`, `jarvis/jarvis_theme_glass.py`, workshop/forge backend files
- Routes: `/forge`, `/forge-center`, `/api/forge/...`
- Status: real code, real routes, domain-specific usefulness
- Caveat: a specialized maker tool lane, not central companion identity

### Agents / supervision UI

- Routes: `/agents`, `/agents-center`, `/agents/hierarchy`, `/mission-board`, `/agent-ops-center`
- Status: real route-backed control surfaces
- Caveat: pulls the product toward operator console grammar

### Settings / accounts UI

- Route: `/settings-center`, plus many account and profile endpoints
- Status: real
- Caveat: required because the system has many connectors and feature flags

### Mobile / TV / Apple concepts

- Swift package and client scaffolds exist in `JarvisApple/`
- `jarvis/device_views.py` contains device-specific HTML views
- CarPlay and Apple route surface exists in `jarvis/apple_api.py`
- Reality: Apple client contract work is real, but the native app side is still scaffold-level in this checkout

### Usability conclusion

Usable today:

- core web shell
- many JSON APIs
- several module pages
- some health/workbench/mission surfaces

Not credibly unified today:

- overall IA
- emotional experience
- product identity
- boundary between chamber, dashboard, workbench, and admin console

## Conversation system audit

### Where user input enters

Main web path:

- `runtime.converse(...)` in `jarvis/runtime.py`
- API state routes in `jarvis/service.py`
- shell JS from `jarvis/voice_ui.py`

CLI/voice path:

- `JarvisVoiceShell.handle_text_turn()` in `jarvis/voice.py`
- calls `runtime.respond(...)`

Legacy HTTP path:

- `jarvis/web.py`

### Where messages are routed

- `JarvisOrchestrator.route()` in `jarvis/orchestrator.py`

This is heuristic routing, not a learned controller. It infers:

- mode
- module
- workstream
- task class
- provider
- context lane
- model
- risk and privacy

### Whether there is an LLM call

Yes.

Primary path:

- `run_response_graph()` in `jarvis/graphs.py`
- `JarvisOpenAIClient.respond()` in `jarvis/openai_tasks.py`

### Which model/provider is used

Mixed:

- OpenAI Responses API
- Ollama “second brain”
- browser-search-assisted context injection
- some other gateway/provider code exists elsewhere

### Whether system prompts exist

Yes, clearly.

- `jarvis/persona.py`
- `jarvis/voice_pipeline.py` voice rules
- specialist prompts
- Marvel persona snippets

### Whether memory/context is injected

Yes, but unevenly.

- `run_response_graph()` injects live weather/calendar
- may inject OpenViking retrieved context
- `runtime.converse()` builds a continuity excerpt from stored conversation thread and learning hooks

### Whether tools can be called

Not in the main `runtime.respond()` path as a rich agentic tool-calling conversation engine.

What exists instead:

- deterministic intercepts before LLM call for reminders, tasks, calendar, missions
- many direct subsystem endpoints
- separate agent/tool code elsewhere

The product often acts by routing into local code, not by a general tool-calling dialogue loop.

### Whether response text is generated by model, templates, or both

Both.

- Many domain outputs are prompt-generated.
- Many others are deterministic summaries, intercept responses, or route-backed snapshots.

### Whether conversation history persists

Yes.

- `jarvis/conversation.py`
- persisted in `data/conversations/`

### Conversational or command-driven?

Mixed, but currently more command-and-surface-driven than truly companion-conversational.

The conversation layer is real.
The overall product implementation is still dominated by:

- route surfaces,
- subsystem handlers,
- state stores,
- and heuristic dispatch.

### Honest judgment

JARVIS does not yet have one strong unified conversational mind.

It has:

- a real conversation wrapper,
- a persona stack,
- persisted threads,
- some continuity injection,
- LLM calls,
- and many local interceptors.

That is stronger than a stub.
It is weaker than a truly integrated companion intelligence architecture.

## Voice / personality audit

### Where personality lives

- `jarvis/persona.py`
- `jarvis/voice_pipeline.py`
- specialist prompts
- Marvel persona snippets
- various UI copy and hardcoded lines

### Intended sound

Primary persona target:

- calm
- competent
- warm
- crisp
- trusted
- conversational

### Actual sound risk

The repo contains multiple competing voice/posture systems:

- core JARVIS persona
- Marvel agent-domain voice snippets
- voice mode rules
- Chronicle/faith specialty voices
- health doctor personas
- shell/UI posture copy

This creates tonal fragmentation.

### Does it sound like a smart loyal friend?

Sometimes, in the core persona file.

### Does it sound like a therapist?

Less than Monday-era health work, but some formation/health specialist surfaces can drift away from everyday-friend posture.

### Does it sound like a dashboard?

Yes, often.

The route and module structure strongly pushes it toward dashboard/workbench/operator-console behavior.

### Does it sound generic?

Not generic in ambition.
But generic assistant behavior can still appear in many LLM-backed domain outputs because the architecture is fragmented.

### Does it over-explain?

Risk exists, especially where broad domain prompts are used without a tight interaction layer.

### Does it become mystical/corporate/robotic?

All three risks exist in different areas:

- mystical in some Chronicle/formation posture
- corporate in Catalyst/workflow/workbench surfaces
- robotic in system-heavy module and route responses

## Memory / Obsidian / knowledge audit

### What exists

- persisted conversation store
- memory entries/proposals/profile facts in `data/memory/`
- Chronicle continuity
- OpenViking retrieval integration
- known-facts and continuity support code

### Obsidian grounding

Not established here as the clear primary memory backbone.

This audit did not find a simple, central “Obsidian is the memory core” runtime path. The real memory backbone in this checkout is the repo’s own local JSON/JSONL stores plus optional OpenViking retrieval.

### Vector store

OpenViking appears to be the main retrieval-style path, but it is optional and externalized.

### Persistence truth

Memory is real and persisted.
But the memory architecture is not cleanly singular.

## Testing / validation audit

### What is real

- 171 Python test files
- 9 JS e2e files
- Swift package tests in `JarvisApple/Tests`

### What that means

This repo is not untested.
There is significant test intent.

### What it does not mean

It does not prove the whole product is coherent or that the deploy/runtime behavior matches the product story.

The test suite appears broad and subsystem-heavy. That is useful for local regression coverage, but it also reflects the repo’s fragmentation.

## Deployment / ops audit

### Local

- launchd scripts and plists exist
- setup scripts exist
- verify script exists

### Hosted

- Dockerfile
- deploy compose
- nginx
- Cloudflare tunnel
- GitHub Actions deploy workflow

### Reality note

The deploy workflow is real and destructive:

- fetches
- stashes dirty changes
- hard resets to `origin/main`
- rebuilds `jarvis`

The hosted path exists, but it mainly proves deploy machinery, not that the entire multi-surface product is production-ready.

## What works vs what is aspirational

### Real and likely salvageable

- main Python runtime scaffold
- FastAPI app
- persisted local state model
- conversation persistence
- heuristic request planning
- mixed OpenAI/Ollama response path
- health subsystem depth
- missions/approvals/supervision/trust substrate
- workshop/forge subsystem
- Apple contract/scaffold package

### Real but structurally problematic

- enormous route surface
- giant single-file service and UI generators
- multiple overlapping shells and themes
- too many concurrent product grammars
- additive domain growth without enough consolidation

### Aspirational / partially real / overextended

- always-on orchestrator civilization framing as a single clean product reality
- unified companion identity across all modules
- seamless Apple-native experience in this checkout
- one stable, obvious frontend
- one stable memory spine

## Fake, stubbed, or misleading by naming

Not outright fake, but naming often overstates maturity.

Patterns to treat carefully:

- files/routes named like finished “systems” may still be partially wired
- multiple “centers”, “command”, “workspace”, “theme”, and “storyboard” surfaces imply completeness they may not have
- Apple scaffolding is real scaffolding, not the same as completed Apple apps
- “always-on” and “agent society” framing is stronger in docs than in one simple operational runtime story

## What should become the foundation going forward

If the goal is to decide what is worth synthesizing into a future companion system, the strongest foundation pieces in this checkout are:

- `jarvis/runtime.py` plus the store-based local state model
- `jarvis/conversation.py` persisted conversation layer
- `jarvis/orchestrator.py` heuristic request planning as a starting control plane
- `jarvis/openai_tasks.py` and `jarvis/graphs.py` as the current LLM bridge
- mission / approval / supervision / trust substrate
- health and workshop as examples of domain systems that are deeper than mockups
- `JarvisApple/` shared package and API contract work

What should not be treated as the foundation without pruning:

- the full current route surface
- multiple overlapping shell/theme systems
- the current product IA as-is
- the full Marvel/persona layering approach as-is

## Final judgment

JARVIS is not vaporware.

It is also not a cleanly realized private AI companion yet.

The real truth is:

- there is a substantial load-bearing backend here,
- there is real local state, real persistence, and real subsystem work,
- there is a functioning conversation layer,
- but the repository has sprawled into too many product identities at once.

The most honest short description is:

JARVIS is a large, partially integrated household/workbench intelligence platform with a real conversation layer, real local state, strong subsystem ambition, and significant architectural sprawl.

If Chris wants to switch back from Monday to JARVIS, the best reason is not that JARVIS is already cleaner. It is that JARVIS still contains more of the practical runtime substrate and domain machinery that could be consolidated into a future system.

If Architecture Office wants a foundation, the value is in the runtime substrate and the real stores, not in preserving the entire current product surface.
