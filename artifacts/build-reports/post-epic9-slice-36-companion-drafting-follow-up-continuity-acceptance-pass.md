# Post-Epic 9 Slice 36: Companion Drafting Follow-Up Continuity Acceptance Pass

## A. Files Changed
- `jarvis/companion_spine.py`
- `tests/test_companion_spine.py`
- `artifacts/build-reports/post-epic9-slice-36-companion-drafting-follow-up-continuity-acceptance-pass.md`

## B. Scope Reviewed
- The existing companion drafting follow-up seam only.
- Second-turn follow-ups after the concrete drafting fork, especially short natural replies around tone, audience, length, and nearby drafting-language aliases a real user would plausibly send.
- Focused in-process smoke behavior after:
  - `Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?`

## C. Defects Found
- Found one remaining bounded second-turn continuity weakness: the drafting seam was still too literal about short drafting-parameter replies and reset to the generic `short version` fallback for nearby tone synonyms plus audience-only and length-only follow-ups.
- Confirmed failure examples before repair:
  - `formal`
  - `for my boss`
  - `short`
  - `just text him`

## D. Bounded Repairs Made
- Repaired only that one drafting-parameter continuity weakness in `jarvis/companion_spine.py`:
  - nearby tone synonyms now stay inside the drafting seam
    - `gentler` -> warm
    - `formal` / `careful` -> diplomatic
    - `direct` -> blunt
  - audience-only short replies now stay inside the drafting seam
    - `for my boss`
    - `to my brother`
  - length-only short replies now stay inside the drafting seam
    - `short`, `keep it short`, `brief`, `concise`
    - `longer`
  - text-shorthand replies now stay inside the drafting seam
    - `just text him`
- Added focused regression coverage in `tests/test_companion_spine.py` for:
  - `formal`
  - `for my boss`
  - `short`
  - `just text him`

## E. Truth Guarantees Preserved
- Stayed inside the existing companion conversation seam only.
- No new architecture, memory behavior, capability-copy work, therapist drift, or general conversation redesign.
- No fake retrieval, execution, or autonomy claims were introduced.
- The seam stays concrete and useful without pretending JARVIS already knows the audience, length, or final copy details.

## F. Tests / Validation
- Compile proof:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
  - Result: passed
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "drafting_text_request_gets_concrete_fork or drafting_email_request_gets_concrete_fork or drafting_follow_up_warm_gets_concrete_continuation or drafting_follow_up_actual_draft_gets_concrete_continuation or drafting_follow_up_warmer_alias_stays_inside_drafting_thread or drafting_follow_up_write_it_alias_stays_inside_drafting_thread or drafting_follow_up_formal_alias_stays_inside_drafting_thread or drafting_follow_up_audience_only_stays_inside_drafting_thread or drafting_follow_up_length_only_stays_inside_drafting_thread or drafting_follow_up_text_alias_stays_inside_drafting_thread"`
  - Result: `10 passed, 69 deselected in 0.15s`
- Compact in-process smoke proof:
  - `python3 - <<'PY'`
  - `from jarvis.companion_spine import generate_companion_fallback`
  - `packet = {'available_capabilities': ['ongoing conversation in this shell', 'conversation turn persistence'], 'conversation_excerpt': ("Chris: Help me draft a text to my brother\n" "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?")}`
  - `for prompt in ['formal', 'gentler', 'for my boss', 'to my brother', 'short', 'keep it short', 'longer', 'brief', 'concise', 'just text him']:`
  - `    print(f'{prompt}: {generate_companion_fallback(prompt, packet)}')`
  - `PY`
  - Result highlights:
    - `formal` -> stayed inside the diplomatic drafting branch
    - `gentler` -> stayed inside the warm drafting branch
    - `for my boss` and `to my brother` -> stayed inside the audience-aware drafting branch
    - `short`, `keep it short`, `brief`, `concise`, and `longer` -> stayed inside the length-aware drafting branch
    - `just text him` -> stayed inside the text drafting branch

## G. Residual Risks
- This slice intentionally stayed bounded to the drafting follow-up seam only.
- I did not broaden into general drafting UX, object creation, memory behavior, or broader conversation redesign.
- Unrelated dirty-tree capability-copy drift plus previously approved overloaded-week and decision-follow-up seam changes were left untouched.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-36-companion-drafting-follow-up-continuity-acceptance-pass.md`

## I. Recommendation
- Ready for Architect Office review: yes
