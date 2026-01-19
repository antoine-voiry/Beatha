#!/bin/bash
# Project Beatha - Setup Script
# Installs System Dependencies, Configures WiFi AP, and Sets up Services.

set -e
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "🚁 Project Beatha Installer"
echo "==========================="

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./setup.sh)"
  exit 1
fi

# Detect actual user (who ran sudo)
REAL_USER=${SUDO_USER:-$(whoami)}
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

echo "Installing for User: $REAL_USER at $PROJECT_ROOT"

# 1. Update System
echo "[1/5] Updating System & Installing Dependencies..."
apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    socat \
    git \
    nodejs \
    npm \
    nginx \
    rclone

# 2. Python Setup (Virtual Environment)
echo "[2/5] Setting up Python Virtual Environment..."
if [ ! -d ".venv" ]; then
    sudo -u "$REAL_USER" python3 -m venv .venv
fi

# Install dependencies into venv
echo "Installing Python libraries..."
sudo -u "$REAL_USER" .venv/bin/pip install --upgrade pip
sudo -u "$REAL_USER" .venv/bin/pip install -r requirements.txt

# 3. Web UI Build
echo "[3/5] Setting up Web UI..."
# Check if dist exists, if not maybe build (optional for now)
if [ ! -d "src/frontend/dist" ]; then
    echo "Warning: src/frontend/dist not found. Please build the frontend."
    # Create a placeholder to prevent Nginx 404
    mkdir -p src/frontend/dist
    echo "<h1>Beatha Frontend Not Built</h1>" > src/frontend/dist/index.html
fi

# Link to Nginx root
rm -rf /var/www/beatha
mkdir -p /var/www/beatha
cp -r src/frontend/dist/* /var/www/beatha/
chown -R www-data:www-data /var/www/beatha

# 4. Nginx Configuration
echo "[4/5] Configuring Nginx..."
cat > /etc/nginx/sites-available/beatha <<EOF
server {
    listen 80;
    server_name _;

    location / {
        root /var/www/beatha;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/beatha /etc/nginx/sites-enabled/
systemctl restart nginx

# 5. Service Setup
echo "[5/5] Configuring Systemd Service..."

# Log Setup
touch /var/log/beatha.log
chown "$REAL_USER":"$REAL_USER" /var/log/beatha.log
chmod 664 /var/log/beatha.log

# Generate Service File from Template
SERVICE_FILE="/etc/systemd/system/beatha.service"
cp install/beatha.service "$SERVICE_FILE"
sed -i "s|{{USER}}|$REAL_USER|g" "$SERVICE_FILE"
sed -i "s|{{INSTALL_DIR}}|$PROJECT_ROOT|g" "$SERVICE_FILE"

systemctl daemon-reload
systemctl enable beatha
systemctl restart beatha

echo "✅ Setup Complete!"
echo "   - Service: beatha.service"
echo "   - URL: http://beatha.local or http://$(hostname -I | cut -d' ' -f1)"
echo "   - Logs: /var/log/beatha.log"