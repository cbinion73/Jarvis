## A. Exact Prompts Tested
- already-covered opener family:
  - `I need to talk to my brother.`
  - `I need to have a hard conversation.`
  - `I need to talk to my dad.`
  - `I need to talk to my boss.`
  - `I need to have a conversation with my sister.`
  - `I should probably talk to him.`
- additional nearby first-turn probes:
  - `I should have a conversation with her.`
  - `I probably need to talk to her.`
  - `I need to sit down with my brother.`
  - `I need to say something to my dad.`
  - `I need to clear the air with my boss.`
- bounded controls:
  - `I need to text my brother.`
  - `Help me write a text to my brother.`
  - `I need relationship advice.`

## B. Whether a Defect Was Found
- Yes.
- One real remaining bounded opener defect was present at the start of this pass:
  - `I need to sit down with my brother.` still fell through to the generic fallback even though it clearly belongs in the same hard-conversation opener family as `talk to` and `have a conversation`.
- After repairing that smallest local issue, the seam still is not fully acceptance-complete because two nearby conversation-shaped prompts remain generic:
  - `I need to say something to my dad.`
  - `I need to clear the air with my boss.`

## C. Exact Code / Tests Changed
- Code changed:
  - `jarvis/companion_spine.py`
  - Added one bounded opener alias to `_request_needs_practical_handle(...)`:
    - `sit down with`
- Tests changed:
  - `tests/test_companion_spine.py`
  - Added focused opener coverage for:
    - `I need to sit down with my brother.`
- Existing bounded control remained in place:
  - `I need to text my brother.`

## D. Exact Verification Commands Run
- Compile:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "unmatched_practical_conversation_request_gets_concrete_fork or talk_to_brother_prompt_gets_concrete_conversation_fork or have_conversation_with_sister_prompt_gets_concrete_conversation_fork or hard_conversation_prompt_gets_concrete_conversation_fork or sit_down_with_brother_prompt_gets_concrete_conversation_fork or text_prompt_does_not_get_conversation_fork"`
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
  - `6 passed, 156 deselected in 0.17s`
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
  - Bounded controls still stay out:
    - `I need to text my brother.` -> generic fallback
    - `I need relationship advice.` -> generic fallback
  - Existing repo truth remained unchanged for:
    - `Help me write a text to my brother.` -> existing hard-conversation fork path
  - Remaining nearby conversation-shaped prompts still generic:
    - `I need to say something to my dad.`
    - `I need to clear the air with my boss.`

## F. Recommendation
- Another bounded pass
- This acceptance pass repaired one real opener alias gap, but the standalone hard-conversation opener is not yet clean enough to close on acceptance evidence.
- The next pass should stay narrow and decide whether the remaining `say something to` / `clear the air with` family belongs in the same opener seam or whether the current boundary is the truthful stopping point.
