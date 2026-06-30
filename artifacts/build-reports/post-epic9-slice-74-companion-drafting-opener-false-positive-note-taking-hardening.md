# Post-Epic 9 Slice 74: Companion Drafting Opener False-Positive Note-Taking Hardening

Ready for Architect Office review: yes

## Exact prompts tested

False-positive note-taking/document-writing probes:
- `I need to write this down.`
- `I need to write this in my notes.`
- `I need to write this into the doc.`

True drafting/message-writing controls:
- `I need to write to my boss.`
- `I need to write her back.`
- `I need to send a message to my brother.`

## Whether a defect was found

Yes.

The standalone drafting opener was overmatching on the bare drafting term:
- `write this`

That caused non-message note-taking/document-writing prompts to incorrectly route into the drafting fork:
- `I need to write this down.`
- `I need to write this in my notes.`
- `I need to write this into the doc.`

Those prompts do not truthfully belong in the message-writing seam.

## Exact code/tests changed

Code change:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:875)
  - Removed the overly broad `write this` entry from `_is_drafting_request`
  - Kept explicit message-writing terms intact, including:
    - `write this email`
    - `write to`
    - `write her back`
    - `send a message`

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:514)
  - Added focused regression coverage for:
    - `I need to write this down.`
    - `I need to write this in my notes.`
    - `I need to write this into the doc.`
  - Reused true drafting controls to verify no regression:
    - `I need to write to my boss.`
    - `I need to write her back.`
    - `I need to send a message to my brother.`

## Exact verification commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "write_this_down_prompt_does_not_get_drafting_fork or write_this_in_my_notes_prompt_does_not_get_drafting_fork or write_this_into_the_doc_prompt_does_not_get_drafting_fork or writing_email_to_boss_prompt_gets_drafting_fork or write_him_back_prompt_gets_drafting_fork or send_message_to_brother_prompt_gets_drafting_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need to write this down.",
    "I need to write this in my notes.",
    "I need to write this into the doc.",
    "I need to write to my boss.",
    "I need to write her back.",
    "I need to send a message to my brother.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Verification results

- `py_compile`: passed
- focused pytest: `6 passed, 225 deselected`
- in-process smoke:
  - the note-taking/document-writing probes no longer route to:
    - `Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?`
  - the real message-writing controls still route to the drafting fork correctly

## Recommendation

Approve.

This is a narrow overmatch repair inside the standalone drafting opener seam only. It removes the false-positive note-taking path without broadening into a more general writing classifier.
