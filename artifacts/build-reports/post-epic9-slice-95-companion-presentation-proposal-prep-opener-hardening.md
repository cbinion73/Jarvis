# Post-Epic 9 Slice 95: Companion Presentation / Proposal Prep Opener Hardening

Ready for Architect Office review: yes

## Exact prompts tested

Repaired presentation / proposal prep prompts:
- `I need help with this presentation.`
- `I need help getting ready for this presentation.`
- `I need help with this proposal.`
- `I need help getting ready for this proposal.`

Preserved nearby controls rechecked:
- `I need help with this meeting agenda.`
- `I need help with my inbox.`
- `I need help drafting an email to my boss.`
- `I need help with a hard conversation.`
- `I need help deciding between two apartments.`
- `I need help planning tomorrow.`

## Exact code/tests changed

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:417)
  - Added a standalone first-turn presentation / proposal prep opener fork ahead of the inbox, meeting, and generic practical fallbacks.
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:662)
  - Added `_is_presentation_or_proposal_prep_request(...)` as the narrow seam-local matcher for the four presentation/proposal prep phrases above.

New prep opener reply:
- `Good. Is the real work the point you need to land, the structure, or getting ready to deliver it cleanly?`

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:267)
  - Added focused coverage for the four presentation / proposal prep prompts above.

## Exact commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "help_with_this_presentation_prompt_gets_concrete_prep_fork or getting_ready_for_this_presentation_prompt_gets_concrete_prep_fork or help_with_this_proposal_prompt_gets_concrete_prep_fork or getting_ready_for_this_proposal_prompt_gets_concrete_prep_fork or meeting_agenda_prompt_gets_concrete_meeting_fork or help_with_my_inbox_prompt_gets_concrete_inbox_fork or drafting_email_to_boss_prompt_gets_drafting_fork or hard_conversation_prompt_gets_concrete_conversation_fork or decision_shaped_job_prompt_gets_decision_fork or help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this presentation.",
    "I need help getting ready for this presentation.",
    "I need help with this proposal.",
    "I need help getting ready for this proposal.",
    "I need help with this meeting agenda.",
    "I need help with my inbox.",
    "I need help drafting an email to my boss.",
    "I need help with a hard conversation.",
    "I need help deciding between two apartments.",
    "I need help planning tomorrow.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Exact results

- `py_compile`: passed
- focused pytest: `10 passed, 276 deselected`
- in-process smoke:
  - all four presentation / proposal prep prompts now route to:
    - `Good. Is the real work the point you need to land, the structure, or getting ready to deliver it cleanly?`
  - preserved nearby controls still behave correctly:
    - `I need help with this meeting agenda.` stays on the meeting fork
    - `I need help with my inbox.` stays on the inbox fork
    - `I need help drafting an email to my boss.` stays on the drafting fork
    - `I need help with a hard conversation.` stays on the hard-conversation fork
    - `I need help deciding between two apartments.` stays on the concrete decision fork
    - `I need help planning tomorrow.` stays on the tomorrow-planning fork

## Scope safety

This repair stayed inside the smallest existing first-turn companion opener seam only:
- no broad chief-of-staff redesign
- no fake presentation, proposal, audience, or deliverable context claims
- no broad planning-system rewrite
- no changes to unrelated inbox, meeting, drafting, conversation, decision, tomorrow-planning, vacation, retirement, or capability seams

## Architect recommendation

Approve.

This slice fixes the concrete presentation / proposal prep family opener weakness with one narrow prep fork and focused regression coverage, while preserving the adjacent hardened seams unchanged.
