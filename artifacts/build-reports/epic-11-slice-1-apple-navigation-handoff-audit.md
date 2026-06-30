# Epic 11 Slice 1: Apple Navigation Handoff Surface and Repo-Truth Audit

Date: 2026-06-28
Repo: `/Users/chris/Desktop/CODE/JARVIS`

## Scope Reviewed

This slice stayed inside Apple seam truth and handoff visibility.

It did not attempt:

- full iPhone navigation implementation
- live CarPlay simulator delivery
- live routing restoration
- broader Jarvis runtime or conversation changes

## Apple / CarPlay Surfaces Audited

Repo-truth surfaces reviewed:

- `JarvisApple/Package.swift`
- `JarvisApple/README.md`
- `JarvisApple/apps/ios/JarvisPhone/README.md`
- `JarvisApple/apps/ios/JarvisPhone/JarvisPhone.xcodeproj`
- `JarvisApple/apps/ios/JarvisPhone/project.yml`
- `JarvisApple/apps/ios/JarvisPhone/JarvisPhone/Info.plist`
- `JarvisApple/apps/ios/JarvisPhone/JarvisPhone/AppDelegate.swift`
- `JarvisApple/apps/ios/JarvisPhone/JarvisPhone/Scenes/NavigateView.swift`
- `JarvisApple/apps/ios/JarvisPhone/JarvisPhone/CarPlay/CarPlaySceneDelegate.swift`
- `JarvisApple/apps/ios/JarvisPhone/JarvisPhone/CarPlay/JarvisCarPlayController.swift`
- `JarvisApple/apps/ios/JarvisPhone/JarvisPhone/Intents/AskJarvisIntent.swift`
- `JarvisApple/Sources/JarvisKit/Models/NavigationModels.swift`
- `JarvisApple/Sources/JarvisKit/Models/CarPlayModels.swift`
- `JarvisApple/Tests/JarvisKitTests/CarPlayPresentationTests.swift`
- `jarvis/apple_api.py`
- `jarvis/nav_bridge.py`
- `docs/JARVIS-APPLE-HANDOFF-PACK.md`

## Repo-Truth Findings

What already exists and is real:

- A checked-in iOS Xcode project exists at `JarvisApple/apps/ios/JarvisPhone/JarvisPhone.xcodeproj`.
- Xcode targets already exist for:
  - `JarvisPhone`
  - `JarvisNotificationContent`
  - `JarvisWatch`
  - `JarvisWatchComplication`
  - `JarvisWidgetExtension`
- Shared Swift package products already exist for:
  - `JarvisKit`
  - `JarvisKitHealth`
  - `JarvisKitIntents`
  - `JarvisNotifications`
- The iPhone app already contains:
  - `NavigateView.swift`
  - `CarPlaySceneDelegate.swift`
  - `JarvisCarPlayController.swift`
  - App Intent entry points
  - notification wiring
  - checked-in entitlements
- CarPlay scene routing is explicitly present in both:
  - `AppDelegate.swift`
  - `Info.plist`
- The backend Apple seam already exposes Apple-facing navigation and CarPlay-supporting state through `jarvis/apple_api.py`.

What is real but bounded:

- `NavigateView.swift` is a real native navigation cockpit seam, not a placeholder.
- `JarvisCarPlayController.swift` is a real CarPlay template controller with route, stop, voice, publishing, and ops sections.
- `NavigationModels.swift` and `CarPlayModels.swift` define concrete shared transport/state models used by that seam.
- `docs/JARVIS-APPLE-HANDOFF-PACK.md` is a real handoff document and matches the existing code at a high level.

What is scaffolded or not yet proven live in this slice:

- live CarPlay simulator behavior
- real head-unit validation
- live routing/maps proof beyond the existing backend seam
- device-signing/provisioning proof
- entitlement proof on a live Apple runtime

## Truth / Visibility Repairs Made

- `JarvisApple/README.md` previously described the Apple lane as if app targets, entitlements, widgets, intents, and notifications were still future work.
  - Repaired to reflect current repo truth: the Xcode project and those seams already exist.
