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

6.  **USB Device Not Detected / Error -71:**
    *   **Issue:** Flight controller connected via USB shows in `dmesg` but fails with "device descriptor read/64, error -71" and doesn't create `/dev/ttyACM0`.
    *   **Symptoms:**
        * `lsusb` only shows root hub
        * `dmesg` shows "new low-speed USB device" then "error -71"
        * UI shows "drone_connected: false"
        * No `/dev/ttyACM*` or `/dev/ttyUSB*` device
    *   **Common Causes:**
        * **Bad/Low-quality USB cable** (most common - 90% of cases)
        * Insufficient power to USB device
        * USB OTG configuration issue
        * Faulty flight controller USB port
    *   **Troubleshooting Steps:**
        1. **Try a different USB cable** - Use a known-good **data cable**, not charge-only
        2. **Check cable length** - Keep under 1 meter for reliability
        3. **Power the FC separately** - Connect flight controller battery/external power
        4. **Verify dmesg**: `ssh antoine@beatha.local 'dmesg | tail -30'`
        5. **Check for device**: `ssh antoine@beatha.local 'ls /dev/ttyACM* /dev/ttyUSB*'`
        6. **Try different FC USB mode** - Some FCs have DFU/MSC/VCP mode selection
    *   **Successful Connection Looks Like:**
        * `dmesg`: "new full-speed USB device number X using dwc_otg"
        * `dmesg`: "cdc_acm 1-1:1.0: ttyACM0: USB ACM device"
        * Device exists: `/dev/ttyACM0`
        * UI shows: `"drone_connected": true`
    *   **Status:** Hardware/cable issue - not a software bug

7.  **Bluetooth Pairing Fails from Mobile Devices:**
    *   **Issue:** While Bluetooth becomes discoverable (visible on devices), actual pairing/connection from mobile phones may fail. The device shows as "beatha" or with MAC address but won't complete pairing.
    *   **Root Cause:** The NoInputNoOutput agent configuration may not be properly registered with BlueZ, or the SPP (Serial Port Profile) service may not be advertising correctly.
    *   **Observed Behavior:**
        * Device appears in Bluetooth scan results
        * Powered: yes, Discoverable: yes
        * Connection attempts fail or time out
        * No pairing prompt appears on mobile device
    *   **Workaround (Temporary):**
        1. SSH into the Pi: `ssh antoine@beatha.local`
        2. Manually run: `sudo bluetoothctl`
        3. In bluetoothctl: `agent NoInputNoOutput`, then `default-agent`, then `discoverable on`
        4. Try pairing from your phone again
    *   **Status:** Under investigation - may require BlueZ configuration changes or different pairing agent
    *   **Alternative:** Use TCP proxy mode (port 5000) over WiFi instead of Bluetooth

## Reporting Bugs

Please use the GitHub Issue Tracker to report new bugs. Include:
1.  Hardware setup (Pi model, Drone FC).
2.  Logs from `/var/log/beatha.log`.
3.  Steps to reproduce.