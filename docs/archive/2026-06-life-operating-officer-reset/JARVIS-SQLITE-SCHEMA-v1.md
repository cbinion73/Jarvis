# JARVIS SQLite Schema v1

## Purpose

This document derives the first SQLite schema for JARVIS from [JARVIS-DATA-ARCHITECTURE-v1.md](/Users/chris/Desktop/CODE/JARVIS/docs/JARVIS-DATA-ARCHITECTURE-v1.md).

It defines:

- the first actual SQLite tables
- the fields each table should own
- the indexes that matter for chamber performance and background autonomy
- the migration order tied to current store classes

This is not a total rewrite of JARVIS storage.

It is the first database layer for hot structured state while preserving the existing local-first file-backed artifact model.

## Database Location

Recommended path:

- `data/system/jarvis.db`

Recommended SQLite settings:

- `PRAGMA journal_mode = WAL;`
- `PRAGMA foreign_keys = ON;`
- `PRAGMA synchronous = NORMAL;`
- `PRAGMA temp_store = MEMORY;`

WAL mode matters because JARVIS will have:

- interactive reads from the chamber
- background scheduler writes
- approval mutations
- self-improvement queue updates

## Scope

SQLite v1 should own:

- approvals
- memory metadata
- profile facts
- conversation index
- self-improvement jobs
- self-improvement runs
- active runs
- agent work items
- router sessions
- router results

SQLite v1 should not own:

- raw audit logs
- chronicle entry streams
- tutoring session logs
- workshop packages
- long-form generated artifacts
- doctrine and settings files

## Schema Conventions

### ID strategy

JARVIS already uses UUID-like IDs in many places. SQLite v1 should preserve string IDs rather than inventing integer IDs for primary records.

Use:

- `TEXT PRIMARY KEY`

### Time fields

All timestamps should be stored as UTC ISO 8601 strings.

Use:

- `TEXT NOT NULL`

Common fields:

- `created_at`
- `updated_at`
- `last_activity_at`
- `started_at`
- `completed_at`

### JSON payload strategy

Many current file-backed records are still evolving. SQLite v1 should not over-normalize them too early.

Use:

- first-class relational columns for hot query keys
- `payload_json TEXT NOT NULL DEFAULT '{}'` for the full shaped record

This gives JARVIS:

- fast indexed reads
- schema flexibility
- easier migration from existing JSON stores

## Table Definitions

### 1. `approvals`

Owns the hot mutable approval queue currently backed by `ApprovalStore` in [jarvis/audit.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/audit.py).

```sql
CREATE TABLE IF NOT EXISTS approvals (
  request_id TEXT PRIMARY KEY,
  actor TEXT NOT NULL DEFAULT '',
  domain TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',
  summary TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  consequence_level TEXT NOT NULL DEFAULT 'normal',
  approval_kind TEXT NOT NULL DEFAULT '',
  source_system TEXT NOT NULL DEFAULT 'jarvis',
  source_store TEXT NOT NULL DEFAULT 'approval_store',
  room TEXT NOT NULL DEFAULT '',
  recommendation TEXT NOT NULL DEFAULT '',
  rationale TEXT NOT NULL DEFAULT '',
  action_target TEXT NOT NULL DEFAULT '',
  artifact_path TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  expires_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_approvals_status_updated
  ON approvals(status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_approvals_actor_status
  ON approvals(actor, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_approvals_domain_status
  ON approvals(domain, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_approvals_consequence_status
  ON approvals(consequence_level, status, updated_at DESC);
```

Why this shape:

- chamber `Needs You` ranking needs `status`, `domain`, `consequence_level`, and `updated_at`
- the full approval payload still fits cleanly in `payload_json`

### 2. `memory_entries`

Owns indexed memory metadata currently backed by `MemoryStore` in [jarvis/memory.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/memory.py).

