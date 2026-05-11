#!/bin/zsh
set -euo pipefail

ROOT="/Users/chris/Desktop/CODE/JARVIS"
NODE_BIN="/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
NODE_MODULES="/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"

cd "$ROOT"

export NODE_PATH="$NODE_MODULES${NODE_PATH:+:$NODE_PATH}"

"$NODE_BIN" "$ROOT/tests/e2e/run-all-e2e.cjs"
