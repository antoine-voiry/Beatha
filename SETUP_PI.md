# Pi Setup Guide (Step-by-Step)

This guide takes you from a blank MicroSD card to a running Project Beatha system.

## Phase 1: Flash the OS

1.  **Download:** [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2.  **Insert:** Your MicroSD card into your computer.
3.  **Open Imager:**
    *   **OS:** Choose `Raspberry Pi OS (other)` -> `Raspberry Pi OS Lite (Legacy, 32-bit)` (Lite is headless, faster).
    *   **Storage:** Choose your SD Card.
    *   **Settings (Gear Icon):** **CRITICAL STEP**
        *   ✅ **Set Hostname:** `beatha`
        *   ✅ **Enable SSH:** Use password authentication (or public key if confortable with managing keys).
        *   ✅ **Set Username/Password:** user: `pi`, pass: `raspberry` (or your choice with a strong password).
        *   ✅ **Configure Wireless LAN:** Enter your Home WiFi SSID and Password. (This allows you to connect initially to install things).
        *   ✅ **Services (Optional):** Enable **Raspberry Pi Connect** if listed (saves time later).
4.  **Write:** Click Write and wait for verification.

## Phase 2: First Boot & Transfer

1.  **Insert SD:** Put the card into the Pi Zero W.
2.  **Power On:** Plug USB power into the **PWR** port (Outer edge).
3.  **Wait:** Give it 2-3 minutes to boot and connect to WiFi.
4.  **Connect via Terminal:**
    ```bash
    ssh pi@beatha.local
    # Enter password (default: raspberry)
    ```

## Phase 3: Install Project Beatha

Once logged in via SSH:

1.  **Clone the Repo:**
    ```bash
    cd /home/pi
    # Install git if needed (usually installed)
    sudo apt update && sudo apt install -y git
    git clone https://github.com/antoine-voiry/Beatha.git betaflightdebugger
    ```

2.  **Run the Auto-Installer:**
    This script installs Python, React dependencies, Nginx, and sets up the WiFi Access Point.
    ```bash
    cd betaflightdebugger
    sudo bash scripts/setup.sh
    ```
    *(Advanced: To build from source manually, see [ADVANCED_SETUP.md](ADVANCED_SETUP.md))*

3.  **Reboot:**
    ```bash
    sudo reboot
    ```

## Phase 4: Usage

After reboot, the Pi will broadcast a WiFi Hotspot:
*   **SSID:** `Beatha_AP`
*   **Password:** `betaflight`
*   **Web UI:** http://192.168.4.1

You can now connect your drone!

## Phase 5: Remote Access (Optional)

If you want to access your Project Beatha unit from anywhere in the world (without port forwarding), you can use **Raspberry Pi Connect**.

*(Note: If you enabled this in the Raspberry Pi Imager settings during Phase 1, you can skip the install step and just run `rpi-connect signin`)*.

1.  **Install:**
    ```bash
    sudo apt install rpi-connect
    ```
2.  **Sign In:**
    ```bash
    rpi-connect signin
    ```
    *This will provide a URL. Open it on your phone/laptop to link the Pi to your Raspberry Pi ID.*

3.  **Usage:**
    Go to [connect.raspberrypi.com](https://connect.raspberrypi.com) to access your terminal remotely.
