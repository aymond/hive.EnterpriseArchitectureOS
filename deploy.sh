#!/bin/bash
# =============================================================================
# deploy.sh — OCI VM First-Time Setup for hive.EnterpriseArchitectureOS
#
# Run this script on a fresh Oracle Cloud (Ubuntu) compute instance:
#   chmod +x deploy.sh && sudo ./deploy.sh
# =============================================================================
set -e

REPO_URL="https://github.com/aymond/hive.EnterpriseArchitectureOS.git"
APP_DIR="/opt/hive-ea-os"

echo "===> [1/6] Installing system dependencies..."
apt-get update -y
apt-get install -y \
    curl \
    git \
    ca-certificates \
    gnupg \
    lsb-release

echo "===> [2/6] Installing Docker..."
# Check if Docker is already installed
if ! command -v docker &>/dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    echo "Docker installed successfully."
else
    echo "Docker already installed, skipping."
fi

echo "===> [3/6] Configuring firewall (ufw)..."
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP (Nginx)
ufw allow 443/tcp  # HTTPS (future)
# Note: Ports 8000, 3000, and 7474 are NOT opened — they communicate internally via Docker
ufw --force enable
echo "Firewall configured."

echo "===> [4/6] Cloning / updating repository..."
if [ -d "$APP_DIR" ]; then
    echo "Directory exists, pulling latest changes..."
    cd "$APP_DIR" && git pull origin main
else
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

echo "===> [5/6] Checking .env file..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo ""
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "  WARNING: No .env file found."
    echo "  Please copy .env.oci.example to .env and fill in:"
    echo "    - OPENAI_API_KEY"
    echo "    - TAVILY_API_KEY"
    echo "    - NEO4J_PASSWORD (use a strong password)"
    echo "    - JWT_SECRET_KEY (run: openssl rand -hex 32)"
    echo "    - ALLOWED_ORIGINS (your VM public IP or domain)"
    echo "  Then re-run: docker compose up -d --build"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    exit 1
fi

echo "===> [6/6] Building and starting containers..."
cd "$APP_DIR"
docker compose pull neo4j nginx 2>/dev/null || true
docker compose up -d --build

echo ""
echo "====================================================="
echo "  Deployment complete!"
echo "  App is running at: http://$(curl -s ifconfig.me)"
echo "  Check status:      docker compose ps"
echo "  View logs:         docker compose logs -f"
echo "====================================================="
