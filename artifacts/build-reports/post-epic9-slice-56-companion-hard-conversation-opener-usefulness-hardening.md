## A. Exact Prompts Tested
- `I need to talk to my brother.`
- `I need to have a hard conversation.`
- `I need to talk to my dad.`
- `I need to talk to my boss.`
- `I need to have a conversation with my sister.`
- `I should probably talk to him.`
- bounded controls:
  - `I need to text my brother.`
  - `Help me write a text to my brother.`
  - `I need relationship advice.`

## B. Exact Defect Found
- Nearby natural hard-conversation opener phrasing still missed the existing conversation fork and fell through to the generic fallback.
- Concrete misses before the repair:
  - `I need to talk to my brother.`
  - `I need to have a hard conversation.`
  - `I need to talk to my dad.`
  - `I need to talk to my boss.`
  - `I need to have a conversation with my sister.`

## C. Exact Code / Tests Changed
- Code changed:
  - `jarvis/companion_spine.py`
  - Expanded `_request_needs_practical_handle(...)` with the smallest in-bounds opener phrases:
    - `talk to`
    - `have a conversation`
    - `hard conversation`
- Tests changed:
  - `tests/test_companion_spine.py`
  - Added focused opener coverage for:
    - `I need to talk to my brother.`
    - `I need to have a conversation with my sister.`
    - `I need to have a hard conversation.`
  - Added a bounded negative control:
    - `I need to text my brother.`

## D. Exact Verification Commands Run
- Compile:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "unmatched_practical_conversation_request_gets_concrete_fork or talk_to_brother_prompt_gets_concrete_conversation_fork or have_conversation_with_sister_prompt_gets_concrete_conversation_fork or hard_conversation_prompt_gets_concrete_conversation_fork or text_prompt_does_not_get_conversation_fork"`
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
  - `5 passed, 156 deselected in 0.17s`
- Smoke proof:
  - The hard-conversation opener now correctly catches:
    - `I need to talk to my brother.`
    - `I need to have a hard conversation.`
    - `I need to talk to my dad.`
    - `I need to talk to my boss.`
    - `I need to have a conversation with my sister.`
    - `I should probably talk to him.`
  - Bounded controls still stay out:
    - `I need to text my brother.` -> generic fallback
    - `I need relationship advice.` -> generic fallback
  - Existing repo truth remained unchanged for:
    - `Help me write a text to my brother.` -> existing conversation fork behavior

## F. Recommendation
- Approve
- This bounded hard-conversation opener weakness is repaired cleanly from repo truth.
- If Architect Office wants more confidence, the next step should be an acceptance pass only, not another widening hardening pass.