```sql
CREATE TABLE IF NOT EXISTS memory_entries (
  entry_id TEXT PRIMARY KEY,
  actor TEXT NOT NULL DEFAULT '',
  subject_user_id TEXT NOT NULL DEFAULT '',
  memory_type TEXT NOT NULL DEFAULT '',
  scope TEXT NOT NULL DEFAULT '',
  owner TEXT NOT NULL DEFAULT '',
  project TEXT NOT NULL DEFAULT '',
  access_policy TEXT NOT NULL DEFAULT 'shared',
  boundary_label TEXT NOT NULL DEFAULT '',
  source_type TEXT NOT NULL DEFAULT '',
  sensitivity TEXT NOT NULL DEFAULT 'normal',
  confidence TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'active',
  summary TEXT NOT NULL DEFAULT '',
  tags_json TEXT NOT NULL DEFAULT '[]',
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memory_entries_actor_created
  ON memory_entries(actor, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_entries_subject_policy
  ON memory_entries(subject_user_id, access_policy, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_entries_project
  ON memory_entries(project, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_entries_type_scope
  ON memory_entries(memory_type, scope, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_entries_status
  ON memory_entries(status, created_at DESC);
```

Why this shape:

- chamber and agent memory retrieval needs indexed metadata
- sensitive detail can remain local and embedded in `payload_json`

### 3. `memory_proposals`

Owns memory proposals that currently live in `proposals.json`.

```sql
CREATE TABLE IF NOT EXISTS memory_proposals (
  proposal_id TEXT PRIMARY KEY,
  actor TEXT NOT NULL DEFAULT '',
  subject_user_id TEXT NOT NULL DEFAULT '',
  memory_type TEXT NOT NULL DEFAULT '',
  scope TEXT NOT NULL DEFAULT '',
  owner TEXT NOT NULL DEFAULT '',
  project TEXT NOT NULL DEFAULT '',
  access_policy TEXT NOT NULL DEFAULT 'shared',
  sensitivity TEXT NOT NULL DEFAULT 'sensitive',
  status TEXT NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  rationale TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  decided_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_memory_proposals_status_created
  ON memory_proposals(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_proposals_actor_status
  ON memory_proposals(actor, status, created_at DESC);
```

### 4. `memory_profile_facts`

Owns promoted durable profile facts.

```sql
CREATE TABLE IF NOT EXISTS memory_profile_facts (
  fact_id TEXT PRIMARY KEY,
  actor TEXT NOT NULL DEFAULT '',
  subject_user_id TEXT NOT NULL,
  fact_type TEXT NOT NULL DEFAULT '',
  fact_key TEXT NOT NULL DEFAULT '',
  fact_value TEXT NOT NULL DEFAULT '',
  confidence TEXT NOT NULL DEFAULT '',
  source_entry_id TEXT NOT NULL DEFAULT '',
  source_proposal_id TEXT NOT NULL DEFAULT '',
  access_policy TEXT NOT NULL DEFAULT 'personal',
  status TEXT NOT NULL DEFAULT 'active',
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(subject_user_id, fact_key)
);
CREATE INDEX IF NOT EXISTS idx_memory_profile_facts_subject
  ON memory_profile_facts(subject_user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_profile_facts_type
  ON memory_profile_facts(fact_type, updated_at DESC);
```

### 5. `conversation_sessions`

Owns the conversation index currently backed by `ConversationStore` in [jarvis/conversation.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/conversation.py).

Important:

- SQLite v1 owns the session index
- full turn transcripts can stay file-backed per conversation for now

