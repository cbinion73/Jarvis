# JARVIS Data Architecture v1

## Purpose

This document defines the first practical data architecture for JARVIS.

It answers one question directly:

What should stay file-backed, and what should move into SQLite first?

The goal is not to turn JARVIS into enterprise infrastructure. The goal is to give JARVIS a storage model that is:

- local-first
- fast enough for chamber and background-agent use
- safe for household trust boundaries
- queryable across domains
- simple enough to run on one always-on local host

## Current Reality

Today JARVIS is primarily file-backed.

The runtime wires many domain stores from `data/...` and most of those stores read and write JSON or JSONL files directly.

This has been a good fit for:

- rapid feature growth
- simple inspection and debugging
- local-first operation
- artifact-oriented workflows

It is starting to become a weaker fit for:

- cross-domain chamber synthesis
- ranking and retrieval
- concurrent background work
- audit-heavy autonomy
- queue and run coordination
- repeated full-file load and save behavior in hot paths

## Core Decision

JARVIS v1 should use a mixed model:

- `SQLite` for hot structured state
- `JSON` and `JSONL` for bulky artifacts, append-only logs, and export-friendly records

This is the right next step because it improves operational performance and data integrity without forcing a full service/database platform jump.

## Design Rules

1. Local-first remains the default.
2. Sensitive household memory stays local.
3. Chamber-critical reads should come from indexed state, not repeated full-file scans.
4. Append-only audit trails may remain file-backed even if indexed metadata moves into SQLite.
5. Large generated artifacts should remain file-backed unless they need relational querying.
6. Trust boundaries matter more than theoretical normalization.
7. SQLite is the first database, not the forever database.

## Storage Classes

JARVIS data should be treated as four classes:

### 1. Hot Structured State

Frequent reads, updates, filtering, ranking, or joins.

Examples:

- approvals
- memory metadata
- active runs
- agent work items
- conversation/session index
- chamber snapshot inputs

This should move to `SQLite` first.

### 2. Append-Only Event Streams

Useful for auditing, replay, and debugging.

Examples:

- action logs
- tick logs
- inspections
- chronicle entry streams

These may remain `JSONL`, but can also be indexed into SQLite later if needed.

### 3. Generated Artifacts and Drafts

Human-readable outputs, staged packages, drafts, briefs, plans, and payload bundles.

Examples:

- deck drafts
- implementation plans
- content packets
- CAD packages
- print preps

These should remain file-backed unless query pressure grows.

### 4. Configuration and Doctrine

Slow-changing settings and explicit policy state.

Examples:

- trust zones
- authority stages
- doctrine snapshots
- voice settings
- location settings

These can remain file-backed for now unless multi-writer coordination becomes a problem.

## Canonical v1 Posture

### Move to SQLite first

- approvals
- memory metadata and profile facts
- conversation/session index
- self-improvement jobs, runs, and active runs
- agent background state and work queue
- interface router sessions and results
- chamber-facing derived indexes

### Keep file-backed

- audit logs
- chronicle streams
- tutoring session transcripts
- workshop inspection logs
- generated artifacts across catalyst, content, workshop, and family domains
- doctrine, settings, and trust configuration

### Hybrid

- memory
- audit
- catalyst
- content ops
- wealth
- security
- family

Hybrid means:

- relational/indexed metadata in SQLite
- full generated payloads and history artifacts in JSON or JSONL

## Exact Store Mapping

