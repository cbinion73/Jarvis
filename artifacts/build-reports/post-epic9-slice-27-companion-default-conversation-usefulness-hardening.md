# Post-Epic 9 Slice 27: Companion Default-Conversation Usefulness Hardening

## A. Files Changed
- `jarvis/companion_spine.py`
- `tests/test_companion_spine.py`

## B. Scope Reviewed
- Default companion fallback and repair logic in `jarvis/companion_spine.py`
- Focused companion usefulness and truth-boundary coverage in `tests/test_companion_spine.py`
- In-process fallback outputs for ordinary live prompts

## C. Weakness Found
- The ordinary fallback for overloaded planning asks was softer than the seam's own existing practical doctrine.
- Specifically, direct fallback replies like `I need to get my week under control` stayed in a broad planning fork (`too much on the calendar / fuzzy priorities / avoiding`) instead of giving the sharper capacity pushback the same seam already uses when repairing weaker model replies.
- That made the default conversation path less decisive in exactly the sort of live-use moment where Chris most needs a practical cut, not a softer planning prompt.

## D. Bounded Repairs Made
- Kept the change inside the existing default companion conversation seam only.
- Reused the seam's existing `_capacity_pushback_reply(...)` doctrine for overloaded planning requests directly in `_generic_practical_fallback_reply(...)`.
- New behavior:
  - overloaded planning requests now default to:
    - `You do not need a better plan yet. You need one cut. What is actually immovable this week?`
- Left other conversation, decision, drafting, and planning branches unchanged.

## E. Truth Guarantees Preserved
- No new architecture.
- No fake memory, retrieval, autonomy, or execution claims.
- No therapist drift.
- The change improves decisiveness without claiming any action happened beyond the conversation itself.

## F. Tests / Validation
- Compile check:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
  - Result: passed
- Focused pytest battery:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "unmatched_practical_week_planning_request_gets_concrete_fork or overloaded_week_prompt_gets_decisive_capacity_pushback_in_fallback or overloaded_planning_reply_gets_capacity_pushback or overloaded_week_reply_that_avoids_cuts_gets_narrowing_move or good_concise_capacity_pushback_reply_passes_through_unchanged"`
  - Result: `5 passed, 56 deselected in 0.15s`
- Compact in-process smoke proof:
  - `python3 - <<'PY' ... generate_companion_fallback(...) ... PY`
  - Prompts:
    - `I need to get my week under control`
    - `I'm overwhelmed and behind this week`
  - Result for both:
    - `You do not need a better plan yet. You need one cut. What is actually immovable this week?`

## G. Blockers / Residual Risks
- This slice only hardens one overloaded-planning usefulness gap.
- It does not attempt a broad conversation-tone rewrite or wider branching redesign.
- Existing unrelated repo dirtiness remains out of scope and untouched.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-27-companion-default-conversation-usefulness-hardening.md`

## I. Recommendation
- Ready for Architect Office review: yes
