# Post-Epic 9 Slice 8: Minimum Optional-Integration Bootstrap for Bridge Imports

## Scope

- Repo target: `/Users/chris/Desktop/CODE/JARVIS`
- Goal: restore only the minimum package/import support needed for optional Gmail and Google Calendar bridge modules in the repo-supported runtime environment.
- Constraints honored:
  - no feature work
  - no credential or OAuth recovery
  - no live external service authorization work
  - no broad dependency modernization

## Import-Level Findings

1. The affected optional bridges were `jarvis.gmail_bridge` and `jarvis.gcal_bridge`.
2. Both modules already implement graceful degradation around Google imports.
3. The concrete import blocker was package absence in the repo venv, not product logic failure.
4. Before restoration:
   - `google-api-python-client` was missing
   - `google-auth-httplib2` was missing
   - `google-auth-oauthlib` was missing
5. `requirements.txt` already declared the needed package family, so no repo source change was required.

## Dependency / Import Restoration Steps Run

1. Verified the current degraded state:
   - `.venv/bin/python -m jarvis status`
   - observed import-level warnings:
     - `gmail_bridge: google-api-python-client not installed — Gmail will be unavailable`
     - `gcal_bridge: google-api-python-client not installed — Calendar will be unavailable`
2. Verified bridge import behavior from source:
   - `sed -n '1,260p' jarvis/gmail_bridge.py`
   - `sed -n '1,260p' jarvis/gcal_bridge.py`
3. Verified the package family was absent from the repo venv:
   - `.venv/bin/python -m pip show google-api-python-client google-auth-oauthlib google-auth-httplib2`
4. Restored the minimum package family into the repo venv:
   - `.venv/bin/python -m pip install 'google-api-python-client>=2.181.0' 'google-auth-httplib2>=0.2.0' 'google-auth-oauthlib>=1.2.2'`
5. Verified the installed package set:
   - `.venv/bin/python -m pip show google-api-python-client google-auth-httplib2 google-auth-oauthlib`
6. Verified bridge imports now succeed:
   - `.venv/bin/python - <<'PY' ...`
   - result:
     - `{'gmail_bridge_imports': True, 'gcal_bridge_imports': True}`
7. Verified the repo-supported runtime status after restoration:
   - `.venv/bin/python -m jarvis status`
8. Verified the smoke server still boots cleanly in the repo venv:
   - `.venv/bin/python -m jarvis serve --host 127.0.0.1 --port 8787 --read-only-smoke`
   - `curl -sS -i --max-time 3 http://127.0.0.1:8787/health`
   - result: `HTTP/1.1 200 OK`
9. Verified touched Python files still compile:
   - `.venv/bin/python -m py_compile jarvis/gmail_bridge.py jarvis/gcal_bridge.py jarvis/main.py`

## Runtime Status / Degraded-Path Result

### Before restoration

- Gmail degraded for missing import support.
- Google Calendar degraded for missing import support.

### After restoration

- The Gmail/Calendar import-level warnings disappeared from `jarvis status`.
- Remaining Google-side degradation is now truthful runtime state:
  - `google-workspace: blocked - No Google accounts are currently connected.`

That is the correct narrower failure reason for this slice: package support exists, but credentials/account connectivity are still out of scope and absent.

## Defects Found and Repairs Made

### Repaired

- Optional bridge import blocker in repo venv:
  - installed:
    - `google-api-python-client 2.198.0`
    - `google-auth-httplib2 0.4.0`
    - `google-auth-oauthlib 1.4.0`

### Not repaired because out of scope

- No Google accounts are currently connected.
- OpenAI API key is absent in this runtime.
- Local brain/Ollama is not ready.
- Other optional integrations remain degraded for their own runtime reasons.

## Truth Guarantees Preserved

- No fake Gmail or Calendar capability claim was introduced.
- No OAuth, credential, or live Google-service access was implied.
- The bridges now fail for the right reason when unavailable:
  - disconnected accounts / missing credentials
  - not missing Python packages
- The runtime smoke path stayed truthful and bootable after the package restoration.

## Blockers / Residual Risks

- Google account connection and authorization are still absent and intentionally untouched in this slice.
- This slice restored import/runtime support only for the Google bridge package family.
- Additional optional integrations may still depend on their own separate package or credential boundaries.

## Recommendation

- Treat this slice as a successful minimum optional-integration bootstrap for bridge imports in the repo-supported runtime environment.
- Architect Office can now consider the Gmail/Calendar bridge degradation narrowed from import failure to truthful account/credential absence.
- If a follow-on slice is desired, the next bounded target should be account/credential posture visibility, not broader dependency churn.
