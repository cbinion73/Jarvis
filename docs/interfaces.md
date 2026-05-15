# JARVIS Interfaces

This document defines the interface contract between `JARVIS`, `Chronicle`, and `Catalyst Personal`.

The operating posture is:

- `JARVIS` is the shell, router, permission broker, and cross-domain continuity layer.
- `Chronicle` is the source of truth and system of record for faith life.
- `Catalyst Personal` is the executive workflow engine that operates inside JARVIS and can take bounded delegated work.

## System Roles

| System | Core Role | UX Position | Record Authority |
| --- | --- | --- | --- |
| JARVIS | Orchestrator, shell, router, action broker | Primary conversational and operational surface | Shared operating context |
| Chronicle | Faith life platform | Invoked from JARVIS, but runs as Chronicle | Faith, prayer, study, formation records |
| Catalyst Personal | Executive workflow engine | Embedded inside JARVIS | Delegated executive artifacts and run history |

## Design Rules

1. Faith-domain experiences belong in `Chronicle`.
2. Day management, signal review, and action routing belong in `JARVIS`.
3. Heavy executive synthesis can be delegated to `Catalyst Personal`.
4. JARVIS may summarize or reference Chronicle state, but it must not become a shadow faith database.
5. Consequential external actions stay under JARVIS permissions, even when Catalyst prepares them.

## Intent Taxonomy

| Intent Family | Subtype Examples | Primary System | Default Mode |
| --- | --- | --- | --- |
| `faith.study` | passage study, theme study, word study | Chronicle | `launch` |
| `faith.prayer` | guided prayer, prayer journaling, prayer review | Chronicle | `launch` |
| `faith.formation` | reflection, conviction tracking, spiritual pattern review | Chronicle | `launch` |
| `faith.lookup` | retrieve prior study, prayer, or insight summary | Chronicle | `embed` |
| `faith.capture` | save insight, prayer, takeaway, spiritual event | Chronicle | `delegate` |
| `day.review` | today view, priorities, cadence, signals | JARVIS | `native` |
| `day.communications` | email, messages, replies, follow-up | JARVIS | `embed` |
| `day.calendar` | agenda, prep, conflicts, transitions | JARVIS | `embed` |
| `exec.prep` | meeting prep, brief prep, talking points | Catalyst Personal | `delegate` |
| `exec.research` | vendor scan, market synthesis, landscape summary | Catalyst Personal | `delegate` |
| `exec.decision` | options, tradeoffs, recommendations | Catalyst Personal | `delegate` |
| `exec.packaging` | memo, deck outline, task plan, action plan | Catalyst Personal | `delegate` |
| `system.route` | choose app, mode, workflow | JARVIS | `native` |
| `system.control` | launch app, switch workspace, maintain context | JARVIS | `native` |

## Routing Rules

- If the request is spiritual, reflective, prayer-oriented, or tied to faith-history recording, route to `Chronicle`.
- If the request is about inbox, agenda, daily priorities, transitions, or household/professional signal management, keep it in `JARVIS`.
- If the request requires heavier synthesis, packaging, or decision framing, delegate to `Catalyst Personal`.
- If a request spans systems, JARVIS remains the primary shell and invokes the needed secondary system.

## Capability Registry

### Chronicle Capabilities

| Capability | Intent Families | Modes | Writes Record | Description |
| --- | --- | --- | --- | --- |
| `study_passage` | `faith.study` | `launch`, `embed` | yes | Open a passage-centered study flow |
| `trace_theme` | `faith.study` | `launch`, `embed` | no | Trace a theological theme through Scripture |
| `prayer_session` | `faith.prayer` | `launch` | yes | Open guided prayer or prayer reflection |
| `formation_memory_lookup` | `faith.lookup`, `faith.formation` | `embed`, `delegate` | no | Retrieve prior spiritual continuity |
| `record_spiritual_event` | `faith.capture`, `faith.formation` | `delegate` | yes | Save insight, conviction, prayer, or milestone |
| `spiritual_timeline` | `faith.formation` | `launch`, `embed` | no | Show longitudinal formation patterns |

### Catalyst Personal Capabilities

