# Known Bugs & Issues

## Current Issues (v0.1 Alpha)

1.  **rpi_ws281x & Audio Conflict:**
    *   **Issue:** The `rpi_ws281x` library (used for NeoPixels) uses PWM/DMA channels that conflict with the Pi's onboard audio.
    *   **Workaround:** Onboard audio must be disabled in `/boot/config.txt` (`dtparam=audio=off`). The `setup.sh` does not currently automate this.

2.  **rclone "Root Trap":**
    *   **Issue:** If `rclone config` is run as `root` (via sudo), the configuration file is saved in `/root/.config/rclone/`. If the application runs as user `pi`, it won't find the config.
    *   **Workaround:** Always run `rclone config` as the user who will run the service (usually `pi`). Do **not** use `sudo rclone config`.

3.  **USB Hotplug Latency:**
    *   **Issue:** Detection of the drone connection might take 1-2 seconds due to polling/udev event processing.

4.  **Buzzer Volume:**
    *   **Issue:** Driving a buzzer directly from a 3.3V GPIO pin might be quiet. A transistor driver is recommended for louder output.

5.  **First Boot Delay:**
    *   **Issue:** The first time the backend starts, it might take a few seconds to initialize the Python environment.

## Reporting Bugs

Please use the GitHub Issue Tracker to report new bugs. Include:
1.  Hardware setup (Pi model, Drone FC).
2.  Logs from `/var/log/beatha.log`.
3.  Steps to reproduce.