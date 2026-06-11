# Phase 1 Trust-Zone Schemas and API Contracts

## Purpose

This document turns Phase 1 of the recursive growth roadmap into concrete schema and API contracts for:

- `trust_zone`
- `resource_arena`
- `authority_stage`
- email draft staging

These contracts are designed for a mandate-first JARVIS that operates with broad delegated initiative inside bounded arenas.

## Canonical Schema Files

- [schemas/trust-zone.v1.json](/Users/chris/Desktop/CODE/JARVIS/schemas/trust-zone.v1.json)
- [schemas/resource-arena.v1.json](/Users/chris/Desktop/CODE/JARVIS/schemas/resource-arena.v1.json)
- [schemas/authority-stage.v1.json](/Users/chris/Desktop/CODE/JARVIS/schemas/authority-stage.v1.json)
- [schemas/email-draft-staging-request.v1.json](/Users/chris/Desktop/CODE/JARVIS/schemas/email-draft-staging-request.v1.json)
- [schemas/email-draft-staging-response.v1.json](/Users/chris/Desktop/CODE/JARVIS/schemas/email-draft-staging-response.v1.json)

## Resource Model

### `trust_zone`

Defines the authority envelope for a class of operation.

Core responsibilities:

- declare allowed actions
- declare review mode
- declare promotion and demotion rules
- bind action types to a bounded resource scope

### `resource_arena`

Defines a real operating surface attached to a trust zone.

Examples:

- shared email draft pipeline
- sandbox brokerage account
- research workspace

Core responsibilities:

- identify the bounded resource
- define limits
- define pause conditions
- define promotion eligibility

### `authority_stage`

Defines the maturity stage for agents or arenas.

Stages:

- `observe`
- `draft`
- `stage_alert`
- `sandbox_live`
- `mature_live`
- `suspended`

### Email Draft Staging

Defines the stage-and-alert flow for shared email systems:

1. read permitted context
2. generate draft
3. save to drafts
4. alert principal
5. record outcome for audit and promotion scoring

## API Contracts

## `GET /api/trust-zones`

Purpose:

- list active trust zones

Response `200`

```json
{
  "zones": [
    {
      "zone_id": "shared-email.stage",
      "name": "Shared Email Draft Stage",
      "zone_type": "draft_stage",
      "resource_scope": {
        "systems": ["gmail"],
        "data_classes": ["shared_email", "relationship_memory"]
      },
      "allowed_actions": ["observe", "classify", "draft", "stage", "alert"],
      "approval_mode": "stage_and_alert",
      "audit_mode": "standard",
      "promotion_rules": {
        "eligible_next_stages": ["stage_alert"],
        "minimum_success_rate": 0.95,
        "minimum_review_count": 25
      },
      "demotion_rules": {
        "triggers": ["hidden_action", "error_rate_breach"],
        "fallback_stage": "draft"
      },
      "status": "active"
    }
  ]
}
```

## `POST /api/trust-zones`

Purpose:

- create a new trust zone

Request body:

- `TrustZoneV1`

Response `201`

```json
{
  "zone_id": "finance-sandbox.live",
  "status": "active"
}
```

## `GET /api/resource-arenas`

Purpose:

- list resource arenas and their linked zones

Response `200`

```json
{
  "arenas": [
    {
      "arena_id": "gmail.shared.drafts",
      "name": "Shared Gmail Draft Arena",
      "resource_type": "email_draft_pipeline",
      "linked_zone_id": "shared-email.stage",
      "owner_principal": "chris",
      "risk_class": "low",
      "limits": {
        "action_budget": {
          "max_drafts_per_day": 25
        },
        "message_limits": {
          "send_enabled": false,
          "draft_folder_required": true
        }
      },
      "pause_conditions": ["draft_save_failure", "principal_override"],
      "status": "active"
    }
  ]
}
```

## `POST /api/resource-arenas`

Purpose:

- create a new bounded operating arena

Request body:

