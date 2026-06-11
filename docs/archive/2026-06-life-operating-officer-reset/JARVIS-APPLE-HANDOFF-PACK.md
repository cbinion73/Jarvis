# JARVIS Apple Handoff Pack

## Purpose

This document is the direct handoff artifact for Codex in Xcode.

It defines how the Apple-native JARVIS clients should be built against the
existing JARVIS system, with special attention to:

- Apple Health
- CarPlay
- Siri and App Intents
- Widgets and Live Activities
- Watch complications
- notification architecture
- health advisor behavior

The governing principle is simple:

`JARVIS core remains the orchestrator and system brain.`

Apple-native apps are device-specific clients and capability bridges.
They should not become a second source of truth for memory, routing, or
cross-domain reasoning.

## System Role Split

| System | Role | Owns |
| --- | --- | --- |
| `JARVIS` Python runtime | orchestration layer and shared intelligence | routing, memory policy, recommendations, daily feed logic, Chronicle and Catalyst contracts, permissions policy |
| `JarvisApple` native clients | device-specific surfaces and Apple capability bridge | HealthKit access, push and local notifications, App Intents, widgets, CarPlay, native lifecycle, native UX |
| `Chronicle` | faith system of record | spiritual records, prayer and study continuity |
| `Catalyst` | executive subsystem | executive artifacts, work synthesis, delegated work products |

## Build Priorities

### V1

- `iPhone` app
- `Apple Health` sync bridge
- health advisor daily feed card
- local notifications
- basic Siri and App Intents
- shared Swift package foundation

### V1.5

- `Apple Watch` companion
- widgets
- Live Activities
- richer health trend views

### V2

- `CarPlay`
- `macOS` command-center client
- `iPad` workspace client
- clinical-record import refinement
- deeper approval and recommendation UX

## Apple Platform Architecture v2

| Capability / Platform | Primary Use Case | Native Features | What Stays Shared | What Must Be Platform-Specific | Repo / Structure Recommendation |
| --- | --- | --- | --- | --- | --- |
| `macOS` | full command center | menu bar, multiwindow, camera and mic access, desktop notifications, file review, drag and drop | routing, memory, contracts, dashboards, health summaries | windowing, menu bar UX, desktop lifecycle, desktop audio behavior | `JarvisApple/apps/macos/JarvisMac` |
| `iPhone` | main personal companion and health hub | HealthKit, push, camera, Siri, Shortcuts, Live Activities, CarPlay host | APIs, models, sync rules, recommendation engine, feed contracts | mobile layouts, background refresh, permissions, mobile-safe notifications | `JarvisApple/apps/ios/JarvisPhone` |
| `iPad` | larger workspace client | split view, multitasking, richer dashboards, keyboard support | same contracts, APIs, models, health summaries | adaptive tablet layout, stage manager behavior, larger workspace navigation | shared iOS target or dedicated iPad scene modules |
| `Apple Watch` | glanceable health and approvals | workouts, complications, quick capture, actionable notifications, dictation | short-form summaries, approvals, sync contracts | watch UX, battery-aware refresh, tiny surface rules | `JarvisApple/apps/watchos/JarvisWatch` |
| `Apple TV` | ambient family and briefing surface | focus engine, fullscreen scene display, passive dashboards | dashboard feeds, family and home summaries | tvOS navigation, passive display cadence, TV-safe interaction model | `JarvisApple/apps/tvos/JarvisTV` |
| `Apple Health` | health data ingestion and longitudinal context | HealthKit, clinical records, background delivery | health schema, trend logic, safety rules, recommendations | entitlements, permission flows, protected local cache, HealthKit queries | `JarvisKitHealth` |
| `CarPlay` | safe in-car JARVIS companion | CarPlay templates, Siri, audio session, safe quick actions | calendar and message summaries, quick actions, priorities, commute context payloads | driver-safe UI, interaction limits, audio UX, transport context behavior | feature inside `JarvisPhone` |
| `Siri / App Intents` | voice-first entry into JARVIS flows | App Intents, Shortcuts, Siri responses | routing contracts, action payloads, recommendation and approval intents | phrase design, shortcut exposure, Siri-native result presentation | `JarvisKitIntents` |
| `Widgets / Live Activities` | glanceable status and ongoing context | home screen widgets, lock screen widgets, Live Activities | summary payloads, feed cards, top priorities | widget timelines, Live Activity formatting, platform-specific update cadence | widget extension targets |
| `Watch complications` | ultra-light health and day signals | complication families, Smart Stack presence | tiny health and day summaries | watch-specific complication layouts, update cadence | watch extension |
| `Notification architecture` | approvals, alerts, health escalations, reminders | APNs, local notifications, actions, interruption levels | event model, escalation classes, preferences policy | delivery categories, platform-specific notification UX, permission flows | shared notification model plus per-platform adapters |

