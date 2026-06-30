# Post-Epic 9 Slice 7: Minimum Runtime Bootstrap Restoration for Read-Only Smoke

## Scope

- Repo target: `/Users/chris/Desktop/CODE/JARVIS`
- Goal: restore only the minimum local runtime dependencies needed for the repo-supported read-only smoke path:
  - `python3 -m jarvis serve --host 127.0.0.1 --port 8787 --read-only-smoke`
- Constraint honored: no feature work, no broad environment cleanup, no optional integration restoration.

## Bootstrap Findings

1. The earlier blocked smoke attempt was not a broad product failure.
2. The repo already contains a local virtual environment at `.venv` with most required runtime packages present.
3. The repo-supported runtime path was viable through `.venv/bin/python`, while the earlier system `python3` path was missing multiple dependencies and was not the right bootstrap target for this slice.
4. `psycopg2-binary` was already present in the repo venv and did not require restoration.
5. The remaining minimum missing dependency for the smoke boot path was `fastmcp`.

## Dependency / Runtime Restoration Steps Run

1. Verified repo setup path and dependency declarations:
   - `sed -n '1,240p' README.md`
   - `sed -n '1,260p' requirements.txt`
   - `sed -n '1,260p' scripts/setup.sh`
2. Verified repo venv package state:
   - `.venv/bin/python -V`
   - `.venv/bin/python -m pip show fastmcp openai fastapi uvicorn`
   - `.venv/bin/python -m pip show psycopg2-binary`
3. Verified runtime status from the repo venv:
   - `.venv/bin/python -m jarvis status`
4. Reproduced the smoke boot blocker from the repo venv before repair:
   - `.venv/bin/python -m jarvis serve --host 127.0.0.1 --port 8787 --read-only-smoke`
   - observed blocker:
     - `MCP server unavailable: No module named 'fastmcp'`
5. Restored the minimum missing dependency:
   - `.venv/bin/python -m pip install 'fastmcp>=2.0.0'`
   - installed version:
     - `fastmcp 3.4.2`
6. Retried the smoke boot path from the repo venv:
   - `.venv/bin/python -m jarvis serve --host 127.0.0.1 --port 8787 --read-only-smoke`
   - result:
     - server stayed up
     - reachable health route confirmed

## Live Acceptance Retry Result

The smoke server booted far enough for the tiny live acceptance route set to run.

### Successful live checks

- Health route:
  - `curl -sS -i --max-time 3 http://127.0.0.1:8787/health`
  - result: `HTTP/1.1 200 OK`
  - proof highlights:
    - `"ok": true`
    - `"service": "fastapi"`
    - obsidian probe remained local/truthful

- Root shell route:
  - `curl -sS -i --max-time 5 http://127.0.0.1:8787/ | sed -n '1,30p'`
  - result: `HTTP/1.1 200 OK`
  - proof highlight:
    - `<title>JARVIS · Glass</title>`

- Companion-facing response path:
  - `curl -sS -i --max-time 20 -X POST http://127.0.0.1:8787/api/respond -H 'Content-Type: application/json' -d '{"actor":"Chris","room":"office","request":"Hey Jarvis"}'`
  - result: `HTTP/1.1 200 OK`
  - proof highlights:
    - returned a fallback companion reply
    - `action_truth.execution_trace` was empty
    - `action_truth.reasoning_only` was `true`
  - truth result:
    - the runtime did not overclaim tool or background execution on a plain response path

- Recorded-state review family path:
  - `curl -sS -i --max-time 20 http://127.0.0.1:8787/mission-board/research-tasks | sed -n '1,80p'`
  - result: `HTTP/1.1 200 OK`
  - proof highlight:
    - `<title>Research Task Queue</title>`

- Truthful degraded path:
  - `curl -sS -i --max-time 20 http://127.0.0.1:8787/api/navigation/module | sed -n '1,140p'`
  - result: `HTTP/1.1 200 OK`
  - proof highlights:
    - `"available": true`
    - route preview summary:
      - `Route saved, but live route intelligence is temporarily unavailable in this runtime.`
    - warning captured the actual SSL certificate verification failure
  - truth result:
    - the navigation module degraded honestly instead of implying live route intelligence success

## Defects Found and Repairs Made

### Repaired

- Repo smoke bootstrap blocker:
  - defect: `fastmcp` was missing from the repo venv used for the supported smoke path
  - repair: installed `fastmcp` into `.venv`

### Clarified but not repaired because out of slice

- Gmail bridge degraded:
  - `google-api-python-client` not installed
- Calendar bridge degraded:
  - `google-api-python-client` not installed
- OpenAI API unavailable:
  - `OPENAI_API_KEY` missing from the current runtime environment
- Local brain unavailable:
  - Ollama/qwen not ready
- Navigation live route intelligence degraded:
  - SSL certificate verification failure in the upstream dependency path

These did not block the repo-supported read-only smoke route set for this slice.

## Truth Guarantees Preserved

- No fake bootstrap success was claimed before the health route became reachable.
- No fake `psycopg2` repair was claimed; it was already present in the repo venv.
- No optional integrations were restored just to make the smoke pass look healthier.
- Companion response proof remained reasoning-only and inspectable.
- Navigation remained explicit about saved-route continuity versus unavailable live route intelligence.

## Residual Risks

- The smoke pass is now bootable, but it still depends on the repo venv, not the bare system `python3` environment.
- Gmail/Calendar/OpenAI/local-brain integrations remain unavailable in this environment and were intentionally not restored here.
- Live navigation intelligence still depends on an external SSL/certificate path outside this bounded bootstrap slice.

## Recommendation

- The minimum runtime bootstrap restoration objective is met for the repo-supported read-only smoke path.
- Architect Office can treat the live-proof lane as no longer blocked by the previously observed missing-package failure.
- If a follow-on slice is needed, it should target only the next highest-value environment blocker rather than broad runtime modernization.
