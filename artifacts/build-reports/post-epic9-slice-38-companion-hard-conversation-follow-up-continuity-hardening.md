# Post-Epic 9 Slice 38: Companion Hard-Conversation Follow-Up Continuity Hardening

## A. Files Changed
- `jarvis/companion_spine.py`
- `tests/test_companion_spine.py`
- `artifacts/build-reports/post-epic9-slice-38-companion-hard-conversation-follow-up-continuity-hardening.md`

## B. Scope Reviewed
- The existing companion hard-conversation follow-up seam only.
- Second-turn follow-ups after the concrete hard-conversation fork, especially short natural replies around what to say, how to say it, whether to have the conversation at all, and nearby natural aliases.
- Focused in-process smoke behavior after:
  - `What's the hard part: what to say, how to say it, or whether to have the conversation at all?`

## C. Defects Found
- Found one real bounded continuity weakness: the hard-conversation follow-up seam was keyed too literally to one fork phrasing and too narrowly to a few exact reply strings, so even canonical second turns plus nearby natural aliases were missing the intended follow-up path.
- Confirmed failure examples before repair:
  - `what to say`
  - `how to say it`
  - `whether to have it`
  - `wording`
  - `tone`
  - `should i even have it`

## D. Bounded Repairs Made
- Repaired only that one hard-conversation continuity weakness in `jarvis/companion_spine.py`:
  - the seam now recognizes both current fork phrasings:
    - `what you need to say, how to say it, or whether to have the conversation at all`
    - `what to say, how to say it, or whether to have the conversation at all`
  - wording aliases now stay inside the `what to say` branch
    - `say it`, `wording`, `the wording`
  - delivery aliases now stay inside the `how to say it` branch
    - `tone`, `delivery`
  - whether-to-have-it aliases now stay inside the conversation-worth-having branch
    - `whether`
    - `should i even have it`
    - `if i should do it`
    - `do i even need to`
- Added focused regression coverage in `tests/test_companion_spine.py` for:
  - `wording`
  - `tone`
  - `should i even have it`

## E. Truth Guarantees Preserved
- Stayed inside the existing companion conversation seam only.
- No new architecture, memory behavior, capability-copy work, therapist drift, or general conversation redesign.
- No fake retrieval, execution, or autonomy claims were introduced.
- The repair keeps the hard-conversation fork concrete without pretending JARVIS already knows the opening line, tone, or whether the conversation should happen.

## F. Tests / Validation
- Compile proof:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
  - Result: passed
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "conversation_follow_up_gets_concrete_continuation or conversation_follow_up_wording_alias_gets_concrete_continuation or conversation_follow_up_tone_alias_gets_concrete_continuation or conversation_follow_up_whether_alias_gets_concrete_continuation or practical_fork_follow_up_conversation_gets_concrete_continuation or capacity_follow_up_conversation_alias_stays_inside_conversation_thread"`
  - Result: `6 passed, 79 deselected in 0.22s`
- Compact in-process smoke proof:
  - `python3 - <<'PY'`
  - `from jarvis.companion_spine import generate_companion_fallback`
  - `packet = {'available_capabilities': ['ongoing conversation in this shell', 'conversation turn persistence'], 'conversation_excerpt': ("Chris: I need to have a hard conversation.\n" "Jarvis: What's the hard part: what to say, how to say it, or whether to have the conversation at all?")}`
  - `for prompt in ['what to say', 'how to say it', 'whether to have it', 'say it', 'wording', 'tone', 'delivery', 'should i even have it', 'whether', 'if i should do it', 'do i even need to', 'the wording']:`
  - `    print(f'{prompt}: {generate_companion_fallback(prompt, packet)}')`
  - `PY`
  - Result highlights:
    - `what to say`, `say it`, `wording`, and `the wording` now stay inside the framing branch
    - `how to say it`, `tone`, and `delivery` now stay inside the delivery branch
    - `whether to have it`, `whether`, `should i even have it`, `if i should do it`, and `do i even need to` now stay inside the conversation-worth-having branch

## G. Residual Risks
- This slice intentionally stayed bounded to the hard-conversation follow-up seam only.
- I did not broaden into general hard-conversation coaching, broader companion redesign, memory behavior, or capability-copy work.
- Unrelated dirty-tree capability-copy drift plus previously approved overloaded-week, decision-follow-up, and drafting-follow-up seam changes were left untouched.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-38-companion-hard-conversation-follow-up-continuity-hardening.md`

## I. Recommendation
- Ready for Architect Office review: yes
