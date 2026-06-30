# Post-Epic 9 Slice 45: Companion Capacity Follow-Up Continuity Acceptance Pass

## A. Files Changed
- `jarvis/companion_spine.py`
- `tests/test_companion_spine.py`
- `artifacts/build-reports/post-epic9-slice-45-companion-capacity-follow-up-continuity-acceptance-pass.md`

## B. Scope Reviewed
- The existing overloaded-week capacity follow-up seam only.
- Short natural second-turn replies after the concrete capacity fork:
  - `You do not need a better plan yet. You need one cut. What is actually immovable this week?`
- Nearby hedged, article, mixed, and softened selectors only.

## C. Remaining Weakness Found
- Found exactly one remaining bounded continuity weakness during acceptance: the capacity seam still treated a nearby softened/article alias family too literally, so natural follow-ups around calendar, priorities, avoiding, conversation, and mixed overload still dropped to the generic fallback instead of staying inside the existing capacity fork.
- Confirmed failure examples before repair:
  - `maybe the calendar`
  - `probably schedule`
  - `the priorities stuff`
  - `probably priorities`
  - `the avoiding stuff`
  - `probably avoiding`
  - `maybe avoiding`
  - `the conversation stuff`
  - `maybe the conversation`
  - `kind of all of it`
  - `some of all of it`
  - `probably everything`
  - `not sure honestly`
  - `all of that`
  - `the schedule`
  - `the priorities`
  - `the avoidance`
  - `that whole conversation`

## D. Bounded Repair Made
- Repaired only that one softened/article alias family in [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:666):
  - mixed/uncertain branch now also handles:
    - `kind of all of it`
    - `some of all of it`
    - `probably everything`
    - `not sure honestly`
    - `all of that`
  - calendar branch now also handles:
    - `maybe the calendar`
    - `probably schedule`
    - `the schedule`
  - priorities branch now also handles:
    - `the priorities stuff`
    - `probably priorities`
    - `the priorities`
  - avoiding branch now also handles:
    - `the avoiding stuff`
    - `probably avoiding`
    - `maybe avoiding`
    - `the avoidance`
  - conversation branch now also handles:
    - `the conversation stuff`
    - `maybe the conversation`
    - `that whole conversation`
- Added focused regression coverage in [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:1130):
  - `test_capacity_follow_up_maybe_calendar_alias_stays_inside_calendar_thread`
  - `test_capacity_follow_up_priorities_stuff_alias_stays_inside_priorities_thread`
  - `test_capacity_follow_up_avoiding_stuff_alias_stays_inside_avoiding_thread`
  - `test_capacity_follow_up_maybe_conversation_alias_stays_inside_conversation_thread`
  - `test_capacity_follow_up_kind_of_all_of_it_alias_stays_inside_cutting_thread`
  - `test_capacity_follow_up_probably_everything_alias_stays_inside_cutting_thread`

## E. Truth Guarantees Preserved
- Stayed inside the existing companion conversation seam only.
- No broader overloaded-week redesign, memory expansion, capability-copy work, therapist drift, or architecture work.
- No fake retrieval, execution, or autonomy claims were introduced.
- The mixed reply remains a narrowing question about overload source rather than implying JARVIS already knows what must be cut.

## F. Tests / Validation
- Compile proof:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
  - Result: passed
- Focused pytest acceptance battery:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "capacity_follow_up_calendar_stays_inside_cutting_thread or capacity_follow_up_fuzzy_priorities_stays_inside_cutting_thread or capacity_follow_up_conversation_stays_inside_cutting_thread or capacity_follow_up_schedule_alias_stays_inside_calendar_thread or capacity_follow_up_cut_alias_stays_inside_cutting_thread or capacity_follow_up_conversation_alias_stays_inside_conversation_thread or capacity_follow_up_probably_calendar_alias_stays_inside_calendar_thread or capacity_follow_up_schedule_stuff_alias_stays_inside_calendar_thread or capacity_follow_up_maybe_priorities_alias_stays_inside_priorities_thread or capacity_follow_up_probably_conversation_alias_stays_inside_conversation_thread or capacity_follow_up_all_of_it_alias_stays_inside_cutting_thread or capacity_follow_up_i_do_not_know_alias_stays_inside_cutting_thread or capacity_follow_up_maybe_calendar_alias_stays_inside_calendar_thread or capacity_follow_up_priorities_stuff_alias_stays_inside_priorities_thread or capacity_follow_up_avoiding_stuff_alias_stays_inside_avoiding_thread or capacity_follow_up_maybe_conversation_alias_stays_inside_conversation_thread or capacity_follow_up_kind_of_all_of_it_alias_stays_inside_cutting_thread or capacity_follow_up_probably_everything_alias_stays_inside_cutting_thread"`
  - Result: `18 passed, 101 deselected in 0.24s`
- Compact in-process smoke proof:
  - `python3 - <<'PY'`
  - `from jarvis.companion_spine import generate_companion_fallback`
  - `packet = {'available_capabilities': ['ongoing conversation in this shell', 'conversation turn persistence'], 'conversation_excerpt': ("Chris: My week is a mess.\n" "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?")}`
  - `for prompt in ['maybe the calendar', 'probably schedule', 'the priorities stuff', 'probably priorities', 'the avoiding stuff', 'probably avoiding', 'maybe avoiding', 'the conversation stuff', 'maybe the conversation', 'kind of all of it', 'some of all of it', 'probably everything', 'not sure honestly', 'all of that', 'the schedule', 'the priorities', 'the avoidance', 'that whole conversation']:`
  - `    print(f'{prompt}: {generate_companion_fallback(prompt, packet)}')`
  - `PY`
  - Result highlights:
    - calendar aliases now stay inside the calendar branch
    - priorities aliases now stay inside the priorities branch
    - avoiding aliases now stay inside the avoiding branch
    - conversation aliases now stay inside the conversation branch
    - mixed/uncertain aliases now stay inside the capacity seam and get the overload-source narrowing reply
    - no tested alias in this acceptance family falls back to the generic `short version` reply anymore

## G. Residual Risks
- This acceptance pass stayed tightly bounded to the capacity follow-up seam only.
- I did not broaden into general overloaded-week redesign, broader multi-turn conversation work, memory behavior, or capability-copy drift.
- Unrelated dirty-tree work was left untouched.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-45-companion-capacity-follow-up-continuity-acceptance-pass.md`

## I. Recommendation
- Ready for Architect Office review: yes
