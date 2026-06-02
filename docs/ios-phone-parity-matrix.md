# iPhone App / Web JARVIS Parity Matrix

## Goal

Keep the current iPhone app layout, but make each tab function as a native client of the live web JARVIS instance.

Source-of-truth rule:

- Web JARVIS behavior and live backend state are canonical.
- `/api/apple/*` is the iPhone contract layer over that canonical state.
- The phone UI should not invent alternate truth when web JARVIS already owns the behavior.

This document tracks parity and contract truth.

It is not the long-term mobile UX model.

Now that parity is broadly in place, the next frontend step is to reshape the phone into a smaller command system centered on:

- Today / Brief
- Focus / priorities
- Family / household
- Decisions / approvals
- Navigate / commute
- continuity and resume

See `docs/iphone-mobile-command-system.md`.

## Status Legend

- `Full`: iPhone tab is meaningfully backed by live JARVIS behavior.
- `Partial`: iPhone tab exists and uses live data, but key web behavior is still missing.
- `Missing`: web behavior exists but the phone has no equivalent functional surface.

## Matrix

| Area | Web JARVIS source | iPhone surface | Apple contract | Status | Main gaps |
|---|---|---|---|---|---|
| Brief / Overview | `jarvis/jarvis_theme_glass.py` overview loaders, briefing renderers, family bar, alert banner, mini-cards | `BriefingView.swift` | `GET /api/apple/briefing`, `GET /api/apple/app-state` | Full | Brief now carries the core JARVIS overview layer on phone, including ranked alerts, household posture, morning workflow cards, and strategic Catalyst/Chronicle/Publishing mini-cards |
| Needs / Approvals | `renderApprovals`, approval workflows | `NeedsView.swift` | `GET /api/apple/needs`, `POST /api/apple/approvals/{id}/approve` | Full | Phone Needs now carries richer request context, alternate action clarity, confirmation state, staged payload context, and approval-center workflow summaries |
| Health | `loadHealth`, SAM/score panels, overview health cards | `HealthView.swift` | `GET /api/apple/health/summary`, `POST /api/apple/health/log` | Full | Phone Health now carries daily score depth, readiness factors, Thor movement posture, completeness gaps, watchlist context, and protocol guidance from the broader JARVIS health layer |
| Weather | `loadWeatherWidget`, weather modal, route weather hooks | `WeatherView.swift` | `GET /api/apple/weather` | Full | Phone Weather now mirrors the core JARVIS storm surface with near-term outlook, alerts, radar, daily forecast context, and saved-route travel weather monitoring |
| Home | `loadHomeDashboard`, home email/calendar/projects/tasks, home ops | `HomeView.swift` | `GET /api/apple/home/state`, `POST /api/apple/home/command`, `POST /api/apple/presence` | Full | Phone Home now carries the live house-state plus a compact home-ops snapshot for inbox, task queue, active projects, calendar movement, and sync health from the broader JARVIS home dashboard |
| Catalyst | `loadOverviewCatalyst`, catalyst workspace panels | `CatalystView.swift` | `GET /api/apple/catalyst` | Full | Phone Catalyst now mirrors the live workspace pulse with portfolio lanes, connector readiness, workflow throughput, recent runs, and active work context from the broader JARVIS catalyst overview |
| Chronicle | `loadChronicle`, context/pattern loaders | `ChronicleView.swift` | `GET /api/apple/chronicle`, `POST /api/apple/chronicle/capture`, `POST /api/apple/chronicle/prayers/*`, `POST /api/apple/chronicle/study/save` | Full | Phone Chronicle now carries live formation context, prayer follow-up actions, study save workflow, and pattern visibility from the broader JARVIS Chronicle layer |
| Faith | `loadFaith`, faith roster/context | `FaithView.swift` | `GET /api/apple/faith`, `POST /api/apple/faith/chat` | Full | Phone Faith now carries the live council roster, formation prompts, and guided agent conversation flow alongside the daily word and prayer capture experience |
| Publish | `loadPublishing`, KDP/launch/pipeline panels | `PublishView.swift` | `GET /api/apple/publishing`, `POST /api/apple/publishing/reviews/*` | Full | Phone Publish now mirrors the deeper JARVIS publishing layer with KDP/platform readiness, checklist progress, launch asset coverage, and pending review workflow instead of only launch-control posture |
| Huddle / Agents | `loadHuddle`, `loadAgentRoster`, `loadLiveAgents` | `HuddleView.swift` | `GET /api/apple/huddle`, `POST /api/apple/huddle/party-mode/start` | Full | Phone Huddle now mirrors the broader orchestration layer with live runtime posture, party-mode session status, ready dossiers, and a wake-agents control alongside standups and approvals |
| Navigate | `renderNavRoute`, `loadNavPOIs`, active route controls, POI toggles, parks radius slider | `NavigateView.swift` | `GET /api/apple/navigation/*` | Full | Route HUD, restore/recovery, smart-stop controls, route weather windows, and destination aerial preview now mirror the core JARVIS navigation experience on phone |
| Forge | forge/workshop panels | `ForgeView.swift` | `GET /api/apple/forge`, `POST /api/apple/forge/projects`, `POST /api/apple/forge/submit`, `POST /api/apple/forge/save` | Full | Phone Forge now mirrors the live workshop with project intake, workspace pulse, active project readiness, recent jobs, generated outputs, and photogrammetry capture flow from JARVIS |
| Voice / Chat | chat + command flows, voice interactions | `VoiceView.swift` | `POST /api/apple/speak`, `GET /api/apple/voice/greeting`, `GET /api/apple/voice/state` | Full | Phone Voice now carries live command-session continuity, recent conversation context, quick commands, and voice-stack readiness instead of only a one-shot speak bridge |
| Systems / Settings | `settingsNavTo(...)`, accounts, voice, location, family, devices, costs, Maps API status | `SettingsView.swift` | `GET /api/apple/status`, `GET /api/apple/app-state`, `GET /api/apple/systems/admin-summary` plus server-side config endpoints | Full | Systems now mirrors the broader admin layer on phone too, including accounts, family roster/device posture, voice stack readiness, service runtime status, and month-to-date AI cost/config visibility |
| Notifications | web ambient/alert surfaces | `BriefingView.swift`, `SettingsView.swift`, `NotificationCenterView` | `GET /api/apple/app-state`, `GET /api/apple/notifications`, `GET /api/apple/events/recent`, `POST /api/apple/notifications/*` | Full | Phone Notifications now carry the live inbox plus ambient routing truth, delivery posture, routing lanes, category counts, and event-flow summary from the broader JARVIS notification control plane |
| Calendar sync | web calendar panels | `BriefingView.swift`, `SettingsView.swift` | `GET /api/apple/app-state`, `GET /api/apple/calendar/state`, `POST /api/apple/calendar/*` | Full | Calendar now carries live mirror truth plus richer event-management depth on phone, including today and route-window sections, event notes and meeting links, and real route-action handoff through the Apple contract |
| Reminders sync | web task/reminder panels | `BriefingView.swift`, `SettingsView.swift` | `GET /api/apple/app-state`, `GET /api/apple/reminders/state`, `POST /api/apple/reminders/*` | Full | Reminders now carry broader task-management depth on phone too, including queue summaries, list-level load visibility, simultaneous overdue/due-soon/priority lanes, and complete or snooze workflow actions against live mirrored reminder state |
| Focus sync | web notification/focus behavior | `BriefingView.swift`, `SettingsView.swift` | `GET /api/apple/app-state`, `GET /api/apple/focus-state`, `POST /api/apple/focus` | Full | Focus now carries real control breadth on phone too, including live focus-filter posture, routing lanes, stored JARVIS mode controls, and preset apply actions backed by the Apple focus contract |
| Sound alerts | web/security ambient flows | `BriefingView.swift`, `SettingsView.swift` | `GET /api/apple/app-state`, `GET /api/apple/sound-alerts`, `POST /api/apple/sound-alert`, `POST /api/apple/sound-alerts/{id}/resolve` | Full | Sound alerts now carry downstream automation and policy depth on phone too, including live sound-policy rules, follow-up response plans, high-confidence security routing, and resolve workflow against the Apple signal contract |
| Vision scan | web/vision security/workflow surface | `BriefingView.swift`, `SettingsView.swift` | `GET /api/apple/app-state`, `GET /api/apple/vision/scans`, `POST /api/apple/vision/scan`, `POST /api/apple/vision/scans/{id}/resolve` | Full | Vision scans now carry broader automation depth on phone too, including live vision-policy rules, follow-up response plans, entryway and package routing context, and resolve workflow against the Apple vision contract |
| Now playing | web ambient media behavior | `BriefingView.swift`, `SettingsView.swift` | `GET /api/apple/app-state`, `GET /api/apple/now-playing/state`, `POST /api/apple/now-playing` | Full | Media now carries deeper ambient orchestration on phone too, including playback posture, media routing rules, session plans, recommended controls, recent history, and control-plane visibility through the Apple now-playing contract |

