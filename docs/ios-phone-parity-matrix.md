# iPhone App / Web JARVIS Parity Matrix

## Goal

Keep the current iPhone app layout, but make each tab function as a native client of the live web JARVIS instance.

Source-of-truth rule:

- Web JARVIS behavior and live backend state are canonical.
- `/api/apple/*` is the iPhone contract layer over that canonical state.
- The phone UI should not invent alternate truth when web JARVIS already owns the behavior.

## Status Legend

- `Full`: iPhone tab is meaningfully backed by live JARVIS behavior.
- `Partial`: iPhone tab exists and uses live data, but key web behavior is still missing.
- `Missing`: web behavior exists but the phone has no equivalent functional surface.

## Matrix

| Area | Web JARVIS source | iPhone surface | Apple contract | Status | Main gaps |
|---|---|---|---|---|---|
| Brief / Overview | `jarvis/jarvis_theme_glass.py` overview loaders, briefing renderers, family bar, alert banner, mini-cards | `BriefingView.swift` | `GET /api/apple/briefing` | Partial | Phone shows packet, but not the richer overview orchestration, alert banner behavior, presence rollups, reminder/tasks/catalyst/chronicle mini-card depth |
| Needs / Approvals | `renderApprovals`, approval workflows | `NeedsView.swift` | `GET /api/apple/needs`, `POST /api/apple/approvals/{id}/approve` | Partial | Approve path exists; missing richer request context, alternate actions, and deeper workflow state |
| Health | `loadHealth`, SAM/score panels, overview health cards | `HealthView.swift` | `GET /api/apple/health/summary`, `POST /api/apple/health/log` | Partial | Good live summary, but not full SAM protocol / daily score / deeper web health modules |
| Weather | `loadWeatherWidget`, weather modal, route weather hooks | `WeatherView.swift` | `GET /api/apple/weather` | Partial | Core live weather works; still missing broader weather-module parity and some richer route/weather integrations |
| Home | `loadHomeDashboard`, home email/calendar/projects/tasks, home ops | `HomeView.swift` | `GET /api/apple/home/state`, `POST /api/apple/home/command`, `POST /api/apple/presence` | Partial | Phone was HomeKit-first; needs live JARVIS house-state parity, staged commands, presence, and household context |
| Catalyst | `loadOverviewCatalyst`, catalyst workspace panels | `CatalystView.swift` | `GET /api/apple/catalyst` | Partial | Data exists, but phone lacks full action depth and overview integration |
| Chronicle | `loadChronicle`, context/pattern loaders | `ChronicleView.swift` | `GET /api/apple/chronicle`, `POST /api/apple/chronicle/capture` | Partial | Entries and capture exist; missing pattern/context parity and broader chronicle tooling |
| Faith | `loadFaith`, faith roster/context | `FaithView.swift` | `GET /api/apple/faith` | Partial | Daily word works; missing deeper faith mode orchestration from web |
| Publish | `loadPublishing`, KDP/launch/pipeline panels | `PublishView.swift` | `GET /api/apple/publishing` | Partial | Summary exists; missing fuller publishing workspace actions and platform-specific tools |
| Huddle / Agents | `loadHuddle`, `loadAgentRoster`, `loadLiveAgents` | `HuddleView.swift` | `GET /api/apple/huddle` | Partial | Basic huddle view exists; missing richer agent roster/live-agent parity |
| Navigate | `renderNavRoute`, `loadNavPOIs`, active route controls, POI toggles, parks radius slider | `NavigateView.swift` | `GET /api/apple/navigation/*` | Partial | Strong progress; still needs continued HUD parity, more route-state polish, and long-route reliability |
| Forge | forge/workshop panels | `ForgeView.swift` | `GET /api/apple/forge`, `POST /api/apple/forge/submit`, `POST /api/apple/forge/save` | Partial | Capture/upload exists; processing and broader workshop parity are still incomplete |
| Voice / Chat | chat + command flows, voice interactions | `VoiceView.swift` | `POST /api/apple/speak`, `GET /api/apple/voice/greeting` | Partial | Basic live voice bridge exists; missing broader chat/system command parity with web |
| Systems / Settings | `settingsNavTo(...)`, accounts, voice, location, family, devices, costs, Maps API status | `SettingsView.swift` | `GET /api/apple/status` plus server-side config endpoints | Partial | Phone Systems is still a thin diagnostics view, far behind web settings breadth |
| Notifications | web ambient/alert surfaces | no real phone inbox surface | `GET /api/apple/notifications/pending` | Missing | Pull notifications exist server-side, but the phone app does not expose them as a first-class UI |
| Calendar sync | web calendar panels | no explicit phone UI | `POST /api/apple/calendar` | Missing | Ingest endpoint exists but no visible sync/status surface |
| Reminders sync | web task/reminder panels | no explicit phone UI | `POST /api/apple/reminders` | Missing | Same as calendar |
| Focus sync | web notification/focus behavior | no explicit phone UI | `POST /api/apple/focus` | Missing | Server can store focus state, but phone has no product UI around it |
| Sound alerts | web/security ambient flows | no explicit phone UI | `POST /api/apple/sound-alert` | Missing | Backend ingest exists only |
| Vision scan | web/vision security/workflow surface | no explicit phone UI | `POST /api/apple/vision/scan` | Missing | Backend ingest exists only |
| Now playing | web ambient media behavior | only indirect brief usage | `POST /api/apple/now-playing` | Partial | Server ingest exists; phone has no dedicated now-playing sync/status surface |

## Implementation Checklist

### Phase 1: Stop Split-Brain State

- [x] Home tab must reflect live JARVIS house state and not rely only on local HomeKit.
- [x] Brief tab must expose more live overview truth from JARVIS instead of acting as a reduced report.
- [x] Systems tab must surface production sync health for the major shared state domains.
- [ ] Phone-local caches for home, location, navigation preferences, and route state must hydrate from JARVIS.

### Phase 2: Deepen Existing Tabs

- [x] Expand Needs into a richer request workflow surface.
- [x] Bring Health closer to SAM / score / protocol parity.
- [ ] Add richer Chronicle context and pattern visibility.
- [ ] Add deeper Publishing workspace actions and launch pipeline visibility.
- [ ] Add richer Huddle / live-agent roster visibility.
- [ ] Continue Navigation HUD and route-state parity.

### Phase 3: Expose Existing Apple Endpoints

- [ ] Add notification inbox / pending notification surface.
- [ ] Add calendar sync visibility.
- [ ] Add reminders sync visibility.
- [ ] Add focus-mode sync visibility.
- [ ] Add sound-alert visibility.
- [ ] Add vision-scan visibility.
- [ ] Add dedicated now-playing sync/status visibility.

### Phase 4: Guardrails

- [ ] Add contract tests for all `/api/apple/*` payloads.
- [ ] Add Swift decode tests for all JarvisKit Apple models.
- [ ] Add a parity checklist to every live feature rollout: backend contract, web behavior, phone surface, device verification.

Verification command:

- `python3 scripts/verify_apple_contracts.py --ssh-host root@5.78.212.15 --container jarvis-family-jarvis-1`

## Priority Order

1. Home
2. Brief
3. Systems
4. Needs
5. Navigation polish and reliability
6. Health depth
7. Remaining ingestion surfaces

## Current Pass

Current implementation pass is focused on collapsing remaining split-brain state into the production-backed Apple contracts, starting with `Home`, `Brief`, `Systems`, `Needs`, and `Health`.
