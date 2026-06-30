# Post-Epic 9 Slice 73: Companion Generic Practical Fallback Final Call-Term Repair

Ready for Architect Office review: yes

## Exact prompts tested

False-positive document-shaped `call` prompts:
- `I need help with my call sheet.`
- `I need help with my call notes.`
- `I need help with this call log.`

Explicit person-shaped `call` prompts:
- `I need to call my mom.`
- `I need to call my brother.`
- `I should call my dad.`
- `I need to call her.`

## Whether a defect was found

Yes.

The `call` family had a split defect inside the same generic practical fallback seam:

- document-shaped `call` prompts were false-positively routing to the hard-conversation fork
- explicit person-shaped `call` prompts were under-routing out of the practical lane and landing on the generic non-practical fallback

That meant `call` was too broad as a bare conversation term, but too weakly captured as a person-shaped practical/conversation cue.

## Exact code/tests changed

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:515)
  - Added explicit person-shaped `call` patterns to `_request_needs_practical_handle`:
    - `call my`
    - `call him`
    - `call her`
    - `call them`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1081)
  - Removed bare `call` from the generic fallback’s loose `conversation_terms`
  - Added a dedicated `call_terms` tuple for the same explicit person-shaped `call` patterns
  - Routed only those explicit `call` patterns into the hard-conversation fork

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:340)
  - Added focused regression coverage for:
    - `I need help with my call sheet.`
    - `I need help with my call notes.`
    - `I need help with this call log.`
    - `I need to call my mom.`
    - `I need to call my brother.`
    - `I should call my dad.`
    - `I need to call her.`

## Exact verification commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "call_sheet_prompt_does_not_get_conversation_fork or call_notes_prompt_does_not_get_conversation_fork or call_log_prompt_does_not_get_conversation_fork or call_my_mom_prompt_gets_conversation_fork or call_my_brother_prompt_gets_conversation_fork or should_call_my_dad_prompt_gets_conversation_fork or call_her_prompt_gets_conversation_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my call sheet.",
    "I need help with my call notes.",
    "I need help with this call log.",
    "I need to call my mom.",
    "I need to call my brother.",
    "I should call my dad.",
    "I need to call her.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Verification results

- `py_compile`: passed
- focused pytest: `7 passed, 221 deselected`
- in-process smoke:
  - document-shaped `call` prompts now stay out of the hard-conversation fork and fall back to the generic practical sorter
  - explicit person-shaped `call` prompts now route to:
    - `Let's make it concrete. Is the hard part what you need to say, how to say it, or whether to have the conversation at all?`

## Recommendation

Approve.

This is the narrow final `call` family repair inside the generic practical fallback seam. It fixes both sides of the defect without widening into broader routing changes.
