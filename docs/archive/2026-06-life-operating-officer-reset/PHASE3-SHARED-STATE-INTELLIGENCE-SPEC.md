# Phase 3: Shared-State Intelligence Spec

## Purpose

Phase 3 turns JARVIS from a set of live-backed tabs into a shared-state intelligence system.

The goal is not to add random screens.
The goal is to give JARVIS one ambient nervous system across web, iPhone, and later Watch, CarPlay, and home surfaces.

Phase 3 should establish four foundations:

- a unified event log
- a real notification workflow
- interruption posture and delivery discipline
- deeper shared-state workflow surfaces for calendar, reminders, focus, sound, vision, and media

This phase is the bridge between:

- Phase 2 behavioral parity
- Phase 4 trust-zone control plane
- Phase 5 ambient JARVIS
- Phase 6 memory and continuity

## Outcomes

When Phase 3 is complete:

- JARVIS has a dedicated inbox for household-relevant notifications
- every proactive or consequential shared-state event leaves a trace
- web and iPhone can inspect the same event/notification truth
- interruption behavior is governed by posture instead of ad hoc pushes
- calendar, reminders, focus, sound, vision, and media become actionable workflows instead of static visibility

## Design Rules

- Web JARVIS behavior remains canonical.
- `/api/apple/*` remains the iPhone contract layer over canonical truth.
- Shared-state surfaces must not invent alternate phone-only behavior.
- Proactive behavior must be explainable.
- Every surfaced item should answer:
  - what happened
  - why it matters
  - what can be done next
  - why it was shown now
- The system must prefer restraint over noise.

## Phase 3 Subsystems

Phase 3 should be implemented as explicit subsystems, not scattered feature work.

### 1. Event Log

Purpose:
Create one append-only timeline of consequential JARVIS events.

Examples:

- approval requested
- approval resolved
- home command staged
- home command executed
- route restored
- route replanned
- weather warning elevated
- focus turned on
- memory candidate proposed
- publishing review requested
- agent escalated
- device reported a sound alert
- device reported a vision scan

Storage:

- `data/state/event_log.jsonl`

Each event record should include:

- `id`
- `ts`
- `actor`
- `surface`
- `domain`
- `kind`
- `severity`
- `title`
- `detail`
- `status`
- `source`
- `source_id`
- `thread_id`
- `navigation_target`
- `actions`
- `trust_zone`
- `authority_stage`
- `why_now`
- `metadata`

Recommended enums:

- `domain`: `approvals`, `home`, `navigation`, `weather`, `calendar`, `reminders`, `health`, `chronicle`, `publish`, `huddle`, `vision`, `sound`, `media`, `system`
- `kind`: `info`, `warning`, `action_needed`, `stage_ready`, `resolved`, `escalation`
- `severity`: `low`, `medium`, `high`, `critical`
- `status`: `new`, `seen`, `snoozed`, `resolved`, `expired`, `promoted`

Rules:

- append-only by default
- status changes recorded as follow-on events or persisted state overlays
- every notification should originate from or reference an event
- every future trust-zone action should be able to cite an event trail

### 2. Notification Center

Purpose:
Provide a first-class inbox for pending household-relevant attention.

This is the highest-value Phase 3 user-facing surface.

Notification Center should exist in:

- web JARVIS
- iPhone app
- future Watch summary / badge pathway

Categories:

- `approval`
- `household`
- `route`
- `weather`
- `health`
- `memory`
- `agent`
- `publish`
- `system`

Item shape:

- `id`
- `event_id`
- `category`
- `title`
- `detail`
- `severity`
- `status`
- `created_at`
- `updated_at`
- `expires_at`
- `audience`
- `delivery_mode`
- `navigation_target`
- `available_actions`
- `why_now`
- `source_summary`

Allowed actions:

- `open`
- `dismiss`
- `snooze`
- `resolve`
- `stage`
- `escalate`
- `route`

Storage:

- `data/state/notification_center.json`

Behavior:

- `pending` means active and visible
- `seen` means surfaced but not handled
- `snoozed` hides until a later time
- `resolved` removes from active attention load
- `promoted` marks it as elevated to a more urgent surface

### 3. Interruption Posture Engine

Purpose:
Decide whether JARVIS should interrupt now, badge quietly, or wait.

Inputs:

- current focus state
- time of day
- household presence
- device posture
- item severity
- item category
- active household mode
- user-specific preferences