```sql
CREATE TABLE IF NOT EXISTS conversation_sessions (
  conversation_id TEXT PRIMARY KEY,
  actor TEXT NOT NULL DEFAULT '',
  room TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT 'shell',
  title TEXT NOT NULL DEFAULT 'New conversation',
  status TEXT NOT NULL DEFAULT 'active',
  summary TEXT NOT NULL DEFAULT '',
  memory_signals_json TEXT NOT NULL DEFAULT '[]',
  turn_count INTEGER NOT NULL DEFAULT 0,
  latest_user_text TEXT NOT NULL DEFAULT '',
  latest_assistant_text TEXT NOT NULL DEFAULT '',
  thread_path TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  last_activity_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_actor_activity
  ON conversation_sessions(actor, last_activity_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_room_activity
  ON conversation_sessions(room, last_activity_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_status_activity
  ON conversation_sessions(status, last_activity_at DESC);
```

### 6. `self_improvement_jobs`

Owns self-improvement job queue metadata from [jarvis/self_improvement.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/self_improvement.py).

```sql
CREATE TABLE IF NOT EXISTS self_improvement_jobs (
  job_id TEXT PRIMARY KEY,
  job_key TEXT NOT NULL DEFAULT '',
  actor TEXT NOT NULL DEFAULT '',
  domain TEXT NOT NULL DEFAULT 'system',
  title TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  selection_reason TEXT NOT NULL DEFAULT '',
  selected_runner TEXT NOT NULL DEFAULT '',
  active_run_id TEXT NOT NULL DEFAULT '',
  priority INTEGER NOT NULL DEFAULT 0,
  artifact_path TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  queued_at TEXT NOT NULL DEFAULT '',
  started_at TEXT NOT NULL DEFAULT '',
  completed_at TEXT NOT NULL DEFAULT '',
  UNIQUE(job_key)
);
CREATE INDEX IF NOT EXISTS idx_self_improvement_jobs_status_updated
  ON self_improvement_jobs(status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_self_improvement_jobs_run
  ON self_improvement_jobs(active_run_id, updated_at DESC);
```

### 7. `self_improvement_runs`

Owns historical run metadata.

```sql
CREATE TABLE IF NOT EXISTS self_improvement_runs (
  run_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL DEFAULT '',
  actor TEXT NOT NULL DEFAULT '',
  domain TEXT NOT NULL DEFAULT 'system',
  status TEXT NOT NULL,
  current_step TEXT NOT NULL DEFAULT '',
  message TEXT NOT NULL DEFAULT '',
  worktree_path TEXT NOT NULL DEFAULT '',
  report_path TEXT NOT NULL DEFAULT '',
  patch_path TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  queued_at TEXT NOT NULL DEFAULT '',
  started_at TEXT NOT NULL DEFAULT '',
  completed_at TEXT NOT NULL DEFAULT '',
  FOREIGN KEY(job_id) REFERENCES self_improvement_jobs(job_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_self_improvement_runs_job
  ON self_improvement_runs(job_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_self_improvement_runs_status
  ON self_improvement_runs(status, updated_at DESC);
```

### 8. `active_runs`

Owns only live run state for fast chamber and API reads.

```sql
CREATE TABLE IF NOT EXISTS active_runs (
  run_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL DEFAULT '',
  actor TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  current_step TEXT NOT NULL DEFAULT '',
  message TEXT NOT NULL DEFAULT '',
  worktree_path TEXT NOT NULL DEFAULT '',
  visible_surface TEXT NOT NULL DEFAULT 'self-improvement',
  payload_json TEXT NOT NULL DEFAULT '{}',
  queued_at TEXT NOT NULL DEFAULT '',
  started_at TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES self_improvement_runs(run_id) ON DELETE CASCADE,
  FOREIGN KEY(job_id) REFERENCES self_improvement_jobs(job_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_active_runs_status_updated
  ON active_runs(status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_active_runs_actor_status
  ON active_runs(actor, status, updated_at DESC);
```

Why separate `active_runs`:

- chamber rendering should not scan the whole run history
- current-state reads stay simple and fast

### 9. `agent_work_items`

Owns background-agent work queue and current state from `BackgroundStateStore` and future workstream execution state in [jarvis/agentic.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/agentic.py).

