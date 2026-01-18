# Known Bugs & Issues

This document tracks known limitations and bugs in Project Beatha.

## 🐛 Open Issues

### 1. Bluetooth Bridge Compatibility
*   **Issue:** The current implementation focuses on WiFi TCP bridging (`socat`). Bluetooth SPP (Serial Port Profile) implementation is planned but not fully robust for all Android/iOS devices.
*   **Workaround:** Use the WiFi Hotspot + Betaflight Configurator (TCP Mode).

### 2. Pi Zero W First Boot Slowness
*   **Issue:** The first boot can take 10+ minutes while resizing the filesystem.
*   **Workaround:** Be patient. Check `TROUBLESHOOTING.md`.

### 3. Log Format Consistency
*   **Issue:** Some startup scripts or system-level errors might not follow the ISO 8601 format perfectly (systemd adds its own timestamps).
*   **Status:** Backend logs are fixed (v1.1).

---
*To report a new bug, please open an issue on GitHub.*
