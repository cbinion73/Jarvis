# Epic 10 Slice 1: Surface Inventory and First-Pass Repair

## Scope reviewed
- Repo truth in `/Users/chris/Desktop/CODE/JARVIS`
- Local runtime truth on `http://127.0.0.1:8787`
- Existing JARVIS web surfaces only
- No new product behavior added

## Surface inventory covered

### Primary routed pages checked
- `/`
- `/glass`
- `/command-center`
- `/chronicle-center`
- `/navigation-center`
- `/huddle-center`
- `/briefing-center`
- `/progress-center`
- `/recovery-center`
- `/mission-board`
- `/activity-center`
- `/agent-ops-center`
- `/settings-center`
- `/implementation-outline`
- `/approval-queue`
- `/supervision-snapshot`
- `/agents/hierarchy`
- `/dining-center`
- `/publish`
- `/google/connect`

### Additional HTML routes confirmed reachable
- `/nexus`
- `/storm-dashboard`
- `/health-desktop-storyboard`
- `/health-desktop`
- `/health-center`
- `/home-center`
- `/calendar-center`
- `/email-center`
- `/news-center`
- `/social-center`
- `/legacy-center`
- `/faith-center`
- `/agents-center`
- `/agents`
- `/intel-center`
- `/forge-center`
- `/forge`
- `/catalyst-center`
- `/foundry-center`
- `/foundry`
- `/workshop-center`
- `/workshop`
- `/vision-center`
- `/vision`
- `/journey-center`
- `/journey`
- `/needs-you-center`

### Representative controls and interfaces exercised
- Internal route links from `/` and `/command-center`
- Chronicle topbar/API links and refresh surface
- Chronicle form-backed APIs:
  - `/api/devotional-pause`
  - `/api/family-devotional`
  - `/api/chronicle-capture`
- Navigation form/API seam:
  - `/api/navigation/module`
  - `/api/navigation/module/route`
  - `/api/navigation/module/state`
  - `/api/navigation/module/resume`
- Home surface read APIs:
  - `/api/home/dashboard`
  - `/api/home/projects`
  - `/api/home/tasks`
  - `/api/home/tasks/overdue`
  - `/api/home/tasks/today`
  - `/api/home/email`
  - `/api/home/email/stats`
  - `/api/home/calendar`
  - `/api/home/calendar/upcoming`

## Consistency findings
- Most routed pages return HTTP 200 and render expected page titles.
- Several `*-center` routes currently resolve to the shared Glass shell HTML. That may be intentional route-to-shell multiplexing rather than a broken route by itself.
- The Chronicle page exposed a raw topbar link to `/api/devotional-pause`, which is a POST-only action path and therefore not a valid clickable proof link.
- The Home read-only API surface was internally inconsistent:
  - `/api/home/dashboard` already returned truthful degraded payloads when Postgres was unavailable.
  - sibling read endpoints like `/api/home/projects`, `/api/home/tasks`, `/api/home/email`, and `/api/home/calendar` threw 500s for the same missing dependency.

## Bounded fixes made

### 1. Honest degraded responses for Home read APIs
- Normalized read-only Home endpoints to return compact truthful unavailable payloads instead of 500s when the Home DB is unavailable or throws:
  - `/api/home/projects`
  - `/api/home/tasks`
  - `/api/home/tasks/overdue`
  - `/api/home/tasks/today`
  - `/api/home/email`
  - `/api/home/email/stats`
  - `/api/home/calendar`
  - `/api/home/calendar/upcoming`
  - `/api/home/calendar/today`
- Kept write/mutation routes unchanged.
- Preserved the existing truth posture:
  - `available: false`
  - explicit error text
  - empty list/object payloads instead of fake data

### 2. Fixed Chronicle proof-link wiring
- Replaced the Chronicle topbar link from POST-only `/api/devotional-pause` to GET-able `/api/chronicle/status`.
- This keeps the proof link inspectable from the UI without implying a devotional action was executed.

## Runtime evidence
- After restart, the following now return HTTP 200 with truthful degraded payloads instead of 500:
  - `/api/home/projects`
  - `/api/home/tasks`
  - `/api/home/tasks/overdue`
  - `/api/home/tasks/today`
  - `/api/home/email`
  - `/api/home/email/stats`
  - `/api/home/calendar`
  - `/api/home/calendar/upcoming`
- `/chronicle-center` now includes `/api/chronicle/status` and no longer includes `href="/api/devotional-pause"`.
- `/api/navigation/module/route` returns quickly and honestly in the current runtime with:
  - summary: `Route saved, but live route intelligence is temporarily unavailable in this runtime.`
  - warning showing upstream SSL certificate verification failure

## Open defects and blocked items

### 1. Home intelligence backend dependency still unavailable
- Surface: Home shell and home-backed module reads
- Failure observed: Postgres at `127.0.0.1:5432` is not available
- Likely cause: missing/stopped local Home DB dependency
- Recommended next action: restore the local Home DB or add a dedicated startup health gate for that dependency

### 2. Navigation live route intelligence blocked by upstream certificate/runtime dependency
- Surface: `/navigation-center` route preview
- Failure observed: route preview degrades with SSL certificate verification failure and no live route coordinates/stops
- Likely cause: upstream routing/weather bridge certificate or trust-chain problem
- Recommended next action: inspect the runtime path behind `runtime.storm_route_weather(...)` and its certificate/trust configuration

### 3. `google/connect` remains blocked by account/auth state
- Surface: `/google/connect`
- Failure observed: renders account-required state rather than a connected flow
- Likely cause: missing connected account/session
- Recommended next action: verify expected auth prerequisites and test with valid credentials

### 4. Full UI-action sweep is still first-pass, not exhaustive-by-branch
- Surface: shared Glass shell and deep route-specific buttons
- Failure observed: broad route/link coverage is complete, but not every hidden or state-dependent shell action has been manually clicked in this slice
- Likely cause: surface breadth and dependency gating
- Recommended next action: continue with Epic 10 slice 2 as a focused interaction-by-interaction pass on the Glass shell and the remaining stateful modules

## Tests and checks run
- `python3 -m pytest -q tests/test_command_center_service_surface.py -k "home_dashboard_returns_honest_unavailable_payload_when_db_errors or home_read_routes_return_honest_unavailable_payloads_when_db_errors or chronicle_center_links_to_status_api_instead_of_post_only_devotional_api"`
- `python3 -m py_compile jarvis/service.py jarvis/render_pages.py tests/test_command_center_service_surface.py`
- Local runtime checks against `http://127.0.0.1:8787`

## Results
- Focused tests passed
- Compile checks passed
- Local runtime checks confirmed the repaired surfaces now behave truthfully

## Residual risks
- The Home lane still depends on external/local Postgres availability for full functionality.
- Navigation route intelligence is still partially blocked by upstream SSL/runtime conditions.
- Shared-shell routes need a deeper interaction pass to confirm every stateful button path under real dependencies.

## Recommendation
`Epic 10 slice 1 can move forward to Architect Office review.`