```sql
CREATE TABLE IF NOT EXISTS agent_work_items (
  work_item_id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  stewardship_lane TEXT NOT NULL DEFAULT '',
  actor TEXT NOT NULL DEFAULT '',
  domain TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 0,
  consequence_level TEXT NOT NULL DEFAULT 'normal',
  trigger_type TEXT NOT NULL DEFAULT '',
  source_system TEXT NOT NULL DEFAULT 'jarvis',
  recommendation TEXT NOT NULL DEFAULT '',
  artifact_path TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  started_at TEXT NOT NULL DEFAULT '',
  completed_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_agent_work_items_status_priority
  ON agent_work_items(status, priority DESC, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_work_items_agent_status
  ON agent_work_items(agent_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_work_items_actor_status
  ON agent_work_items(actor, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_work_items_lane_status
  ON agent_work_items(stewardship_lane, status, updated_at DESC);
```

### 10. `router_sessions`

Owns routed handoff sessions from `InterfaceRouterStore` in [jarvis/interfaces.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/interfaces.py).

```sql
CREATE TABLE IF NOT EXISTS router_sessions (
  request_id TEXT PRIMARY KEY,
  source_system TEXT NOT NULL DEFAULT 'jarvis',
  target_system TEXT NOT NULL,
  actor_id TEXT NOT NULL DEFAULT '',
  actor_role TEXT NOT NULL DEFAULT 'primary_user',
  intent_family TEXT NOT NULL DEFAULT '',
  intent_subtype TEXT NOT NULL DEFAULT '',
  capability TEXT NOT NULL DEFAULT '',
  mode TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'accepted',
  stub INTEGER NOT NULL DEFAULT 0,
  deep_link TEXT NOT NULL DEFAULT '',
  permissions_json TEXT NOT NULL DEFAULT '{}',
  context_json TEXT NOT NULL DEFAULT '{}',
  return_contract_json TEXT NOT NULL DEFAULT '{}',
  payload_json TEXT NOT NULL DEFAULT '{}',
  timestamp TEXT NOT NULL,
  accepted_at TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_router_sessions_target_status
  ON router_sessions(target_system, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_router_sessions_actor_status
  ON router_sessions(actor_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_router_sessions_intent
  ON router_sessions(intent_family, updated_at DESC);
```

### 11. `router_results`

Owns returned results from routed systems.

```sql
CREATE TABLE IF NOT EXISTS router_results (
  request_id TEXT PRIMARY KEY,
  target_system TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT '',
  result_type TEXT NOT NULL DEFAULT '',
  artifact_path TEXT NOT NULL DEFAULT '',
  summary TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(request_id) REFERENCES router_sessions(request_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_router_results_status_updated
  ON router_results(status, updated_at DESC);
```

## Optional Tier 2 Tables

These should not block SQLite v1, but they are the next likely candidates.

### `family_state_index`

- derived from [jarvis/family.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/family.py)
- tracks active household state, drafts, and decision-ready items

### `security_incidents`

- derived from [jarvis/security.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/security.py)
- tracks active or recent household security posture

### `wealth_opportunities`

- derived from [jarvis/wealth.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/wealth.py)
- tracks active opportunity and diligence workflow state

### `catalyst_work_items`

- derived from [jarvis/catalyst.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/catalyst.py)
- tracks active planning and executive workflow items

### `content_queue`

- derived from [jarvis/content_ops.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/content_ops.py)
- tracks current content pipeline state

## Migration Order Tied To Current Store Classes

### Migration 001: bootstrap database

Create:

