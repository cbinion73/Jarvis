# Post-Epic 9 Slice 29: Companion Practical Follow-Up Continuity Hardening

## A. Files Changed
- `jarvis/companion_spine.py`
- `tests/test_companion_spine.py`

## B. Scope Reviewed
- Practical follow-up continuation logic in `jarvis/companion_spine.py`
- Existing follow-up coverage for planning, conversations, drafting, and decisions in `tests/test_companion_spine.py`
- In-process fallback outputs for short second-turn replies after practical forks

## C. Weakness Found
- After the first-turn overloaded-week fork was hardened to `one cut / what is actually immovable`, short second-turn replies like `calendar` or `fuzzy priorities` were not staying inside that same practical thread.
- Instead, those follow-ups fell back to the generic `Give me the short version, or tell me which part feels off` reply.
- That made the second turn less useful and less concrete than the first, which is exactly the continuity failure this slice was meant to catch.

## D. Bounded Repairs Made
- Kept the change inside the existing companion conversation seam only.
- Added one bounded follow-up continuation helper for the existing capacity-pushback branch:
  - `_capacity_follow_up_reply(...)`
- Wired it into `_fork_follow_up_continuation_reply(...)` after the existing decision / practical / drafting / retirement / conversation follow-up branches.
- New behavior:
  - `calendar` / `too much on the calendar`
    - `Okay. What on the calendar is truly fixed, and what are you treating as fixed because it feels easier than cutting it?`
  - `fuzzy priorities` / `priorities`
    - `Okay. What are the two things that actually matter this week, and what is loud but not important?`
  - `avoiding`
    - `Okay. What are you avoiding because it is hard, and what are you avoiding because it should not be on your plate at all?`

## E. Truth Guarantees Preserved
- No new architecture.
- No fake memory, hidden retrieval, autonomy, or execution claims.
- No therapist drift.
- The repair only improves second-turn continuity inside an already-existing practical conversation branch.

## F. Tests / Validation
- Compile check:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
  - Result: passed
- Focused pytest battery:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "capacity_follow_up_calendar_stays_inside_cutting_thread or capacity_follow_up_fuzzy_priorities_stays_inside_cutting_thread or practical_fork_follow_up_plan_gets_concrete_continuation or unmatched_practical_week_planning_request_gets_concrete_fork or overloaded_week_prompt_gets_decisive_capacity_pushback_in_fallback"`
  - Result: `5 passed, 58 deselected in 0.16s`
- Compact in-process smoke proof:
  - Prompt chain base:
    - `Chris: I need to get my week under control`
    - `Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?`
  - Follow-ups exercised:
    - `calendar`
    - `too much on the calendar`
    - `fuzzy priorities`
  - Results:
    - `calendar` -> `Okay. What on the calendar is truly fixed, and what are you treating as fixed because it feels easier than cutting it?`
    - `too much on the calendar` -> same truthful continuation
    - `fuzzy priorities` -> `Okay. What are the two things that actually matter this week, and what is loud but not important?`

## G. Blockers / Residual Risks
- This slice only hardens one concrete follow-up continuity gap in the overloaded-planning branch.
- It does not broaden into generalized multi-turn conversation redesign.
- Existing unrelated repo dirtiness remains out of scope and untouched.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-29-companion-practical-follow-up-continuity-hardening.md`

## I. Recommendation
- Ready for Architect Office review: yes
