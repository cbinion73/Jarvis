# Live Feature Rollout Checklist

Use this checklist for every live JARVIS feature rollout that touches web, Apple, or shared-state behavior.

Verification commands:

```bash
python3 scripts/verify_live_rollout_checklist.py docs/live-feature-rollout-checklist.md
python3 scripts/test_verify_apple_contracts.py
swift test --package-path JarvisApple
```

## Backend Contract

- [ ] API shape is documented for any new or changed endpoint.
- [ ] Server response envelope matches the expected Apple/web client contract.
- [ ] `python3 scripts/test_verify_apple_contracts.py` passes if `/api/apple/*` behavior changed.
- [ ] Any new action endpoint has a sample request body and response fixture.

## Web Behavior

- [ ] Web JARVIS surface exposes the feature from live server truth.
- [ ] Empty, loading, stale, and error states were reviewed.
- [ ] Shared event / notification behavior is correct if the feature emits ambient state.
- [ ] Any operator-facing workflow is reachable without debug-only steps.

## Phone Surface

- [ ] JarvisPhone surface exists or was intentionally confirmed unnecessary.
- [ ] JarvisKit model decode path is covered by `swift test --package-path JarvisApple`.
- [ ] iPhone UI uses the live Apple contract layer and does not invent alternate truth.
- [ ] Any action button or workflow state has success, failure, and retry behavior.

## Intentional Permission Flow

- [ ] No sensitive permission prompt appears automatically at app launch unless explicitly intended for the feature.
- [ ] Every permission request has an explicit user-owned entry point in the UI.
- [ ] Settings / Systems surfaces expose any required opt-in or escalation path when the permission affects device behavior.
- [ ] Notification, calendar, reminders, health, microphone, and location flows were checked for both `notDetermined` and `denied` states.
- [ ] If a feature can operate in a reduced mode without permission, that fallback was confirmed in the real app.

## Device Verification

- [ ] Feature was exercised on a physical Apple surface when device behavior matters.
- [ ] Voice, notification, focus, camera, media, or location behavior was verified on-device if touched.
- [ ] Any platform permission or entitlement behavior was validated in the real app.
- [ ] Proof artifact was captured:
  - command output, screenshot, screen recording, or log path

## Rollout Notes

- Feature:
- Branch:
- Server / environment:
- Proof artifacts:
- Follow-up risks:
