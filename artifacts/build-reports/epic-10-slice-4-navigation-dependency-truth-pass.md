# Epic 10 Slice 4: Navigation Center and Dependency-Truth Pass

## Scope Reviewed
- `/navigation-center`
- Glass shell navigation module in `/`
- Navigation-facing APIs:
  - `/api/navigation/module`
  - `/api/navigation/module/route`
  - `/api/navigation/module/resume`
  - `/api/nav/maps-key`
  - `/api/nav/route`

## Navigation / Dependency Surfaces Covered
- Standalone navigation center route-preview form, route-history resume controls, and navigation truth copy.
- Glass navigation module route-preview button, shared-route hydration, runtime note, and degraded shell copy.
- Dependency-sensitive route wording tied to:
  - missing Google Maps runtime backing
  - unavailable detailed live routing
  - upstream certificate verification blocking route-intelligence hydration

## Consistency Findings
- The standalone `POST /api/nav/route` path was not degrading honestly. It threw a local argument error instead of returning a truthful unavailable/persisted-only result.
- The Glass navigation shell still used live-sounding default copy such as `Plan Route`, aggressive departure copy, and a `live and connected` runtime note before hydration.
- The standalone navigation center still used broader claims like `Stored routes can be resumed across desktop, iPhone, and CarPlay.` even though this runtime slice only proves shared local state plus desktop resume.
- The shell exposed raw upstream certificate text into visible route-window copy instead of translating it into plain dependency-truth language.

## Bounded Fixes Made
- Repaired `/api/nav/route` to:
  - persist shared navigation state through the existing route-history seam
  - return a truthful `persisted: true`, `available: false` response
  - explain that detailed live routing is unavailable in this runtime
- Tightened Glass navigation shell wording to:
  - default to `Navigation status is loading.`
  - relabel the primary route action to `Preview Route`
  - stop promising departure timing before live route data exists
  - keep `Start Navigation` hidden when only persisted route state exists
  - translate dependency failures into plain text instead of raw SSL/internal wording
- Tightened `/navigation-center` wording to:
  - describe route preview as persisted/shared-state first
  - stop claiming broad desktop/iPhone/CarPlay resume proof
  - explain that live route intelligence only appears when this runtime can actually provide it
  - translate degraded voice guidance into plain saved-context language

## Tests Run
- `python3 -m pytest -q tests/test_glass_theme_shell.py`
- `python3 -m pytest -q tests/test_command_center_service_surface.py`
- `python3 -m compileall jarvis/jarvis_theme_glass.py jarvis/render_pages.py jarvis/service.py`

## Runtime Checks
- `curl -sS http://127.0.0.1:8787/health`
- `POST /api/nav/route`
  - returned `200`
  - returned `{"ok":true,"available":false,"persisted":true,...}`
- Live browser check on `/navigation-center`
  - route note now says live route intelligence only loads when available
  - route-history note now stays inside shared navigation state truth
  - voice copy now admits saved-context-only guidance when live intelligence is unavailable
- Live browser check on Glass navigation module
  - primary button now reads `Preview Route`
  - degraded route action keeps `Start Navigation` hidden
  - shell copy now says the route was saved to shared state only
  - shell route window now says live route intelligence is blocked by upstream certificate verification in this runtime

## Open Defects Logged
1. `Navigation shell and /navigation-center live route intelligence`
   - Failure observed: live route intelligence still depends on an upstream request path that currently fails with certificate verification.
   - Likely cause: external route/weather dependency trust chain is not healthy in this runtime.
   - Recommended next action: handle certificate trust/dependency wiring in a later backend/dependency slice, not in Epic 10 UI truth work.
2. `Glass map rendering / route map surface`
   - Failure observed: live map rendering remains unavailable.
   - Likely cause: Google Maps runtime backing is not configured (`/api/nav/maps-key` returns unavailable).
   - Recommended next action: restore config/dependency in a dedicated maps capability slice if desired.
3. `Cross-device resume claims beyond desktop`
   - Failure observed: desktop runtime only proves shared local navigation state and desktop resume behavior.
   - Likely cause: iPhone/CarPlay resume proof is outside this runtime slice.
   - Recommended next action: verify or implement those surfaces in their own platform lane before any UI copy broadens again.

## Residual Risks
- The shared navigation state is real, but preview counters/history continue to accumulate from repeated local smoke use; that is expected and should not be treated as live-route proof.
- Existing non-navigation Postgres-backed surfaces still degrade elsewhere in the app; this slice intentionally did not broaden into those dependencies.
- `compileall` still emits pre-existing `SyntaxWarning` noise in `jarvis_theme_glass.py` unrelated to this navigation pass.

## Recommendation
`Epic 10 slice 4 ready for Architect Office review.`
