# JarvisApple

This folder is the native Apple package and app-target seam for JARVIS.

It is intentionally package-first so Codex in Xcode can:

- open it immediately
- resolve shared models and contracts
- layer app-target work on top of a stable shared layer
- keep the Apple clients thin and contract-driven

## Current Scope

Implemented here:

- `JarvisKit`
- `JarvisKitHealth`
- `JarvisKitIntents`
- `JarvisNotifications`
- a checked-in iOS Xcode project at `apps/ios/JarvisPhone/JarvisPhone.xcodeproj`
- platform target folders for `JarvisPhone`, `JarvisMac`, `JarvisWatch`, and `JarvisTV`
- explicit health and feed API contract models
- an Apple-native navigation seam for `JarvisPhone`
- a CarPlay scene + controller seam for route, stop, and voice-navigation surfaces
- checked-in entitlements, App Intents, widgets, notifications, and watch-extension sources for the iOS lane

Still expected from Codex in Xcode:

- simulator and device verification
- signing and provisioning validation
- HealthKit, CarPlay, Siri, and notification entitlement verification on a real Apple runtime
- native UI polish and interaction refinement
- live routing/maps dependency validation where external services are required

## Open In Xcode

1. Open `JarvisApple/Package.swift` in Xcode.
2. Open `apps/ios/JarvisPhone/JarvisPhone.xcodeproj` for the existing iPhone, widget, notification, and watch targets.
3. Confirm the shared package products resolve cleanly into the checked-in targets.
4. Use the handoff pack before changing the navigation or CarPlay seam.

## First Native Build Order

1. `JarvisPhone`
2. HealthKit permission flow
3. mock health summary screen
4. widget
5. App Intent
6. notifications

## Navigation And CarPlay

The current repo truth already includes:

- `apps/ios/JarvisPhone/JarvisPhone/Scenes/NavigateView.swift`
- `apps/ios/JarvisPhone/JarvisPhone/CarPlay/CarPlaySceneDelegate.swift`
- `apps/ios/JarvisPhone/JarvisPhone/CarPlay/JarvisCarPlayController.swift`
- shared route, stop, and navigation-state models in `Sources/JarvisKit/Models/`

Use the handoff pack below before changing that lane so phone navigation, CarPlay, and truth boundaries stay aligned.

## Source Of Truth

Read this before changing architecture:

- [JARVIS-APPLE-HANDOFF-PACK.md](../docs/JARVIS-APPLE-HANDOFF-PACK.md)
- [HEALTH-API-CONTRACT.md](HEALTH-API-CONTRACT.md)
