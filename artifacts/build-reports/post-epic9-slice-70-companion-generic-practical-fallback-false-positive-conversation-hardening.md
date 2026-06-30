# Post-Epic 9 Slice 70: Companion Generic Practical Fallback False-Positive Conversation Hardening

Ready for Architect Office review: yes

## Exact prompts tested

False-positive probes:
- `I need help with my collection of essays.`
- `I need help with this essay.`
- `I need help with my essays.`

In-bounds conversation controls:
- `I need to talk to my brother.`
- `I need to have a conversation with my sister.`
- `I need to say something to my dad.`
- `I need to clear the air with my boss.`

## Whether a defect was found

Yes.

The generic practical fallback was doing loose substring matching for conversation terms, including:
- `say`

That caused false-positive conversation routing for non-conversation writing prompts like:
- `I need help with my collection of essays.`
- `I need help with this essay.`
- `I need help with my essays.`

Repo-truth smoke confirmed those were incorrectly landing on the hard-conversation fork because `essay` / `essays` contains `say`.

## Exact code/tests changed

Code change:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1077)
  - Hardened `_generic_practical_fallback_reply` by introducing a narrow local matcher:
    - multi-word conversation phrases still use substring matching
    - single-word conversation terms now require regex word boundaries
  - This preserves real conversation routing while removing substring false positives like `essay` -> `say`.

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:289)
  - Added focused false-positive regression tests for:
    - `I need help with my collection of essays.`
    - `I need help with this essay.`
    - `I need help with my essays.`
  - Reused existing real conversation controls in the same focused seam to verify no regression.

## Exact verification commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "unmatched_practical_conversation_request_gets_concrete_fork or talk_to_brother_prompt_gets_concrete_conversation_fork or have_conversation_with_sister_prompt_gets_concrete_conversation_fork or hard_conversation_prompt_gets_concrete_conversation_fork or sit_down_with_brother_prompt_gets_concrete_conversation_fork or say_something_to_dad_prompt_gets_concrete_conversation_fork or clear_the_air_with_boss_prompt_gets_concrete_conversation_fork or should_clear_the_air_with_her_prompt_gets_concrete_conversation_fork or collection_of_essays_prompt_does_not_get_conversation_fork or essay_prompt_does_not_get_conversation_fork or essays_prompt_does_not_get_conversation_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my collection of essays.",
    "I need help with this essay.",
    "I need help with my essays.",
    "I need to talk to my brother.",
    "I need to have a conversation with my sister.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Verification results

- `py_compile`: passed
- focused pytest: `11 passed, 203 deselected`
- in-process smoke:
  - essay prompts no longer hit the hard-conversation fork
  - they now fall back to the generic practical sorter:
    - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
  - real conversation prompts still route to:
    - `Let's make it concrete. Is the hard part what you need to say, how to say it, or whether to have the conversation at all?`

## Recommendation

Approve.

This is a narrow false-positive hardening inside the generic practical fallback seam only. It fixes the substring bug without widening essay prompts into any book-work or broader writing classifier.
