# Canon Registry

Architect Office should not treat every repo document as equal. This registry defines what is binding canon, what is useful reference, and what is historical only. As of the 2026-07-08 doc consolidation, canon is deliberately narrow: one living doc plus the two Chris-context files that live code reads directly.

## Canon

- `docs/README.md` [canon] single canonical doc — product identity, architecture, current state, blockers; supersedes all prior roadmap/status/vision docs
- `docs/CHRIS-INTENT-CANON.md` [canon] voice/tone spec and Truth Contract, read directly by `jarvis/companion_spine.py`
- `docs/CHRIS-CONTEXT-CANON.md` [canon] Chris context, taste, life domains, read directly by `jarvis/companion_spine.py`

## Reference

- `docs/QA-TEAM-PROTOCOL.md` [reference] evidence-quality bar for verification, still generically useful
- `docs/JARVIS-AG2-ADOPTION-MAP.md` [reference] technical build-vs-buy analysis, not vision

## Deprecated / Archive

Everything else previously listed as canon or reference was consolidated into `docs/README.md` and archived to `docs/archive/2026-07-doc-consolidation/` on 2026-07-08 — household-OS/Life-Operating-Officer/civilization-scale vision docs, phase plans, and process protocols whose durable facts (if any) were folded into the new doc. See that folder and `docs/README.md`'s changelog for what moved.

Earlier archive material remains at `docs/archive/2026-06-life-operating-officer-reset/`.

## Rules

- Architect Office reviews against Canon entries, not the whole docs tree.
- Reference entries may inform review, but they do not override Canon.
- Deprecated and archive entries are historical only.
- Stale docs must not override current phase gates or Chris canon.
