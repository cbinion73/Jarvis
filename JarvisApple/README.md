# JarvisApple

This folder is the native Apple scaffold for JARVIS.

It is intentionally package-first so Codex in Xcode can:

- open it immediately
- resolve shared models and contracts
- create app targets around a stable shared layer
- keep the Apple clients thin and contract-driven

## Current Scope

Implemented here:

- `JarvisKit`
- `JarvisKitHealth`
- `JarvisKitIntents`
- `JarvisNotifications`
- platform target folders for `JarvisPhone`, `JarvisMac`, `JarvisWatch`, and `JarvisTV`
- explicit health and feed API contract models

Still expected from Codex in Xcode:

- Xcode workspace
- app targets
- entitlements
- HealthKit capability wiring
- widgets
- App Intents
- notifications

## Open In Xcode

1. Open `JarvisApple/Package.swift` in Xcode.
2. Create a new workspace named `JarvisApple`.
3. Add app targets using the folders under `apps/`.
4. Link the shared package products into the app targets.

## First Native Build Order

1. `JarvisPhone`
2. HealthKit permission flow
3. mock health summary screen
4. widget
5. App Intent
6. notifications

## Source Of Truth

Read this before changing architecture:

- [JARVIS-APPLE-HANDOFF-PACK.md](../docs/JARVIS-APPLE-HANDOFF-PACK.md)
- [HEALTH-API-CONTRACT.md](HEALTH-API-CONTRACT.md)