## Implementation Checklist

### Phase 1: Stop Split-Brain State

- [x] Home tab must reflect live JARVIS house state and not rely only on local HomeKit.
- [x] Brief tab must expose more live overview truth from JARVIS instead of acting as a reduced report.
- [x] Systems tab must surface production sync health for the major shared state domains.
- [x] Phone-local caches for home, location, navigation preferences, and route state must hydrate from JARVIS.

### Phase 2: Deepen Existing Tabs

- [x] Complete Brief orchestration overview parity and final polish.
- [x] Expand Needs into a richer request workflow surface.
- [x] Bring Health closer to SAM / score / protocol parity.
- [x] Complete Weather module parity and route-weather integration.
- [x] Add richer Chronicle context and pattern visibility.
- [x] Add deeper Publishing workspace actions and launch pipeline visibility.
- [x] Add richer Huddle / live-agent roster visibility.
- [x] Finish navigation HUD and reliability polish, including route weather and aerial-intel parity.
- [x] Continue Navigation HUD and route-state parity.

### Phase 3: Deepen Existing Shared State Surfaces

- [x] Add notification inbox / pending notification workflow surface.
- [x] Add calendar sync visibility.
- [x] Add reminders sync visibility.
- [x] Add focus-mode sync visibility.
- [x] Add sound-alert visibility.
- [x] Add vision-scan visibility.
- [x] Add now-playing sync/status visibility.
- [x] Add control-plane freshness and event-flow visibility in Systems and Notifications.
- [x] Add signal resolve workflows for sound alerts and vision scans.

### Phase 4: Guardrails

- [x] Add contract tests for all `/api/apple/*` payloads.
- [x] Add Swift decode tests for all JarvisKit Apple models.
- [x] Add a parity checklist to every live feature rollout: backend contract, web behavior, phone surface, device verification.

Verification command:

- `python3 scripts/verify_apple_contracts.py --ssh-host root@5.78.212.15 --container jarvis-family-jarvis-1`
- `python3 scripts/test_verify_apple_contracts.py`
- `python3 scripts/verify_live_rollout_checklist.py docs/live-feature-rollout-checklist.md`

## Priority Order

1. Home
2. Brief
3. Systems
4. Needs
5. Navigation HUD and reliability polish
6. Health depth
7. Remaining ingestion surfaces

## Current Pass

Current implementation pass has effectively closed out parity.

The next pass should not add more equal-weight top-level phone surfaces. It should reorganize the mobile experience into a silent-first command layer while preserving the production-backed truth already established here.
