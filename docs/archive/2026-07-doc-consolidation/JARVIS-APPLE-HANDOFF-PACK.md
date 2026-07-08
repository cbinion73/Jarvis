# JARVIS Apple Handoff Pack

This document is the repo-truth handoff pack for Apple-native JARVIS work.

It exists so Build Office, Architect Office, and native Xcode follow-through can work from the same concrete seams instead of rebuilding the Apple surface from scratch.

## Current Apple Surface

The current Apple-native implementation in repo truth lives under:

- `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/Package.swift`
- `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/apps/ios/JarvisPhone/JarvisPhone.xcodeproj`
- `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/apps/ios/JarvisPhone/JarvisPhone`
- `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/Sources/JarvisKit`

The package is intentionally package-first. Xcode should open `Package.swift` first and layer app-target finish work on top of the existing shared models and phone surfaces.

## Navigation And CarPlay Seams

The current Epic 11 starting seams already exist:

- iPhone navigation tab:
  - `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/apps/ios/JarvisPhone/JarvisPhone/Scenes/NavigateView.swift`
- CarPlay scene wiring:
  - `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/apps/ios/JarvisPhone/JarvisPhone/CarPlay/CarPlaySceneDelegate.swift`
- CarPlay template controller:
  - `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/apps/ios/JarvisPhone/JarvisPhone/CarPlay/JarvisCarPlayController.swift`
- Shared route, stop, and navigation-state models:
  - `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/Sources/JarvisKit/Models/NavigationModels.swift`
  - `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/Sources/JarvisKit/Models/CarPlayModels.swift`

These seams are real implementation seams, not placeholders.

## Image-to-Repo Mapping

The supplied navigation concept images map cleanly onto current repo truth:

- Turn-by-turn guidance:
  - `NavigateView.swift` active route + maneuver cards
- Upcoming maneuvers:
  - `NavigateView.swift` upcoming steps rail
- Live street or route-preview feel:
  - `NavigateView.swift` Look Around and route preview panels
- Destination view:
  - `NavigateView.swift` destination preview card
- Smart stops:
  - `NavigateView.swift` smart-stop sections and stop detail cards
  - `JarvisCarPlayController.swift` route-aware smart-stop sections
- Route overview:
  - `NavigateView.swift` route overview / route intel
  - `JarvisCarPlayController.swift` navigation command center and route detail sections
- Voice-first guidance:
  - `NavigateView.swift` voice navigation panel
  - `JarvisCarPlayController.swift` voice navigation consultation section

## Truth Boundaries

Native follow-through must preserve these boundaries:

- Do not imply live search unless the current path actually performed it.
- Do not imply live save/sync unless the current path actually persisted or synced.
- Do not imply external calendar, task, booking, vehicle, or Obsidian integration unless it is wired.
- If a route, stop, or weather surface is backed by local or current API data only, say that plainly.
- CarPlay should remain driver-focused and non-theatrical.

## What Xcode Work Is Still Expected

This repo is not yet the full end-state native app.

Xcode follow-through is still expected for:

- signing and provisioning validation
- Apple capability validation on a real runtime
- simulator/device verification once the local CoreSimulator blocker is cleared
- CarPlay entitlement and head-unit testing
- polish passes for layout, animation, and Apple-native interaction details

## Recommended Xcode Handoff Order

1. Open `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/Package.swift` in Xcode.
2. Confirm the package products resolve cleanly.
3. Open `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/apps/ios/JarvisPhone/JarvisPhone.xcodeproj` and verify the checked-in app targets resolve.
4. Verify `AppDelegate.swift` and `Info.plist` still point CarPlay to `CarPlaySceneDelegate`.
5. Run the package tests before simulator UI polish.
6. Finish phone navigation polish before expanding CarPlay beyond the current route/stop/voice consultation seam.

## Current Verification Surface

The current repo-truth proof for this lane is:

- Swift package tests in `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/Tests/JarvisKitTests`
- shared payload decoding tests for navigation and CarPlay models
- CarPlay presentation tests for destination choice building and route headline shaping
- generic iOS `xcodebuild` proof for the shared `JarvisKit` scheme without simulator launch

## Current Machine Blockers

The current repo and handoff pack must stay honest about what is still blocked on this Mac:

- CoreSimulator is out of date relative to the installed Xcode build, so simulator-backed iPhone and CarPlay runtime proof is not currently available here.
- This lane is code-backed and compile-backed, but not yet simulator-proven in this environment.
- Follow-on work should not claim live CarPlay runtime behavior until that local simulator/toolchain blocker is cleared.

## Practical Guidance For The Next Build Step

If Epic 11 is assigned for implementation, start from:

- truth-preserving route-state continuity
- navigation-specific regression coverage
- phone navigation verification, with simulator-specific work deferred until the CoreSimulator blocker is cleared
- bounded CarPlay template improvements that still fit the current controller seam

Do not start from a greenfield redesign.