| Area | Store / File | Current Backing | v1 Decision | Why |
| --- | --- | --- | --- | --- |
| Memory | `jarvis/memory.py` -> `data/memory/entries.json`, `proposals.json`, `profile_facts.json` | JSON | `Hybrid` | Memory needs indexed lookup, filtering, and ranking, but full payloads and restricted-local behavior still fit file artifacts well. |
| Approvals | `jarvis/audit.py` -> `data/approvals/pending.json` | JSON | `SQLite first` | Pending approvals are chamber-critical, consequence-ranked, and mutable. This is a clear hot-state table. |
| Audit log | `jarvis/audit.py` -> `data/logs/actions.jsonl` | JSONL | `Keep file-backed` | Append-only audit streams are readable and durable as JSONL. Add SQLite index later only if query cost becomes painful. |
| Self-improvement | `jarvis/self_improvement.py` -> `jobs.json`, `runs.json`, `active_runs.json`, `settings.json` | JSON | `SQLite first for jobs/runs/active runs; keep settings file-backed` | Job queues and active runs need safe concurrent updates and fast status reads. Settings are low-churn config. |
| Conversation index | `jarvis/conversation.py` -> `data/conversations/index.json` | JSON | `SQLite first` | Conversation/session lookup is a clear indexed-state use case. |
| Agent background state | `jarvis/agentic.py` -> `data/agents/background_state.json`, `tick_log.jsonl` | JSON + JSONL | `Hybrid` | Background state and work items should move to SQLite; tick log can stay append-only JSONL. |
| Life agent studio | `jarvis/agentic.py` -> `data/agents/...` | JSON | `SQLite first for registry and work tracking; file-backed for definitions if human-edited` | Agent identity and work ownership want indexed state. Human-readable agent definitions can stay as files if desired. |
| Interface router | `jarvis/interfaces.py` -> `data/router/sessions.json`, `results.json` | JSON | `SQLite first` | Routed handoffs, session tracking, and result lookup are transactional and query-heavy. |
| Catalyst structured state | `jarvis/catalyst.py` -> `signals.json`, `pipeline_state.json`, `pipeline_reviews.json`, `work_lifecycle.json` | JSON | `Hybrid` | Pipeline state and lifecycle indexes belong in SQLite; generated briefs, drafts, and plans can stay file-backed. |
| Catalyst artifacts | `jarvis/catalyst.py` -> run files like `briefing_runs.json`, `draft_runs.json`, `implementation_plans.json`, `project_briefs.json` | JSON | `Keep file-backed` | These are artifacts first, not hot relational state. |
| Content ops state | `jarvis/content_ops.py` -> `veronica_queue.json`, `marketing_state.json`, `marketing_reviews.json` | JSON | `Hybrid` | Queue and state should move to SQLite; content output artifacts can remain file-backed. |
| Family state | `jarvis/family.py` -> `mode_state.json`, `message_drafts.json`, `meal_plans.json`, etc. | JSON + JSONL | `Hybrid` | Household state and approvals benefit from indexing; drafts and plans remain friendly as files. |
| Family history | `jarvis/family.py` -> `mode_history.jsonl` | JSONL | `Keep file-backed` | Event stream, not hot mutable state. |
| Security state | `jarvis/security.py` -> `security_incidents.json`, `arrival_events.json`, `unlock_assessments.json` | JSON | `Hybrid` | Current and active incidents should be indexed; raw historical event payloads can remain file-backed. |
| Perception | `jarvis/perception.py` -> event and observation JSON files | JSON | `Keep file-backed for now` | This is likely to become time-series heavy. SQLite is not the first performance win here unless chamber queries start depending on it heavily. |
| Home | `jarvis/home.py` -> `entity_overrides.json`, `home_actions.json` | JSON | `Keep file-backed for now` | Low enough churn and complexity today. |
| Wealth state | `jarvis/wealth.py` -> `finance_state.json`, `finance_reviews.json` | JSON | `Hybrid` | Active decision state and opportunity indexes should move to SQLite; reviews and generated analysis can remain file-backed. |
| Workshop | `jarvis/workshop.py` -> `inspections.jsonl`, `vendor_preps.json`, `cad_packages.json`, `print_preps.json` | JSON + JSONL | `Keep file-backed` | This is artifact-heavy and benefits from inspectable files more than relational state right now. |
| Tutoring | `jarvis/tutoring.py` -> `sessions.jsonl`, `device_boundaries.json` | JSONL + JSON | `Keep file-backed` | Session transcripts and boundary config do not yet justify indexed migration. |
| Chronicle | `jarvis/chronicle.py` -> `entries.jsonl` | JSONL | `Keep file-backed` | Chronicle should remain a distinct record authority with append-friendly storage. |
| Trust configuration | `jarvis/trust.py` -> `trust_zones.json`, `resource_arenas.json`, `authority_stages.json`, `stage_queue.json` | JSON | `Keep file-backed now; consider SQLite for stage queue later` | Policy definitions are explicit config. The only likely hot-state candidate is `stage_queue`. |
| Doctrine / adaptation / first-light / assistant-core | dedicated store classes | mixed local files | `Keep file-backed for now` | These are configuration and internal doctrine stores, not the first performance bottleneck. |
| Settings | `jarvis/settings.py` | local settings files | `Keep file-backed` | User-facing settings are low-volume and explicit. |