## Native Repo Structure

Recommended Apple-native workspace:

```text
JarvisApple/
  Package.swift
  apps/
    ios/JarvisPhone/
    macos/JarvisMac/
    watchos/JarvisWatch/
    tvos/JarvisTV/
  Packages/
    JarvisKit/
    JarvisKitHealth/
    JarvisKitIntents/
    JarvisDesignKit/
    JarvisNotifications/
```

### Module Responsibilities

| Module | Responsibility |
| --- | --- |
| `JarvisKit` | shared API models, networking, auth/session state, feed models, shared routing models |
| `JarvisKitHealth` | HealthKit integration, health permissions, clinical record ingestion bridge, health cache |
| `JarvisKitIntents` | Siri and App Intents, Shortcuts exposure, intent routing |
| `JarvisDesignKit` | shared Apple-native design tokens and reusable components |
| `JarvisNotifications` | local and remote notification categories, scheduling, action mapping |

## JARVIS Health Advisor

### Mission

JARVIS should act as a `health copilot`.

That means:

- read Apple Health data
- read supported clinical records and test results
- summarize trends
- keep personal health context synchronized
- place concise recommendations into the daily feed
- flag items that may need follow-up

It must not present itself as an autonomous diagnostician or treatment authority.

### Health Advisor Role Boundaries

| Allowed | Not Allowed |
| --- | --- |
| wellness coaching | autonomous diagnosis |
| trend summaries | medication changes without clinician direction |
| appointment and retest reminders | treatment instructions framed as medical authority |
| lab-result explanation with provenance | emergency triage beyond conservative escalation language |
| clinician follow-up prompts | replacing a physician or licensed clinician |

## Health Advisor Data Model

| Model | Fields |
| --- | --- |
| `HealthProfile` | demographics, unit preferences, goals, clinician context, conditions, medications, consent flags |
| `HealthSignal` | metric type, timestamp, value, unit, source, provenance, confidence |
| `HealthTrend` | metric, window, baseline, delta, slope, significance, confidence |
| `ClinicalResult` | test name, code, specimen date, result, unit, reference range, abnormal flag, institution |
| `HealthInsight` | summary, rationale, supporting signals, severity, confidence |
| `HealthRecommendation` | category, recommendation text, rationale, urgency, requires_clinician_review, expires_at |
| `EscalationEvent` | trigger, threshold, evidence, escalation class, recommended next action |
| `ConsentPolicy` | read scopes, write scopes, sync scopes, retention rules, sensitivity flags |

### Suggested Shared Codable Types

```swift
struct HealthSignal: Codable, Identifiable {
    let id: String
    let metric: String
    let timestamp: Date
    let value: Double?
    let unit: String?
    let source: String
    let provenance: String
    let confidence: Double?
}

struct ClinicalResult: Codable, Identifiable {
    let id: String
    let testName: String
    let code: String?
    let specimenDate: Date?
    let resultText: String?
    let numericValue: Double?
    let unit: String?
    let referenceRange: String?
    let abnormalFlag: String?
    let institution: String?
    let provenance: String
}

struct HealthRecommendation: Codable, Identifiable {
    let id: String
    let category: String
    let summary: String
    let rationale: String
    let urgency: String
    let requiresClinicianReview: Bool
    let supportingSignalIDs: [String]
}
```

## Apple Health Sync Design

### Source Of Truth

