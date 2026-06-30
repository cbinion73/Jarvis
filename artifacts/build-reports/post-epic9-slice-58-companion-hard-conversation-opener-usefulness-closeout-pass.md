## A. Exact Prompts Tested
- already-covered opener family:
  - `I need to talk to my brother.`
  - `I need to have a hard conversation.`
  - `I need to talk to my dad.`
  - `I need to talk to my boss.`
  - `I need to have a conversation with my sister.`
  - `I should probably talk to him.`
  - `I should have a conversation with her.`
  - `I probably need to talk to her.`
  - `I need to sit down with my brother.`
- remaining opener family under review:
  - `I need to say something to my dad.`
  - `I need to clear the air with my boss.`
- nearby family checks:
  - `I need to say something to my brother.`
  - `I should clear the air with her.`
  - `I need to clear the air with my sister.`
- bounded controls:
  - `I need to tell my dad something hard.`
  - `I need to text my brother.`
  - `Help me write a text to my brother.`
  - `I need relationship advice.`

## B. Whether a Defect Was Found
- Yes.
- The remaining opener family still fell through to the generic fallback even though it clearly belonged in the same hard-conversation opener seam:
  - `I need to say something to my dad.`
  - `I need to clear the air with my boss.`

## C. Exact Code / Tests Changed
- Code changed:
  - `jarvis/companion_spine.py`
  - Added two bounded opener aliases to `_request_needs_practical_handle(...)`:
    - `say something to`
    - `clear the air with`
  - Added one bounded conversation-shape cue to `_generic_practical_fallback_reply(...)`:
    - `clear the air`
- Tests changed:
  - `tests/test_companion_spine.py`
  - Added focused positive coverage for:
    - `I need to say something to my dad.`
    - `I need to clear the air with my boss.`
    - `I should clear the air with her.`

## D. Exact Verification Commands Run
- Compile:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "unmatched_practical_conversation_request_gets_concrete_fork or talk_to_brother_prompt_gets_concrete_conversation_fork or have_conversation_with_sister_prompt_gets_concrete_conversation_fork or hard_conversation_prompt_gets_concrete_conversation_fork or sit_down_with_brother_prompt_gets_concrete_conversation_fork or say_something_to_dad_prompt_gets_concrete_conversation_fork or clear_the_air_with_boss_prompt_gets_concrete_conversation_fork or should_clear_the_air_with_her_prompt_gets_concrete_conversation_fork or text_prompt_does_not_get_conversation_fork"`
- Compact in-process smoke:
  - `python3 - <<'PY'`
  - `from jarvis.companion_spine import generate_companion_fallback`
  - `packet={'available_capabilities':['ongoing conversation in this shell','conversation turn persistence']}`
  - `prompts=[`
  - `    'I need to talk to my brother.',`
  - `    'I need to have a hard conversation.',`
  - `    'I need to talk to my dad.',`
  - `    'I need to talk to my boss.',`
  - `    'I need to have a conversation with my sister.',`
  - `    'I should probably talk to him.',`
  - `    'I should have a conversation with her.',`
  - `    'I probably need to talk to her.',`
  - `    'I need to sit down with my brother.',`
  - `    'I need to say something to my dad.',`
  - `    'I need to clear the air with my boss.',`
  - `    'I need to say something to my brother.',`
  - `    'I should clear the air with her.',`
  - `    'I need to clear the air with my sister.',`
  - `    'I need to tell my dad something hard.',`
  - `    'I need to text my brother.',`
  - `    'Help me write a text to my brother.',`
  - `    'I need relationship advice.',`
  - `]`
  - `for prompt in prompts:`
  - `    print(f'PROMPT: {prompt}\\nREPLY: {generate_companion_fallback(prompt, packet)}\\n')`
  - `PY`

## E. Verification Results
- Compile:
  - passed with no output
- Focused pytest:
  - `9 passed, 156 deselected in 0.18s`
- Smoke proof:
  - Hard-conversation opener now catches:
    - `I need to talk to my brother.`
    - `I need to have a hard conversation.`
    - `I need to talk to my dad.`
    - `I need to talk to my boss.`
    - `I need to have a conversation with my sister.`
    - `I should probably talk to him.`
    - `I should have a conversation with her.`
    - `I probably need to talk to her.`
    - `I need to sit down with my brother.`
    - `I need to say something to my dad.`
    - `I need to clear the air with my boss.`
    - `I need to say something to my brother.`
    - `I should clear the air with her.`
    - `I need to clear the air with my sister.`
  - Bounded controls still stay out:
    - `I need to tell my dad something hard.`
    - `I need to text my brother.`
    - `I need relationship advice.`
  - Existing repo truth remained unchanged for:
    - `Help me write a text to my brother.` -> existing hard-conversation fork path

## F. Recommendation
- Approve
- The remaining opener family clearly belonged in the existing hard-conversation seam and is now covered with a narrow truthful patch.
- Stop here on the current truthful boundary; no additional opener widening looks necessary from repo truth.
