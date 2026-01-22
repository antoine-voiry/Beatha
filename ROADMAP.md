# 🗺️ Project Beatha Roadmap

## 🚀 Phase 1: MVP (Complete)

*   ✅ Headless Raspberry Pi Zero W implementation.
*   ✅ Auto-detection of USB Hotplug.
*   ✅ "Dump All" extraction for Betaflight/INAV.
*   ✅ Local Storage + Basic Cloud Sync (via pre-configured rclone).
*   ✅ Web UI for status and control.
*   ✅ Bluetooth Proxy (Wireless Configurator Bridge).
*   ✅ ArduPilot Detection (Basic).

## 🌟 Phase 1.5: UI/UX Overhaul (Complete)

*   ✅ Dark/Light mode toggle with localStorage persistence.
*   ✅ Tab-based navigation (Flight Controller / Preferences).
*   ✅ Serial port selection dropdown with refresh button.
*   ✅ Baud rate selection (9600-921600).
*   ✅ FC type and version detection display (Betaflight/INAV/ArduPilot).
*   ✅ Live log card showing TX/RX/info/error messages.
*   ✅ Organized dumps in directories by board name + version.
*   ✅ MSC mode API for Betaflight SD card access (`/api/fc/msc`).
*   ✅ Basic MAVLink connection for ArduPilot (heartbeat detection).

## 🌟 Phase 2: Enhanced User Experience (Next Up)

*   **Smart Cloud Setup:** Move away from CLI `rclone config`. Implement a UI-based OAuth flow where the user pastes an auth code to link Google Drive/Dropbox.
*   **LLM Analysis Integration:** "Doctor Beatha" feature. Analyze the dump using an LLM (Gemini/OpenAI) to suggest tuning improvements or diagnose issues based on blackbox logs.
*   **Mobile Companion App:** A PWA (Progressive Web App) manifest for the frontend so it installs like a native app on phones.
*   **Full MAVLink FTP:** Complete ArduPilot log file download via MAVLink FTP protocol.

## 🔮 Phase 3: The "Pro" Tool (Long Term)
*   **ESC Protocol Support:** Implement BLHeli/Bluejay serial passthrough to dump ESC firmware settings (Requires reverse engineering the 4-way interface protocol).
*   **Universal Device Support:**
    *   **ArduPilot:** Full MAVLink parameter extraction.
    *   **Kiss / Fettec:** Support for their proprietary CLI protocols.
    *   **VTX Analyzer:** Read VTX tables and power settings to ensure legal compliance.
*   **Blackbox Auto-Sync:** Automatically mount the FC's SD card (MSC mode) and sync gigabytes of blackbox logs to a local SSD or cloud bucket.

## 🌍 Phase 4:The Unknown (Ecosystem)
*   **Global Tune Database:** Anonymized, searchable database of "Known Good Tunes" for every frame/motor combination.
*   **Fleet Management:** A cloud dashboard for schools/racing leagues to manage firmware versions across 50+ drones.
*   **AI Auto-Tune:** Use the database + LLM to generate a `diff` file that tunes your drone perfectly for your flying style.


*   **"The Digital Pit Crew" (Automated Hardware Diagnostics):**
    *   Active health check: Spin motors via MSP and read DSHOT telemetry (RPM/Current) to detect bad bearings, desync risks, or stalled motors *before* flight.
*   **"Touchless" Race Check-In:**
    *   Event organizers place a Beatha unit at registration. Pilots plug in -> Beatha auto-assigns valid VTX Channel, Power Level, and OSD Name based on the race heat structure.
*   **Edge Blackbox Explorer:**
    *   Host a lightweight Blackbox log visualizer directly on the Pi. View flight logs on your phone's browser immediately after landing, no laptop required.
*   **Parts DNA & Anti-Tamper:**
    *   Cryptographic fingerprinting of drone hardware (MCU Serial, Gyro ID, ESC Signature). Alerts fleet managers if components have been swapped (swapped parts detection).
