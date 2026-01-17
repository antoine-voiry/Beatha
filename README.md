<div align="center">
  <img src="assets/logo.svg" alt="Project Beatha Logo" width="500">
  <br>
  <h1>Project Beatha</h1>
  <h3>"Bringing Dead Drones Back to Life"</h3>
</div>

## The Story
The name **Beatha** (pronounced *ba-ha*) comes from the Irish word for **"Life"**. It is a nod to the popular flight control software **Betaflight**. When a drone crashes and is unresponsive or "dead" on the field, Project Beatha acts as a field recovery medic, extracting critical firmware configurations and "black box" data settings to bring it back to life or diagnose the cause of death without needing a laptop.

## Overview
Project Beatha is a "Headless" field recovery tool for FPV drones. It runs on a Raspberry Pi Zero W and automatically extracts `dump all` firmware configurations from a connected flight controller and uploads them to the cloud.

### Features
*   **Bus Powered:** The Pi provides power to the connected drone FC via USB.
*   **Modes:**
    *   **Idle/Proxy:** Acts as a TCP bridge allowing wireless connection to Betaflight Configurator.
    *   **Extraction:** One-button firmware dump extraction.
    *   **Pairing:** dedicated button to enable Bluetooth discovery for configuration.
*   **Visual Feedback:** Clear 4-stage LED status indication.
*   **Audible Feedback:** (Optional) Buzzer beeps for start/success/fail.
*   **Cloud Sync:** Automatic upload to Google Drive via `rclone`.

## Hardware Specification

For a complete list of materials, please see **[BOM.md](BOM.md)**.

*   **Controller:** Raspberry Pi Zero W v1.1 (Minimum)
*   **Interface:** Custom "Hat" using a Prototyping Board (Buttons + LEDs + Buzzer).
*   **Input:** USB OTG to Drone Flight Controller
*   **Power:** 5V 2A+ Power Supply

### Wiring & Connections

For detailed wiring instructions, please refer to **[WIRING.md](WIRING.md)**.

**Quick Pinout Reference:**
*   **GPIO 23:** Dump Button
*   **GPIO 24:** Pairing Button
*   **GPIO 25:** Buzzer (Optional)
*   **GPIO 18:** LED Data Line

## Setup Guide

### 1. Prerequisites
Ensure your Raspberry Pi Zero W is set up with Raspberry Pi OS Lite and has internet access.

### 2. System Dependencies
Install system packages:
```bash
sudo apt-get update
sudo apt-get install python3-pip python3-venv socat git
```

Install `rclone` and configure it:
```bash
curl https://rclone.org/install.sh | sudo bash
rclone config
# Follow prompts to create a remote named 'gdrive' pointing to Google Drive
# Create a folder 'BF_Dumps' in your Drive.
```

### 3. Project Installation
Clone the repository:
```bash
cd /home/pi
git clone https://github.com/yourusername/project-beatha.git betaflightdebugger
cd betaflightdebugger
```

Install Python dependencies:
```bash
# Note: rpi_ws281x requires root privileges to access GPIO registers
sudo pip3 install -r requirements.txt --break-system-packages
```
*(Note: On newer Raspberry Pi OS, you might need to use a virtual environment or `--break-system-packages` as shown above, but running as root service is standard for hardware GPIO access).*

### 4. Service Installation
Install the systemd service to run Beatha on boot:
```bash
sudo cp install/beatha.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable beatha.service
sudo systemctl start beatha.service
```

## Usage

### LED Status Indicators

1.  **Breathing Blue:** System Idle / TCP Proxy Mode Active. (Connect via WiFi to port 5000).
2.  **Orange (LED 1):** Connecting to Serial Port.
3.  **Orange (LED 2):** Reading Dump Data.
4.  **Yellow (LED 3):** Saving Dump to Local Storage.
5.  **Green (LED 4):** Success - Cloud Upload Complete.
6.  **Red (LED 4):** Error - Extraction or Upload Failed.

### Manual Operation
*   **Button Press:** Triggers Extraction Mode.
*   **Wait:** Watch the LEDs progress from 1 to 4.
*   **Finish:** After success/fail indication (3 seconds), system returns to Breathing Blue.

## License
MIT License. See [LICENSE](LICENSE) for details.