| Capability | Intent Families | Modes | Writes Record | Description |
| --- | --- | --- | --- | --- |
| `meeting_prep` | `exec.prep`, `day.calendar` | `delegate`, `embed` | yes | Build meeting prep from signals and context |
| `briefing_build` | `exec.prep`, `exec.packaging` | `delegate` | yes | Build executive briefs and talking points |
| `decision_support` | `exec.decision` | `delegate`, `embed` | yes | Structure options, tradeoffs, and recommendation |
| `research_synthesis` | `exec.research` | `delegate` | yes | Turn notes and sources into structured findings |
| `action_packaging` | `exec.packaging` | `delegate` | yes | Turn reasoning into tasks, drafts, and next steps |
| `signal_triage` | `day.review`, `day.communications` | `delegate`, `embed` | yes | Process inbox/calendar/message signals |

## Capability Manifest Format

Each external subsystem should publish a machine-readable capability manifest so JARVIS can route against declared contracts rather than hardcoded assumptions.

### Chronicle Manifest

```json
{
  "system": "chronicle",
  "version": "1.0",
  "capabilities": {
    "study_passage": {
      "intent_families": ["faith.study"],
      "mode_support": ["launch", "embed"],
      "writes_record": true
    },
    "trace_theme": {
      "intent_families": ["faith.study"],
      "mode_support": ["launch", "embed"],
      "writes_record": false
    },
    "prayer_session": {
      "intent_families": ["faith.prayer"],
      "mode_support": ["launch"],
      "writes_record": true
    },
    "formation_memory_lookup": {
      "intent_families": ["faith.lookup", "faith.formation"],
      "mode_support": ["embed", "delegate"],
      "writes_record": false
    },
    "record_spiritual_event": {
      "intent_families": ["faith.capture", "faith.formation"],
      "mode_support": ["delegate"],
      "writes_record": true
    },
    "spiritual_timeline": {
      "intent_families": ["faith.formation"],
      "mode_support": ["launch", "embed"],
      "writes_record": false
    }
  }
}
```

### Catalyst Personal Manifest

```json
{
  "system": "catalyst",
  "version": "1.0",
  "capabilities": {
    "meeting_prep": {
      "intent_families": ["exec.prep", "day.calendar"],
      "mode_support": ["delegate", "embed"],
      "writes_record": true
    },
    "briefing_build": {
      "intent_families": ["exec.prep", "exec.packaging"],
      "mode_support": ["delegate"],
      "writes_record": true
    },
    "decision_support": {
      "intent_families": ["exec.decision"],
      "mode_support": ["delegate", "embed"],
      "writes_record": true
    },
    "research_synthesis": {
      "intent_families": ["exec.research"],
      "mode_support": ["delegate"],
      "writes_record": true
    },
    "action_packaging": {
      "intent_families": ["exec.packaging"],
      "mode_support": ["delegate"],
      "writes_record": true
    },
    "signal_triage": {
      "intent_families": ["day.review", "day.communications"],
      "mode_support": ["delegate", "embed"],
      "writes_record": true
    }
  }
}
```

## Endpoint Proposals

JARVIS should own the routing seam. Chronicle and Catalyst should expose capability-driven interfaces that can receive a handoff and return a structured result.

### JARVIS Router Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/router/intent` | `POST` | Classify a user request into intent family, target system, and mode |
| `/api/router/handoff` | `POST` | Send a structured handoff from JARVIS to Chronicle or Catalyst |
| `/api/router/result` | `POST` | Receive a structured result from Chronicle or Catalyst |
| `/api/router/capabilities` | `GET` | Aggregate known capability manifests |
| `/api/router/session/:id` | `GET` | Inspect a routed session and its current handoff/result state |

### Chronicle Endpoint Proposals

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/chronicle/capabilities` | `GET` | Return the Chronicle capability manifest |
| `/api/chronicle/handoff` | `POST` | Receive a Chronicle-directed handoff |
| `/api/chronicle/session/:id` | `GET` | Return session status for an active Chronicle workflow |
| `/api/chronicle/result/:id` | `GET` | Return a finalized Chronicle result payload |

### Catalyst Endpoint Proposals

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/catalyst/capabilities` | `GET` | Return the Catalyst Personal capability manifest |
| `/api/catalyst/handoff` | `POST` | Receive a Catalyst-directed delegated task |
| `/api/catalyst/run/:id` | `GET` | Return status for an active Catalyst run |
| `/api/catalyst/result/:id` | `GET` | Return a finalized Catalyst result payload |

