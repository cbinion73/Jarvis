# Post-Epic 9 Slice 6: Small Live Runtime / Browser Acceptance Pass

## Live Acceptance Scope

This slice stayed intentionally narrow:

- verify the minimum local runtime path
- confirm health/liveness reachability
- attempt the repo-supported safe local launch mode
- stop immediately if runtime startup was blocked before a truthful browser pass could begin

Planned live route set, if the runtime had come up cleanly:

- `/health` for liveness
- one companion-facing or primary surface route
- one recorded-state review family route
- one truthful degraded-path route if safely reachable

## Runtime / Route Checks Run

1. `python3 -m jarvis status`
   - Result:
     - reported current integration posture
     - confirmed several degraded dependencies are already truthfully surfaced
     - did **not** prove the local web runtime was serving

2. Direct health check before startup:
   - `http://127.0.0.1:8787/health`
   - Result: connection refused

3. Standard local launch attempt:
   - `python3 -m jarvis serve --host 127.0.0.1 --port 8787`
   - Result:
     - no health route became reachable
     - no usable runtime proof obtained

4. Repo-supported safe smoke launch attempt:
   - `python3 -m jarvis serve --host 127.0.0.1 --port 8787 --read-only-smoke`
   - Result:
     - startup blocked before the browser pass could begin
     - exact observed output:
       - `psycopg2 not installed — CatalystDB unavailable`
       - `openai not installed — WorkIntelligence unavailable`
       - `Home intelligence imports failed: No module named 'psycopg2'`
       - `MCP server unavailable: No module named 'fastmcp'`

5. Follow-up live checks after smoke launch:
   - `curl -i --max-time 3 http://127.0.0.1:8787/health`
   - Result: connection failed, server never became reachable

## Defects Found and Repairs Made

- No product-surface defect was exercised because the local runtime never reached a live serving state.
- No code change was made in this slice.
- The blocking condition is environmental/runtime bootstrap state in the current checkout environment:
  - missing `fastmcp`
  - missing `psycopg2`

## Truth Guarantees Preserved

- No fake browser acceptance evidence is claimed.
- No fake live route success is claimed.
- No broadening into dependency recovery or environment repair was performed.
- The result is reported as a blocked live-proof attempt, not as a product failure beyond what was directly observed.

## Blockers / Residual Risks

- The local live runtime/browser pass is currently blocked by missing runtime dependencies in this environment.
- Because the server never reached a listening health route, this slice could not provide browser-driven evidence on top of the clean repo-truth test battery.
- Repo-truth acceptance from Slice 5 still stands; this slice only failed to add the extra live-browser proof layer.

## Recommendation

- Recommended next bounded step only if Architect Office wants live proof: restore the minimum local runtime dependencies needed for `python3 -m jarvis serve --read-only-smoke` to boot, then rerun this same tiny route set.
- If Architect Office is satisfied with repo-truth acceptance alone, this blocked live-proof slice can be treated as environment-blocked rather than product-regressed.
