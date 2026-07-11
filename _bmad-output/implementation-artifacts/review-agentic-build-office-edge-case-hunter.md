# Edge Case Hunter Review Assignment

Work read-only in `/Users/chris/Desktop/CODE/JARVIS-codex-build-office`.

Do not edit, format, stage, commit, switch branches, clean files, create worktrees, merge, or push.

Invoke the `bmad-review-edge-case-hunter` skill on the complete change from baseline `df73198769cf7c592fa7ba2368883148caa6cebc`.

The complete review surface is:

- tracked diff: `git diff df73198769cf7c592fa7ba2368883148caa6cebc -- .gitignore`
- `_bmad-output/implementation-artifacts/spec-agentic-build-office-control-plane.md`
- `docs/BUILD-OFFICE-AUTOMATION.md`
- `jarvis/build_office.py`
- `scripts/jarvis_build_office.py`
- `tests/test_build_office.py`

Read every file completely. Walk every branch and boundary condition, especially concurrent mission creation, stale and expired leases, glob-overlap detection, symlinks and path aliases, occupied worktrees, branch reuse, CLI absence, process timeout/crash, review ordering, failed evidence, dirty repositories, state corruption, cleanup, critical approval, and release readiness.

Return only unhandled edge cases. For each include consequence, exact file and line, triggering inputs/state, and expected safe behavior. If all meaningful cases are handled, state that explicitly. Do not implement corrections.
