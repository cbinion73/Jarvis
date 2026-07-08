# JARVIS

This is the single canonical doc for the JARVIS project: what it is, who it's for, current architecture, current real state, open blockers, and how this doc gets updated. Most of what used to live in `docs/` as competing vision/roadmap/status documents has been archived to `docs/archive/2026-07-doc-consolidation/` — it's historical record, not active canon. If you're looking for "what should I read before making a decision," it's this file. Nothing else.

Four files were deliberately **not** archived even though they read like planning docs, because live code reads them by exact path at runtime: `docs/CHRIS-CONTEXT-CANON.md` and `docs/CHRIS-INTENT-CANON.md` are loaded by `jarvis/companion_spine.py` to ground actual conversation responses (retirement/health/travel topic snippets); `JARVIS_LEVEL9_DOCTRINE.md` (repo root) is referenced by `jarvis/supervision_snapshot.py`'s served `/supervision-snapshot` page; `OPENAI_BUILD_GUIDE.md` (repo root) is in an exact-match allowlist in `jarvis/runtime.py`'s sandbox-sync logic. Their content is still summarized in this doc below (Truth Contract, safety guardrails), but don't move the files themselves without updating the code that points at them.

---

## What JARVIS actually is

JARVIS is Chris's personal AI companion: a FastAPI backend plus a cinematic web HUD, grounded in Chris's own notes (Obsidian), memory, and daily rhythms. It is not a household smart-speaker OS, not a multi-agent civilization simulator, and not a generic chatbot. The product surface that's actually shipping is a companion experience — a morning brief, a holographic-styled HUD ("The Forge"), a Health page with real data, a coaching module ("Sam Wilson"), and vault-grounded conversation — sitting on top of a real backend subsystem for missions, agents, permissions, and memory that predates the current visual direction and is still actively developed alongside it.

**Scope, explicitly (2026-07-08 decision):** personal, not household-wide. Earlier planning (PRD v1, the original README, several archived docs) described a whole-household operating system — family logistics, child-safe tutoring, smart-home control for everyone. That's no longer the target. JARVIS is built around Chris. Family members remain background context (below), not product users with their own accounts, permissions, or tutoring flows.

This doc replaces roughly 30 prior vision/roadmap/status documents that had drifted out of sync with each other and with the code. If a decision needs a "why," look at the code and tests first; this doc is a map, not a constitution.

## Chris — the person this is built for

- Chris Binion, Alexandria/Northern Kentucky. Director of Digital Innovation at Thermo Fisher Scientific (AI, scientific copilots, "Lab of the Future," knowledge graphs, agentic systems).
- Family: wife Rebekah, daughter Anna, son Caleb, adult son Jonathan.
- Scoutmaster, Troop 95.
- Writing/publishing projects: *Signal to Action*, *The Thinking Partner*, *The Influence Engine*, *4P*, plus faith and leadership titles.
- Faith background: Southern Baptist / Pentecostal Evangelical.
- Health context relevant to the Health module: Type 2 diabetes, high blood pressure, metabolic syndrome, gastric sleeve history, chronic pain.

## Current architecture (factual, not aspirational)

