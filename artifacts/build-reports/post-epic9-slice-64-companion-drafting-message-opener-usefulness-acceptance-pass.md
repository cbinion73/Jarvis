# Post-Epic 9 Slice 64: Companion Drafting/Message Opener Usefulness Acceptance Pass

Ready for Architect Office review: yes

## Exact prompts tested

Acceptance prompts already holding at start of this slice:
- `I need to reply to her.`
- `I need help writing an email to my boss.`
- `I need to send a message to my brother.`
- `I should probably send him a message.`
- `I need to text my brother.`
- `Help me draft a text to my brother.`
- `I need to answer this email.`
- `I need to write to my boss.`
- `I need to send him a text.`
- `I should probably text him.`
- `I need to message my brother.`
- `I need to write him back.`
- `I need to email my boss.`

Bounded controls still staying out:
- `I need to talk to my brother.`
- `I need relationship advice.`

Nearby natural opener probes that exposed the remaining local defect:
- `I should send a note to my brother.`
- `I need to write her a message.`
- `I need to send my boss a note.`

Post-repair smoke rechecked:
- `I need to reply to her.`
- `I need help writing an email to my boss.`
- `I need to send a message to my brother.`
- `I should probably send him a message.`
- `I need to text my brother.`
- `Help me draft a text to my brother.`
- `I need to answer this email.`
- `I need to write to my boss.`
- `I need to send him a text.`
- `I should probably text him.`
- `I need to message my brother.`
- `I need to write him back.`
- `I need to email my boss.`
- `I should send a note to my brother.`
- `I need to email him back.`
- `I need to write her a message.`
- `I need to send my boss a note.`
- `I need to talk to my brother.`
- `I need relationship advice.`

## Whether a defect was found

Yes.

The acceptance pass found one remaining bounded drafting-opener weakness: note-style message requests and `write ... a message` first-turn phrasing still fell through to the generic fallback even though they were clearly asking JARVIS to help draft or send a message.

Before repair:
- `I should send a note to my brother.` -> generic fallback
- `I need to write her a message.` -> generic fallback
- `I need to send my boss a note.` -> generic fallback

After repair:
- all three now route into the existing drafting fork:
  - `Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?`

## Exact code/tests changed if any

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:500)
  - Extended `_request_needs_practical_handle` with the smallest missing note/message-writing aliases:
    - `send a note`
    - `send him a note`
    - `send her a note`
    - `send them a note`
    - `send my boss a note`
    - `write him a message`
    - `write her a message`
    - `write them a message`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:846)
  - Extended `_is_drafting_request` with the same alias family so the opener and drafting classifier stay aligned.

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:382)
  - Added focused regression coverage for:
    - `I should send a note to my brother.`
    - `I need to write her a message.`
    - `I need to send my boss a note.`

## Exact verification commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "drafting_text_request_gets_concrete_fork or drafting_email_request_gets_concrete_fork or writing_email_to_boss_prompt_gets_drafting_fork or send_message_to_brother_prompt_gets_drafting_fork or should_probably_send_him_a_message_prompt_gets_drafting_fork or text_my_brother_prompt_gets_drafting_fork or should_probably_text_him_prompt_gets_drafting_fork or message_my_brother_prompt_gets_drafting_fork or write_him_back_prompt_gets_drafting_fork or email_my_boss_prompt_gets_drafting_fork or send_note_to_brother_prompt_gets_drafting_fork or write_her_a_message_prompt_gets_drafting_fork or send_my_boss_a_note_prompt_gets_drafting_fork or talk_to_brother_prompt_does_not_get_drafting_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need to reply to her.",
    "I need help writing an email to my boss.",
    "I need to send a message to my brother.",
    "I should probably send him a message.",
    "I need to text my brother.",
    "Help me draft a text to my brother.",
    "I need to answer this email.",
    "I need to write to my boss.",
    "I need to send him a text.",
    "I should probably text him.",
    "I need to message my brother.",
    "I need to write him back.",
    "I need to email my boss.",
    "I should send a note to my brother.",
    "I need to email him back.",
    "I need to write her a message.",
    "I need to send my boss a note.",
    "I need to talk to my brother.",
    "I need relationship advice.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Verification results

- `py_compile`: passed
- `pytest`: `14 passed, 174 deselected`
- In-process smoke:
  - all drafting/message prompts above routed to the drafting fork after repair
  - `I need to talk to my brother.` still routes to the hard-conversation fork
  - `I need relationship advice.` still stays on the generic fallback

## Recommendation

Approve.

This acceptance pass found one real remaining opener-family defect, repaired it in a tightly bounded way, and the drafting/message opener now holds cleanly across the nearby natural first-turn phrasing exercised here. The next step, if desired, should be a closeout pass rather than another broad hardening slice.
