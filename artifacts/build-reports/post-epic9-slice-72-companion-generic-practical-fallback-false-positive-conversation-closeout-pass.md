# Post-Epic 9 Slice 72: Companion Generic Practical Fallback False-Positive Conversation Closeout Pass

Ready for Architect Office review: yes

## Exact prompts tested

Known false-positive probes rechecked:
- `I need help with my collection of essays.`
- `I need help with this essay.`
- `I need help with my essays.`
- `I need help with this essay collection.`
- `I need help with this textbook.`
- `I need help with this callback draft.`
- `I need help with this smalltalk scene.`

Focused closeout-pass probes:
- `I need help with my boundary notes.`
- `I need help with my conflict essay.`

Real conversation controls:
- `I need help setting a boundary with my mom.`
- `I need to talk to my brother.`
- `I need to have a conversation with my sister.`
- `I need to say something to my dad.`
- `I need to clear the air with my boss.`

## Whether a defect was found

Yes.

One final bounded false-positive family remained inside the generic practical fallback seam:
- `boundary`
- `conflict`

When those single words appeared inside document-shaped prompts, they were still forcing the hard-conversation fork:
- `I need help with my boundary notes.`
- `I need help with my conflict essay.`

That was too broad. These words can describe conversation problems, but by themselves they are not reliable enough to force the hard-conversation fork in the generic fallback seam.

The truthful boundary after repair is:
- person-shaped or explicit conversation prompts still route to the hard-conversation fork
- abstract document-shaped prompts with `boundary` or `conflict` alone now stay on the generic practical sorter

## Exact code/tests changed if any

Code change:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1079)
  - Removed `boundary` and `conflict` from the generic fallback's bare `conversation_terms`.
  - Kept the existing word-boundary matcher and stronger person/conversation cues unchanged.

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:324)
  - Added focused closeout-pass regression tests for:
    - `I need help with my boundary notes.`
    - `I need help with my conflict essay.`
    - `I need help setting a boundary with my mom.`

## Exact verification commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "talk_to_brother_prompt_gets_concrete_conversation_fork or have_conversation_with_sister_prompt_gets_concrete_conversation_fork or say_something_to_dad_prompt_gets_concrete_conversation_fork or clear_the_air_with_boss_prompt_gets_concrete_conversation_fork or boundary_with_mom_prompt_still_gets_conversation_fork or collection_of_essays_prompt_does_not_get_conversation_fork or essay_prompt_does_not_get_conversation_fork or essays_prompt_does_not_get_conversation_fork or essay_collection_prompt_does_not_get_conversation_fork or textbook_prompt_does_not_get_conversation_fork or callback_draft_prompt_does_not_get_conversation_fork or smalltalk_scene_prompt_does_not_get_conversation_fork or boundary_notes_prompt_does_not_get_conversation_fork or conflict_essay_prompt_does_not_get_conversation_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my collection of essays.",
    "I need help with this essay.",
    "I need help with my essays.",
    "I need help with this essay collection.",
    "I need help with this textbook.",
    "I need help with this callback draft.",
    "I need help with this smalltalk scene.",
    "I need help with my boundary notes.",
    "I need help with my conflict essay.",
    "I need help setting a boundary with my mom.",
    "I need to talk to my brother.",
    "I need to have a conversation with my sister.",
    "I need to say something to my dad.",
    "I need to clear the air with my boss.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Verification results

- `py_compile`: passed
- focused pytest: `14 passed, 207 deselected`
- in-process smoke:
  - all document-shaped false-positive probes stayed out of the hard-conversation fork
  - `I need help setting a boundary with my mom.` still routed to the hard-conversation fork
  - the explicit conversation controls still routed correctly

## Recommendation

Approve and close this sublane.

This closeout pass found one final bounded overmatch, repaired it narrowly inside the generic practical fallback seam, and preserved the truthful boundary between explicit person/conversation prompts and abstract writing/document prompts.
