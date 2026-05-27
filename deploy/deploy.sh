#!/bin/bash
# deploy.sh — run from your Mac to push updates to the server
# Usage: ./deploy.sh [service]
# Example: ./deploy.sh         (deploys all)
#          ./deploy.sh jarvis  (deploys only JARVIS)

set -e

SERVER="jarvis@YOUR_SERVER_IP"
REMOTE_DIR="~/CODE/deploy"

echo "Deploying to $SERVER..."

# Pull latest code on server for all repos
ssh "$SERVER" "
  cd ~/CODE/JARVIS && git pull --ff-only &&
  cd ~/CODE/chronicle && git pull --ff-only &&
  cd ~/CODE/GHOSTWRITR && git pull --ff-only &&
  cd ~/CODE/deploy && git pull --ff-only
"

# Rebuild and restart
if [ -n "$1" ]; then
  echo "Rebuilding $1..."
  ssh "$SERVER" "cd $REMOTE_DIR && docker compose up -d --build $1"
else
  echo "Rebuilding all services..."
  ssh "$SERVER" "cd $REMOTE_DIR && docker compose up -d --build"
fi

echo "Deploy complete."
echo "  JARVIS:     https://jarvis.teambinion.org"
echo "  Chronicle:  https://chronicle.teambinion.org"
echo "  Ghostwritr: https://ghostwritr.teambinion.org"
