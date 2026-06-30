# Epic 5 Slice 4: Explicit Degraded-Mode Honesty

## Scope Reviewed

- `/Users/chris/Desktop/CODE/JARVIS/jarvis/openai_tasks.py`
- `/Users/chris/Desktop/CODE/JARVIS/jarvis/persona.py`
- `/Users/chris/Desktop/CODE/JARVIS/jarvis/runtime.py`
- `/Users/chris/Desktop/CODE/JARVIS/tests/test_degraded_mode_honesty.py`
- Existing truth-preservation tests:
  - `/Users/chris/Desktop/CODE/JARVIS/tests/test_openai_tasks_search_truth.py`
  - `/Users/chris/Desktop/CODE/JARVIS/tests/test_save_open_truth_proof.py`
  - `/Users/chris/Desktop/CODE/JARVIS/tests/test_creation_truth_proof.py`
  - `/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py`

## Degraded-Mode Truth Findings

- Repo truth already had good slice-level rules against fake search, fake save, and fake open claims, but the manual AI fallback copy still risked sounding smoother than the failure state really was.
- The main gap was not raw capability plumbing; it was wording consistency when an AI path was unavailable, partially wired, or generally degraded.
- Existing fallback copy usually named the error, but it did not always say plainly whether the path was unavailable versus only partially wired, nor what reduced help still remained.

## Bounded Fixes Made

- Added a narrow degraded-mode wording helper in `jarvis/openai_tasks.py`.
- Updated manual response, prompt, and image fallbacks to say plainly whether the path is:
  - unavailable
  - partially wired
  - blocked or degraded
- Kept the fallback useful by explicitly saying what JARVIS can still do in reduced mode without implying success.
- Added focused regression tests covering:
  - plain unavailable wording
  - plain partially wired wording
  - plain degraded wording
  - no fake implied search or successful live completion on degraded paths

## Tests Run

- `python3 -m py_compile jarvis/openai_tasks.py tests/test_degraded_mode_honesty.py`
- `python3 -m pytest -q tests/test_degraded_mode_honesty.py tests/test_openai_tasks_search_truth.py tests/test_save_open_truth_proof.py tests/test_creation_truth_proof.py tests/test_companion_spine.py`

## Results

- `py_compile`: passed
- `pytest`: `72 passed in 0.26s`

## Residual Risks

- This slice improves degraded-path honesty in the manual AI fallback seam only; it does not yet normalize every independent UI/store error string across the whole repo.
- Future tool-specific degraded paths should reuse the same unavailable / partially wired / reduced-help posture instead of inventing one-off language.

## Recommendation

`Epic 5 Slice 4 ready for Architect Office review if bounded tests stay green`
