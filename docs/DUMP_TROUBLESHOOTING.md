# Dump Extraction Troubleshooting

## Issue: "Unknown Device or Garbage Data"

When you press the **Dump** button but nothing happens or you see an error, the flight controller isn't responding properly.

### Common Causes

1. **Flight Controller Not Powered**
   - **Solution**: Connect a battery to the FC before dumping
   - USB power alone may not boot the FC properly

2. **Flight Controller in DFU/Bootloader Mode**
   - **Symptom**: FC appears as "STM32 BOOTLOADER" or similar in dmesg
   - **Solution**:
     - Exit bootloader mode (usually by unplugging USB)
     - Or flash firmware first, then try dump

3. **Flight Controller in MSC (Mass Storage) Mode**
   - **Symptom**: FC appears as storage device, not serial port
   - **Solution**: Change FC USB mode to VCP/Serial (check FC documentation)

4. **Wrong Baud Rate**
   - **Symptom**: Garbled data or no response
   - **Solution**: Check `config.json` - most FCs use 115200 (default)

5. **Flight Controller Crashed/Frozen**
   - **Solution**: Power cycle the FC (disconnect battery and USB, wait 5 seconds, reconnect)

### How to Diagnose

#### Check Device Type
```bash
ssh antoine@beatha.local 'dmesg | tail -20'
```

**Good (CDC ACM - Serial Port)**:
```
cdc_acm 1-1:1.0: ttyACM0: USB ACM device
```

**Bad (Mass Storage)**:
```
usb-storage 1-1:1.0: USB Mass Storage device detected
```

**Bad (DFU Bootloader)**:
```
Device Descriptor: bcdDevice 2.00 (STM32 BOOTLOADER)
```

#### Check What FC is Sending
```bash
ssh antoine@beatha.local 'cat /dev/ttyACM0'
```

Then type `#` and press Enter on your keyboard. You should see:
- Betaflight: Prompt returns or version info
- INAV: Similar behavior
- Garbage/Nothing: FC not in correct mode

Press Ctrl+C to exit.

#### Check Logs
```bash
ssh antoine@beatha.local 'tail -50 /var/log/beatha.log | grep -i dump'
```

Look for:
- "Opening Serial for Dump" - Started successfully
- "Unknown Device or Garbage Data" - FC not responding
- "Detected Firmware Info: Betaflight..." - Working!

### Successful Dump Process

When dump works correctly, you'll see in logs:
```
Opening Serial for Dump...
Detected Firmware Info: Betaflight/STM32F411 4.4.0 ...
Reading Data...
Dump saved to /home/antoine/dumps/dump_20260120-123456.txt
Cloud Upload Success
```

And in the UI:
- Status changes to "DUMPING"
- LEDs progress through stages:
  1. Orange LED 1: Connecting
  2. Orange LED 2: Reading
  3. Yellow LED 3: Saving
  4. Green LED 4: Success
- Status returns to "IDLE"
- Latest dump info appears in UI

### Flight Controller Compatibility

**Tested & Working:**
- Betaflight (all versions with CLI)
- INAV (all versions with CLI)
- EmuFlight

**Partial Support:**
- ArduPilot (detected but full parameter dump requires MAVLink)

**Not Supported:**
- Flight controllers without CLI interface
- DJI flight controllers
- Proprietary FCs without serial access

### Quick Checklist

Before pressing Dump:
- [ ] FC connected via USB
- [ ] UI shows "drone_connected: true"
- [ ] FC has battery connected (recommended)
- [ ] FC is not in bootloader/DFU mode
- [ ] FC USB mode is VCP/Serial (not MSC)
- [ ] LEDs show blue breathing pattern (IDLE)

### Still Not Working?

1. Try Betaflight Configurator first to verify FC responds
2. Check FC documentation for USB mode settings
3. Flash/reflash FC firmware
4. Check `/var/log/beatha.log` for detailed errors
5. Report issue with logs at: https://github.com/antoine-voiry/Beatha/issues
