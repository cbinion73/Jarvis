# Post-Epic 9 Slice 9: Account / Credential Posture Visibility for Optional Integrations

## Scope Reviewed

- Repo target: `/Users/chris/Desktop/CODE/JARVIS`
- Visibility surfaces reviewed:
  - `python -m jarvis status`
  - `python -m jarvis google-status`
  - runtime `/api/status` and `/api/google/status` backing seams
- Narrow focus:
  - Gmail / Google Calendar optional-integration posture only
  - no OAuth, no account connection flow work, no live upstream authorization

## Visibility Gaps Found

1. The shared runtime status line for `google-workspace` was too vague.
   - Before this slice it reported:
     - `No Google accounts are currently connected.`
   - That hid whether:
     - Google bridge libraries were installed
     - client credentials were present
     - account records already existed in the repo
2. The Google-specific status surface had the raw details, but not a compact top-level posture summary.
   - An operator had to infer the real blocker by reading nested `default` and `accounts` structures.
3. In the current repo truth there is a meaningful distinction between:
   - recorded Google accounts in the account registry
   - usable Google connections in the current runtime
   - credential-level blockers such as missing `config/google_client_secret.json`
   - import-level blockers
   - token/account-connection blockers

## Bounded Repairs Made

### Runtime posture helper

- Added a bounded Google Workspace posture summarizer in [jarvis/runtime.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/runtime.py).
- It now computes and exposes:
  - `libraries_ready`
  - `client_credentials_present`
  - `token_present`
  - `recorded_account_count`
  - `recorded_connected_account_count`
  - `usable_connected_account_count`
  - `blocking_layer`
  - `detail`

### Shared status improvement

- Updated `runtime.status()` so the shared `google-workspace` line now distinguishes:
  - import-level blocker
  - client-credential blocker
  - token/account-connection blocker
  - usable connection
- In the current environment it now reports:
  - `Google bridge code is ready, but client credentials are missing. Recorded accounts: 2; registry-connected: 1; usable now: 0.`

### Google-specific status improvement

- Updated `runtime.google_workspace_status()` so it now returns a top-level `posture` block in addition to the existing `default` and `accounts` data.
- This makes the current blocker inspectable without digging through nested fields.

## Truth Guarantees Preserved

- No fake Gmail or Google Calendar capability was implied.
- The surfaces now distinguish:
  - bridge code/import readiness
  - client-credential posture
  - recorded account posture
  - usable runtime connection posture
- No OAuth, credential recovery, or live account connection was implemented or implied.
- The lane remains degraded truthfully when disconnected.

## Tests / Validation

- Compile checks:
  - `.venv/bin/python -m py_compile jarvis/runtime.py tests/test_optional_integration_posture_visibility.py`
  - result: passed
- Focused regression tests:
  - `python3 -m pytest -q tests/test_optional_integration_posture_visibility.py tests/test_google_workspace_store.py`
  - result: `4 passed in 0.16s`
- Live runtime-visible proof:
  - `.venv/bin/python -m jarvis status`
  - result included:
    - `google-workspace: blocked - Google bridge code is ready, but client credentials are missing. Recorded accounts: 2; registry-connected: 1; usable now: 0.`
  - `.venv/bin/python -m jarvis google-status`
  - result included:
    - top-level `posture.blocking_layer: "client_credentials"`
    - `posture.recorded_account_count: 2`
    - `posture.recorded_connected_account_count: 1`
    - `posture.usable_connected_account_count: 0`

## Blockers / Residual Risks

- `config/google_client_secret.json` is still absent in this runtime.
- Recorded Google account metadata can still say `connected` at the account-registry level even when the runtime is unusable; this slice made that mismatch visible rather than changing account state semantics.
- No live Google authorization or mailbox/calendar validation was attempted.

## Recommendation

- Treat this slice as a successful bounded visibility hardening pass.
- The remaining Google/Gmail/Calendar degradation is now more plainly attributable to client-credential posture rather than vague unavailability.
- If a follow-on slice is desired, the next bounded move should target credential/account-state hygiene or operator guidance, not broader feature work.
