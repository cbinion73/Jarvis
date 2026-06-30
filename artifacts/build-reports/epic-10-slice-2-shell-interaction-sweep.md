# Epic 10 Slice 2: Shared Shell Interaction Sweep and Stateful Control Repair

## Scope reviewed
- Shared Glass shell in the main repo runtime at `http://127.0.0.1:8787/`
- Stateful controls on the main module surfaces exercised in this slice:
  - Command
  - Daily Brief
  - Legacy
  - Navigate
  - shared Settings overlay

## Interactive surfaces covered
- Shell navigation buttons:
  - `Command`
  - `Legacy`
  - `Navigate`
- Daily Brief controls:
  - `Refresh Brief`
  - `Refresh Live Brief`
- Command controls:
  - `Refresh`
  - `Refresh Live`
- Legacy controls:
  - `Open Study` modal handoff
- Navigate controls:
  - `Refresh Navigation`
  - `Plan Route`
  - `⚙ Settings`
- Shared settings controls:
  - settings overlay open
  - settings pill switch to `accounts`

## Consistency findings
- Daily Brief refresh actions are live and update runtime-note text honestly.
- Command refresh actions remain non-throwing under degraded dependencies, but their visible note can remain unchanged when the same degraded upstream state is returned.
- Legacy `Open Study` is a real modal handoff, not a dead button.
- Navigate route preview is degrading honestly when Google Maps is unavailable.
- Two shell inconsistencies were confirmed:
  - the Command route card opened navigation but was labeled `Open full calendar`
  - the Navigate `⚙ Settings` button attempted a nonexistent `settings` view fallback instead of opening the shared settings overlay

## Bounded fixes made
1. Corrected the Command route-card label from `Open full calendar` to `Open full navigation` so the shell copy matches the actual view handoff.
2. Rewired the Navigate `⚙ Settings` fallback path to use the real shared `openSettings()` overlay seam instead of `switchView('settings')`.
3. Added regression coverage for both fixes in `tests/test_glass_theme_shell.py`.

## Truth-boundary findings
- Navigation route planning currently reports degraded state plainly instead of faking route intelligence:
  - `Google Maps is not configured in this runtime, so live map rendering is unavailable.`
  - `Navigation route preview is unavailable right now.`
- Daily Brief and Command continue to surface degraded Home/Postgres dependency failures plainly rather than implying success.
- No fake success behavior was introduced in this slice.

## Runtime evidence
- Daily Brief:
  - `Refresh Brief` moved the note into a loading state.
  - `Refresh Live Brief` completed with `Live brief refreshed for Chris.`
- Navigate:
  - `⚙ Settings` now opens the shared settings overlay.
  - switching the settings pill to `accounts` updates the active pill state.
- Command:
  - route-card link text now renders as `Open full navigation →`.

## Tests run
- `python3 -m pytest -q tests/test_glass_theme_shell.py`
  - result: `28 passed`
- `python3 -m compileall jarvis/jarvis_theme_glass.py`
  - result: passed

## Open defects / blocked paths
1. Surface: Navigate
   - Control: route preview / route planning
   - Failure observed: route summary and start-navigation affordance stay unavailable
   - Likely cause: live Google Maps configuration is missing in this runtime
   - Recommended next action: restore configured maps dependency, then re-run stateful navigation preview checks
2. Surface: Command and Daily Brief
   - Control: live refresh content depth
   - Failure observed: degraded Home/Postgres dependency keeps some refreshed content in an unavailable state
   - Likely cause: local Postgres-backed Home signals are unavailable
   - Recommended next action: restore backing dependency only if Epic 10 later expands into dependency recovery; otherwise keep as degraded-but-honest

## Residual risks
- Other module-local settings/deep-link affordances may still contain similar copy or fallback drift and will need later slices to sweep beyond the subset exercised here.
- Runtime checks in this slice were bounded to the live local shell and did not include external-service recovery.

## Recommendation
Epic 10 slice 2 is ready for Architect Office review as a bounded shared-shell interaction sweep with two confirmed repairs and an evidence-backed blocked-path list.
