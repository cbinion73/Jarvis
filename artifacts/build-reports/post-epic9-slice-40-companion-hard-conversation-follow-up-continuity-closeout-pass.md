# Post-Epic 9 Slice 40: Companion Hard-Conversation Follow-Up Continuity Closeout Pass

## A. Files Changed
- `jarvis/companion_spine.py`
- `tests/test_companion_spine.py`
- `artifacts/build-reports/post-epic9-slice-40-companion-hard-conversation-follow-up-continuity-closeout-pass.md`

## B. Scope Reviewed
- The existing companion hard-conversation follow-up seam only.
- Compact natural second-turn replies after the concrete hard-conversation fork, especially mixed, softened, article, and hedged selectors around what to say, how to say it, and whether to have the conversation at all.
- Focused in-process smoke behavior for nearby ambiguity cases a real user would plausibly send.

## C. Defects Found and Repairs Made
- Found one remaining bounded second-turn continuity weakness: softened/article selector variants were still too literal, so mixed and hedged replies like `probably both`, `all of those`, `probably the tone`, and `maybe the conversation itself` were falling out of the hard-conversation seam, and one longer phrase still needed a short-follow-up gate exception.
- Repaired only that one remaining selector-family weakness in `jarvis/companion_spine.py`:
  - mixed replies now stay inside the hard-conversation seam for nearby variants such as:
    - `probably both`
    - `all of those`
    - `all of it honestly`
    - `i do not know`
    - `i don't know`
    - `the whole thing honestly`
  - whether-to-have-it variants now stay inside the worth-having branch for nearby variants such as:
    - `maybe the conversation itself`
    - `the whole conversation`
    - `whether i even need to`
    - `if i even need to have it`
    - `probably the conversation itself`
    - `maybe whether`
  - wording variants now stay inside the framing branch for nearby variants such as:
    - `what i actually say`
    - `probably the wording`
    - `maybe wording`
  - delivery variants now stay inside the tone/delivery branch for nearby variants such as:
    - `how i actually say it`
    - `probably the tone`
    - `maybe delivery`
  - added the smallest explicit short-follow-up allowance for the longer phrase:
    - `if i even need to have it`
- Added focused regression coverage in `tests/test_companion_spine.py` for:
  - `probably both`
  - `probably the wording`
  - `probably the tone`
  - `if i even need to have it`

## D. Truth / Continuity Guarantees Confirmed
- Stayed inside the existing companion conversation seam only.
- No new architecture, memory behavior, capability-copy work, therapist drift, or general conversation redesign.
- No fake retrieval, execution, or autonomy claims were introduced.
- The seam now stays concrete about which hard-conversation branch Chris means without pretending JARVIS already knows the answer or the script.

## E. Tests / Validation
- Compile proof:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
  - Result: passed
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "conversation_follow_up_gets_concrete_continuation or conversation_follow_up_wording_alias_gets_concrete_continuation or conversation_follow_up_tone_alias_gets_concrete_continuation or conversation_follow_up_whether_alias_gets_concrete_continuation or conversation_follow_up_hedged_wording_alias_gets_concrete_continuation or conversation_follow_up_article_tone_alias_gets_concrete_continuation or conversation_follow_up_hedged_whether_alias_gets_concrete_continuation or conversation_follow_up_mixed_alias_stays_inside_conversation_thread or conversation_follow_up_probably_how_to_say_it_stays_inside_conversation_thread or conversation_follow_up_probably_whether_stays_inside_conversation_thread or conversation_follow_up_all_of_it_phrase_stays_inside_conversation_thread or conversation_follow_up_probably_both_stays_inside_conversation_thread or conversation_follow_up_probably_the_wording_stays_inside_conversation_thread or conversation_follow_up_probably_the_tone_stays_inside_conversation_thread or conversation_follow_up_if_i_even_need_to_have_it_stays_inside_conversation_thread or practical_fork_follow_up_conversation_gets_concrete_continuation or capacity_follow_up_conversation_alias_stays_inside_conversation_thread"`
  - Result: `17 passed, 79 deselected in 0.24s`
- Compact in-process smoke proof:
  - `python3 - <<'PY'`
  - `from jarvis.companion_spine import generate_companion_fallback`
  - `packet = {'available_capabilities': ['ongoing conversation in this shell', 'conversation turn persistence'], 'conversation_excerpt': ("Chris: I need to have a hard conversation.\n" "Jarvis: What's the hard part: what to say, how to say it, or whether to have the conversation at all?")}`
  - `for prompt in ['probably both', 'all of those', 'all of it honestly', 'i do not know', \"i don't know\", 'maybe the conversation itself', 'the whole conversation', 'whether i even need to', 'if i even need to have it', 'how i actually say it', 'what i actually say', 'probably the tone', 'probably the wording', 'probably the conversation itself', 'maybe delivery', 'maybe wording', 'maybe whether', 'the whole thing honestly']:`
  - `    print(f'{prompt}: {generate_companion_fallback(prompt, packet)}')`
  - `PY`
  - Result highlights:
    - mixed variants stay inside the mixed-branch narrowing path
    - wording variants stay inside the framing branch
    - delivery variants stay inside the tone/delivery branch
    - whether-to-have-it variants stay inside the worth-having branch

## F. Residual Risks
- This closeout pass stayed tightly bounded to the hard-conversation follow-up seam only.
- I did not broaden into general hard-conversation coaching, broader companion redesign, memory behavior, or capability-copy work.
- Unrelated dirty-tree capability-copy drift plus previously approved overloaded-week, decision-follow-up, and drafting-follow-up seam changes were left untouched.

## G. Artifact Path
- `artifacts/build-reports/post-epic9-slice-40-companion-hard-conversation-follow-up-continuity-closeout-pass.md`

## H. Recommendation
- Ready for Architect Office review: yes
