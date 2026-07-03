#!/usr/bin/env bash
# Sync the Obsidian retrieval index from the Mac into the repo so production
# gets vault-grounded conversation.
#
# The vault itself stays on the Mac (/Volumes/Monday/Obsidian). This script
# rebuilds the retrieval index from the live vault, copies it into
# data/obsidian/index.json, and commits it. The existing push-to-main deploy
# then carries it to Hetzner, where ObsidianVaultSupport serves retrieval in
# "synced-index" mode — honestly labeled as reflecting the last sync.
#
# Run manually after meaningful vault changes, or schedule it (launchd/cron).
# Pass --push to also push to main (which deploys).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "Rebuilding Obsidian index from the live vault..."
set -a; source .env 2>/dev/null || true; set +a
.venv/bin/python - << 'PYEOF'
import os
from pathlib import Path
from jarvis.obsidian_context import ObsidianVaultSupport

support = ObsidianVaultSupport(
    vault_path=Path(os.getenv("JARVIS_OBSIDIAN_VAULT", "/Volumes/Monday/Obsidian")),
    index_path=Path(os.getenv("JARVIS_OBSIDIAN_INDEX_PATH", "/Volumes/Monday/JARVIS/indexes/obsidian/index.json")),
)
if support.mode != "live-vault":
    raise SystemExit(f"Vault not readable here (mode={support.mode}) — run this on the Mac with the vault mounted.")
index = support.ensure_index()
print(f"Index fresh: {index.get('file_count', 0)} notes, {index.get('chunk_count', 0)} chunks.")
PYEOF

mkdir -p data/obsidian
cp "${JARVIS_OBSIDIAN_INDEX_PATH:-/Volumes/Monday/JARVIS/indexes/obsidian/index.json}" data/obsidian/index.json

if git diff --quiet -- data/obsidian/index.json 2>/dev/null && git ls-files --error-unmatch data/obsidian/index.json >/dev/null 2>&1; then
  echo "Index unchanged since last sync — nothing to do."
  exit 0
fi

git add data/obsidian/index.json
git commit -m "Sync Obsidian retrieval index for production

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
echo "Committed. "

if [[ "${1:-}" == "--push" ]]; then
  git push origin HEAD:main
  echo "Pushed to main — deploy will carry the index to production."
else
  echo "Not pushed. Run with --push (or push manually) to deploy."
fi