## Handoff JSON Schemas

All routed work should use a common envelope with target-specific context.

### Common Handoff Envelope

```json
{
  "$schema": "https://jarvis.local/schemas/handoff-envelope.v1.json",
  "request_id": "uuid",
  "timestamp": "2026-05-12T01:00:00Z",
  "source_system": "jarvis",
  "target_system": "chronicle",
  "intent_family": "faith.study",
  "intent_subtype": "passage_study",
  "capability": "study_passage",
  "mode": "launch",
  "actor": {
    "actor_id": "chris",
    "role": "primary_user"
  },
  "context": {},
  "permissions": {},
  "return_contract": {}
}
```

### Chronicle Handoff Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ChronicleHandoffV1",
  "type": "object",
  "required": [
    "request_id",
    "target_system",
    "intent_family",
    "capability",
    "mode",
    "actor",
    "context",
    "return_contract"
  ],
  "properties": {
    "request_id": { "type": "string" },
    "target_system": { "const": "chronicle" },
    "intent_family": { "type": "string", "pattern": "^faith\\." },
    "capability": { "type": "string" },
    "mode": { "enum": ["launch", "embed", "delegate"] },
    "actor": {
      "type": "object",
      "required": ["actor_id"],
      "properties": {
        "actor_id": { "type": "string" }
      }
    },
    "context": {
      "type": "object",
      "properties": {
        "passage": { "type": "string" },
        "theme": { "type": "string" },
        "prompt": { "type": "string" },
        "continuity_refs": {
          "type": "array",
          "items": { "type": "string" }
        },
        "preferences": {
          "type": "array",
          "items": { "type": "string" }
        }
      },
      "additionalProperties": true
    },
    "return_contract": {
      "type": "object",
      "properties": {
        "summary_to_jarvis": { "type": "boolean" },
        "writeback_type": { "type": "string" },
        "deep_link_back": { "type": "boolean" }
      },
      "additionalProperties": false
    }
  }
}
```

### Catalyst Personal Handoff Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CatalystHandoffV1",
  "type": "object",
  "required": [
    "request_id",
    "target_system",
    "intent_family",
    "capability",
    "mode",
    "actor",
    "context",
    "permissions",
    "return_contract"
  ],
  "properties": {
    "request_id": { "type": "string" },
    "target_system": { "const": "catalyst" },
    "intent_family": { "type": "string", "pattern": "^(exec|day)\\." },
    "capability": { "type": "string" },
    "mode": { "enum": ["embed", "delegate"] },
    "actor": {
      "type": "object",
      "required": ["actor_id"],
      "properties": {
        "actor_id": { "type": "string" }
      }
    },
    "context": {
      "type": "object",
      "properties": {
        "calendar_event_id": { "type": "string" },
        "message_ids": {
          "type": "array",
          "items": { "type": "string" }
        },
        "email_ids": {
          "type": "array",
          "items": { "type": "string" }
        },
        "document_ids": {
          "type": "array",
          "items": { "type": "string" }
        },
        "goal": { "type": "string" },
        "output_format": { "type": "string" }
      },
      "additionalProperties": true
    },
    "permissions": {
      "type": "object",
      "required": ["autonomy_level"],
      "properties": {
        "autonomy_level": {
          "enum": ["read_only", "bounded_write", "propose_only"]
        },
        "allowed_actions": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "return_contract": {
      "type": "object",
      "properties": {
        "artifact_type": { "type": "string" },
        "summary_to_jarvis": { "type": "boolean" },
        "proposed_actions": { "type": "boolean" },
        "deep_link_back": { "type": "boolean" }
      },
      "additionalProperties": false
    }
  }
}
```

## Result JSON Schemas

All subsystems should return a common result envelope with target-specific detail.

### Common Result Envelope

```json
{
  "$schema": "https://jarvis.local/schemas/result-envelope.v1.json",
  "request_id": "uuid",
  "source_system": "chronicle",
  "status": "completed",
  "summary": "string",
  "artifacts": [],
  "memory_updates": [],
  "proposed_actions": [],
  "deep_link": "string or null"
}
```

### Chronicle Result Schema

