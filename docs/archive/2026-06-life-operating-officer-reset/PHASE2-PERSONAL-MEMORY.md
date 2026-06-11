# Phase 2: Personal Memory Partitions

Phase 2 makes JARVIS memory personal in a real, enforceable way.

## What changed

- Every memory entry can now declare:
  - `subject_user_id`
  - `access_policy`
  - `boundary_label`
  - `source_type`
  - `confidence`
- Personal and restricted memory lanes now stay local-first by default.
- Approved memory can be promoted into durable per-person `profile facts`.
- A nightly curation pass can scan approved memory and rebuild profile facts.

## Access policies

- `personal`
  - about one person
  - visible to that person and adults
- `shared`
  - safe to reuse in collaborative/project contexts
- `household`
  - household continuity, routines, and shared planning
- `restricted`
  - private or sensitive; strongly local-first

## Durable profile facts

Profile facts are distilled continuity records created from approved memories.

Examples:

- Chris prefers the executive brief after coffee.
- Anna likes reminders after breakfast.
- Caleb responds better to quiz-style coaching.

These are stored in:

- `data/memory/profile_facts.json`

## Endpoints

- `GET /api/memory-overview?viewer=Chris`
- `GET /api/memory-review?viewer=Chris`
- `GET /api/memory-profiles?viewer=Chris`
- `POST /api/memory-remember`
- `POST /api/memory-curation/run`

## Notes

- This phase does not yet make JARVIS infer identity from voice or face.
- It does give JARVIS a clean memory partition model so later adaptation can stay honest.
- Restricted and child-private memory should remain local-first unless explicitly reworked later.
