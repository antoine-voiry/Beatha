# Dump Display Feature

## Overview

The web interface now displays detailed information about the latest dump, including firmware version and full dump contents.

## Features

### 1. Latest Dump Card

When a successful dump is completed, the UI automatically displays a "Latest Dump" card showing:

- **Filename**: Name of the dump file (e.g., `dump_20260120-123456.txt`)
- **Size**: File size in human-readable format (B, KB, MB)
- **Timestamp**: Date and time when the dump was created
- **Firmware Version**: Detected firmware (e.g., "Betaflight/STM32F411 4.4.0...")

### 2. View Full Dump

Click "View Full Dump" to expand and see the complete dump contents:
- Line count displayed
- Scrollable pre-formatted text view
- Syntax-preserved dump data
- Max height: 400px with scroll

## API Endpoints

### GET /api/status

Returns system status including latest dump information:

```json
{
  "mode": "IDLE",
  "drone_connected": true,
  "buttons": {
    "dump": false,
    "pair": false
  },
  "latest_dump": {
    "filename": "dump_20260120-123456.txt",
    "timestamp": 1737412345.678,
    "size": 12345
  }
}
```

### GET /api/dumps/{filename}

Retrieves full dump content and metadata:

```json
{
  "filename": "dump_20260120-123456.txt",
  "content": "# dump\n\n# version\n...",
  "version": "Betaflight/STM32F411 4.4.0 Jan 15 2024 / 12:34:56 (abcd1234)",
  "size": 12345
}
```

**Security**: Filename sanitization prevents directory traversal attacks (no `..` or `/` allowed)

## User Experience

### Before Dump
- UI shows "Start Dump" button (enabled when drone connected)
- No dump card displayed

### During Dump
- Status changes to "DUMPING"
- LEDs progress through stages (Orange → Yellow → Green)
- Animation spinner shows activity

### After Successful Dump
- Status returns to "IDLE"
- "Latest Dump" card appears automatically
- Card is expanded by default
- Firmware version highlighted in green
- Full dump content available in collapsible section

### After Failed Dump
- No dump card appears (no file saved)
- Check [DUMP_TROUBLESHOOTING.md](DUMP_TROUBLESHOOTING.md) for common issues
- Logs contain error details

## Common Issues

### "Unknown Device or Garbage Data"

**Symptoms:**
- Dump triggered but no dump card appears
- Logs show "Unknown Device or Garbage Data"

**Solutions:**
1. Connect battery to flight controller
2. Ensure FC is not in bootloader/DFU mode
3. Verify FC USB mode is VCP/Serial (not MSC)
4. See [DUMP_TROUBLESHOOTING.md](DUMP_TROUBLESHOOTING.md) for full guide

### No Firmware Version Shown

**Possible Reasons:**
- Custom firmware without standard version string
- ArduPilot (uses MAVLink, not CLI)
- Proprietary FC firmware

**Workaround:** Full dump content still available in "View Full Dump" section

## Technical Implementation

### Frontend (React)

**Component:** `DumpInfo` in [src/frontend/src/App.jsx](../src/frontend/src/App.jsx)

- Auto-fetches dump content when `latest_dump` changes
- Formats timestamp and file size
- Extracts version line from first 20 lines
- Collapsible details element for full dump

### Backend (FastAPI)

**Handler:** `get_dump()` in [src/backend/server.py](../src/backend/server.py:594-619)

- Reads dump file from `~/dumps/` directory
- Searches for firmware version in first 20 lines
- Returns JSON with content, version, and metadata

**Status Handler:** `get_status()` in [src/backend/server.py](../src/backend/server.py:535-554)

- Scans `~/dumps/` directory
- Finds most recent dump file (by modification time)
- Returns filename, timestamp, and size

## Version Detection

The system detects these firmware types:
- **Betaflight**: `Betaflight/...` in version line
- **INAV**: `INAV/...` in version line
- **EmuFlight**: `EmuFlight/...` in version line
- **ArduPilot**: `ArduPilot/...` in version line (detected but full dump requires MAVLink)

Version line is extracted from the first 20 lines of the dump file.

## File Storage

- **Location**: `~/dumps/` (expands to `/home/antoine/dumps` on Pi)
- **Naming**: `dump_YYYYMMDD-HHMMSS.txt`
- **Permissions**: Created by root (service user), readable by all
- **Cleanup**: Manual (no automatic cleanup implemented)

## Future Enhancements

Potential improvements:
1. Download dump file button
2. Delete old dumps from UI
3. Dump history list (multiple dumps)
4. Syntax highlighting for dump content
5. Search/filter within dump
6. Compare two dumps side-by-side
7. Parse specific settings (e.g., PID values) into structured view

## Related Documentation

- [DUMP_TROUBLESHOOTING.md](DUMP_TROUBLESHOOTING.md) - Troubleshooting guide
- [BLUETOOTH_PAIRING.md](BLUETOOTH_PAIRING.md) - Bluetooth connectivity
- [DEPLOYMENT_SUMMARY.md](../DEPLOYMENT_SUMMARY.md) - System overview
