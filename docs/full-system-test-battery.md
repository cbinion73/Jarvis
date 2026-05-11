# JARVIS Full-System Test Battery

This is the maintenance battery for the current JARVIS platform after the identity, memory, First Light, provider, and connected-device work.

## What it covers

- platform health and root shell reachability
- core API seam checks
- First Light, persona, and learning-review endpoints
- downloadable TTS generation
- shell interactivity through Playwright
- Connected Devices admin view
- Catalyst packet routing
- Model Forge generation, downloads, and viewer state
- Vision modal controls with a stubbed camera
- Identity and device admin mutation with rollback
- Memory proposal, fact-governance, and curation integrity with rollback
- Approval queue mutation and history integrity with rollback

## Run

```bash
NODE_PATH=/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
/Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-full-system.e2e.cjs
```

Run the full maintenance suite:

```bash
NODE_PATH=/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
/Users/chris/Desktop/CODE/JARVIS/tests/e2e/run-all-e2e.cjs
```

Run the focused workbench battery directly:

```bash
NODE_PATH=/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
/Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-workbench.e2e.cjs
```

Run the identity admin mutation battery directly:

```bash
NODE_PATH=/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
/Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-identity-admin.e2e.cjs
```

Run the memory governance battery directly:

```bash
NODE_PATH=/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
/Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-memory-governance.e2e.cjs
```

Run the approval queue battery directly:

```bash
NODE_PATH=/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
/Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-approval-queue.e2e.cjs
```

Or use the wrapper:

```bash
/Users/chris/Desktop/CODE/JARVIS/ops/run_playwright_qa.sh
```

## Artifacts

- JSON report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-full-system-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-full-system-report.json)
- screenshots: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/screenshots](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/screenshots)
- suite report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-e2e-suite-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-e2e-suite-report.json)
- suite summary: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-e2e-suite-summary.md](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-e2e-suite-summary.md)
- workbench report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-workbench-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-workbench-report.json)
- identity admin report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-identity-admin-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-identity-admin-report.json)
- memory governance report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-memory-governance-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-memory-governance-report.json)
- approval queue report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-approval-queue-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-approval-queue-report.json)

## Maintenance note

Use this battery as the first stop after major shell, provider, identity, or packet changes. It is meant to catch:

- dead shell buttons
- stale packet selectors
- broken modal routing
- identity/device admin regressions
- TTS provider outages without a local downloadable fallback
- Model Forge viewer or download regressions
- Vision packet control regressions even when no real camera is attached
- identity, device, or service-plan save paths that fail to round-trip cleanly
- learning proposals, profile facts, or curation paths that drift or leave residue behind
- approval queue transitions or related family/workshop records that stop matching each other