Outputs:

- `deliver_now`
- `badge_only`
- `hold_for_brief`
- `quiet_store`
- `suppress`
- `escalate`

Initial rules should stay simple and deterministic.

Example rules:

- `critical` household safety items can interrupt
- `approval` can badge quietly during focus unless urgent
- `memory` candidates should never interrupt immediately
- `route` warnings can interrupt only during an active route window
- `sound` and `vision` detections should usually enter the inbox and only escalate when severity rules are met

Persistence:

- every delivery decision should record:
  - `decision`
  - `decision_reason`
  - `posture_snapshot`

This is essential for future trust and debugging.

### 4. Shared-State Workflow Surfaces

Purpose:
Turn mirrored state into actionable surfaces.

This phase should deepen:

- notifications
- calendar
- reminders
- focus
- sound alerts
- vision scans
- now playing
- systems sync truth

These should be surfaced without adding a large number of new top-level tabs.

## API Plan

### Event Log

Add:

- `GET /api/apple/events`
- `GET /api/apple/events/recent`
- `POST /api/apple/events/{event_id}/status`

Recommended query parameters:

- `domain`
- `status`
- `severity`
- `limit`
- `before`
- `after`

`GET /api/apple/events/recent` should be optimized for briefing and lightweight refresh.

### Notification Center

Add:

- `GET /api/apple/notifications`
- `POST /api/apple/notifications/{notification_id}/seen`
- `POST /api/apple/notifications/{notification_id}/dismiss`
- `POST /api/apple/notifications/{notification_id}/snooze`
- `POST /api/apple/notifications/{notification_id}/resolve`
- `POST /api/apple/notifications/{notification_id}/escalate`

Retain:

- `GET /api/apple/notifications/pending`

But treat it as a compatibility or push-delivery-oriented endpoint, not the primary workflow endpoint.

### Calendar Workflow

Add:

- `GET /api/apple/calendar/state`
- `POST /api/apple/calendar/events/{event_id}/ack`
- `POST /api/apple/calendar/events/{event_id}/route`
- `POST /api/apple/calendar/events/{event_id}/prepare`

State should include:

- next events
- events today
- event attention flags
- route-sensitive events
- preparation cues

### Reminders Workflow

Add:

- `GET /api/apple/reminders/state`
- `POST /api/apple/reminders/{reminder_id}/complete`
- `POST /api/apple/reminders/{reminder_id}/defer`
- `POST /api/apple/reminders/{reminder_id}/stage`

State should include:

- open reminders
- priority reminders
- overdue reminders
- grouped contexts where available

### Focus Workflow

Add:

- `GET /api/apple/focus/state`
- `POST /api/apple/focus/posture`

This should expose:

- current focus state
- interruption posture
- suppression rules now in effect
- last updated source

### Sound / Vision History

Add:

- `GET /api/apple/sound-alerts`
- `GET /api/apple/vision/scans`
- `POST /api/apple/sound-alerts/{id}/resolve`
- `POST /api/apple/vision/scans/{id}/resolve`

Initial goal is history and inspection, not heavy automation.

### Media State

Add:

- `GET /api/apple/now-playing/state`

Optional follow-ons if already practical:

- `POST /api/apple/now-playing/pause`
- `POST /api/apple/now-playing/play`
- `POST /api/apple/now-playing/skip`

Only add control actions if the runtime truth can support them honestly.

## Data Model Notes

### EventRecord

```json
{
  "id": "evt_...",
  "ts": "2026-05-29T12:34:56Z",
  "actor": "jarvis",
  "surface": "iphone",
  "domain": "navigation",
  "kind": "warning",
  "severity": "medium",
  "title": "Route weather is changing",
  "detail": "Rain is likely in 18 minutes on the current route.",
  "status": "new",
  "source": "apple.route_weather",
  "source_id": "route_123",
  "navigation_target": "navigate",
  "actions": ["open", "route", "dismiss"],
  "trust_zone": "household_logistics",
  "authority_stage": "draft",
  "why_now": "Active route and arrival window is at risk.",
  "metadata": {}
}
```

### NotificationItem

