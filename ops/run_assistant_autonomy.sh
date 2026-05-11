#!/bin/zsh
set -euo pipefail

ROOT="/Users/chris/Desktop/CODE/JARVIS"
PYTHON="$ROOT/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo "JARVIS virtualenv python was not found at $PYTHON" >&2
  exit 1
fi

cd "$ROOT"
exec "$PYTHON" -m jarvis assistant-autonomy-run "$@"
