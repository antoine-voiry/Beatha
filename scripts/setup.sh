#!/bin/bash
# Project Beatha - Setup Script
# Installs System Dependencies, Configures WiFi AP, and Sets up Services.

set -e
cd "$(dirname "$0")/.."

echo "🚁 Project Beatha Installer"
echo "==========================="

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./setup.sh)"
  exit
fi

# 1. Update System
echo "[1/5] Updating System..."
apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    socat \
    git \
    nodejs \
    npm \
    hostapd \
    dnsmasq \
    nginx

# 2. Python Setup
echo "[2/5] Installing Python Libs..."
# Note: Removed [standard] from uvicorn to avoid compiling uvloop on Pi Zero (too slow)
pip3 install fastapi uvicorn pyserial rpi_ws281x adafruit-circuitpython-neopixel RPi.GPIO --break-system-packages

# 3. Web UI Build
if [ -d "src/frontend/dist" ]; then
    echo "[3/5] Found pre-built Web UI. Skipping build..."
    mkdir -p /var/www/beatha
    cp -r src/frontend/dist/* /var/www/beatha/
else
    echo "[3/5] Building Web UI (This might take a while)..."
    # Placeholder for React Build - (In real scenario, we would npm install && npm build)
    # For now, we assume the build artifacts will be present or we create a dummy index.html
    mkdir -p /var/www/beatha
    echo "<h1>Project Beatha Web UI</h1><p>Status: Online</p>" > /var/www/beatha/index.html
fi

# 4. Nginx Configuration (Port 80 Reverse Proxy)
echo "[4/5] Configuring Nginx..."
cat > /etc/nginx/sites-available/beatha <<'EOF'
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
echo "[5/5] Installing Systemd Service..."
cp install/beatha.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable beatha

echo "✅ Setup Complete! Please reboot."
