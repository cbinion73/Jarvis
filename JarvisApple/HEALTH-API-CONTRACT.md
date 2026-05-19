# Health API Contract

This is the native-client-facing API contract for the first JARVIS Health Advisor pass.

## Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/health/profile` | `GET` | fetch current health profile and consent state |
| `/api/health/profile` | `PUT` | update goals, units, health preferences |
| `/api/health/sync` | `POST` | ingest normalized HealthKit sync payload |
| `/api/health/summary` | `GET` | fetch latest health summary for daily feed and widgets |
| `/api/health/recommendations` | `GET` | fetch current recommendation set |
| `/api/health/escalations` | `GET` | fetch active escalation events |
| `/api/health/clinical-results` | `GET` | list structured clinical results |
| `/api/health/clinical-results/import` | `POST` | submit parsed clinical result import payload |

## Rules

- iPhone is the HealthKit bridge.
- JARVIS remains the recommendation and memory orchestrator.
- Clients should not invent independent business logic beyond presentation and local permission handling.
- Raw sensitive data should remain local-first when possible.

## V1 Read Categories

- sleep
- workouts
- steps
- active energy
- resting heart rate
- heart rate variability
- weight
- blood pressure if available
- blood glucose if available
- clinical records if explicitly approved

## Sync Payload

```json
{
  "source": "jarvis_iphone",
  "synced_at": "2026-05-16T08:00:00Z",
  "signals": [
    {
      "id": "sleep_2026_05_16",
      "metric": "sleep_duration",
      "timestamp": "2026-05-16T06:45:00Z",
      "value": 6.4,
      "unit": "h",
      "source": "healthkit",
      "provenance": "apple_health",
      "confidence": 0.98
    }
  ],
  "clinical_results": [],
  "device_context": {
    "platform": "ios",
    "watch_paired": true,
    "healthkit_available": true
  }
}
```

## Daily Feed Health Summary

```json
{
  "status": "monitor",
  "headline": "Recovery looks low today.",
  "signals": [
    "Sleep down 3 nights",
    "Resting heart rate elevated",
    "No workout recovery day yet"
  ],
  "recommendations": [
    "Hydrate early",
    "Keep activity light today",
    "Aim for earlier sleep tonight"
  ],
  "escalations": []
}
```