- `iPhone` is the primary HealthKit bridge.
- `Apple Watch` contributes workout, heart, activity, and wearable signals through Apple Health.
- `JARVIS` stores normalized summaries, trends, and references.

### Sync Flow

1. Native iPhone client requests HealthKit permission.
2. Native client reads allowed categories.
3. Data is normalized into JARVIS health models.
4. Native client posts a sync payload to JARVIS.
5. JARVIS computes trends, insights, and recommendation candidates.
6. Daily feed includes a health card when enough signal is present.

### Initial HealthKit Read Categories

Recommended v1 read scope:

- sleep
- workouts
- steps
- active energy
- resting heart rate
- heart rate variability
- weight
- blood pressure if present
- blood glucose if present
- medications if present
- symptoms if explicitly approved
- clinical records if explicitly approved

### Sync Cadence

| Trigger | Behavior |
| --- | --- |
| app launch | refresh lightweight summary |
| manual refresh | full allowed sync |
| background refresh | bounded sync if the platform allows it |
| background delivery callback | incremental ingest where supported |
| recommendation request | reuse cached data when fresh, otherwise prompt refresh if needed |

### Sync Design Rules

- local protected cache on device first
- send only approved categories
- separate sensitive categories from general feed content
- maintain provenance for every data point
- expose clear last-sync timestamps

## Test Result And Clinical Record Ingestion

### Path 1: HealthKit Clinical Records

Use HealthKit clinical records when the user has connected a supported institution.

Preferred output:

- structured clinical result
- provenance preserved
- institution and date preserved
- lab abnormal flags preserved

### Path 2: File Import

Fallback path for:

- PDF lab reports
- portal export files
- screenshots converted through review flow

This path should feed a parsing pipeline with lower confidence until reviewed.

### Path 3: Manual Entry

Allow manual recording for isolated values:

- blood pressure
- glucose
- weight
- lab value

Mark these as `manual` provenance.

### Parsing Rules

Required extraction targets:

- test name
- collection date
- numeric or text result
- unit
- reference range
- abnormal marker
- institution if present

## Daily Feed Health Card

### Card Structure

| Section | Content |
| --- | --- |
| `Top line` | one-sentence health posture |
| `Status row` | sleep, recovery proxy, activity, weight trend, BP/glucose/lab availability |
| `Signals` | up to 3 notable changes or new results |
| `Recommendations` | up to 3 practical next steps |
| `Escalation` | distinct warning block when follow-up may be needed |

### Example Output

```text
Health: recovery looks low today.
Signals: sleep down 3 nights, resting HR elevated, new LDL result posted.
Recommendations: walk lightly, hydrate, review the LDL result this evening.
Escalation: consider clinician follow-up if elevated trend persists.
```

### Feed Rules

- maximum 3 signals
- maximum 3 recommendations
- clear provenance available on detail open
- health card can be hidden when no recent signal exists

## Safety And Escalation Rules

### Escalation Classes

| Class | Meaning |
| --- | --- |
| `inform` | useful context only |
| `monitor` | watch for continued pattern |
| `follow_up` | user should act within a reasonable window |
| `clinician_review` | user should discuss with a clinician |
| `urgent_attention` | prompt conservative urgent-care style language, not diagnosis |

### Rules

- recommendations must cite the supporting time window
- abnormal lab explanation must show provenance
- symptom and vitals combinations should be conservative
- health insights should be clearly labeled as assistive, not diagnostic
- user must be able to dismiss, snooze, or mark addressed

### Memory Policy

Health is a restricted memory domain.

Guidance:

- store summary and trend layers in shared JARVIS memory
- store raw or highly sensitive content in protected health storage
- require explicit opt-in before broader cross-domain use

## Native Endpoint Contract For Xcode Codex

These should exist in the JARVIS backend for Apple-native clients.

### Health Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/health/profile` | `GET` | fetch current health profile and consent state |
| `/api/health/profile` | `PUT` | update goals, units, and health preferences |
| `/api/health/sync` | `POST` | ingest normalized HealthKit sync payload |
| `/api/health/summary` | `GET` | fetch latest health summary for feed and widgets |
| `/api/health/recommendations` | `GET` | fetch recommendation set |
| `/api/health/escalations` | `GET` | fetch active escalations |
| `/api/health/clinical-results` | `GET` | list structured clinical results |
| `/api/health/clinical-results/import` | `POST` | submit parsed clinical-result payload or file-import result |