- `ResourceArenaV1`

Response `201`

```json
{
  "arena_id": "brokerage.sandbox.primary",
  "status": "active"
}
```

## `GET /api/authority-stages`

Purpose:

- list stage definitions used by zones, agents, and arenas

Response `200`

```json
{
  "stages": [
    {
      "stage_id": "draft",
      "name": "Draft Only",
      "sequence": 1,
      "allowed_action_types": ["observe", "classify", "draft"],
      "approval_requirements": {
        "pre_action": "draft_only",
        "boundary_crossing": "escalate"
      },
      "reporting_requirements": {
        "summary_level": "standard",
        "cadence": "per_action",
        "must_capture_outcomes": true
      },
      "promotion_criteria": {
        "minimum_success_rate": 0.95,
        "minimum_review_count": 25,
        "maximum_boundary_violations": 0
      },
      "demotion_triggers": ["hidden_action", "error_rate_breach", "principal_override"],
      "status": "active"
    }
  ]
}
```

## `POST /api/stage/email/draft`

Purpose:

- execute the shared-email draft staging flow

Request body:

- `EmailDraftStagingRequestV1`

Example request:

```json
{
  "request_id": "req_01jv_email_001",
  "arena_id": "gmail.shared.drafts",
  "principal_id": "chris",
  "source_message": {
    "message_id": "msg_1839",
    "thread_id": "thr_552",
    "mailbox_id": "gmail_primary",
    "from": "partner@example.com",
    "subject": "Follow-up on next week"
  },
  "draft_intent": {
    "intent_type": "reply",
    "tone": "warm and direct",
    "goal": "confirm next week and offer two time windows",
    "key_points": [
      "thank them",
      "confirm interest",
      "offer Tuesday or Thursday"
    ]
  },
  "stage_policy": {
    "save_to_drafts": true,
    "send_enabled": false,
    "alert_required": true
  }
}
```

Response `201`

- `EmailDraftStagingResponseV1`

Example response:

```json
{
  "request_id": "req_01jv_email_001",
  "draft_id": "draft_9921",
  "arena_id": "gmail.shared.drafts",
  "stage_status": "alerted",
  "draft_location": {
    "mailbox_id": "gmail_primary",
    "folder": "drafts",
    "thread_id": "thr_552",
    "draft_message_id": "draft_msg_9921"
  },
  "alert": {
    "status": "queued",
    "channel": "in_app",
    "message": "Email draft prepared and saved to drafts for review."
  },
  "promotion_signal": {
    "eligible_for_review": true,
    "stage_id": "draft"
  },
  "audit_ref": "audit_01jv_email_001"
}
```

## `GET /api/stage/queue`

Purpose:

- list pending staged actions that need human review

Response `200`

```json
{
  "items": [
    {
      "request_id": "req_01jv_email_001",
      "arena_id": "gmail.shared.drafts",
      "action_type": "email_draft_review",
      "status": "awaiting_principal_review",
      "created_at": "2026-05-15T13:00:00Z"
    }
  ]
}
```

## Contract Notes

### Notes on `trust_zone`

- `approval_mode` is intentionally zone-level, not global
- `promotion_rules` and `demotion_rules` are part of the canonical object, not loose policy notes

### Notes on `resource_arena`

- the arena is the real bounded surface where JARVIS operates
- email and finance are modeled the same way at this layer: both are explicit arenas with different risk limits

### Notes on `authority_stage`

- stage definitions are reusable across zones and agents
- stage order is explicit through `sequence`

### Notes on Email Staging

- the Phase 1 contract is intentionally draft-first
- no send capability is present in this contract
- promotion to live-send would require a higher stage and a different contract

## Recommended Next Implementation Files

1. an internal type layer mirroring the JSON schemas
2. persistence tables or collections for zones, arenas, stages, and staged actions
3. a service for `POST /api/stage/email/draft`
4. an audit writer for staged-action results
5. a promotion evaluator that can score draft-review outcomes over time