- `JarvisApple/apps/ios/JarvisPhone/README.md` previously said to create the iOS app target in Xcode.
  - Repaired to reflect current repo truth: the iOS target already exists and the next work is validation, signing, and runtime verification.

## Validation

### Safe inspection proof

Command:

```bash
xcodebuild -list -project JarvisApple/apps/ios/JarvisPhone/JarvisPhone.xcodeproj
```

Result:

- project resolves
- targets listed:
  - `JarvisNotificationContent`
  - `JarvisPhone`
  - `JarvisWatch`
  - `JarvisWatchComplication`
  - `JarvisWidgetExtension`
- schemes listed:
  - `JarvisKit`
  - `JarvisKitHealth`
  - `JarvisKitIntents`
  - `JarvisNotifications`
  - `JarvisPhone`
  - `JarvisWatch`

### Swift package proof

Command:

```bash
swift test
```

Working directory:

```bash
/Users/chris/Desktop/CODE/JARVIS/JarvisApple
```

Result:

- passed
- 10 tests passed in 4 suites

### Xcode compile proof

Command:

```bash
xcodebuild -project JarvisApple/apps/ios/JarvisPhone/JarvisPhone.xcodeproj -scheme JarvisKit -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO build
```

Result:

- build succeeded
- confirms the checked-in Xcode project can resolve and build the shared Apple navigation package for generic iOS without requiring simulator launch

### Python contract/regression checks

Command:

```bash
python3 -m pytest -q tests/test_apple_carplay_ops.py tests/test_apple_navigation_state_store.py tests/test_level9_apple_contract_truth.py
```

Result:

- `tests/test_apple_carplay_ops.py`: passed
- `tests/test_apple_navigation_state_store.py`: passed
- `tests/test_level9_apple_contract_truth.py`: one failure

Failure detail:

- the failing test expects:
  - `docs/jarvis_build_tracker.csv`
  - `docs/jarvis_master_tracker.csv`
- current repo truth only has archived copies under:
  - `docs/archive/2026-06-life-operating-officer-reset/`

This is a tracker-path truth issue, not a CarPlay/navigation compile failure.

## Open Defects / Blockers

1. CoreSimulator version mismatch on this Mac
   - Observed: Xcode reports CoreSimulator is out of date relative to the installed Xcode build.
   - Effect: simulator-backed iPhone/CarPlay runtime verification is blocked in this slice.
   - Next action: update the local macOS/Xcode simulator toolchain before claiming simulator proof.

2. No live CarPlay or head-unit proof in this slice
   - Observed: current proof is code, project, and compile level only.
   - Effect: CarPlay controller is inspectable and build-backed, but not runtime-proven on a simulator or vehicle.
   - Next action: use Xcode simulator / CarPlay runtime once the CoreSimulator blocker is cleared.

3. Navigation live-dependency truth remains bounded
   - Observed: backend navigation seam still depends on external maps/routing backing where applicable.
   - Effect: this slice cannot claim live route intelligence or full native maps proof.
   - Next action: keep truth boundaries explicit in any follow-on implementation slice.

4. Apple contract truth test references missing root tracker files
   - Observed: `tests/test_level9_apple_contract_truth.py` expects non-archived tracker CSVs that are not present in repo truth.
   - Effect: one governance-style test fails even though the Apple seam itself compiles.
   - Next action: repair or retire that tracker-path expectation in a separate bounded documentation/governance slice.

## Handoff Recommendation

The Apple navigation/CarPlay lane is real and handoff-ready for Xcode follow-on work at the code and compile level.

The next safe implementation step should start from:

- `NavigateView.swift`
- `CarPlaySceneDelegate.swift`
- `JarvisCarPlayController.swift`
- `NavigationModels.swift`
- `CarPlayModels.swift`
- `docs/JARVIS-APPLE-HANDOFF-PACK.md`

Do not restart this lane as greenfield.

Recommended status:

- Apple handoff surface is ready for Architect Office review
- full CarPlay runtime delivery is not yet proven
- simulator verification is presently blocked by local CoreSimulator drift
