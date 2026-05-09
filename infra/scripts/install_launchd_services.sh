#!/bin/zsh
set -euo pipefail

ROOT="/Users/chris/Desktop/CODE/JARVIS"
AGENTS_DIR="$HOME/Library/LaunchAgents"

mkdir -p "$AGENTS_DIR"
mkdir -p "$ROOT/data/logs"

cp "$ROOT/infra/launchd/com.chris.jarvis.dashboard.plist" "$AGENTS_DIR/"
cp "$ROOT/infra/launchd/com.chris.jarvis.voice-shell.plist" "$AGENTS_DIR/"

launchctl unload "$AGENTS_DIR/com.chris.jarvis.dashboard.plist" >/dev/null 2>&1 || true
launchctl load "$AGENTS_DIR/com.chris.jarvis.dashboard.plist"

echo "Installed launchd templates into $AGENTS_DIR"
echo "Dashboard service loaded."
echo "Voice shell template copied but not auto-loaded."
