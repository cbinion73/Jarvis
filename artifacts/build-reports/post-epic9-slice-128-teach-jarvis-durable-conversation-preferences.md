# Build Office Report

## A. Start State

- branch: `phase-1-companion-spine`
- starting commit:
  - mixed main repo; bounded slice added on top of existing active worktree
- git status:
  - main repo already contained unrelated tracked and untracked changes
  - this slice stayed inside the conversation + memory seam only

## B. Scope

- requested scope:
  - keep `/correct` as thread-local self-correction
  - add a durable command so Chris can teach Jarvis a reply preference that persists into future conversations
- phase:
  - post-epic9 bounded companion hardening
- non-goals:
  - broad memory redesign
  - hosted deployment proof
  - UI redesign beyond minimal command discoverability text

## C. Files Changed

- file: `jarvis/companion_spine.py`
  - purpose:
    - expanded correction parsing to support `/teach`
    - carried correction mode into the companion context packet
    - taught fallback rewrite path to acknowledge carry-forward behavior
- file: `jarvis/runtime.py`
  - purpose:
    - added `/teach` parsing and durable preference storage through existing memory support
    - promoted conversation-style preferences into always-relevant known facts for future companion turns
    - returned `taught_preference` in the conversation response payload
- file: `jarvis/memory.py`
  - purpose:
    - allowed durable memory writes to carry explicit provenance
    - preserved `instruction` provenance when promoting profile facts
- file: `jarvis/voice_ui.py`
  - purpose:
    - exposed `/teach` in the main shell composer placeholder
- file: `jarvis/chat_only_page.py`
  - purpose:
    - exposed `/teach` in the chat-only composer placeholder
- file: `tests/test_companion_spine.py`
  - purpose:
    - added coverage for `/teach` packet context, fallback rewrite, durable teaching storage, and conversation-style preference resurfacing

## D. Tests / Validation

- command:
  - `python3 -m pytest tests/test_companion_spine.py -q`
- result:
  - `364 passed in 0.31s`

- command:
  - `python3 -m pytest tests/test_voice_ui_conversation_posture.py -q`
- result:
  - `5 passed in 0.02s`

- command:
  - `python3 -m py_compile jarvis/companion_spine.py jarvis/runtime.py jarvis/memory.py jarvis/voice_ui.py jarvis/chat_only_page.py`
- result:
  - passed

## E. Runtime Evidence

- command:
  - `curl -fsS http://127.0.0.1:8787/health`
- result:
  - active local runtime restarted on current code
  - `startup_vs_disk: false`

- command:
  - local memory verification after `/teach`:
  - `python3 - <<'PY' ... JarvisRuntime.from_env() ... profile_facts(...) ... PY`
- result:
  - durable fact present:
  - `Chris prefers Jarvis replies to be more practical about timing and walking`
  - tags include:
  - `personal,preference,conversation-style,teach-jarvis,jarvis`
  - provenance:
  - `instruction`

- command:
  - `/api/respond` end-to-end `/teach` probe
- result:
  - server was on current build, but a clean end-to-end response proof was not captured in this pass because live request probing stalled while unrelated runtime noise was present
  - no false claim is made that a complete local response transcript was captured

## F. Truthfulness / Safety

- capability claims made:
  - `/teach` now stores a durable conversation-style preference
  - future companion turns can surface those preferences through known profile facts
  - `/correct` remains thread-local
- evidence paired:
  - green tests on the exact bounded seam
  - current-code runtime health proof
  - direct profile-fact readback showing stored preference and `instruction` provenance
- unresolved truth risks:
  - live `/api/respond` response transcript for `/teach` was not captured cleanly in this pass
  - companion quality outside this seam is unchanged

## G. Risks / Limitations

- known risks:
  - conversation-style preferences now get baseline priority in `_relevant_profile_facts`, so future preference growth should be kept curated
- limitations:
  - this proves local durable storage and retrieval, not hosted rollout behavior
  - unrelated local runtime warnings and connector failures remain outside this slice

## H. Commit

- commit hash:
  - not created in the mixed main repo during this pass
- final git status:
  - main repo remains mixed

## I. Ready for Architecture Review

- yes or no:
  - yes
- blocking issues:
  - none for bounded review of the `/teach` durable-preference slice