## SQLite v1 Schema Priorities

If JARVIS adds SQLite, these should be the first tables.

### Tier 1

- `approvals`
- `memory_entries`
- `memory_profile_facts`
- `conversation_sessions`
- `self_improvement_jobs`
- `self_improvement_runs`
- `active_runs`
- `agent_work_items`
- `router_sessions`
- `router_results`

### Tier 2

- `family_state_index`
- `security_incidents`
- `wealth_opportunities`
- `catalyst_work_items`
- `content_queue`
- `stage_queue`

### Tier 3

- `audit_index`
- `perception_summary_index`
- `chamber_snapshot_cache`

## Recommended SQLite Boundaries

SQLite should own:

- IDs
- status
- timestamps
- actor and domain keys
- priority and consequence ranks
- approval state
- queue state
- cross-reference pointers to artifacts

Files should own:

- large payload bodies
- human-readable drafts
- long-form generated content
- append-only logs
- exported bundles
- binary and media-adjacent artifacts

## Performance Wins Expected

This architecture should improve:

- chamber load speed
- `Needs You` ranking
- `Already Working` selection
- run and queue coordination
- memory lookup and filtering
- approval mutation safety
- background agent concurrency

It will not directly improve:

- LLM provider latency
- model reasoning quality
- slow third-party API calls
- heavy frontend rendering by itself

## What Should Not Move First

JARVIS should not begin by moving everything into SQLite.

Do not migrate first:

- chronicle entry streams
- workshop packages
- CAD and print payloads
- long-form content artifacts
- raw audit logs
- doctrine documents
- settings files

That would create migration work without buying the biggest performance or integrity gains.

## Migration Order

### Phase A: Add SQLite without breaking file-backed behavior

1. Introduce a single local SQLite database under `data/system/jarvis.db`.
2. Add repository-safe migration code.
3. Create adapters for approvals, memory metadata, conversation index, and self-improvement runs.
4. Leave existing files in place during dual-write or import phase.

### Phase B: Move chamber-critical state first

1. approvals
2. active runs
3. conversation index
4. memory metadata and facts
5. router sessions

This phase should directly improve chamber responsiveness and decision quality.

### Phase C: Move autonomous coordination state

1. agent work items
2. background scheduler state
3. catalyst pipeline state
4. content queue
5. security/family/wealth active indexes

This phase makes background autonomy safer and more queryable.

### Phase D: Add optional indexes for reporting and analytics

1. audit index
2. chamber snapshot cache
3. perception summaries

This phase is useful, but not required for the first win.

## Operational Rules

1. SQLite lives locally with the rest of JARVIS runtime state.
2. The `.db` file must be included in encrypted local backup posture.
3. Restricted and child-sensitive memory remains local-first.
4. Export, inspection, and recovery paths should remain human-auditable.
5. If SQLite is unavailable or corrupt, JARVIS should fail clearly and preserve file artifacts.

## First Implementation Recommendation

If we only do one real storage upgrade next, it should be this:

1. create `data/system/jarvis.db`
2. migrate approvals into SQLite
3. migrate self-improvement jobs and active runs into SQLite
4. migrate memory metadata and profile facts into SQLite
5. keep raw memory payloads, audit logs, and generated artifacts file-backed

That gives JARVIS the highest-value performance and integrity win without overbuilding the storage layer.

## Final Position

JARVIS does need a database soon, but not for everything.

The right v1 answer is:

- SQLite for hot operating state
- files for artifacts, logs, and local-first record surfaces

That keeps the system simple, fast, inspectable, and aligned with the way JARVIS is actually growing.
