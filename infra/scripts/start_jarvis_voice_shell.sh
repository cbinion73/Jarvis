#!/bin/zsh
set -euo pipefail

ROOT="/Users/chris/Desktop/CODE/JARVIS"
VENV_PYTHON="$ROOT/.venv/bin/python"

cd "$ROOT"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Missing virtualenv python at $VENV_PYTHON" >&2
  exit 1
fi

exec "$VENV_PYTHON" -m jarvis voice --text-loop
