# Bluetooth Pairing Guide

## Overview

Project Beatha supports Bluetooth connectivity, allowing you to connect to your flight controller wirelessly through Betaflight Configurator or other compatible apps.

## How to Activate Pairing Mode

### Method 1: Physical Button
1. Press the **Pair Button** on the device
2. LEDs will blink purple for 30 seconds
3. Device is now discoverable as "beatha"

### Method 2: Web Interface
1. Open http://beatha.local in your browser
2. Click the **Start Pairing** button
3. Device will enter pairing mode for 30 seconds

### Method 3: API
```bash
curl -X POST http://beatha.local:8000/api/action/pair
```

## Connecting from Betaflight Configurator

### On Android
1. Activate pairing mode on Beatha (purple blinking LEDs)
2. Open Betaflight Configurator
3. Select "Bluetooth" connection type
4. Look for device named "beatha" or showing MAC address starting with `B8:27:EB`
5. Connect

### On iOS (if supported)
Same steps as Android

### On Desktop (requires Bluetooth adapter)
1. Pair your computer with "beatha" through system Bluetooth settings
2. Open Betaflight Configurator
3. Select the Bluetooth serial port
4. Connect

## Pairing Mode Behavior

- **Duration**: 30 seconds
- **Visual Indicator**: Purple blinking LEDs (0.5s on, 0.5s off)
- **Auto-stop**: Pairing mode exits automatically after 30 seconds
- **During pairing**: TCP proxy (port 5000) is stopped temporarily

## Troubleshooting

### Device Not Visible
**Problem**: Can't see "beatha" in Bluetooth device list

**Solutions**:
1. Make sure pairing mode is active (purple blinking LEDs)
2. Check that Bluetooth is enabled on your device
3. Move closer to the Beatha device (Bluetooth range ~10m)
4. Try activating pairing mode again

### Connection Fails
**Problem**: Device appears but won't connect

**Solutions**:
1. Remove/forget previous "beatha" pairing on your device
2. Restart Bluetooth on your device
3. Activate pairing mode again
4. Try connecting immediately after pairing mode activates

### Bluetooth Was Soft-Blocked
**Technical Note**: If Bluetooth was previously disabled (soft-blocked), Beatha automatically unblocks it when entering pairing mode. This takes ~4 seconds.

You can manually check Bluetooth status:
```bash
ssh antoine@beatha.local
sudo rfkill list bluetooth
# Should show: Soft blocked: no
```

## Technical Details

### Bluetooth Hardware
- **Chip**: Built-in Raspberry Pi Zero W Bluetooth
- **MAC Address**: Usually starts with `B8:27:EB`
- **Profile**: SPP (Serial Port Profile)
- **Baud Rate**: 115200

### Pairing Process
When pairing mode is activated, Beatha:
1. Unblocks Bluetooth (if soft-blocked)
2. Powers on Bluetooth interface
3. Makes device discoverable for 30 seconds
4. Accepts connections without PIN (NoInputNoOutput agent)
5. Auto-exits after 30 seconds

### Security
- **No PIN required**: Uses NoInputNoOutput pairing for ease of use
- **Recommendation**: Only activate pairing mode when you need it
- **Auto-timeout**: Reduces exposure window to 30 seconds

## Advanced Configuration

### Change Bluetooth Device Name
Edit `/etc/bluetooth/main.conf` on the Pi:
```ini
[General]
Name = beatha
```

Then restart Bluetooth:
```bash
sudo systemctl restart bluetooth
```

### Increase Pairing Duration
Edit the pairing loop in `src/backend/server.py`:
```python
for _ in range(60):  # 60 = 30 seconds (0.5s on + 0.5s off)
```
Change `60` to `120` for 60 seconds, etc.

## LED Status Reference

| LED Color | Pattern | Meaning |
|-----------|---------|---------|
| Purple | Blinking (0.5s on/off) | Pairing mode active |
| Blue | Breathing | Idle/TCP proxy mode |
| Orange | Solid | Working (dump in progress) |
| Green | Solid | Success |
| Red | Solid | Error |

## Support

If Bluetooth pairing continues to fail:
1. Check logs: `ssh antoine@beatha.local 'tail -f /var/log/beatha.log'`
2. Verify Bluetooth service: `systemctl status bluetooth`
3. Check rfkill status: `rfkill list bluetooth`
4. Report issues at: https://github.com/antoine-voiry/Beatha/issues
