# Project Beatha

<div align="center">
  <img src="assets/beatha_logo.png" alt="Project Beatha Logo" width="500">
  <br>
  <h1>Project Beatha</h1>
  <h3>"Bringing Dead Drones Back to Life"</h3>
  <p><em>A Weekend Project Experiment</em></p>
</div>

## 📜 The Story (Read This First)
Project Beatha started as a midnight idea on a Friday. It was built in **under 12 hours** over a single weekend.

While commercial tools like **SpeedyBee** exist and are fantastic, this project is about:
1.  **Open Source Freedom:** Hackable, modifiable, and free.
2.  **AI-Assisted Engineering:** This entire project—code, docs, and architecture—was brainstormed and built with the assistance of AI agents.
3.  **Differentiation:** Focusing on "Headless Recovery" and "Cloud Sync" rather than just configuration.

**Disclaimer:** This is **v0.1 (Alpha)**. Expect rough edges. It is a proof-of-concept.

## 🔮 Future Vision: The Drone Database
By automatically uploading dumps to the cloud, Project Beatha lays the foundation for a global **Drone Database**.
*   **Analysis:** Automatically analyze your configuration against known "good" tunes.
*   **History:** Track changes over time.
*   **Blackbox:** Future support for uploading and analyzing Blackbox logs to diagnose crashes instantly.

## Overview
Project Beatha is a "Headless" field recovery tool for FPV drones. It runs on a Raspberry Pi Zero W and automatically extracts `dump all` firmware configurations from a connected flight controller and uploads them to the cloud.

### Features
*   **Bus Powered:** The Pi provides power to the connected drone FC via USB.
*   **Modes:**
    *   **Idle/Proxy:** Acts as a TCP bridge allowing wireless connection to Betaflight Configurator.
    *   **Extraction:** One-button firmware dump extraction.
    *   **Pairing:** Dedicated button to enable Bluetooth discovery for configuration.
*   **Visual Feedback:** Clear 4-stage LED status indication.
*   **Audible Feedback:** (Optional) Buzzer beeps for start/success/fail.
*   **Cloud Sync:** Automatic upload to Google Drive via `rclone`.

## Hardware Specification

For a complete list of materials, please see **[BOM.md](BOM.md)**.

*   **Controller:** Raspberry Pi Zero W v1.1 (Minimum)
*   **Interface:** Custom "Hat" using a Prototyping Board (Buttons + LEDs + Buzzer).
*   **Case:** 3D Printable STL files available in `assets/3dmodels/`.
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
Install `rclone` and configure it (RUN AS YOUR USER, NOT ROOT):
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
git clone https://github.com/antoine-voiry/Beatha.git beatha-project
cd beatha-project
```

### 4. Automated Installer
We have provided a setup script that creates a virtual environment, installs dependencies, builds the frontend, and sets up the systemd service.

```bash
sudo ./scripts/setup.sh
```

**Note:** The installer will automatically detect your user (e.g., `pi`) and configure the service to run as that user to avoid permission issues with `rclone`.

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

## Known Bugs
See **[KNOWN_BUGS.md](KNOWN_BUGS.md)** for a list of current issues and workarounds.

## License

**Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**

*   **You are free to:** Share and Adapt the material.
*   **Under these terms:**
    *   **Attribution:** You must give appropriate credit.
    *   **NonCommercial:** You may **NOT** use the material for commercial purposes (e.g., selling units).
    *   **ShareAlike:** If you remix, transform, or build upon the material, you must distribute your contributions under the same license.

**Commercial Use:**
If you wish to sell Project Beatha units or use this for commercial purposes, please contact **Antoine Voiry** via GitHub.