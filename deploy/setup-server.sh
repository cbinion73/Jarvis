#!/bin/bash
# setup-server.sh
# Run this ONCE on a fresh Hetzner Ubuntu 24.04 server as root:
#   ssh root@YOUR_SERVER_IP
#   curl -sL https://raw.githubusercontent.com/YOUR_REPO/deploy/main/setup-server.sh | bash

set -e

echo "═══════════════════════════════════════"
echo "  JARVIS Server Setup"
echo "═══════════════════════════════════════"

# System update
apt-get update && apt-get upgrade -y

# Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Git
apt-get install -y git

# Firewall (only SSH + HTTP for Cloudflare Tunnel)
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP (Cloudflare Tunnel needs this)
ufw --force enable

# Create jarvis user
if ! id "jarvis" &>/dev/null; then
    useradd -m -s /bin/bash jarvis
    usermod -aG docker jarvis
    echo "Created user: jarvis"
fi

# SSH key for jarvis user (copy from root)
mkdir -p /home/jarvis/.ssh
cp /root/.ssh/authorized_keys /home/jarvis/.ssh/ 2>/dev/null || true
chown -R jarvis:jarvis /home/jarvis/.ssh
chmod 700 /home/jarvis/.ssh
chmod 600 /home/jarvis/.ssh/authorized_keys 2>/dev/null || true

echo ""
echo "✓ Server ready."
echo ""
echo "Next steps:"
echo "  1. SSH back in as: ssh jarvis@YOUR_SERVER_IP"
echo "  2. Clone your repos into ~/CODE/"
echo "  3. Set up .env file in ~/CODE/deploy/"
echo "  4. Run: cd ~/CODE/deploy && docker compose up -d --build"
