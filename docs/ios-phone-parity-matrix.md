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
| Brief / Overview | `jarvis/jarvis_theme_glass.py` overview loaders, briefing renderers, family bar, alert banner, mini-cards | `BriefingView.swift` | `GET /api/apple/briefing`, `GET /api/apple/app-state` | Partial | Alert-banner ranking, presence rollups, and control-plane posture now surface in Brief; remaining gaps are deeper catalyst/chronicle orchestration and any final web-to-phone polish |
| Needs / Approvals | `renderApprovals`, approval workflows | `NeedsView.swift` | `GET /api/apple/needs`, `POST /api/apple/approvals/{id}/approve` | Partial | Approve path exists; missing richer request context, alternate actions, and deeper workflow state |
| Health | `loadHealth`, SAM/score panels, overview health cards | `HealthView.swift` | `GET /api/apple/health/summary`, `POST /api/apple/health/log` | Partial | Good live summary, but not full SAM protocol / daily score / deeper web health modules |
| Weather | `loadWeatherWidget`, weather modal, route weather hooks | `WeatherView.swift` | `GET /api/apple/weather` | Partial | Core live weather works; still missing broader weather-module parity and some richer route/weather integrations |
| Home | `loadHomeDashboard`, home email/calendar/projects/tasks, home ops | `HomeView.swift` | `GET /api/apple/home/state`, `POST /api/apple/home/command`, `POST /api/apple/presence` | Partial | Live JARVIS house-state, staged commands, presence, and household context now surface on phone; remaining gaps are broader home-ops depth and web-only management tooling |
| Catalyst | `loadOverviewCatalyst`, catalyst workspace panels | `CatalystView.swift` | `GET /api/apple/catalyst` | Partial | Data exists, but phone lacks full action depth and overview integration |
| Chronicle | `loadChronicle`, context/pattern loaders | `ChronicleView.swift` | `GET /api/apple/chronicle`, `POST /api/apple/chronicle/capture` | Partial | Phone Chronicle now shows live formation context and pattern visibility from JARVIS; remaining gaps are broader chronicle tooling and deeper prayer/study workflows |
| Faith | `loadFaith`, faith roster/context | `FaithView.swift` | `GET /api/apple/faith` | Partial | Daily word works; missing deeper faith mode orchestration from web |
| Publish | `loadPublishing`, KDP/launch/pipeline panels | `PublishView.swift` | `GET /api/apple/publishing`, `POST /api/apple/publishing/reviews/*` | Partial | Phone Publish now exposes launch-control posture and pending review workflow from JARVIS; remaining gaps are broader KDP/platform-specific tools and deeper asset-generation controls |
| Huddle / Agents | `loadHuddle`, `loadAgentRoster`, `loadLiveAgents` | `HuddleView.swift` | `GET /api/apple/huddle` | Partial | Live roster depth now mirrors JARVIS more closely; remaining gaps are deeper live-agent controls and broader orchestration context |
| Navigate | `renderNavRoute`, `loadNavPOIs`, active route controls, POI toggles, parks radius slider | `NavigateView.swift` | `GET /api/apple/navigation/*` | Partial | Core HUD parity, route restore, stop recovery, and route-state reliability now mirror JARVIS more closely; remaining gaps are broader weather/aerial extras rather than core navigation behavior |
| Forge | forge/workshop panels | `ForgeView.swift` | `GET /api/apple/forge`, `POST /api/apple/forge/submit`, `POST /api/apple/forge/save` | Partial | Capture/upload exists; processing and broader workshop parity are still incomplete |
| Voice / Chat | chat + command flows, voice interactions | `VoiceView.swift` | `POST /api/apple/speak`, `GET /api/apple/voice/greeting` | Partial | Basic live voice bridge exists; missing broader chat/system command parity with web |
| Systems / Settings | `settingsNavTo(...)`, accounts, voice, location, family, devices, costs, Maps API status | `SettingsView.swift` | `GET /api/apple/status`, `GET /api/apple/app-state` plus server-side config endpoints | Partial | Systems now shows mirror state, workflow surfaces, posture, event-flow, and freshness truth; remaining gaps are broader web settings/admin breadth like accounts, family management, and cost/config panels |
| Notifications | web ambient/alert surfaces | `BriefingView.swift`, `SettingsView.swift`, `NotificationCenterView` | `GET /api/apple/app-state`, `GET /api/apple/notifications`, `GET /api/apple/events/recent`, `POST /api/apple/notifications/*` | Partial | Dedicated inbox/workflow surfaces, interruption posture, filters, search, and category actions now exist on web and phone; remaining gaps are broader ambient routing and any final closeout polish |
| Calendar sync | web calendar panels | `BriefingView.swift`, `SettingsView.swift` | `GET /api/apple/app-state`, `GET /api/apple/calendar/state`, `POST /api/apple/calendar/*` | Partial | Calendar now has mirror truth, workflow state, prep actions, route actions, and Systems visibility; remaining gaps are deeper event management breadth rather than missing shared-state workflow |
| Reminders sync | web task/reminder panels | `BriefingView.swift`, `SettingsView.swift` | `GET /api/apple/app-state`, `GET /api/apple/reminders/state`, `POST /api/apple/reminders/*` | Partial | Reminders now have mirror truth, grouped workflow state, complete/snooze actions, and Systems visibility; remaining gaps are broader task-management depth rather than missing shared-state workflow |
| Focus sync | web notification/focus behavior | `BriefingView.swift`, `SettingsView.swift` | `GET /api/apple/app-state`, `GET /api/apple/focus-state`, `POST /api/apple/focus` | Partial | Focus now has an explicit workflow surface, interruption posture, suppression rules, and Brief/System visibility; remaining gaps are deeper control breadth rather than missing shared-state surfacing |
| Sound alerts | web/security ambient flows | `BriefingView.swift`, `SettingsView.swift` | `GET /api/apple/app-state`, `GET /api/apple/sound-alerts`, `POST /api/apple/sound-alert`, `POST /api/apple/sound-alerts/{id}/resolve` | Partial | Sound alerts now have history, attention flags, and resolve workflow on web and phone; remaining gaps are broader downstream automation and policy depth |
| Vision scan | web/vision security/workflow surface | `BriefingView.swift`, `SettingsView.swift` | `GET /api/apple/app-state`, `GET /api/apple/vision/scans`, `POST /api/apple/vision/scan`, `POST /api/apple/vision/scans/{id}/resolve` | Partial | Vision scans now have history, recent contexts, attention flags, and resolve workflow on web and phone; remaining gaps are broader vision automation depth |
| Now playing | web ambient media behavior | `BriefingView.swift`, `SettingsView.swift` | `GET /api/apple/app-state`, `GET /api/apple/now-playing/state`, `POST /api/apple/now-playing` | Partial | Media now has dedicated state, recent history, and control-plane visibility; remaining gaps are richer playback control or broader ambient media orchestration |

## Implementation Checklist

### Phase 1: Stop Split-Brain State

- [x] Home tab must reflect live JARVIS house state and not rely only on local HomeKit.
- [x] Brief tab must expose more live overview truth from JARVIS instead of acting as a reduced report.
- [x] Systems tab must surface production sync health for the major shared state domains.
- [x] Phone-local caches for home, location, navigation preferences, and route state must hydrate from JARVIS.

### Phase 2: Deepen Existing Tabs

- [x] Expand Needs into a richer request workflow surface.
- [x] Bring Health closer to SAM / score / protocol parity.
- [x] Add richer Chronicle context and pattern visibility.
- [x] Add deeper Publishing workspace actions and launch pipeline visibility.
- [x] Add richer Huddle / live-agent roster visibility.
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
5. Navigation HUD and reliability polish
6. Health depth
7. Remaining ingestion surfaces

## Current Pass

Current implementation pass is focused on Phase 3 closeout: final morning-flow parity, control-plane truth, and proof-discipline cleanup while keeping the iPhone app tied to production-backed JARVIS truth.
