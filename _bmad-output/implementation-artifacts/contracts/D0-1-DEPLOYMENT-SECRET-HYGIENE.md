---
title: D0.1 Deployment Secret Hygiene and Configuration Proof
status: frozen
owner: architect-office
charter_version: 1.0.0
risk: high
program: JARVIS-GAP-CLOSURE-PROGRAM.md
---

# Frozen Architect Contract: D0.1 Deployment Secret Hygiene and Configuration Proof

## Bounded goal

Remove the committed Chronicle database credential from the deploy configuration and add deterministic, offline evidence that required database inputs are fail-closed and tracked deployment files do not reintroduce literal credentials.

This mission changes repository configuration and validation only. It does not deploy, rotate a live credential, add application authentication, alter database schemas, or change JARVIS runtime product behavior.

## Risk classification

**High.** The diff is small, but it touches production deployment configuration and addresses an exposed credential. Incorrect interpolation can prevent Chronicle or JARVIS services from starting. High-risk routing requires independent QA after Build and no production mutation.

## Architecture invariants

1. No database password or complete credential-bearing database URL may be committed in `deploy/docker-compose.yml`.
2. Chronicle must derive its database URL from the same required `DB_USER` and `DB_PASSWORD` inputs used by the Postgres service; there may not be a second Chronicle-only password source.
3. Missing or empty required database inputs must fail configuration validation before a deploy command can start containers.
4. Validation must be deterministic and runnable without network access, paid services, production credentials, or mutation of the developer environment.
5. Example configuration may contain recognizable non-secret placeholders only and must not be accepted by validation as a deployable production value.
6. The mission must not broaden into authentication, secret rotation, deployment execution, database migration, scheduler activation, or unrelated cleanup.

## Owned paths

- `deploy/docker-compose.yml`
- `.env.example`
- `scripts/verify_deploy_config.py`
- `tests/test_deploy_config.py`

Build may create the two new files above. Existing files outside these paths are read-only.

## Forbidden paths and actions

- `jarvis/**`
- `data/**`
- `.github/workflows/**`
- `docs/**`
- `_bmad-output/**`
- any real `.env` file or secret store
- production hosts, Docker daemon mutation, external services, merge, and push

## Required build list

1. Replace the literal Chronicle database URL credential with required Compose interpolation from `DB_USER` and `DB_PASSWORD`.
2. Preserve the `chronicle` database name, `postgres` host, port `5432`, service dependencies, volumes, and networks.
3. Make required database variables fail closed during Compose interpolation; plain `${VAR}` expansion that silently accepts emptiness is insufficient for the Chronicle URL.
4. Update `.env.example` so the required database variables are present as obvious non-secret placeholders and are distinguishable from production-ready values.
5. Add `scripts/verify_deploy_config.py`, an offline read-only verifier that:
   - exits nonzero for a literal credential-bearing Chronicle URL;
   - exits nonzero when required Chronicle variable interpolation is absent;
   - exits nonzero if the example uses the known exposed password or another production-looking literal in the database fields;
   - exits zero for the corrected repository state;
   - prints concise, actionable failures without echoing discovered secret values.
6. Add focused tests covering the passing repository state and isolated failing fixtures for every verifier rejection above.

## Acceptance criteria

### AC1 — No committed Chronicle credential

Given the Build diff and committed target, when QA inspects `deploy/docker-compose.yml`, then `CHRONICLE_DATABASE_URL` contains required variable interpolation and no literal username/password pair from the previous URL.

### AC2 — Required-input posture

Given missing or empty `DB_USER` or `DB_PASSWORD`, when Compose interpolation is evaluated or the offline verifier inspects the file, then validation fails before container startup and identifies the missing variable without revealing any credential.

### AC3 — Preserved topology

Given the corrected Compose file, when QA compares the Chronicle service topology with the baseline, then the database name remains `chronicle`, the host remains `postgres`, the port remains `5432`, and dependencies, volumes, and networks are unchanged.

### AC4 — Safe example configuration

Given `.env.example`, when QA inspects its database fields, then required variables are documented with clearly non-secret placeholders and no value from the exposed Chronicle URL remains.

### AC5 — Deterministic verifier

Given the corrected checkout, when QA runs `python3 scripts/verify_deploy_config.py`, then it exits `0`. Given each isolated unsafe fixture, the verifier exits nonzero with a redacted actionable reason.

### AC6 — Focused regression evidence

Given the completed implementation, when QA runs `python3 -m pytest -q tests/test_deploy_config.py`, then every positive and negative case passes. `git diff --check` must also pass.

### AC7 — Scope integrity

Given Build evidence, when QA lists changed files, then every changed path is in the owned-path list and no real secret, runtime data, workflow, product code, or production state was modified.

## Build order

1. Add failing verifier fixtures/tests for the current literal-credential and missing-required-interpolation states.
2. Implement the offline verifier until the negative fixtures fail safely and redact values.
3. Correct `deploy/docker-compose.yml` with required shared-variable interpolation.
4. Correct `.env.example` placeholders and documentation.
5. Run focused tests, the verifier, Compose configuration rendering if locally available, and `git diff --check`.
6. Commit only the owned paths and return exact changed-file and test evidence to Orchestration.

## Required QA evidence

- Immutable implementation commit and clean target worktree.
- Exact changed-file list.
- `python3 scripts/verify_deploy_config.py` output and exit status.
- `python3 -m pytest -q tests/test_deploy_config.py` output.
- `git diff --check` output.
- Static comparison proving preserved Chronicle topology.
- Confirmation that no real `.env`, production host, merge, or push was touched.

Missing evidence is blocking. QA may not infer safety from a passing prose report.

## Residual risk and required human follow-up

The previously committed credential must be treated as exposed. Rotation of the live database credential and verification of the production `.env` are required human/operations follow-ups, explicitly outside this Build mission. This contract does not claim that repository remediation rotates or invalidates the exposed value.

## Finding disposition rule

- Any violation of an invariant, owned-path boundary, or acceptance criterion is an **implementation defect** unless the contract itself proves technically impossible or contradictory.
- A technically impossible or contradictory requirement returns to Architect as a **contract defect**; Build must not substitute another design silently.
- Additional secret-management improvements outside this bounded goal are **optional improvements** or later D0 contracts and must not expand this mission.
