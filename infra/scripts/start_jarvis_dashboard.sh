#!/bin/zsh
set -euo pipefail

ROOT="/Users/chris/Desktop/CODE/JARVIS"
VENV_PYTHON="$ROOT/.venv/bin/python"

cd "$ROOT"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Missing virtualenv python at $VENV_PYTHON" >&2
  exit 1
fi

# launchd doesn't inherit the user shell env, so python-dotenv handles most vars.
# Force TCP for Postgres: Unix socket connections time out from launchd context
# (Postgres.app socket at /tmp/.s.PGSQL.5432 is ready before JARVIS fully starts,
# but non-blocking libpq on the Unix socket path stalls in launchd; TCP is stable).
export GHOSTWRITR_DB_URL="postgresql://chris@127.0.0.1:5432/book_platform_builder"

exec "$VENV_PYTHON" -m jarvis serve --host 0.0.0.0 --port 8787
