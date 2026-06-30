# Post-Epic 9 Slice 44: Companion Capacity Follow-Up Continuity Hardening

## A. Files Changed
- `jarvis/companion_spine.py`
- `tests/test_companion_spine.py`
- `artifacts/build-reports/post-epic9-slice-44-companion-capacity-follow-up-continuity-hardening.md`

## B. Scope Reviewed
- The existing overloaded-week capacity follow-up seam only.
- Short natural second-turn replies after the concrete capacity fork:
  - `You do not need a better plan yet. You need one cut. What is actually immovable this week?`
- Nearby hedged, article, and mixed/uncertain selectors only.

## C. Defects Found
- Found one bounded continuity weakness: the capacity seam was still too literal about nearby natural selectors, so short hedged/article replies that clearly mapped to the existing calendar, priorities, conversation, or mixed capacity branches were falling out of the seam and dropping to the generic fallback.
- Confirmed failure examples before repair:
  - `probably the calendar`
  - `the schedule stuff`
  - `maybe priorities`
  - `probably the conversation`
  - `i do not know`
  - `all of it`

## D. Bounded Repairs Made
- Repaired only that one alias-literalness weakness in [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:666):
  - added nearby calendar aliases:
    - `probably the calendar`
    - `the schedule stuff`
  - added nearby priorities alias:
    - `maybe priorities`
  - added nearby conversation alias:
    - `probably the conversation`
  - added one mixed/uncertain branch for:
    - `all of it`
    - `i do not know`
    - `i don't know`
    - `not sure`
    - `probably all of it`
- Added focused regression coverage in [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:1052):
  - `test_capacity_follow_up_probably_calendar_alias_stays_inside_calendar_thread`
  - `test_capacity_follow_up_schedule_stuff_alias_stays_inside_calendar_thread`
  - `test_capacity_follow_up_maybe_priorities_alias_stays_inside_priorities_thread`
  - `test_capacity_follow_up_probably_conversation_alias_stays_inside_conversation_thread`
  - `test_capacity_follow_up_all_of_it_alias_stays_inside_cutting_thread`
  - `test_capacity_follow_up_i_do_not_know_alias_stays_inside_cutting_thread`

## E. Truth Guarantees Preserved
- Stayed inside the existing companion conversation seam only.
- No broader overloaded-week redesign, memory expansion, capability-copy work, therapist drift, or architecture work.
- No fake retrieval, execution, or autonomy claims were introduced.
- The new mixed/uncertain reply stays truthful and narrowing: it asks which concrete overload source is actually driving the week instead of pretending JARVIS already knows.

## F. Tests / Validation
- Compile proof:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
  - Result: passed
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "capacity_follow_up_calendar_stays_inside_cutting_thread or capacity_follow_up_fuzzy_priorities_stays_inside_cutting_thread or capacity_follow_up_conversation_stays_inside_cutting_thread or capacity_follow_up_schedule_alias_stays_inside_calendar_thread or capacity_follow_up_cut_alias_stays_inside_cutting_thread or capacity_follow_up_conversation_alias_stays_inside_conversation_thread or capacity_follow_up_probably_calendar_alias_stays_inside_calendar_thread or capacity_follow_up_schedule_stuff_alias_stays_inside_calendar_thread or capacity_follow_up_maybe_priorities_alias_stays_inside_priorities_thread or capacity_follow_up_probably_conversation_alias_stays_inside_conversation_thread or capacity_follow_up_all_of_it_alias_stays_inside_cutting_thread or capacity_follow_up_i_do_not_know_alias_stays_inside_cutting_thread"`
  - Result: `12 passed, 101 deselected in 0.17s`
- Compact in-process smoke proof:
  - `python3 - <<'PY'`
  - `from jarvis.companion_spine import generate_companion_fallback`
  - `packet = {'available_capabilities': ['ongoing conversation in this shell', 'conversation turn persistence'], 'conversation_excerpt': ("Chris: My week is a mess.\n" "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?")}`
  - `for prompt in ['probably the calendar', 'the schedule stuff', 'maybe priorities', 'probably the conversation', 'i do not know', 'all of it']:`
  - `    print(f'{prompt}: {generate_companion_fallback(prompt, packet)}')`
  - `PY`
  - Result highlights:
    - `probably the calendar` and `the schedule stuff` now stay inside the calendar branch
    - `maybe priorities` now stays inside the priorities branch
    - `probably the conversation` now stays inside the conversation branch
    - `i do not know` and `all of it` now stay inside the capacity seam and get a narrowing overload-source question
    - no tested alias in this bounded family falls back to the generic `short version` reply anymore

## G. Residual Risks
- This slice stayed tightly bounded to the capacity follow-up seam only.
- I did not broaden into general overloaded-week redesign, broader multi-turn conversation work, memory behavior, or capability-copy drift.
- Unrelated dirty-tree work was left untouched.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-44-companion-capacity-follow-up-continuity-hardening.md`

## I. Recommendation
- Ready for Architect Office review: yes
