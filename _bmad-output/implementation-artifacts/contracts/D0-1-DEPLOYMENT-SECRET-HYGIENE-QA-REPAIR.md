---
title: D0.1 Deployment Secret Hygiene QA Repair
status: frozen
owner: architect-office
charter_version: 1.0.0
risk: high
parent_contract: D0-1-DEPLOYMENT-SECRET-HYGIENE.md
parent_implementation_commit: 44185456511efdb07e4cd43e04cd4f651f2818d3
---

# Frozen Architect Contract: D0.1 Deployment Secret Hygiene QA Repair

## Bounded Goal

Repair the D0.1 deployment secret hygiene implementation based on the live Codex review findings from the recovered QA dispatch.

The repair must preserve the original D0.1 goal: remove committed Chronicle database credentials and provide deterministic offline validation. It must not deploy, rotate credentials, modify real `.env` files, change application authentication, alter database schemas, or touch production systems.

## Finding Disposition

### Finding 1: URI-reserved password characters break database URLs

Classification: implementation defect.

The current `postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/...` interpolation can produce invalid URLs when `DB_PASSWORD` contains URI-reserved characters such as `@`, `:`, `/`, `#`, or `%`. D0.1 explicitly exists to make deployment configuration safer; a configurable secret that breaks normal strong-password characters is not acceptable without an explicit validation boundary.

Repair requirement: fail closed with deterministic offline validation unless the configured password is safe for the URL form actually used by `docker-compose.yml`. If the implementation cannot encode in Compose, it must make the constraint explicit in tracked examples and verifier failures. It may not silently accept unsafe values.

### Finding 2: deploy-side environment template is unguarded

Classification: contract defect repaired by this contract.

The original D0.1 owned paths omitted `deploy/.env.example`, but the live repository has a tracked deploy-side template used by deployment setup. Secret hygiene validation that checks only root `.env.example` is incomplete.

Repair requirement: include `deploy/.env.example` in this repair scope and ensure it cannot retain literal credential-bearing database URLs or production-looking database values.

## Owned Paths

- `.env.example`
- `deploy/.env.example`
- `deploy/docker-compose.yml`
- `scripts/verify_deploy_config.py`
- `tests/test_deploy_config.py`

No other files may change.

## Forbidden Paths and Actions

- `jarvis/**`
- `docs/**`
- `_bmad-output/**`
- `.github/**`
- `data/**`
- any real `.env` file
- production hosts
- Docker daemon mutation
- credential rotation
- merge
- push

## Acceptance Criteria

1. Given the repair commit, when QA lists changed files from `44185456511efdb07e4cd43e04cd4f651f2818d3` to the repair commit, then every changed file is in the owned-path list above and no forbidden file changed.
2. Given `deploy/docker-compose.yml`, when QA inspects Chronicle, Catalyst, and JARVIS Home database URLs, then no literal credential remains and every database URL still fails closed on required database inputs.
3. Given unsafe database password examples containing URI-reserved characters that would break the configured URL form, when `python3 scripts/verify_deploy_config.py` runs against an isolated fixture, then it exits nonzero with a concise redacted failure.
4. Given root `.env.example` and `deploy/.env.example`, when the verifier inspects them, then both use non-secret placeholders and neither contains the exposed Chronicle credential nor a production-looking database password.
5. Given the corrected checkout, when QA runs `python3 scripts/verify_deploy_config.py`, then it exits `0`.
6. Given focused regression tests, when QA runs `python3 -m pytest -q tests/test_deploy_config.py`, then every positive and negative case passes.
7. Given the repair commit, when QA runs `git diff --check 44185456511efdb07e4cd43e04cd4f651f2818d3..<repair_commit>`, then it exits `0`.
8. Given the repair commit, when QA runs the recovered control-plane review dispatch or an independent read-only review, then no unsupported Codex flag failure, false `.env.example` scope violation, or unpreserved review evidence history recurs.

## Build Order

1. Add failing focused tests for unsafe URL-reserved `DB_PASSWORD` values.
2. Add failing focused tests for `deploy/.env.example` retaining literal database URLs or production-looking database credentials.
3. Update verifier logic to validate both root and deploy example files and to reject unsafe URL-form password inputs without printing secrets.
4. Update tracked example files and Compose configuration only as needed to satisfy the verifier and preserve D0.1 topology.
5. Run:
   - `python3 scripts/verify_deploy_config.py`
   - `python3 -m pytest -q tests/test_deploy_config.py`
   - `git diff --check 44185456511efdb07e4cd43e04cd4f651f2818d3..<repair_commit>`
   - `git diff --name-only 44185456511efdb07e4cd43e04cd4f651f2818d3..<repair_commit>`

## Required Build Evidence

Build must return:

- baseline commit: `44185456511efdb07e4cd43e04cd4f651f2818d3`
- repair commit
- exact changed-file list
- clean worktree status
- refreshed target fingerprint
- command outputs and exit statuses for every command in Build Order step 5
- explicit note that no real `.env`, production host, Docker daemon, merge, push, or credential rotation occurred.
