# Post-Epic 9 Slice 32: Companion Decision Follow-Up Continuity Hardening

## A. Files Changed
- `jarvis/companion_spine.py`
- `tests/test_companion_spine.py`
- `artifacts/build-reports/post-epic9-slice-32-companion-decision-follow-up-continuity-hardening.md`

## B. Scope Reviewed
- Decision follow-up continuation logic in `jarvis/companion_spine.py`
- Existing decision second-turn coverage in `tests/test_companion_spine.py`
- In-process smoke behavior for short natural decision-language follow-ups after the concrete decision fork

## C. Weakness Found
- One real bounded continuity weakness was found in the decision follow-up seam.
- After the concrete decision fork (`money / energy / risk / regret`), natural short alias replies such as:
  - `pay`
  - `upside`
  - `downside`
  - `stability`
  - `future`
  were falling out of the decision thread and resetting to the generic:
  - `I'm here. Give me the short version, or tell me which part feels off.`
- That made the second turn less sharp and less useful than the first-turn fork.

## D. Bounded Repairs Made
- Kept the change inside the existing decision follow-up seam only.
- Expanded `_decision_follow_up_reply(...)` alias handling:
  - money thread:
    - `money`, `pay`, `upside`
  - risk thread:
    - `risk`, `downside`
  - regret thread:
    - `regret`, `regret not taking`, `stability`, `future`
- No broader conversation redesign or unrelated branch changes were made.

## E. Tests / Validation
- Compile check:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
  - Result: passed
- Focused pytest battery:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "decision_follow_up_energy_gets_concrete_continuation or decision_follow_up_risk_gets_concrete_continuation or decision_follow_up_pay_alias_stays_inside_money_thread or decision_follow_up_stability_alias_stays_inside_regret_thread or decision_shaped_job_prompt_gets_decision_fork or decision_shaped_torn_prompt_gets_decision_fork"`
  - Result: `6 passed, 63 deselected in 0.16s`
- Compact in-process smoke proof:
  - Base prompt chain:
    - `Chris: Should I take the new job?`
    - `Jarvis: Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?`
  - Follow-ups exercised:
    - `pay`
    - `upside`
    - `downside`
    - `stability`
    - `future`
  - Results:
    - `pay` -> `Okay. Is the real question pay now, long-term upside, or how much margin this buys you?`
    - `upside` -> same continuity reply
    - `downside` -> `Okay. Is the risk more about money, reputation, or ending up stuck in something you already know is wrong?`
    - `stability` -> `Okay. Which miss would bother you more a year from now: losing stability, or not taking the shot?`
    - `future` -> same continuity reply

## F. Truth Guarantees Preserved
- No new architecture.
- No hidden-memory claims.
- No fake autonomy or execution claims.
- No therapist drift.
- The seam stays practical, sharp, and truthfully bounded inside ordinary conversation only.

## G. Residual Risks
- This slice stayed tightly scoped to decision follow-up continuity only.
- It does not attempt broader multi-turn decision coaching or general companion copy cleanup.
- Existing unrelated dirty-tree drift remains out of scope and untouched.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-32-companion-decision-follow-up-continuity-hardening.md`

## I. Recommendation
- Ready for Architect Office review: yes