```json
{
  "type": "object",
  "required": ["request_id", "source_system", "status", "summary"],
  "properties": {
    "request_id": { "type": "string" },
    "source_system": { "const": "chronicle" },
    "status": { "enum": ["completed", "needs_input", "failed"] },
    "summary": { "type": "string" },
    "session_id": { "type": "string" },
    "record_ids": {
      "type": "array",
      "items": { "type": "string" }
    },
    "memory_updates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "reference_id"],
        "properties": {
          "type": { "enum": ["summary_only", "link_only"] },
          "reference_id": { "type": "string" },
          "label": { "type": "string" }
        }
      }
    },
    "deep_link": { "type": ["string", "null"] }
  }
}
```

### Catalyst Personal Result Schema

```json
{
  "type": "object",
  "required": ["request_id", "source_system", "status", "summary"],
  "properties": {
    "request_id": { "type": "string" },
    "source_system": { "const": "catalyst" },
    "status": { "enum": ["completed", "needs_input", "failed"] },
    "summary": { "type": "string" },
    "artifact_type": { "type": "string" },
    "artifact_id": { "type": "string" },
    "artifact_uri": { "type": "string" },
    "proposed_actions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["action_type", "label"],
        "properties": {
          "action_type": { "type": "string" },
          "label": { "type": "string" },
          "target": { "type": "string" },
          "requires_approval": { "type": "boolean" }
        }
      }
    },
    "memory_updates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "reference_id"],
        "properties": {
          "type": { "enum": ["ops_summary", "artifact_link"] },
          "reference_id": { "type": "string" }
        }
      }
    },
    "deep_link": { "type": ["string", "null"] }
  }
}
```

## Permission Model

JARVIS is the permission broker. Chronicle and Catalyst operate within system-specific boundaries and return structured proposals when approval is required.

### Permission Tiers

| Tier | Meaning |
| --- | --- |
| `read_only` | Inspect signals and return a summary only |
| `propose_only` | Prepare recommendations and artifacts, but do not write or act |
| `bounded_write` | Write only within named safe scopes |
| `approval_required` | Prepare actions, but require explicit approval before execution |
| `system_write` | Reserved for tightly controlled internal writes only |

### Permission Matrix

| Action | JARVIS | Chronicle | Catalyst Personal |
| --- | --- | --- | --- |
| Read shared identity and preferences | yes | yes | yes |
| Read full faith records | summary only | yes | no |
| Write faith records | no | yes | no |
| Read email/calendar/messages | yes | no | via JARVIS context only |
| Write tasks and follow-ups | yes | no | bounded via JARVIS |
| Send emails or messages | approval required | no | approval required via JARVIS |
| Create executive artifacts | yes, simple | no | yes |
| Execute external app actions | yes | limited to Chronicle domain | via JARVIS authority |

### Permission Rules

- Chronicle never writes outside faith-domain records.
- Catalyst never receives broad raw connector access by default.
- JARVIS decides what external actions may execute.
- Any send, schedule, message, or durable write outside a bounded safe store requires explicit approval unless pre-authorized.

## Memory Sync Policy

Memory must be shared carefully so continuity is preserved without duplicating authoritative records.

### Memory Classes

| Class | Meaning |
| --- | --- |
| `authoritative` | Owned by one system only |
| `shared_summary` | Portable summary that JARVIS can use for continuity |
| `ephemeral_context` | Turn-scoped or session-scoped context only |
| `linked_reference` | Pointer back to the authoritative system of record |

### Memory Ownership and Sync

| Memory Type | Owner | Sync Direction | JARVIS Storage |
| --- | --- | --- | --- |
| Faith records | Chronicle | Chronicle -> JARVIS summary only | summary + link |
| Prayer/session history | Chronicle | Chronicle -> JARVIS summary only | summary + link |
| Executive artifacts | Catalyst Personal | Catalyst -> JARVIS summary and link | summary + link |
| Day-state | JARVIS | JARVIS -> Catalyst scoped context | current operating state |
| Preferences and style defaults | JARVIS shared core | JARVIS -> both | shared copy |
| Sensitive spiritual reflections | Chronicle | no automatic full sync | link only or summary only |
| Inbox/calendar state | JARVIS | JARVIS -> Catalyst ephemeral only | not transferred in ownership |

### Memory Sync Rules

