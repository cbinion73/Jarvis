# QA Team Protocol

QA exists as a separate function from Build Office.

Its job is not to implement features.

Its job is to verify what is real, catch regressions, challenge weak evidence, and protect the product from false confidence.

## Role

QA is responsible for:

- testing Build Office claims
- reproducing important behavior
- checking for regressions
- checking truthfulness of runtime evidence
- checking that the changed slice matches canon and phase scope
- identifying what is proven, what is assumed, and what is unverified

QA does not:

- set product direction
- approve product doctrine changes
- silently implement missing behavior for Build Office
- accept test output as sufficient if runtime claims are stronger than the proof

## Required QA Questions

For every build slice, QA should ask:

1. What exactly changed?
2. What was actually tested?
3. What user-facing behavior was proven?
4. What was only unit-tested or text-asserted?
5. What could have regressed on the main path?
6. What claims were made without enough evidence?

## Evidence Standard

Strong evidence:

- passing targeted tests that actually exercise the changed behavior
- runtime smoke with exact prompts, routes, and observed outputs
- direct route or file inspection when the claim is structural
- before/after proof for a known regression

Weak evidence:

- tests that only assert strings exist in source files
- compile success presented as behavior proof
- generic “works locally” claims without prompt-level evidence
- claims about retrieval, memory, tools, or agents without output proof

## QA Outcomes

QA should classify results as:

- proven
- partially proven
- unproven
- contradicted by code or runtime evidence

QA should surface:

- regressions
- scope drift
- missing tests
- misleading claims
- residual risk

## Separation

Build Office implements.

QA tests.

Architect Office defines, directs, and approves.

No function self-certifies its own work.
