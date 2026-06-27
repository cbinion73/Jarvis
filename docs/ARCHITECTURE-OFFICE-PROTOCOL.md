# Architecture Office Protocol

Architect Office is a repo-local governance program for building JARVIS. It is separate from the `jarvis/` runtime product and exists to enforce process, phase discipline, truthfulness, and product direction before Architecture Office gives product judgment.

Architect Office does not replace Chris or ChatGPT Architecture Office. Chris remains owner. Architecture Office still owns product and architecture decisions. Build Office implements. QA verifies. Architect Office decides what should be built, what evidence is required, and whether the resulting work is acceptable for product review.

Approval flow:

1. Architect Office defines the active slice, boundaries, and evidence bar.
2. Build Office first determines whether the main repo is already clean enough for fair review.
3. If the main repo is mixed, Build Office must start in a clean sibling worktree/clone or another explicitly isolated review target before implementation begins.
4. Build Office works only inside that scope and returns the required report.
5. QA verifies the claims and highlights regressions, gaps, and residual risks.
6. Architect Office reviews the code, evidence, QA findings, and canon fit.
7. Architecture Office decides whether the work should stand.

Guardrails:

- JARVIS does not approve itself.
- Build Office does not approve itself.
- QA does not self-implement the missing feature and then call it verified.
- No task is complete until Architecture Office review exists.
- Procedural approval never overrides product vision.
- Repo cleanliness, report completeness, and evidence are mandatory inputs to review.
- Architect Office should default to understanding first, then directing, then approving.
- If the main repo is mixed, isolated-first execution is the default, not an optional cleanup pass after implementation.

Isolated-first rule:

- Architect Office should prefer bounded slices that are implemented directly in a clean sibling worktree or clean clone when the main repo is already mixed.
- Architect Office should prefer `git worktree` isolation before creating a brand-new clone.
- Architect Office should prefer reusing a named clean workspace family when that preserves clarity and does not contaminate slice boundaries.
- Architect Office should treat “implement in mixed repo, then isolate for approval” as an exception path, not the standard path.
- Build requests should explicitly say whether the slice must start in:
  - the main repo, because the repo is already clean enough
  - or a clean isolated review target, because the main repo is mixed
- Architecture Review should record the execution target so approval does not require rediscovering where clean truth lives.
- Fresh clones should be reserved for cases where:
  - worktree reuse would blur slice boundaries
  - the needed git state cannot be represented cleanly as a sibling worktree
  - or the local repo state makes worktree use unsafe or confusing
