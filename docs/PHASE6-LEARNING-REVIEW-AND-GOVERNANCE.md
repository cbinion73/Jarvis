# Phase 6: Learning Review and Governance

Phase 6 makes JARVIS learning visible, reviewable, and safer for a real household.

## What this phase adds

- A learning review surface for each person
- Explicit approve and reject actions for learning proposals
- The ability to retire durable profile facts
- Child-safe review boundaries
- Stronger anticipation signals beyond the morning window

## Learning review

New API:

- `GET /api/learning-review`
- `POST /api/learning/proposals/{proposal_id}`
- `POST /api/learning/facts/{fact_id}`

The learning review payload combines:

- adaptive persona snapshot
- pending memory proposals for the selected person
- active durable profile facts
- recent First Light history
- governance capabilities for the viewer

## Review actions

Reviewers can now:

- approve a proposal into durable memory
- reject a proposal
- retire a durable fact when it is stale or wrong

This keeps the learning system editable instead of silently accreting certainty.

## Child-safe boundaries

Children may only review their own learning profile.

Adults can review the full household learning layer, but the system still respects the underlying memory access rules for personal and child-private facts.

## Anticipation expansion

Adaptive persona snapshots now look beyond First Light alone. They can also factor in:

- near-term calendar pressure
- pending approvals
- approved durable profile facts
- connected presence signals

This is still intentionally conservative. It is an anticipation layer, not a surveillance layer.
