# Post-Epic 9 Slice 46: Companion Capacity Follow-Up Continuity Closeout Pass

## A. Files Changed
- `jarvis/companion_spine.py`
- `tests/test_companion_spine.py`
- `artifacts/build-reports/post-epic9-slice-46-companion-capacity-follow-up-continuity-closeout-pass.md`

## B. Scope Reviewed
- The existing overloaded-week capacity follow-up seam only.
- Short natural second-turn replies after the concrete capacity fork:
  - `You do not need a better plan yet. You need one cut. What is actually immovable this week?`
- Closeout focus only:
  - nearby softened/article branch selectors
  - nearby compact mixed or multi-branch ambiguity replies

## C. Final Weakness Found
- Found one final bounded continuity weakness in the capacity seam: nearby softened/article selectors and compact mixed ambiguity replies were still treated too literally, so natural follow-ups that clearly referred back to the existing calendar, priorities, avoiding, conversation, or mixed branches still fell out of the seam and dropped to the generic fallback.
- Confirmed failure examples before the closeout repair:
  - softened/article branch selectors:
    - `maybe the calendar`
    - `probably schedule`
    - `the priorities stuff`
    - `probably priorities`
    - `the avoiding stuff`
    - `probably avoiding`
    - `maybe avoiding`
    - `the conversation stuff`
    - `maybe the conversation`
    - `the schedule`
    - `the priorities`
    - `the avoidance`
    - `that whole conversation`
  - compact mixed / multi-branch ambiguity replies:
    - `both`
    - `either`
    - `kind of both`
    - `some of both`
    - `all of those`
    - `all of the above`
    - `all of them`
    - `all of these`
    - `honestly all of them`
    - `more than one`
    - `mixed`
    - `the calendar and priorities`
    - `calendar and priorities`
    - `conversation and priorities`
    - `avoiding and the calendar`
    - `the calendar or priorities`

## D. Bounded Repair Made
- Repaired only that one final capacity ambiguity family in [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:666):
  - softened/article calendar aliases now stay inside the calendar branch
  - softened/article priorities aliases now stay inside the priorities branch
  - softened/article avoiding aliases now stay inside the avoiding branch
  - softened/article conversation aliases now stay inside the conversation branch
  - compact mixed selectors like `both`, `either`, `all of those`, `mixed`, and multi-branch `and` / `or` phrases now stay inside the capacity seam and get a narrowing overload-source question
- Added focused regression coverage in [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:1130):
  - `test_capacity_follow_up_maybe_calendar_alias_stays_inside_calendar_thread`
  - `test_capacity_follow_up_priorities_stuff_alias_stays_inside_priorities_thread`
  - `test_capacity_follow_up_avoiding_stuff_alias_stays_inside_avoiding_thread`
  - `test_capacity_follow_up_maybe_conversation_alias_stays_inside_conversation_thread`
  - `test_capacity_follow_up_kind_of_all_of_it_alias_stays_inside_cutting_thread`
  - `test_capacity_follow_up_probably_everything_alias_stays_inside_cutting_thread`
  - `test_capacity_follow_up_both_alias_stays_inside_cutting_thread`
  - `test_capacity_follow_up_all_of_those_alias_stays_inside_cutting_thread`
  - `test_capacity_follow_up_calendar_and_priorities_alias_stays_inside_cutting_thread`
  - `test_capacity_follow_up_mixed_alias_stays_inside_cutting_thread`

## E. Truth Guarantees Preserved
- Stayed inside the existing companion conversation seam only.
- No broader overloaded-week redesign, memory expansion, capability-copy work, therapist drift, or architecture work.
- No fake retrieval, execution, or autonomy claims were introduced.
- The mixed reply remains a narrowing question about what is actually driving overload rather than pretending JARVIS already knows what must be cut.

## F. Tests / Validation
- Compile proof:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
  - Result: passed
- Focused pytest closeout battery:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "capacity_follow_up_calendar_stays_inside_cutting_thread or capacity_follow_up_fuzzy_priorities_stays_inside_cutting_thread or capacity_follow_up_conversation_stays_inside_cutting_thread or capacity_follow_up_schedule_alias_stays_inside_calendar_thread or capacity_follow_up_cut_alias_stays_inside_cutting_thread or capacity_follow_up_conversation_alias_stays_inside_conversation_thread or capacity_follow_up_probably_calendar_alias_stays_inside_calendar_thread or capacity_follow_up_schedule_stuff_alias_stays_inside_calendar_thread or capacity_follow_up_maybe_priorities_alias_stays_inside_priorities_thread or capacity_follow_up_probably_conversation_alias_stays_inside_conversation_thread or capacity_follow_up_all_of_it_alias_stays_inside_cutting_thread or capacity_follow_up_i_do_not_know_alias_stays_inside_cutting_thread or capacity_follow_up_maybe_calendar_alias_stays_inside_calendar_thread or capacity_follow_up_priorities_stuff_alias_stays_inside_priorities_thread or capacity_follow_up_avoiding_stuff_alias_stays_inside_avoiding_thread or capacity_follow_up_maybe_conversation_alias_stays_inside_conversation_thread or capacity_follow_up_kind_of_all_of_it_alias_stays_inside_cutting_thread or capacity_follow_up_probably_everything_alias_stays_inside_cutting_thread or capacity_follow_up_both_alias_stays_inside_cutting_thread or capacity_follow_up_all_of_those_alias_stays_inside_cutting_thread or capacity_follow_up_calendar_and_priorities_alias_stays_inside_cutting_thread or capacity_follow_up_mixed_alias_stays_inside_cutting_thread"`
  - Result: `22 passed, 101 deselected in 0.18s`
- Compact in-process smoke proof:
  - `python3 - <<'PY'`
  - `from jarvis.companion_spine import generate_companion_fallback`
  - `packet = {'available_capabilities': ['ongoing conversation in this shell', 'conversation turn persistence'], 'conversation_excerpt': ("Chris: My week is a mess.\n" "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?")}`
  - `for prompt in ['both', 'either', 'kind of both', 'some of both', 'all of those', 'all of the above', 'the calendar and priorities', 'calendar and priorities', 'conversation and priorities', 'avoiding and the calendar', 'honestly all of them', 'probably both', 'maybe both', 'the calendar or priorities', 'all of them', 'all of these', 'more than one', 'mixed', 'maybe the calendar', 'probably schedule', 'the priorities stuff', 'the avoiding stuff', 'the conversation stuff']:`
  - `    print(f'{prompt}: {generate_companion_fallback(prompt, packet)}')`
  - `PY`
  - Result highlights:
    - softened/article branch selectors now stay inside their correct capacity branches
    - compact mixed replies now stay inside the capacity seam and get the overload-source narrowing question
    - no tested alias in this bounded closeout family falls back to the generic `short version` reply anymore

## G. Residual Risks
- This closeout pass stayed tightly bounded to the capacity follow-up seam only.
- I did not broaden into general overloaded-week redesign, broader multi-turn conversation work, memory behavior, or capability-copy drift.
- Unrelated dirty-tree work was left untouched.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-46-companion-capacity-follow-up-continuity-closeout-pass.md`

## I. Closeout Recommendation
- The capacity follow-up continuity sublane is now clean enough to close on acceptance evidence.
- Ready for Architect Office review: yes
