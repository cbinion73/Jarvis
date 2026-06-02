## Apple Native Launch Flow Clean Package

This artifact captures a scope-disciplined packaging of the native launch-flow stabilization work against the `codex/orchestrator-backend-integration` baseline.

Patch:
- `artifacts/patches/apple-native-launch-flow-clean-package.patch`

What this package proves:
- `JarvisPhone` can be built from a clean helper checkout with the launch-flow stabilization slice applied.
- The first-run launch-flow changes are not only valid in the dirty main checkout.

What is included:
- startup no longer eagerly requests notifications
- startup no longer eagerly requests Health sync
- startup no longer eagerly requests calendar/reminders sync
- calendar/reminders sync becomes explicit-only via Settings-triggered access flow
- speech authorization becomes refresh-first instead of prompt-on-init
- the watch delegate compile blocker is removed

What was intentionally kept out of the clean package:
- Siri voice-handoff support files that belong to the separate voice-launch lane
- sound-analysis suspension hooks that belong to the sound-analysis lane
- unrelated local admin/governance expansion in `SettingsView.swift`

Secure dependency note:
- The helper package build required the existing local `JarvisApple/Sources/JarvisKit/CloudflareConfig.swift`.
- That file was intentionally excluded from the patch artifact because it contains environment secrets and should not be published through a generic patch path.

Validation performed:
- clean helper checkout created from the remote integration branch tarball
- launch-flow slice applied selectively
- helper checkout build succeeded:

```bash
xcodebuild -project JarvisApple/apps/ios/JarvisPhone/JarvisPhone.xcodeproj \
  -scheme JarvisPhone \
  -destination 'platform=iOS Simulator,name=iPhone 17,OS=26.5' \
  build
```

Relationship to runtime proof:
- Separate from this clean-package validation, the dirty main checkout already proved the zero-state user outcome on a freshly erased simulator: JARVIS launches directly into the real command surface with no startup permission wall.