### Suggested Sync Payload

```json
{
  "source": "jarvis_iphone",
  "synced_at": "2026-05-15T12:00:00Z",
  "signals": [
    {
      "id": "sig_sleep_2026_05_15",
      "metric": "sleep_duration",
      "timestamp": "2026-05-15T06:30:00Z",
      "value": 6.1,
      "unit": "h",
      "source": "healthkit",
      "provenance": "apple_health",
      "confidence": 0.98
    }
  ],
  "clinical_results": [],
  "device_context": {
    "platform": "ios",
    "healthkit_available": true,
    "watch_paired": true
  }
}
```

## Siri And App Intents

Initial intents for Xcode Codex to build:

- `Open Daily Feed`
- `Show Health Summary`
- `Refresh Health`
- `Show Recommendations`
- `Log Weight`
- `Log Blood Pressure`
- `Open Approvals`

Rules:

- keep intents short and obvious
- prefer retrieval and lightweight capture first
- do not expose medical-claim-heavy language in Siri surfaces

## Widgets And Live Activities

### Widgets

Recommended first widgets:

- `Today Overview`
- `Health Summary`
- `Approvals`

### Live Activities

Recommended first Live Activity:

- `Focused day briefing`

Optional later:

- `timed recovery prompt`
- `appointment or follow-up reminder`

## Watch Complications

Recommended complication content:

- readiness or recovery summary
- next key reminder
- health attention flag
- approval count

Complications should never try to show dense interpretation.

## Notification Architecture

### Notification Classes

| Class | Example |
| --- | --- |
| `briefing` | morning daily feed ready |
| `approval` | a decision needs review |
| `health_signal` | elevated trend or new result |
| `health_followup` | retest or appointment reminder |
| `urgent_attention` | conservative escalation prompt |

### Notification Rules

- approvals should be actionable
- health notifications should be conservative and clear
- avoid notification spam by coalescing repeated trends
- use interruption levels carefully
- let the user configure per-domain preferences

## CarPlay

CarPlay should be deliberately narrow.

### Allowed v1

- what is next
- commute-aware reminders
- safe message triage
- brief daily status
- voice capture into JARVIS

### Not Allowed v1

- dense dashboards
- touch-heavy browsing
- medical deep dives
- settings-heavy workflows

## Xcode Codex Build Order

### Phase 1

- create `JarvisApple` workspace
- create `JarvisKit`
- create `JarvisPhone`
- add health permission scaffold
- add JARVIS API client scaffold

### Phase 2

- implement HealthKit bridge
- implement health sync payloads
- implement daily health summary view
- implement notification categories

### Phase 3

- add widgets
- add App Intents
- add watch companion

### Phase 4

- add CarPlay
- add macOS client
- add richer clinical-result review flows

## V1 Acceptance Criteria

- iPhone app can request HealthKit permissions successfully
- iPhone app can sync approved health categories into JARVIS
- JARVIS can produce a daily health summary and recommendation payload
- health card can appear in the daily feed
- at least one widget can display the health summary
- at least one App Intent can open the health summary
- notification categories are defined and working locally
- health advice remains within wellness and follow-up guardrails

## Guidance For Codex In Xcode

Build the Apple-native clients as thin but capable device-specific shells.

Prefer:

- local-first protected storage
- strong provenance tracking
- explicit permissions
- small, well-named Swift packages
- stable API models

Avoid:

- turning the iPhone app into a second orchestration brain
- inventing ad hoc schemas that drift from JARVIS contracts
- overbuilding CarPlay early
- overclaiming medical authority

## Immediate Next Deliverables

Codex in Xcode should produce these first:

1. `JarvisApple workspace scaffold`
2. `JarvisKit` models and API client
3. `JarvisPhone` HealthKit permission and sync prototype
4. `Health summary` screen
5. `Daily feed widget`
6. `Show Health Summary` App Intent

