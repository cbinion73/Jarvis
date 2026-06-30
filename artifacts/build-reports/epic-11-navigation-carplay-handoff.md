# Epic 11 Navigation and CarPlay Handoff

Date: 2026-06-27
Repo: `/Users/chris/Desktop/CODE/JARVIS`

## Scope

This bounded Build Office pass did not start a new architecture lane.

It did three specific things:

1. queued Epic 11 canonically after Epic 10
2. materialized the missing Apple handoff pack already referenced by the repo
3. tightened navigation and CarPlay presentation proof around the existing `JarvisApple` seam

## Repo-Truth Starting Point

The repo already contains a substantial Apple-native navigation surface:

- `NavigateView.swift` for the iPhone navigation cockpit
- `CarPlaySceneDelegate.swift` for CarPlay scene entry
- `JarvisCarPlayController.swift` for CarPlay templates and route/stop/voice sections
- shared navigation and CarPlay models in `JarvisKit`

This means Epic 11 is not a greenfield concept. It is a real existing seam that can be advanced and handed off into Xcode.

## Consistency Findings

- The canonical build plan did not yet include Epic 11.
- The Architect Office status file did not yet include Epic 11 queue status.
- `JarvisApple/README.md` referenced `docs/JARVIS-APPLE-HANDOFF-PACK.md`, but that file did not exist in repo truth.
- CarPlay presentation tests existed, but the proof surface did not yet cover:
  - current-location origin labeling
  - route-history destination inclusion without duplicates
  - route-detail truth when only partial route data exists

## Bounded Fixes Made

- Added Epic 11 to `/Users/chris/Desktop/CODE/JARVIS/docs/JARVIS-MASTER-BUILD-PLAN.md`
- Added Epic 11 queue status to `/Users/chris/Desktop/CODE/JARVIS/artifacts/architecture-reviews/architect-office-status.md`
- Updated `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/README.md` so the navigation/CarPlay seam is explicitly called out
- Created `/Users/chris/Desktop/CODE/JARVIS/docs/JARVIS-APPLE-HANDOFF-PACK.md`
- Extended `CarPlayPresentationTests.swift` with bounded navigation/CarPlay proof

## Tests Run

Command:

```bash
swift test
```

Working directory:

```bash
/Users/chris/Desktop/CODE/JARVIS/JarvisApple
```

Result:

- build completed successfully
- Swift Testing run passed
- 10 tests passed in 4 suites

## Truth Boundaries Preserved

- no fake live-search claims were added
- no fake save/sync claims were added
- no fake calendar/task/vehicle integration claims were added
- the handoff pack explicitly keeps CarPlay and navigation inside the current wired seams

## Residual Risks

- This pass did not run simulator UI verification; it is package-proof and handoff-proof only
- `NavigateView.swift` is large and likely needs a future native polish/refactor pass inside Xcode
- CarPlay behavior is still constrained to the current controller/template model and has not yet been exercised against a real CarPlay simulator or head unit in this pass

## Recommendation

Epic 11 is now properly queued after Epic 10, and the current Apple-native navigation/CarPlay lane is materially more handoff-ready.

The next safe execution step is an Epic 11 implementation assignment that starts from the existing `JarvisApple` navigation and CarPlay seam rather than replacing it.
