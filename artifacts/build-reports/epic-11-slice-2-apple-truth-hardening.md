# Epic 11 Slice 2: Apple Contract-Truth and Handoff Hardening

Date: 2026-06-28
Repo: `/Users/chris/Desktop/CODE/JARVIS`

## Scope

This slice stayed inside Apple truth hardening.

It did not:

- attempt CoreSimulator repair
- attempt CarPlay simulator runtime proof
- add native navigation features
- change runtime conversation logic

## Apple Truth Surfaces Hardened

- `/Users/chris/Desktop/CODE/JARVIS/tests/test_level9_apple_contract_truth.py`
- `/Users/chris/Desktop/CODE/JARVIS/docs/JARVIS-APPLE-HANDOFF-PACK.md`

## Findings

1. The Apple governance test still assumed tracker CSVs lived only at:
   - `docs/jarvis_build_tracker.csv`
   - `docs/jarvis_master_tracker.csv`

2. Current repo truth keeps the canonical tracker evidence under:
   - `docs/archive/2026-06-life-operating-officer-reset/jarvis_build_tracker.csv`
   - `docs/archive/2026-06-life-operating-officer-reset/jarvis_master_tracker.csv`

3. The handoff pack already described the Apple seam well, but it did not yet say plainly that:
   - generic iOS compile proof exists today
   - simulator-backed proof is still blocked on this Mac by CoreSimulator drift

## Repairs Made

### 1. Tracker-path truth hardening

`tests/test_level9_apple_contract_truth.py` now resolves tracker evidence from:

- current `docs/` location when present
- archived canonical location when the root tracker file is absent

This keeps the governance test aligned with current repo reality without inventing new tracker files.

### 2. Handoff-pack honesty hardening

`docs/JARVIS-APPLE-HANDOFF-PACK.md` now explicitly records:

- generic iOS `xcodebuild` proof for `JarvisKit`
- the current CoreSimulator/Xcode mismatch as a machine blocker
- that the Apple seam is compile-backed but not simulator-proven in this environment

## Open Defects / Blockers

1. CoreSimulator mismatch remains unresolved
   - still blocks simulator-backed iPhone/CarPlay runtime proof

2. No live CarPlay runtime proof in this slice
   - compile-backed and file-backed only

3. Full-app Xcode runtime proof was intentionally not attempted
   - out of scope for this hardening pass

## Validation

Commands run:

```bash
python3 -m pytest -q tests/test_level9_apple_contract_truth.py
```

Result:

- passed after tracker-path hardening

```bash
python3 -m pytest -q tests/test_apple_carplay_ops.py tests/test_apple_navigation_state_store.py tests/test_level9_apple_contract_truth.py
```

Result:

- all passed

```bash
xcodebuild -project JarvisApple/apps/ios/JarvisPhone/JarvisPhone.xcodeproj -scheme JarvisKit -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO build
```

Result:

- `BUILD SUCCEEDED`
- still emits the previously known CoreSimulator out-of-date warning before the generic iOS build completes

## Recommendation

The Apple truth lane is more consistent now:

- governance test matches repo-truth tracker locations
- handoff docs distinguish compile proof from blocked simulator proof

This leaves the Apple seam better prepared for later Xcode-focused implementation without overstating current runtime validation.
