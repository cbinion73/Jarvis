## Apple Native Launch Flow Clean Package

This artifact captures a scope-disciplined packaging of the native launch-flow stabilization work against the `codex/orchestrator-backend-integration` baseline.

Patch:
- `artifacts/patches/apple-native-launch-flow-clean-package.patch`

What this package proves:
- the native launch-flow stabilization slice is captured as a clean branch patch against the orchestrator integration base
- the publish-safe version no longer depends on an untracked local secret source file
- The first-run launch-flow changes are not only valid in the dirty main checkout.

What is included:
- startup no longer eagerly requests notifications
- startup no longer eagerly requests Health sync
- startup no longer eagerly requests calendar/reminders sync
- calendar/reminders sync becomes explicit-only via Settings-triggered access flow
- speech authorization becomes refresh-first instead of prompt-on-init
- the watch delegate compile blocker is removed
- Cloudflare Access headers now come from tracked optional config values instead of a local-only Swift file

What was intentionally kept out of this slice:
- Siri voice-handoff support files that belong to the separate voice-launch lane
- sound-analysis suspension hooks that belong to the sound-analysis lane
- unrelated local admin/governance expansion in `SettingsView.swift`

Access configuration note:
- `JarvisApple/Sources/JarvisKit/JARVISAccessConfig.swift` is now tracked.
- It reads optional values from:
  - `JARVIS_CF_ACCESS_CLIENT_ID`
  - `JARVIS_CF_ACCESS_CLIENT_SECRET`
- Those values can come from `Info.plist` or environment variables.
- Empty values are allowed, so the app can still build cleanly without a local secret file.

Validation performed:
- live `JarvisPhone` simulator build succeeded after the config hardening change:

```bash
xcodebuild -project JarvisApple/apps/ios/JarvisPhone/JarvisPhone.xcodeproj \
  -scheme JarvisPhone \
  -destination 'platform=iOS Simulator,name=iPhone 17,OS=26.5' \
  build
```

Relationship to runtime proof:
- Separate from this clean-package validation, the dirty main checkout already proved the zero-state user outcome on a freshly erased simulator: JARVIS launches directly into the real command surface with no startup permission wall.
