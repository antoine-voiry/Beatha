# Advanced Setup Guide (Build from Source)

This guide is for users who want full control over the installation process, wish to modify the build parameters, or debug installation issues.

> **Note:** If you just want to get running quickly, use the automated `scripts/setup.sh` described in [SETUP_PI.md](SETUP_PI.md).

## Prerequisites
*   Raspberry Pi Zero W running Raspberry Pi OS Lite.
*   SSH Access.
*   Git installed.

---

## Step 1: System Dependencies
Install the required system packages manually.

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv socat git nodejs npm hostapd dnsmasq nginx
```

## Step 2: Backend Setup (Python)

We strictly use a Virtual Environment (`venv`) to avoid polluting the system Python.

1.  **Create Virtual Environment:**
    ```bash
    cd /home/pi/betaflightdebugger
    python3 -m venv .venv
    ```

2.  **Activate & Install:**
    ```bash
    source .venv/bin/activate
    pip install fastapi uvicorn[standard] pyserial rpi_ws281x adafruit-circuitpython-neopixel RPi.GPIO
    # Note: On Pi Zero (ARMv6), some packages might take a while to build.
    ```

## Step 3: Frontend Setup (React)

We need to build the React application into static files (HTML/JS/CSS) that Nginx can serve.

1.  **Install Dependencies:**
    ```bash
    cd src/frontend
    npm install
    ```

2.  **Build:**
    ```bash
    npm run build
    ```
    *Result: A `dist/` folder will be created inside `src/frontend` containing the production assets.*

3.  **Deploy:**
    Move the built files to the web root.
    ```bash
    sudo mkdir -p /var/www/beatha
    sudo cp -r dist/* /var/www/beatha/
    ```

## Step 4: Nginx Configuration (Reverse Proxy)

Nginx serves the frontend (Port 80) and proxies API calls to the backend (Port 8000).

1.  **Create Config:**
    ```bash
    sudo nano /etc/nginx/sites-available/beatha
    ```

2.  **Paste Configuration:**
    ```nginx
    server {
        listen 80;
        server_name _;

        location / {
            root /var/www/beatha;
            index index.html;
            try_files $uri /index.html;
        }

        location /api {
            proxy_pass http://127.0.0.1:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
    ```

3.  **Enable & Restart:**
    ```bash
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo ln -s /etc/nginx/sites-available/beatha /etc/nginx/sites-enabled/
    sudo systemctl restart nginx
    ```

## Step 5: Service Installation

Configure systemd to auto-start the Python backend on boot.

1.  **Copy Service File:**
    ```bash
    cd /home/pi/betaflightdebugger
    sudo cp install/beatha.service /etc/systemd/system/
    ```

2.  **Verify Service File:**
    Ensure the service points to your `.venv` python executable. You might need to edit it:
    ```bash
    sudo nano /etc/systemd/system/beatha.service
    ```
    *Change `ExecStart` to:* `/home/pi/betaflightdebugger/.venv/bin/python src/backend/server.py`

3.  **Enable & Start:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable beatha
    sudo systemctl start beatha
    ```

## Step 6: WiFi Hotspot (Optional)
If you want the Pi to create its own WiFi network (`Beatha_AP`), you need to configure `hostapd` and `dnsmasq`. This is complex to do manually. Refer to the `scripts/setup.sh` file for the exact `nmcli` or config commands used.
