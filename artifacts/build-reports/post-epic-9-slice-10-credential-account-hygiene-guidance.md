# Post-Epic 9 Slice 10: Credential and Account-State Hygiene Guidance

## Guidance Scope

- Repo target: `/Users/chris/Desktop/CODE/JARVIS`
- Narrow surfaces reviewed:
  - `python -m jarvis status`
  - `python -m jarvis google-status`
  - runtime backing logic in `jarvis/runtime.py`
- Scope stayed bounded to messaging, status, and recovery guidance only.

## Visibility / Hygiene Gaps Found

1. The shared `google-workspace` status line now exposed the blocker category, but it still did not tell the operator:
   - the exact missing file path
   - the next recovery step
   - whether a `connected` registry record was stale versus usable
2. The Google-specific status surface exposed the blocker category and counts, but it still needed a more direct recovery-oriented hygiene layer:
   - `missing_requirement_path`
   - `next_recovery_step`
   - explicit stale-account note when registry posture and runtime posture disagree

## Bounded Repairs Made

- Extended the shared Google posture helper in [jarvis/runtime.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/runtime.py) to expose:
  - `stale_recorded_connected_account_count`
  - `missing_requirement_path`
  - `next_recovery_step`
  - `account_hygiene_note`
- Tightened the shared `google-workspace` status detail so it now includes the stale-record note when applicable.
- Tightened `google_workspace_status()` so the top-level `posture` block now includes recovery-oriented hygiene guidance.

### Current runtime-visible result

- `python -m jarvis status` now reports:
  - `google-workspace: blocked - Google bridge code is ready, but client credentials are missing. Recorded accounts: 2; registry-connected: 1; usable now: 0. 1 account record(s) are still marked connected in the registry but are not usable in this runtime.`
- `python -m jarvis google-status` now reports:
  - `posture.missing_requirement_path = "config/google_client_secret.json"`
  - `posture.next_recovery_step = "Add the Google OAuth client file at config/google_client_secret.json and rerun \`python -m jarvis google-status\`."`
  - `posture.account_hygiene_note = "1 account record(s) are still marked connected in the registry but are not usable in this runtime."`

## Truth Guarantees Preserved

- No fake Gmail, Calendar, or Google connection claims were introduced.
- No OAuth, credential recovery, or live external authorization was implemented.
- The surfaces remain explicit about:
  - bridge code readiness
  - missing client credentials
  - stale registry-connected records
  - next recovery action
- No account semantics were changed in this slice.

## Tests / Validation

- Focused regression tests:
  - `python3 -m pytest -q tests/test_optional_integration_posture_visibility.py tests/test_google_workspace_store.py`
  - result: `4 passed in 0.16s`
- Compile checks:
  - `.venv/bin/python -m py_compile jarvis/runtime.py tests/test_optional_integration_posture_visibility.py`
  - result: passed
- Runtime-visible proof:
  - `.venv/bin/python -m jarvis status`
  - `.venv/bin/python -m jarvis google-status`
  - result: both surfaces now expose the missing file, stale-record note, and next recovery step more clearly than before

## Blockers / Residual Risks

- `config/google_client_secret.json` is still absent in this runtime.
- Registry account status can still remain `connected` while runtime usability is blocked; this slice only makes that hygiene issue visible.
- No live token or account connection proof was attempted.

## Recommendation

- Treat this slice as a successful bounded operator-guidance hardening pass.
- The remaining disconnected Google posture is now easier to interpret and recover from without overstating capability.
- If a follow-on slice is needed, it should target account-state hygiene policy or operator tooling, not broader feature work.