- JARVIS must not duplicate full Chronicle records.
- Chronicle should return `summary + reference`, not full note bodies by default.
- Catalyst may return artifacts and structured summaries that JARVIS can operationalize.
- Shared memory should be minimized to what improves routing, continuity, and user experience.
- Sensitive categories should declare a sync level such as `none`, `summary_only`, or `link_only`.

### Example Sync Policy

```json
{
  "sync_policy": {
    "faith_records": "summary_only",
    "prayer_records": "summary_only",
    "executive_artifacts": "summary_and_link",
    "calendar_state": "ephemeral_only",
    "sensitive_reflections": "link_only"
  }
}
```

## Launch, Embed, and Delegate Rules

| Mode | Chronicle | Catalyst Personal |
| --- | --- | --- |
| `launch` | default for deep faith workflows | optional for dedicated workspaces |
| `embed` | summary cards, session prompts, recent insight | default for operational panels in JARVIS |
| `delegate` | retrieval or write helper only | primary mode for heavy work |

### Decision Rules

- If the request is spiritual and experiential, `launch Chronicle`.
- If the request is spiritual but lightweight, `embed` a Chronicle summary or prompt.
- If the request is executive and ambient, keep it inside `JARVIS`.
- If the request is executive and cognitively heavy, `delegate` to `Catalyst Personal`.
- If the result must become a durable faith record, Chronicle writes it.
- If the result must drive the day forward, JARVIS owns the action loop.

## Deep-Link and Embed Patterns

### Chronicle Patterns

- `launch`: open Chronicle directly into a destination session
- `resume`: reopen a specific study, prayer, or reflection session
- `embed_card`: render a small Chronicle summary card in JARVIS
- `handoff_banner`: show a "Continue in Chronicle" transition inside JARVIS

Example Chronicle deep links:

```text
chronicle://study?passage=1Cor15:1-10
chronicle://prayer/session?id=pr_284
chronicle://formation/timeline?range=90d
chronicle://record/note?id=note_1182
```

### Catalyst Personal Patterns

- `embed_panel`: render a live Catalyst workspace inside JARVIS
- `artifact_view`: open a Catalyst-generated brief inside JARVIS
- `delegate_run`: run a background task with progress and a structured return
- `workspace_focus`: shift the chamber into a Catalyst mode without leaving JARVIS

Example Catalyst deep links:

```text
catalyst://briefing?id=brief_203
catalyst://meeting-prep?event_id=evt_123
catalyst://decision?id=dec_88
catalyst://research?id=res_451
```

### Embed Contracts

Chronicle embed card:

```json
{
  "embed_type": "chronicle_summary_card",
  "title": "1 Corinthians 15 Study",
  "summary": "Paul grounds assurance in the historical gospel and grace.",
  "reference_id": "chr_study_18",
  "deep_link": "chronicle://study/session?id=chr_study_18"
}
```

Catalyst embed panel:

```json
{
  "embed_type": "catalyst_work_panel",
  "title": "2 PM Innovation Review Prep",
  "status": "ready",
  "artifact_id": "brief_203",
  "actions": [
    {
      "label": "Open Brief",
      "target": "catalyst://briefing?id=brief_203"
    },
    {
      "label": "Create Follow-ups",
      "target": "jarvis://actions/followups?artifact=brief_203"
    }
  ]
}
```

## Ownership Summary

| Concern | JARVIS Owns | Chronicle Owns | Catalyst Personal Owns |
| --- | --- | --- | --- |
| Intent detection | yes | no | no |
| User conversation shell | yes | no | no |
| Faith records | no | yes | no |
| Prayer, study, reflection sessions | no | yes | no |
| Day dashboard | yes | no | assist only |
| Inbox, calendar, message orchestration | yes | no | assist only |
| Executive analysis artifacts | no | no | yes |
| Action approvals and safe execution | yes | no | no |
| Cross-system continuity summaries | yes | partial source | partial source |

## Suggested Implementation Order

1. Add capability manifest endpoints for Chronicle and Catalyst.
2. Add `/api/router/intent`, `/api/router/handoff`, and `/api/router/result` inside JARVIS.
3. Build handoff/result envelope validators from the schemas above.
4. Add Chronicle launch and resume deep-link handling.
5. Add Catalyst embedded panel handling and delegated run tracking.
6. Add memory sync enforcement so Chronicle remains the sole faith record owner.