- **Backend:** Python, FastAPI, served via `main.py` → `jarvis/service.py`. `jarvis/web.py` is legacy — not the real server.
- **Persistence:** JSON/JSONL via `jarvis/persistence.py`, using `fcntl` file locking, proven safe under concurrent access. No SQL database (`data/system/jarvis.db` does not exist and there's no active plan to add one).
- **Production:** Hetzner VPS, Docker Compose (`jarvis` + `chronicle` + `ghostwritr` + `nginx` + `cloudflared` + `postgres` + `redis`), data in Docker volume `jarvis_data` at `/app/data`. Push to `main` on GitHub auto-deploys via `.github/workflows/deploy.yml` — this has been reliable (verified via `gh run list`, every recent push deployed successfully in ~30s). Everything runs on Hetzner now — nothing is local-only. This supersedes the original "no cloud dependency, local-first for sensitive data" design value from the household-era vision, for two independent reasons: the whole-house deployment that value assumed is no longer the target (see Scope above), and separately, cheap-tier model inference was found to cost about the same self-hosted as cloud-routed, so there's no cost incentive to keep anything local either. Neither is an oversight.
- **Working directory:** the live repo is `~/Desktop/CODE/JARVIS`. `~/Desktop/JARVIS` (no `CODE`) is a stale empty stub from before the repo was relocated — several older docs and even a launchd plist still reference it (and one OneDrive path variant), which has caused real confusion more than once. If you're not in `CODE/JARVIS`, you're in the wrong place.
- **LLM routing:** `jarvis/llm_gateway.py` implements a cost-aware model ladder, gated by an approval queue for the most expensive tier. It supports a local-Ollama mode (`JARVIS_MODEL_MODE=standard`), but production runs `JARVIS_MODEL_MODE=cloud_light` (the default in `.env.example`) — everything routes through OpenAI/Groq, no local model dependency. This isn't a limitation of Hetzner; Chris determined cheap-tier inference costs about the same whether self-hosted (Ollama on local hardware) or cloud-routed, so there's no cost reason to run anything local-only. Nothing in the system requires local-only operation anymore.
- **Missions subsystem:** `jarvis/missions.py` (real, actively developed, last touched within the last week) with a full `/api/missions*` route set in `service.py`. This is a live backend concept independent of the HUD — don't assume it's superseded just because the visual product has moved to a HUD/companion presentation.
- **Obsidian integration:** Two directions, both real. Read: `jarvis/obsidian_context.py` (LlamaIndex-backed retrieval, env-configured via `JARVIS_OBSIDIAN_VAULT`, `JARVIS_OBSIDIAN_INDEX_PATH`, `JARVIS_OBSIDIAN_RETRIEVER=llamaindex`) feeds live vault context into conversation. Write: `jarvis/obsidian_writer.py` lets JARVIS propose notes back to the vault — it never writes silently; proposals require approval.
- **Governance/safety:** Trust-zone registry (`jarvis/trust.py`), supervision/approval evaluation (`jarvis/supervision.py`), a 50+ action-type policy taxonomy across 14 families (`jarvis/policy_rails.py`), promotion engine (`jarvis/promotion.py`), runtime lifecycle kernel (`jarvis/runtime_kernel.py`). Hard policy rails that always deny regardless of authority level: spend_money, sign_document, remote_unlock, post_social, create_account, change_credentials, submit_filing. Email capability is draft-only — no send capability anywhere in the codebase.
- **Child safety:** `CHILD_USER_IDS = {caleb, anna}` — child data sharing and guardrail overrides always deny.
- **Voice/API vendors:** OpenAI Responses API for text/multimodal, Realtime API for voice; ElevenLabs for premium voice output with a local fallback for critical alerts.
- **LangGraph usage is intentionally scoped**: it lives in `jarvis/graphs.py` / `jarvis/runtime.py` for specific flows (`run_response_graph`, `run_party_mode_graph`, `run_background_cycle_graph`, `run_wealth_leverage_graph`). Do not replace `jarvis/memory.py`, `agent_memory.py`, `known_facts.py`, `llm_gateway.py`, or the approval queue with framework abstractions — that decision was made deliberately.

## Current real state

As of commit `96ffaba` (2026-07-08): 2,216 tests passing, 3 skipped, 0 real failures. Production is current — every recent push has deployed successfully to Hetzner.

Skip percentage-based maturity scoring — this project's history shows it produces false confidence (a prior audit found supposedly-"done" governance features were tested data contracts with zero runtime callers — a route existed and a test passed, but nothing in the actual request path ever called it). If you want to know whether something works, trace the call path from an actual route or CLI entrypoint to the behavior, or write an integration test that exercises it — don't trust a checklist.

**Two workstreams whose status is genuinely unclear and should be confirmed with Chris rather than assumed:**
- Apple/iOS/CarPlay native work (`JarvisApple/` — `JarvisKit`, `NavigateView.swift`, `CarPlaySceneDelegate.swift`). Code- and compile-backed as of the last check, but not simulator-proven (local CoreSimulator/Xcode version mismatch). Unknown if this is still an active lane.
- The three-role "Architect Office / Build Office / QA" process and its "isolated-first" convention (prefer a git worktree over working in a dirty main checkout when picking up a scoped slice of work). Worth confirming whether this is still how Chris wants work structured, or a discarded phase.

## Product voice — the Truth Contract

JARVIS should read as a smart, loyal friend with tools — not a therapist, not a dashboard, not a mystical companion, not a corporate command center, not "agent theater." Two litmus questions for any new capability: *Would Chris want to keep talking to this?* and *Did JARVIS help Chris think, decide, build, remember, or act?*

Hard rule: JARVIS may only say "I searched / I found / I opened / I saved / I remembered / I created / I sent / I scheduled / the agents did / Obsidian says" if that action genuinely happened. If it didn't, state the limitation plainly rather than implying capability that doesn't exist. This is the single most important behavioral rule in the project and the most common way prior iterations went wrong.

New-conversation default: be warm and available, don't force the last topic ("Hey Chris, what are we getting into?" — not "Picking up where we left off...").

## Safety / autonomy guardrails (product-agnostic, still applies)

Pause and ask before: destructive actions, overwriting prior work, deleting branches/worktrees, force-pushing, rebasing mature branches, irreversible migrations, secrets exposure, external communications, purchases/paid services, production/live changes.

Don't pause for: safe local implementation, tests, docs, local demos, clearly-marked mock data, reversible code changes in trusted lanes.

## Open external blockers (need Chris, not code)

Two items from the old household-era blocker list are now out of scope, not just unblocked — they were whole-house features that don't fit a personal-use product:

- ~~Home Assistant~~ — smart-home control for the whole house. Out of scope under the personal-use narrowing; the adapter code exists in the repo but isn't a current priority.
- ~~Perception hardware~~ — porch/garage cameras, room presence, motion sensors. That's household security/presence monitoring, not personal companion functionality. Out of scope.

Still genuinely open, and still personal-scope:

- **Workshop hardware:** Chris's own maker stack (planning, CAD packaging, print prep, safety checks, inventory) is built in software; Bambu/Cricut printer telemetry and upload paths are still simulated, not connected to Chris's real devices.
- **Wake word / speaker ID:** currently heuristic (config + context + device mapping). With scope narrowed to one user, this simplifies to "does JARVIS hear Chris and wake up," not multi-person speaker discrimination — lower complexity than originally scoped, still not real.
- **Home footprint:** launchd templates, runbooks, and network plans exist on paper for a personal local-resilience upgrade (NAS/UPS/segmented network); not applied to any real hardware. Hetzner already satisfies the always-on hosting need, so this is optional polish, not a functional gap.

## Reusable patterns worth remembering (not active work, just good ideas on the shelf)

- A numbered permission-class model (Observe → Suggest → Prepare → Execute-low/med/high → Restricted) was designed once for a broader approval engine. If a future feature needs tiered approval, this pattern is worth revisiting rather than reinventing.
- Evidence-quality bar for claiming something works: a test asserting a string exists in source code is weak proof; a runtime smoke test with exact prompts/routes/outputs is strong proof. Prefer the latter before marking anything done.

## How to update this doc

Append-only changelog style, right here — not a new parallel document. When something material changes (a subsystem ships, a blocker clears, an architecture decision changes), edit the relevant section above and add a dated one-line entry below. If you're about to write a new vision/roadmap/status document instead of editing this one, stop — that's exactly the pattern that produced 30 competing docs last time.

### Changelog

- 2026-07-08 — Consolidated ~30 vision/planning/status docs into this single file. Originals archived to `docs/archive/2026-07-doc-consolidation/`.
- 2026-07-08 — Corrected: nothing runs local-only anymore. Production is fully on Hetzner; cheap-tier model cost was found to be about the same self-hosted vs. cloud-routed, so the local-Ollama path (`JARVIS_MODEL_MODE=standard`) exists in code but isn't the deployed default (`cloud_light` is).
