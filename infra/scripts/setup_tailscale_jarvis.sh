#!/bin/zsh
set -euo pipefail

JARVIS_HEALTH_URL="${JARVIS_HEALTH_URL:-http://127.0.0.1:8787/health}"
JARVIS_TARGET="${JARVIS_TARGET:-localhost:8787}"

TAILSCALE_BIN="$(command -v tailscale || true)"
if [[ -z "$TAILSCALE_BIN" ]]; then
  echo "Tailscale CLI not found."
  echo "Install the Tailscale macOS app first, sign this Mac into your tailnet, then rerun this script."
  exit 1
fi

if ! curl -fsS "$JARVIS_HEALTH_URL" >/dev/null; then
  echo "JARVIS is not responding on $JARVIS_HEALTH_URL"
  echo "Start JARVIS first, then rerun this script."
  exit 1
fi

STATUS_JSON="$("$TAILSCALE_BIN" status --json 2>/dev/null || true)"
if [[ -z "$STATUS_JSON" ]]; then
  echo "Tailscale is installed, but this Mac is not connected yet."
  echo "Open Tailscale, sign in, confirm the device is connected, then rerun this script."
  exit 1
fi

read -r BACKEND_STATE DNS_NAME <<<"$(
  STATUS_JSON="$STATUS_JSON" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["STATUS_JSON"])
state = str(payload.get("BackendState", "")).strip()
dns_name = str((payload.get("Self") or {}).get("DNSName", "")).strip().rstrip(".")
print(state, dns_name)
PY
)"

if [[ "$BACKEND_STATE" != "Running" ]]; then
  echo "Tailscale is present, but not fully connected. Current state: ${BACKEND_STATE:-unknown}"
  echo "Open the Tailscale app, finish login, and make sure the device shows as connected."
  exit 1
fi

if [[ -z "$DNS_NAME" ]]; then
  echo "Connected to Tailscale, but no tailnet DNS name was found."
  echo "Confirm MagicDNS is enabled for your tailnet, then rerun this script."
  exit 1
fi

"$TAILSCALE_BIN" serve --bg "$JARVIS_TARGET"

echo
echo "JARVIS is now shared privately over your tailnet."
echo "Remote URL: https://$DNS_NAME"
echo
echo "Useful checks:"
echo "  tailscale serve status"
echo "  tailscale status"
echo
echo "To disable remote sharing later:"
echo "  tailscale serve reset"
