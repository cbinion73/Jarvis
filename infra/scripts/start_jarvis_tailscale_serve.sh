#!/bin/zsh
set -euo pipefail

TAILSCALE_BIN="$(command -v tailscale || true)"
if [[ -z "$TAILSCALE_BIN" ]]; then
  echo "tailscale CLI not found; skipping remote-access bootstrap."
  exit 0
fi

JARVIS_HEALTH_URL="${JARVIS_HEALTH_URL:-http://127.0.0.1:8787/health}"
JARVIS_TARGET="${JARVIS_TARGET:-localhost:8787}"

if ! curl -fsS --max-time 5 "$JARVIS_HEALTH_URL" >/dev/null 2>&1; then
  echo "JARVIS not healthy on $JARVIS_HEALTH_URL; skipping tailscale serve refresh."
  exit 0
fi

STATUS_JSON="$("$TAILSCALE_BIN" status --json 2>/dev/null || true)"
if [[ -z "$STATUS_JSON" ]]; then
  echo "Tailscale not connected yet; skipping remote-access bootstrap."
  exit 0
fi

BACKEND_STATE="$(
  STATUS_JSON="$STATUS_JSON" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["STATUS_JSON"])
print(str(payload.get("BackendState", "")).strip())
PY
)"

if [[ "$BACKEND_STATE" != "Running" ]]; then
  echo "Tailscale backend state is '$BACKEND_STATE'; skipping remote-access bootstrap."
  exit 0
fi

"$TAILSCALE_BIN" serve --bg "$JARVIS_TARGET"
echo "Tailscale Serve refreshed for $JARVIS_TARGET"
