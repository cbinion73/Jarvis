#!/bin/zsh
set -euo pipefail

ROOT="/Users/chris/Desktop/CODE/JARVIS"
AGENTS_DIR="$HOME/Library/LaunchAgents"
SUPPORT_DIR="$HOME/Library/Application Support/JARVIS"
BIN_DIR="$SUPPORT_DIR/bin"

mkdir -p "$AGENTS_DIR"
mkdir -p "$ROOT/data/logs"
mkdir -p "$BIN_DIR"

cp "$ROOT/infra/scripts/start_jarvis_dashboard.sh" "$BIN_DIR/"
cp "$ROOT/infra/scripts/start_jarvis_voice_shell.sh" "$BIN_DIR/"
cp "$ROOT/infra/scripts/start_jarvis_tailscale_serve.sh" "$BIN_DIR/"
chmod +x "$BIN_DIR/start_jarvis_dashboard.sh" "$BIN_DIR/start_jarvis_voice_shell.sh" "$BIN_DIR/start_jarvis_tailscale_serve.sh"

python3 - <<PY
from pathlib import Path

root = Path("$ROOT")
agents = Path("$AGENTS_DIR")
bin_dir = Path("$BIN_DIR")

replacements = {
    "/Users/chris/Desktop/CODE/JARVIS/infra/scripts/start_jarvis_dashboard.sh": str(bin_dir / "start_jarvis_dashboard.sh"),
    "/Users/chris/Desktop/CODE/JARVIS/infra/scripts/start_jarvis_voice_shell.sh": str(bin_dir / "start_jarvis_voice_shell.sh"),
    "/Users/chris/Desktop/CODE/JARVIS/infra/scripts/start_jarvis_tailscale_serve.sh": str(bin_dir / "start_jarvis_tailscale_serve.sh"),
}

for name in (
    "com.chris.jarvis.dashboard.plist",
    "com.chris.jarvis.voice-shell.plist",
    "com.chris.jarvis.tailscale-serve.plist",
):
    src = root / "infra" / "launchd" / name
    dst = agents / name
    text = src.read_text()
    for old, new in replacements.items():
        text = text.replace(old, new)
    dst.write_text(text)
PY

launchctl unload "$AGENTS_DIR/com.chris.jarvis.dashboard.plist" >/dev/null 2>&1 || true
launchctl unload "$AGENTS_DIR/com.chris.jarvis.tailscale-serve.plist" >/dev/null 2>&1 || true
launchctl load "$AGENTS_DIR/com.chris.jarvis.dashboard.plist"
launchctl load "$AGENTS_DIR/com.chris.jarvis.tailscale-serve.plist"

echo "Installed launchd templates into $AGENTS_DIR"
echo "Dashboard service loaded."
echo "Voice shell template copied but not auto-loaded."
echo "Tailscale serve refresher loaded."
