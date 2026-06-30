# Post-Epic 9 Slice 35: Companion Drafting Follow-Up Continuity Hardening

## A. Files Changed
- `jarvis/companion_spine.py`
- `tests/test_companion_spine.py`
- `artifacts/build-reports/post-epic9-slice-35-companion-drafting-follow-up-continuity-hardening.md`

## B. Scope Reviewed
- The existing companion drafting follow-up seam only.
- Second-turn follow-ups after the concrete drafting fork, especially short natural replies around tone, direct-write intent, audience, and length.
- Focused in-process smoke behavior for natural drafting follow-ups after:
  - `Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?`

## C. Defects Found
- Found one real bounded continuity weakness: the drafting seam was too literal about short natural follow-ups and dropped some common tone/direct-write variants into the generic `short version` fallback.
- Confirmed failure examples before repair:
  - `a little warmer`
  - `just write it`

## D. Bounded Repairs Made
- Repaired only that one alias-brittleness defect in `jarvis/companion_spine.py`:
  - tone follow-up matching now keeps short `warm` variants inside the drafting seam
  - direct-write aliases like `just write it`, `write it`, and `just draft it` now stay inside the actual-draft branch
- Added focused regression coverage in `tests/test_companion_spine.py` for:
  - `a little warmer`
  - `just write it`

## E. Truth Guarantees Preserved
- Stayed inside the existing companion conversation seam only.
- No new architecture, memory behavior, capability-copy work, therapist drift, or general conversation redesign.
- No fake retrieval, execution, or autonomy claims were introduced.
- The repair keeps the follow-up concrete and drafting-shaped without pretending JARVIS already knows the audience, facts, or final wording.

## F. Tests / Validation
- Compile proof:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
  - Result: passed
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "drafting_text_request_gets_concrete_fork or drafting_email_request_gets_concrete_fork or drafting_follow_up_warm_gets_concrete_continuation or drafting_follow_up_actual_draft_gets_concrete_continuation or drafting_follow_up_warmer_alias_stays_inside_drafting_thread or drafting_follow_up_write_it_alias_stays_inside_drafting_thread"`
  - Result: `6 passed, 69 deselected in 0.24s`
- Compact in-process smoke proof:
  - `python3 - <<'PY'`
  - `from jarvis.companion_spine import generate_companion_fallback`
  - `packet = {'available_capabilities': ['ongoing conversation in this shell', 'conversation turn persistence'], 'conversation_excerpt': ("Chris: Help me draft a text to my brother\n" "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?")}`
  - `for prompt in ['a little warmer', 'just write it', 'warm', 'actual draft', 'short', 'for my boss']:`
  - `    print(f'{prompt}: {generate_companion_fallback(prompt, packet)}')`
  - `PY`
  - Result highlights:
    - `a little warmer` -> stayed inside the warm drafting branch
    - `just write it` -> stayed inside the actual-draft branch
    - `short` and `for my boss` still fall back generically and were not broadened in this slice

## G. Residual Risks
- This slice intentionally fixed only the tone/direct-write alias brittleness defect.
- Audience-only and length-only short replies were inspected but left untouched to keep the slice bounded to one real continuity weakness.
- Unrelated dirty-tree capability-copy drift and previously approved overloaded-week / decision-follow-up seam changes were left untouched.

## H. Artifact Path
- `artifacts/build-reports/post-epic9-slice-35-companion-drafting-follow-up-continuity-hardening.md`

## I. Recommendation
- Ready for Architect Office review: yes
