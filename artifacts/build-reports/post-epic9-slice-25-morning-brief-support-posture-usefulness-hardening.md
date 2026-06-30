# Post-Epic 9 Slice 25: Morning Brief Support-Posture Usefulness Hardening

## A. Files Changed
- `jarvis/morning_brief_pipeline.py`
- `tests/test_morning_brief_pipeline.py`
- `tests/test_command_center_service_surface.py`

## B. Scope Reviewed
- Morning Brief `may_have_forgotten` support-posture wording in `jarvis/morning_brief_pipeline.py`
- Existing Obsidian/local-context truth label usage in the Morning Brief
- Existing `/briefing-center` readable surface coverage for brief sections

## C. Support-Posture Weakness Found
- The current Obsidian/local-context note was truthful but too generic: it only said notes were available for local retrieval.
- That wording underused the existing support seam because it did not help Chris understand what the support posture is practically good for next.
- It also did not explicitly restate that the brief had not actually opened or recalled any specific note, which is an important truth boundary for this seam.

## D. Bounded Repairs Made
- Kept the change inside the existing Morning Brief / `/briefing-center` seam only.
- Refined the Obsidian/local-context note in `What May Have Been Forgotten` so it now:
  - stays grounded in support posture only
  - becomes more practically useful when open-loop pressure or recorded catch-up exists
  - explicitly says the brief did not open or recall any specific note
- New behavior:
  - when follow-through pressure or recorded catch-up exists:
    - `Obsidian local context is available if you want to ground today's follow-through in prior notes. This brief did not open or recall any specific note.`
  - otherwise:
    - `Obsidian local context is available if you want prior notes for grounding. This brief did not open or recall any specific note.`
- Added one focused pipeline assertion proving the more useful follow-through wording appears in an open-loop-pressure case.
- Added one focused `/briefing-center` render proof showing the readable surface carries the same no-fake-recall posture.

## E. Truth Guarantees Preserved
- No new architecture.
- No fake memory, hidden retrieval, semantic recall, or note-reading claims.
- The brief still treats Obsidian as local support posture only.
- The new wording makes it more useful without implying any specific note was surfaced, remembered, or interpreted.

## F. Tests / Validation
- Compile check:
  - `python3 -m py_compile jarvis/morning_brief_pipeline.py tests/test_morning_brief_pipeline.py tests/test_command_center_service_surface.py`
  - Result: passed
- Focused pytest battery:
  - `python3 -m pytest -q tests/test_morning_brief_pipeline.py tests/test_command_center_service_surface.py -k "open_loop_pressure_stays_more_useful_without_claiming_thread_understanding or briefing_center_renders_obsidian_support_as_grounding_help_without_fake_recall or truth_labels_use_dynamic_support_posture or connected_but_empty_labels_are_plain"`
  - Result: `4 passed, 146 deselected in 0.48s`

## G. Blockers / Residual Risks
- This slice does not add actual note retrieval or note-specific grounding.
- If later work wants object-aware or note-aware grounding, that should remain a separate bounded lane with its own proof and truth constraints.
- Existing broader repo dirtiness remains out of scope and untouched.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-25-morning-brief-support-posture-usefulness-hardening.md`

## I. Recommendation
- Ready for Architect Office review: yes
