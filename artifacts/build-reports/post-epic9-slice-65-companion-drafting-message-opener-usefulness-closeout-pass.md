# Post-Epic 9 Slice 65: Companion Drafting/Message Opener Usefulness Closeout Pass

Ready for Architect Office review: yes

## Exact prompts tested

Previously-approved drafting/message opener coverage rechecked by repo truth:
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

Closeout-pass nearby natural first-turn prompts:
- `I need to reply to him.`
- `I should reply to my boss.`
- `I need to respond to her.`
- `I should probably respond to him.`
- `I need to send her a note.`
- `I need to send them a note.`
- `I need to write them a message.`
- `I need to write him a message.`
- `I need to message him.`
- `I need to message her.`
- `I should send her a text.`
- `I need to write her back.`
- `I need to email her.`
- `I need to email him.`
- `I need to send a reply.`
- `I need to send a response.`
- `I need to write a reply.`
- `I need to write a response.`

Bounded controls:
- `I need to talk to her.`
- `I need advice about him.`

## Whether a defect was found

Yes.

One final bounded drafting-opener defect remained: nearby `respond to ...` phrasing and generic `send/write a reply/response` first-turn asks still fell through to the generic fallback even though they were clearly in the same drafting/message opener family.

Before repair:
- `I need to respond to her.` -> generic fallback
- `I should probably respond to him.` -> generic fallback
- `I need to send a reply.` -> generic fallback
- `I need to send a response.` -> generic fallback
- `I need to write a reply.` -> generic fallback
- `I need to write a response.` -> generic fallback

After repair:
- all six now route into the existing drafting fork:
  - `Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?`

## Exact code/tests changed if any

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:520)
  - Added the smallest missing drafting aliases to `_request_needs_practical_handle`:
    - `respond to`
    - `send a reply`
    - `send a response`
    - `write a reply`
    - `write a response`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:851)
  - Added the same alias family to `_is_drafting_request` so opener routing and drafting classification stay aligned.

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:403)
  - Added focused regression coverage for:
    - `I need to respond to her.`
    - `I need to send a reply.`
    - `I need to write a response.`

## Exact verification commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "drafting_text_request_gets_concrete_fork or drafting_email_request_gets_concrete_fork or writing_email_to_boss_prompt_gets_drafting_fork or send_message_to_brother_prompt_gets_drafting_fork or should_probably_send_him_a_message_prompt_gets_drafting_fork or text_my_brother_prompt_gets_drafting_fork or should_probably_text_him_prompt_gets_drafting_fork or message_my_brother_prompt_gets_drafting_fork or write_him_back_prompt_gets_drafting_fork or email_my_boss_prompt_gets_drafting_fork or send_note_to_brother_prompt_gets_drafting_fork or write_her_a_message_prompt_gets_drafting_fork or send_my_boss_a_note_prompt_gets_drafting_fork or respond_to_her_prompt_gets_drafting_fork or send_a_reply_prompt_gets_drafting_fork or write_a_response_prompt_gets_drafting_fork or talk_to_brother_prompt_does_not_get_drafting_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need to reply to him.",
    "I should reply to my boss.",
    "I need to respond to her.",
    "I should probably respond to him.",
    "I need to send her a note.",
    "I need to send them a note.",
    "I need to write them a message.",
    "I need to write him a message.",
    "I need to message him.",
    "I need to message her.",
    "I should send her a text.",
    "I need to write her back.",
    "I need to email her.",
    "I need to email him.",
    "I need to send a reply.",
    "I need to send a response.",
    "I need to write a reply.",
    "I need to write a response.",
    "I need to talk to her.",
    "I need advice about him.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Verification results

- `py_compile`: passed
- `pytest`: `17 passed, 174 deselected`
- In-process smoke:
  - all closeout-pass drafting/message prompts above now route to the drafting fork
  - `I need to talk to her.` still routes to the hard-conversation fork
  - `I need advice about him.` still stays on the generic fallback

## Recommendation

Approve and stop here on the truthful boundary.

This closeout pass found one final local alias family, repaired it narrowly, and the standalone drafting/message opener now appears acceptance-complete across the nearby natural first-turn write/send/reply phrasing exercised here. Further widening would risk drifting into broader conversation or relationship-routing work that is outside this seam.