- database file
- PRAGMA setup
- migration tracking table

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
  migration_id TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL
);
```

Implementation target:

- new storage bootstrap module, likely under `jarvis/storage/` or similar

### Migration 002: approvals

Current source:

- `ApprovalStore` in [jarvis/audit.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/audit.py)
- source file: `data/approvals/pending.json`

Work:

1. create `approvals`
2. import all records from `pending.json`
3. switch `list_pending()` and `update_status()` to SQLite-backed reads/writes
4. optionally keep `pending.json` as export or backup during transition

Why first:

- direct chamber impact
- simplest hot-state migration

### Migration 003: self-improvement jobs and runs

Current source:

- `SelfImprovementStore` in [jarvis/self_improvement.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/self_improvement.py)
- source files:
  - `data/system/jobs.json`
  - `data/system/runs.json`
  - `data/system/active_runs.json`

Work:

1. create `self_improvement_jobs`
2. create `self_improvement_runs`
3. create `active_runs`
4. import JSON records
5. switch queue and run lookup paths to SQLite

Why second:

- active chamber state
- background coordination
- correctness under multi-step autonomous work

### Migration 004: conversation index

Current source:

- `ConversationStore` in [jarvis/conversation.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/conversation.py)
- source file: `data/conversations/index.json`

Work:

1. create `conversation_sessions`
2. import `index.json`
3. keep per-thread files like `data/conversations/<conversation_id>.json` file-backed
4. switch `list_recent()` and thread metadata updates to SQLite

Why third:

- clean performance win
- low migration risk
- preserves existing thread file model

### Migration 005: memory metadata and facts

Current source:

- `MemoryStore` in [jarvis/memory.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/memory.py)
- source files:
  - `data/memory/entries.json`
  - `data/memory/proposals.json`
  - `data/memory/profile_facts.json`

Work:

1. create `memory_entries`
2. create `memory_proposals`
3. create `memory_profile_facts`
4. import existing records
5. keep sensitive payload shape in `payload_json`
6. switch overview, review, and profile lookup paths to indexed queries

Why fourth:

- more complex than approvals
- high long-term value for chamber and agent reasoning

### Migration 006: router sessions and results

Current source:

- `InterfaceRouterStore` in [jarvis/interfaces.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/interfaces.py)
- source files:
  - `data/router/sessions.json`
  - `data/router/results.json`

Work:

1. create `router_sessions`
2. create `router_results`
3. import maps into row form
4. switch save/get operations to SQLite

Why fifth:

- lower immediate chamber impact than approvals and memory
- strong fit for relational state

### Migration 007: background agent work items

Current source:

- `BackgroundStateStore` in [jarvis/agentic.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/agentic.py)
- source file: `data/agents/background_state.json`

Work:

1. create `agent_work_items`
2. extract current agent state into row-backed work and status records
3. keep `tick_log.jsonl` file-backed
4. refactor scheduler state reads toward SQLite

Why sixth:

- most structurally important for the future
- also the least stable current shape
- better to migrate after the simpler hot-state surfaces

## Compatibility Strategy

JARVIS should not hard-cut away from file-backed storage immediately.

Recommended rollout:

### Phase 1

- import existing JSON into SQLite
- read from SQLite for migrated stores
- optionally keep file export snapshots during transition

### Phase 2

- stop dual-write for stable stores
- keep only artifact and export file writes

### Phase 3

- clean up legacy hot-state JSON files once confidence is high

## Implementation Rule

Do not try to fully normalize every record on day one.

The right v1 pattern is:

- indexed keys as columns
- original shaped record in `payload_json`

That keeps migration practical and lets the schema evolve with JARVIS instead of freezing the system too early.

## First Build Recommendation

If we want the cleanest first implementation pass, build in this order:

1. SQLite bootstrap and migration runner
2. approvals table and store adapter
3. self-improvement tables and store adapter
4. conversation session index table and adapter
5. memory tables and adapter

That sequence gives the best payoff for:

- chamber responsiveness
- decision quality
- background execution safety
- future agent autonomy

## Final Position

JARVIS SQLite Schema v1 should be small, indexed, and operational.

It should not try to absorb all of JARVIS.

Its job is to make the chamber and the autonomous engine more reliable by moving the right hot state into SQLite first while keeping the broader local-first file model intact.