```json
{
  "id": "notif_...",
  "event_id": "evt_...",
  "category": "route",
  "title": "Weather may affect arrival",
  "detail": "Rain is likely before the Cincinnati arrival window.",
  "severity": "medium",
  "status": "pending",
  "created_at": "2026-05-29T12:35:00Z",
  "updated_at": "2026-05-29T12:35:00Z",
  "delivery_mode": "badge_only",
  "navigation_target": "navigate",
  "available_actions": ["open", "dismiss", "snooze"],
  "why_now": "Active route plus weather risk crossed threshold.",
  "source_summary": "Derived from route and weather state."
}
```

## Surface Plan

### Web

Add:

- dedicated Notification Center panel/view
- event timeline panel in Systems or admin context
- shared-state mini-cards that deep-link into workflow surfaces

Web should remain the richest inspection and admin surface first.

### iPhone

Add:

- dedicated notifications/inbox workflow surface
  - either inside `Brief` as a drill-in
  - or as a new in-app workflow screen reachable from `Brief` and `Systems`
- calendar workflow card expansion
- reminders workflow card expansion
- focus posture card
- sound history and vision history drill-ins

Phone should prioritize:

- quick triage
- clear actions
- shallow but trustworthy history

### Systems

Expand `Systems` to show:

- latest event-log health
- last notification sync
- interruption posture snapshot
- source freshness per shared-state domain

### Brief

Use the new event and notification layers to improve:

- alert banner
- what-matters-now ranking
- quieter surfacing of lower-severity items

## Rollout Order

### Slice 1: Event Spine

Build first:

- `event_log.jsonl`
- event helpers
- event write path for existing major actions
- basic `GET /api/apple/events/recent`

Exit:

- approvals, home actions, navigation changes, and shared-state ingests all emit events

### Slice 2: Notification Center

Build second:

- canonical notification store
- notification list endpoint
- seen/dismiss/snooze/resolve actions
- iPhone inbox surface
- web inbox surface

Exit:

- pending attention no longer lives only in briefing fragments and badge counts

### Slice 3: Interruption Posture

Build third:

- posture decision helper
- initial deterministic rules
- delivery decision recording
- focus-aware and severity-aware behavior

Exit:

- JARVIS decides how to surface items with visible reasons

### Slice 4: Calendar And Reminders Workflow

Build fourth:

- deeper state endpoints
- acknowledgment / complete / defer / prepare flows
- drill-in surfaces on iPhone and web

Exit:

- calendar and reminders are actionable shared-state surfaces, not just mirror summaries

### Slice 5: Sound, Vision, And Media History

Build fifth:

- history endpoints
- drill-in history surfaces
- resolve actions where useful

Exit:

- these domains stop being “latest sample only”

## Verification Gates

Every Slice Must Include:

- backend contract test
- additive-safe decode coverage in `JarvisKit`
- web verification if a web surface changed
- physical-device iPhone verification
- live Hetzner verification
- parity matrix update

Required checks:

- `python3 -m py_compile /Users/chris/Desktop/CODE/JARVIS/jarvis/apple_api.py`
- `swift test` in `/Users/chris/Desktop/CODE/JARVIS/JarvisApple`
- `python3 /Users/chris/Desktop/CODE/JARVIS/scripts/verify_apple_contracts.py --ssh-host root@5.78.212.15 --container jarvis-family-jarvis-1`

Additional Phase 3 verifier coverage should be added for:

- `/api/apple/events/recent`
- `/api/apple/notifications`
- `/api/apple/focus/state`
- `/api/apple/calendar/state`
- `/api/apple/reminders/state`
- `/api/apple/sound-alerts`
- `/api/apple/vision/scans`

## Exit Conditions

Phase 3 is complete when:

- Notification Center exists and is useful on phone and web
- a shared event spine exists for proactive and consequential state changes
- interruption posture is explicit and governs delivery behavior
- calendar/reminders/focus/sound/vision/media have actionable shared-state workflow surfaces
- Systems can explain shared-state freshness and notification posture
- the phone and web feel like one ambient intelligence system, not parallel clients

## What Not To Do

- do not start with autonomous notification spam
- do not add ambient behavior before interruption posture exists
- do not add memory promotion here without provenance and explicit review
- do not make iPhone-only workflow rules that diverge from web JARVIS truth
- do not add top-level tabs unless the workflow truly cannot fit the current structure

## Immediate Next Move

Start with Slice 1 and Slice 2 together:

- build the event spine
- build Notification Center on top of it

That is the strongest technical and product foundation for the rest of Phase 3.
