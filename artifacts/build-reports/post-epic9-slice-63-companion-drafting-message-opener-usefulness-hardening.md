## A. Exact Prompts Tested
- `I need to reply to her.`
- `I need help writing an email to my boss.`
- `I need to send a message to my brother.`
- `I should probably send him a message.`
- `I need to text my brother.`
- `Help me draft a text to my brother.`
- `I need to answer this email.`
- `I need to write to my boss.`
- `I need to send him a text.`
- bounded controls:
  - `I need to talk to my brother.`
  - `I need relationship advice.`

## B. Exact Defect Found
- Natural message-writing phrasing was not consistently reaching the existing drafting fork.
- Concrete misses before the repair:
  - `I need help writing an email to my boss.` routed into the hard-conversation fork
  - `I need to send a message to my brother.` fell to the generic fallback
  - `I should probably send him a message.` fell to the generic fallback
  - `I need to text my brother.` fell to the generic fallback
  - `I need to write to my boss.` fell to the generic fallback
  - `I need to send him a text.` fell to the generic fallback

## C. Exact Code / Tests Changed
- Code changed:
  - `jarvis/companion_spine.py`
  - Expanded `_request_needs_practical_handle(...)` with the smallest message-writing aliases needed to reach the drafting seam:
    - `writing an email`
    - `write to`
    - `send a message`
    - `send him a message`
    - `send her a message`
    - `send them a message`
    - `send a text`
    - `send him a text`
    - `send her a text`
    - `text my`
  - Expanded `_is_drafting_request(...)` with the same bounded message-writing aliases so the drafting fork handles them consistently once reached.
- Tests changed:
  - `tests/test_companion_spine.py`
  - Added focused opener coverage for:
    - `I need help writing an email to my boss.`
    - `I need to send a message to my brother.`
    - `I should probably send him a message.`
    - `I need to text my brother.`
  - Added a bounded negative control:
    - `I need to talk to my brother.` stays in the hard-conversation fork

## D. Exact Verification Commands Run
- Compile:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "drafting_text_request_gets_concrete_fork or drafting_email_request_gets_concrete_fork or writing_email_to_boss_prompt_gets_drafting_fork or send_message_to_brother_prompt_gets_drafting_fork or should_probably_send_him_a_message_prompt_gets_drafting_fork or text_my_brother_prompt_gets_drafting_fork or talk_to_brother_prompt_does_not_get_drafting_fork"`
- Compact in-process smoke:
  - `python3 - <<'PY'`
  - `from jarvis.companion_spine import generate_companion_fallback`
  - `packet={'available_capabilities':['ongoing conversation in this shell','conversation turn persistence']}`
  - `prompts=[`
  - `    'I need to reply to her.',`
  - `    'I need help writing an email to my boss.',`
  - `    'I need to send a message to my brother.',`
  - `    'I should probably send him a message.',`
  - `    'I need to text my brother.',`
  - `    'Help me draft a text to my brother.',`
  - `    'I need to answer this email.',`
  - `    'I need to write to my boss.',`
  - `    'I need to send him a text.',`
  - `    'I need to talk to my brother.',`
  - `    'I need relationship advice.',`
  - `]`
  - `for prompt in prompts:`
  - `    print(f'PROMPT: {prompt}\\nREPLY: {generate_companion_fallback(prompt, packet)}\\n')`
  - `PY`

## E. Verification Results
- Compile:
  - passed with no output
- Focused pytest:
  - `7 passed, 174 deselected in 0.16s`
- Smoke proof:
  - The drafting opener now correctly catches:
    - `I need to reply to her.`
    - `I need help writing an email to my boss.`
    - `I need to send a message to my brother.`
    - `I should probably send him a message.`
    - `I need to text my brother.`
    - `Help me draft a text to my brother.`
    - `I need to answer this email.`
    - `I need to write to my boss.`
    - `I need to send him a text.`
  - Bounded controls still stay out:
    - `I need to talk to my brother.` -> hard-conversation fork
    - `I need relationship advice.` -> generic fallback

## F. Recommendation
- Approve
- This bounded drafting/message opener weakness is repaired cleanly from repo truth.
- If Architect Office wants more confidence, the next step should be an acceptance pass only, not a broader drafting redesign.
