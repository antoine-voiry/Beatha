# Troubleshooting Guide

Something not working? Don't panic. Here are the common issues and fixes.

## 🟢 Pi Zero Status LED Codes

The Green LED behavior can vary by OS version. **The only true test is SSH.**

| LED Behavior | Meaning | Status |
| :--- | :--- | :--- |
| **Flickering / Blinking** | Reading/Writing to SD Card. | ✅ **Normal (Booting/Working)** |
| **Solid ON (No blink)** | System Idle OR Frozen. | ⚠️ **Try SSH.** If SSH works, it's fine. |
| **OFF (after flickering)** | System Idle. | ✅ **Normal** |
| **Off (Never turns on)** | No Power or Dead Pi. | ❌ **Error:** Check cable or 5V soldering. |

> **Rule of Thumb:** If you can ping it or SSH into it, ignore the LED.

---

## 📡 Connectivity Issues

### "I can't connect via SSH" (`ssh: or host not found`)
1.  **Wait Longer:** First boot takes up to 5 minutes to resize the filesystem and generate keys.
2.  **Check Hostname:** Try `ssh pi@beatha.local`. If that fails, look in your router's admin page for the IP address and try `ssh pi@192.168.x.x`.
3.  **Windows Users:** You might need to install **Bonjour Print Services** to resolve `.local` addresses, or just use the IP address.
4.  **Re-Flash:** Did you definitely fill in the **Gear Icon** settings in the Imager? (SSID, Password, Username). If not, re-flash.

### "WiFi Hotspot (Beatha_AP) didn't appear"
1.  **Did you run the installer?** The hotspot is only created *after* you run `scripts/setup.sh`.
2.  **Check Service:** Log in via SSH (Home WiFi) and run `systemctl status hostapd`.

---

## 🔌 Hardware / Wiring Issues

### "The Drone isn't detected"
(Web UI shows "Searching..." forever)

1.  **Check USB Wires:**
    *   Did you swap **Green** (Data+) and **White** (Data-)?
    *   Try swapping them on the PP22/PP23 pads.
2.  **Check Solder:** ensure the wires on PP22/PP23 are not touching each other or the surrounding metal shield of the USB port.
3.  **Check Power:** Is the drone actually powered on? (Does it light up?).

### "The Pi reboots when I plug in the Drone"
*   **Cause:** Voltage Sag. The drone draws too much inrush current.
*   **Fix:** Ensure you have a high-quality 2A+ Power Supply.

### "Magic Smoke / Burning Smell"
*   **Cause:** Short Circuit.
*   **Action:** **UNPLUG IMMEDIATELY.**
*   **Check:** Look at Pin 2 (5V) and Pin 6 (GND) on the header. Are they bridged? Look at the back of the Prototyping Board.
