# Bug Fixes Summary - High Severity Issues

All 4 high-severity bugs have been fixed, tested, and deployed successfully.

## Fixes Applied

### 1. Fix deprecated pyserial flushInput() method
**Files**: `src/main.py:201`, `src/backend/server.py:372`
**Change**: Replaced `ser.flushInput()` → `ser.reset_input_buffer()`
**Impact**: Now compatible with pyserial 3.0+ (flushInput removed in pyserial 3.0)

### 2. Add process cleanup in stop_socat()
**File**: `src/backend/server.py:276-284`
**Change**: Added `.wait(timeout=5)` with kill fallback
**Impact**: Prevents zombie processes and resource leaks

### 3. Fix race condition in state management
**File**: `src/backend/server.py`
**Changes**:
- Added `self.state_lock = threading.Lock()` in `__init__`
- Wrapped all state checks and transitions in `with self.state_lock:` blocks
- Fixed in `trigger_pair()`, `trigger_dump()`, `_perform_pairing()`, and `_perform_extraction()`
**Impact**: Thread-safe state transitions, prevents simultaneous operations

### 4. Fix infinite loop risk in serial reading
**File**: `src/backend/server.py:446-463`
**Change**: Replaced sleep-in-loop with time-based silence detection using `last_data_time` and `silence_threshold`
**Impact**: Eliminated 2-second delay on every iteration, faster data collection

## Additional Fixes

### 5. Fix hardcoded config path
**File**: `src/backend/config_loader.py:5-9`
**Change**: Use absolute path resolution: `os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.json")`
**Impact**: Works regardless of working directory

### 6. Add exception handling in background loops
**Files**: `src/backend/server.py:168-280`
**Change**: Wrapped all daemon thread loops in try-except blocks:
- `_usb_monitor_loop()`
- `_button_monitor_loop()`
- `_socat_manager_loop()`
- `_bt_proxy_manager_loop()`
- `_animation_loop()`
**Impact**: Prevents silent thread crashes, logs errors

### 7. Fix serial port cleanup with context manager
**File**: `src/backend/server.py:380-463`
**Change**: Use `with serial.Serial(...) as ser:` context manager
**Impact**: Guarantees serial port closure even on exceptions

### 8. Fix dump directory path expansion
**File**: `src/backend/server.py:114-120`, `config.json`
**Change**:
- Changed `dump_dir` from `/home/pi/dumps` to `~/dumps`
- Added `os.path.expanduser()` to expand `~` to user home
**Impact**: Works for any user running the service

### 9. Add missing storage_mode config key
**File**: `config.json:16`
**Change**: Added `"storage_mode": "cloud_sync"` to system config
**Impact**: User can configure storage mode (was only using default)

## Testing

### Unit Tests Created
- **File**: `tests/test_bug_fixes_static.py`
- **Tests**: 12 static code analysis tests
- **Result**: ✅ All 12 tests pass

### Integration Testing
- ✅ Deployed to Raspberry Pi target
- ✅ Service starts successfully
- ✅ API responding on http://beatha.local:8000
- ✅ Background threads running
- ✅ Dump directory created with correct permissions

## Deployment

```bash
# From Mac to Pi
./scripts/push_to_pi.sh antoine@beatha.local

# Service status on Pi
sudo systemctl status beatha
# ● beatha.service - Project Beatha - FPV Drone Recovery Tool
#    Active: active (running)
```

## Verification

```bash
# Check logs
tail -f /var/log/beatha.log

# Successful startup:
# 2026-01-20T22:53:07Z | INFO | 🟢 Beatha Manager Started
# INFO: Application startup complete.
# INFO: Uvicorn running on http://0.0.0.0:8000
```

## Commit Messages (for reference)

```
fix: replace deprecated pyserial flushInput with reset_input_buffer

fix: add proper process cleanup in stop_socat to prevent zombies

fix: add threading lock to prevent race conditions in state management

fix: optimize serial reading loop to remove unnecessary delays

fix: use absolute path for config.json to support any working directory

fix: add exception handling to background daemon threads

fix: use context manager for serial port to ensure cleanup

fix: expand tilde in dump_dir path and add storage_mode config
```

## Status: ✅ COMPLETE

All high-severity bugs fixed, tested, and deployed successfully to production.
