# 🗺️ Project Beatha Roadmap

## 🚀 Phase 1: MVP (Current Status)
*   ✅ Headless Raspberry Pi Zero W implementation.
*   ✅ Auto-detection of USB Hotplug.
*   ✅ "Dump All" extraction for Betaflight/INAV.
*   ✅ Local Storage + Basic Cloud Sync (via pre-configured rclone).
*   ✅ Web UI for status and control.
*   ✅ Bluetooth Proxy (Wireless Configurator Bridge).

## 🌟 Phase 2: Enhanced User Experience (Next Up)
*   **Smart Cloud Setup:** Move away from CLI `rclone config`. Implement a UI-based OAuth flow where the user pastes an auth code to link Google Drive/Dropbox.
*   **LLM Analysis Integration:** "Doctor Beatha" feature. Analyze the dump using an LLM (Gemini/OpenAI) to suggest tuning improvements or diagnose issues based on blackbox logs.
*   **Mobile Companion App:** A PWA (Progressive Web App) manifest for the frontend so it installs like a native app on phones.

## 🔮 Phase 3: The "Pro" Tool (Long Term)
*   **ESC Protocol Support:** Implement BLHeli/Bluejay serial passthrough to dump ESC firmware settings (Requires reverse engineering the 4-way interface protocol).
*   **Universal Device Support:**
    *   **ArduPilot:** Full MAVLink parameter extraction.
    *   **Kiss / Fettec:** Support for their proprietary CLI protocols.
    *   **VTX Analyzer:** Read VTX tables and power settings to ensure legal compliance.
*   **Blackbox Offloader:** Automatically mount the FC's SD card (MSC mode) and sync gigabytes of blackbox logs to a local SSD or cloud bucket.

## 🌍 Phase 4: World Domination (Ecosystem)
*   **Global Tune Database:** Anonymized, searchable database of "Known Good Tunes" for every frame/motor combination.
*   **Fleet Management:** A cloud dashboard for schools/racing leagues to manage firmware versions across 50+ drones.
*   **AI Auto-Tune:** Use the database + LLM to generate a `diff` file that tunes your drone perfectly for your flying style.
