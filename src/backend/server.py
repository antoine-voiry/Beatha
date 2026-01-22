from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import os
import sys
import glob
import time
import threading
import logging
import signal
import serial
import serial.tools.list_ports
import pyudev
import re
import shutil
from datetime import datetime
from contextlib import asynccontextmanager
from src.backend.config_loader import config

# Try to import pymavlink for ArduPilot support
try:
    from pymavlink import mavutil
    MAVLINK_AVAILABLE = True
except ImportError:
    MAVLINK_AVAILABLE = False


def sanitize_dirname(name: str) -> str:
    """Sanitize a string to be used as a directory name.

    Removes or replaces characters that are problematic for directory names:
    - Removes: / \\ : * ? " < > | and control characters
    - Replaces spaces with underscores
    - Strips leading/trailing whitespace and dots
    """
    if not name:
        return "unknown"

    # Replace problematic characters
    sanitized = re.sub(r'[/\\:*?"<>|]', '', name)
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    # Remove control characters and non-printable characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    # Strip leading/trailing whitespace and dots (dots at start can hide dirs on unix)
    sanitized = sanitized.strip('. \t\n\r')
    # Collapse multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)

    return sanitized if sanitized else "unknown"


# --- Logging Setup ---
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ',
    force=True
)
logger = logging.getLogger("Beatha")

# --- GPIO Emulation / Hardware Abstraction ---
# Check for forced emulation via Environment Variable (useful for CI/Development)
FORCE_EMULATION = os.environ.get("BEATHA_EMULATION", "false").lower() == "true"

try:
    if FORCE_EMULATION:
        raise ImportError("Forced Emulation Mode")
    import board
    import neopixel
    from digitalio import DigitalInOut, Direction, Pull
    EMULATION_MODE = False
    logger.info("✅ GPIO Libraries Loaded (Live Mode)")
except ImportError:
    if config["features"]["emulation_mode_fallback"] or FORCE_EMULATION:
        EMULATION_MODE = True
        logger.warning("⚠️  Hardware Not Found or Disabled: Running in Emulation Mode")
    else:
        raise ImportError("Hardware not found and emulation disabled.")

    # Mock Classes
    class DigitalInOut:
        def __init__(self, pin): self.value = True # Pull UP = True default
        def direction(self, d): pass
        def pull(self, p): pass

    class Direction: INPUT = 0; OUTPUT = 1
    class Pull: UP = 0

    class MockNeoPixel:
        def __init__(self, pin, n, brightness=0.2, auto_write=False):
            self.n = n
        def fill(self, color): pass
        def show(self): pass
        def __setitem__(self, key, value): pass

    class neopixel:
        NeoPixel = MockNeoPixel

    class Board:
        def __getattr__(self, name):
            if name.startswith("D"): return int(name[1:])
            raise AttributeError(f"Board has no attribute {name}")
    board = Board()

# --- Hardware Initialization ---
HW_CONF = config["hardware"]
SYS_CONF = config["system"]

# Colors
COLOR_OFF = (0, 0, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_ORANGE = (255, 100, 0)
COLOR_YELLOW = (255, 255, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (255, 0, 0)
COLOR_PURPLE = (180, 0, 255)

# Pins
try:
    LED_PIN = getattr(board, f"D{HW_CONF['led_pin']}")
    BTN_DUMP_PIN = getattr(board, f"D{HW_CONF['button_dump_pin']}")
    BTN_PAIR_PIN = getattr(board, f"D{HW_CONF['button_pair_pin']}")
    BUZZER_PIN = getattr(board, f"D{HW_CONF['buzzer_pin']}")
except AttributeError as e:
    logger.error(f"Invalid Pin Configuration: {e}")
    if not EMULATION_MODE: sys.exit(1)

# Peripherals
pixels = neopixel.NeoPixel(LED_PIN, HW_CONF["led_count"], brightness=HW_CONF["led_brightness"], auto_write=False)
btn_dump = DigitalInOut(BTN_DUMP_PIN)
btn_dump.direction = Direction.INPUT
btn_dump.pull = Pull.UP

btn_pair = DigitalInOut(BTN_PAIR_PIN)
btn_pair.direction = Direction.INPUT
btn_pair.pull = Pull.UP

buzzer = DigitalInOut(BUZZER_PIN)
buzzer.direction = Direction.OUTPUT
buzzer.value = False

# --- State Machine & Logic ---
class BeathaManager:
    def __init__(self):
        self.state = "IDLE" # IDLE, DUMPING, PAIRING, ERROR
        self.state_lock = threading.Lock()  # Protect state transitions
        self.socat_process = None
        self.running = True
        self.stop_animation = False
        self.animation_thread = None
        self.drone_connected = False
        self.serial_port = None  # Will be auto-detected
        self.serial_port_config = SYS_CONF["serial_port"]  # Configured port (may not exist)
        self.baud_rate = SYS_CONF.get("baud_rate", 115200)
        self.fc_info = None  # Detected flight controller info
        self.fc_logs = []  # Recent FC communication logs (max 100 entries)
        self.fc_logs_lock = threading.Lock()

        # Ensure dump dir
        self.dump_dir = SYS_CONF["dump_dir"]
        if EMULATION_MODE:
            self.dump_dir = "./dumps_mock"
        else:
            # Expand ~ to user home directory
            self.dump_dir = os.path.expanduser(self.dump_dir)
        os.makedirs(self.dump_dir, exist_ok=True)

    def add_log(self, log_type: str, message: str):
        """Add a log entry to the FC logs"""
        with self.fc_logs_lock:
            timestamp = datetime.now().isoformat()
            self.fc_logs.append({
                "timestamp": timestamp,
                "type": log_type,  # "tx", "rx", "info", "error"
                "message": message
            })
            # Keep only last 100 entries
            if len(self.fc_logs) > 100:
                self.fc_logs = self.fc_logs[-100:]

    def detect_fc_type(self):
        """Detect flight controller type and version"""
        if EMULATION_MODE:
            self.fc_info = {
                "type": "Betaflight",
                "version": "4.4.0 (Emulated)",
                "target": "MOCK_TARGET",
                "raw": "Emulation Mode"
            }
            return self.fc_info

        if not self.serial_port:
            raise Exception("No serial port configured")

        try:
            with serial.Serial(self.serial_port, self.baud_rate, timeout=2) as ser:
                # Wake up and request version
                ser.write(b'#\r\n')
                time.sleep(0.1)
                ser.reset_input_buffer()

                self.add_log("tx", "version")
                ser.write(b'version\r\n')

                version_info = ""
                start_time = time.time()

                while time.time() - start_time < 3:
                    if ser.in_waiting:
                        try:
                            line = ser.readline().decode('utf-8', errors='ignore').strip()
                            if line:
                                self.add_log("rx", line)
                                version_info += line + "\n"

                                # Detect FC type
                                if "Betaflight" in line:
                                    # Parse: "# Betaflight / STM32F405 (S405) 4.4.0 ..."
                                    parts = line.split()
                                    version = next((p for p in parts if p[0].isdigit()), "Unknown")
                                    target = parts[3] if len(parts) > 3 else "Unknown"
                                    self.fc_info = {
                                        "type": "Betaflight",
                                        "version": version,
                                        "target": target.strip("()"),
                                        "raw": line
                                    }
                                    return self.fc_info

                                elif "INAV" in line:
                                    parts = line.split()
                                    version = next((p for p in parts if p[0].isdigit()), "Unknown")
                                    self.fc_info = {
                                        "type": "INAV",
                                        "version": version,
                                        "target": "Unknown",
                                        "raw": line
                                    }
                                    return self.fc_info

                                elif "ArduPilot" in line or "ChibiOS" in line:
                                    self.fc_info = {
                                        "type": "ArduPilot",
                                        "version": "Unknown",
                                        "target": "Unknown",
                                        "raw": line
                                    }
                                    return self.fc_info

                                elif "CC3D" in line or "OpenPilot" in line:
                                    self.fc_info = {
                                        "type": "CC3D/OpenPilot",
                                        "version": "Unknown",
                                        "target": "CC3D",
                                        "raw": line
                                    }
                                    return self.fc_info

                        except Exception as e:
                            self.add_log("error", f"Decode error: {e}")

                # If we got data but couldn't identify
                if version_info:
                    self.fc_info = {
                        "type": "Unknown",
                        "version": "Unknown",
                        "target": "Unknown",
                        "raw": version_info[:200]
                    }
                    return self.fc_info

                raise Exception("No response from flight controller")

        except serial.SerialException as e:
            self.add_log("error", f"Serial error: {e}")
            raise Exception(f"Serial error: {e}")

    def get_board_name(self):
        """Get the craft/board name from Betaflight/INAV using the 'name' CLI command."""
        if EMULATION_MODE:
            return "MockQuad"

        if not self.serial_port:
            return None

        try:
            with serial.Serial(self.serial_port, self.baud_rate, timeout=2) as ser:
                # Wake up CLI
                ser.write(b'#\r\n')
                time.sleep(0.1)
                ser.reset_input_buffer()

                self.add_log("tx", "name")
                ser.write(b'name\r\n')

                start_time = time.time()
                while time.time() - start_time < 2:
                    if ser.in_waiting:
                        try:
                            line = ser.readline().decode('utf-8', errors='ignore').strip()
                            if line:
                                self.add_log("rx", line)
                                # Betaflight returns: "name"  or  "# name" followed by the actual name
                                # Or: name = <name> or name: <name>
                                # Check for actual name response
                                if line.startswith('name') and '=' in line:
                                    # Format: name = MyQuad
                                    name = line.split('=', 1)[1].strip()
                                    if name and name != '-':
                                        return name
                                elif line.startswith('name') and ':' in line:
                                    # Format: name: MyQuad
                                    name = line.split(':', 1)[1].strip()
                                    if name and name != '-':
                                        return name
                                elif not line.startswith('#') and not line.startswith('name') and line and line != '-':
                                    # Might be just the name on its own line
                                    # Skip common CLI responses
                                    if line not in ['#', 'CLI', 'OK', '']:
                                        return line
                        except Exception as e:
                            self.add_log("error", f"Name read error: {e}")
                    else:
                        time.sleep(0.05)

        except serial.SerialException as e:
            self.add_log("error", f"Serial error getting name: {e}")

        return None

    def enter_msc_mode(self):
        """Put Betaflight into MSC (Mass Storage Class) mode for SD card access.

        This makes the FC appear as a USB mass storage device, allowing direct
        access to the SD card for blackbox logs. The FC will need to be unplugged
        and replugged after exiting MSC mode to return to normal operation.

        Returns True if command was sent successfully, False otherwise.
        """
        if EMULATION_MODE:
            self.add_log("info", "MSC mode (emulated)")
            return True

        if not self.serial_port:
            self.add_log("error", "No serial port for MSC mode")
            return False

        try:
            with serial.Serial(self.serial_port, self.baud_rate, timeout=2) as ser:
                # Wake up CLI
                ser.write(b'#\r\n')
                time.sleep(0.1)
                ser.reset_input_buffer()

                self.add_log("tx", "msc")
                self.add_log("info", "Entering MSC mode - FC will appear as USB storage")
                ser.write(b'msc\r\n')

                # Give it a moment to start MSC mode
                time.sleep(0.5)

                return True

        except serial.SerialException as e:
            self.add_log("error", f"Failed to enter MSC mode: {e}")
            return False

    def download_blackbox_msc(self, mount_path: str = None) -> list:
        """Download blackbox files from an FC in MSC mode.

        When MSC mode is active, the SD card appears as a mounted drive.
        This method looks for that mount and copies blackbox files.

        Args:
            mount_path: Optional explicit mount path. If not provided, will try to auto-detect.

        Returns:
            List of downloaded file paths.
        """
        if EMULATION_MODE:
            return []

        # Common mount points to check
        mount_points = [
            mount_path,
            "/media/beatha",
            "/media/pi",
            "/mnt/fc_sd",
            "/mnt",
        ] if mount_path else [
            "/media/beatha",
            "/media/pi",
            "/mnt/fc_sd",
            "/mnt",
        ]

        # Look for a mounted FC SD card
        sd_mount = None
        for mp in mount_points:
            if mp and os.path.isdir(mp):
                # Check for BLACKBOX directory or LOG*.BFL files
                if os.path.isdir(os.path.join(mp, "BLACKBOX")):
                    sd_mount = os.path.join(mp, "BLACKBOX")
                    break
                elif os.path.isdir(os.path.join(mp, "blackbox")):
                    sd_mount = os.path.join(mp, "blackbox")
                    break
                # Check for files at root
                bfl_files = glob.glob(os.path.join(mp, "*.BFL")) + glob.glob(os.path.join(mp, "*.bfl"))
                if bfl_files:
                    sd_mount = mp
                    break

        if not sd_mount:
            self.add_log("error", "Could not find mounted FC SD card")
            return []

        self.add_log("info", f"Found blackbox files at: {sd_mount}")

        # Find all blackbox files
        files = glob.glob(os.path.join(sd_mount, "*.BFL"))
        files += glob.glob(os.path.join(sd_mount, "*.bfl"))
        files += glob.glob(os.path.join(sd_mount, "LOG*.TXT"))

        if not files:
            self.add_log("info", "No blackbox files found")
            return []

        # Copy files to dump directory
        downloaded = []
        for src in files:
            filename = os.path.basename(src)
            dst = os.path.join(self.dump_dir, filename)
            try:
                shutil.copy2(src, dst)
                downloaded.append(dst)
                self.add_log("info", f"Copied: {filename}")
            except Exception as e:
                self.add_log("error", f"Failed to copy {filename}: {e}")

        return downloaded

    def _detect_serial_port(self):
        """
        Smart detection of flight controller serial port.
        Uses same logic as Betaflight Configurator: checks VID:PID, device type, and manufacturer.
        """
        # Common flight controller VID:PID combinations
        KNOWN_FC_VIDPID = [
            (0x0483, 0x5740),  # STM32 DFU
            (0x0483, 0xdf11),  # STM32 Bootloader
            (0x10c4, 0xea60),  # CP210x (used by many FCs)
            (0x0403, 0x6001),  # FTDI
            (0x0403, 0x6015),  # FTDI X-Series
            (0x2341, 0x0001),  # Arduino
            (0x2341, 0x0043),  # Arduino Uno
            (0x16c0, 0x0483),  # Teensy
        ]

        ports = serial.tools.list_ports.comports()
        candidates = []

        for port in ports:
            score = 0

            # Check if it's a known VID:PID
            if port.vid and port.pid and (port.vid, port.pid) in KNOWN_FC_VIDPID:
                score += 10

            # Prefer ACM devices (native USB CDC)
            if 'ACM' in port.device:
                score += 5
            elif 'USB' in port.device:
                score += 3

            # Check description for FC keywords
            desc_lower = (port.description or "").lower()
            if any(kw in desc_lower for kw in ['stm32', 'betaflight', 'inav', 'flight', 'cp210']):
                score += 5

            # Check manufacturer
            mfr_lower = (port.manufacturer or "").lower()
            if any(kw in mfr_lower for kw in ['stm', 'silicon labs', 'ftdi']):
                score += 3

            if score > 0:
                candidates.append((port.device, score, port.description))

        if not candidates:
            return None

        # Sort by score (highest first) and return best match
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_port = candidates[0][0]
        logger.info(f"Detected FC port: {best_port} (score: {candidates[0][1]}, {candidates[0][2]})")
        return best_port

    def start(self):
        """Start background threads"""
        self.running = True
        # Detect serial port on startup
        self.serial_port = self._detect_serial_port()
        if self.serial_port:
            self.drone_connected = True
            logger.info(f"🔌 Detected serial port: {self.serial_port}")
        else:
            self.drone_connected = False
            logger.info("❌ No serial port detected")

        threading.Thread(target=self._animation_loop, daemon=True).start()
        threading.Thread(target=self._button_monitor_loop, daemon=True).start()
        threading.Thread(target=self._usb_monitor_loop, daemon=True).start()
        threading.Thread(target=self._socat_manager_loop, daemon=True).start()
        threading.Thread(target=self._bt_proxy_manager_loop, daemon=True).start()
        logger.info("🟢 Beatha Manager Started")

    def stop(self):
        self.running = False
        self.stop_socat()
        self.stop_bt_proxy()
        pixels.fill(COLOR_OFF)
        pixels.show()

    # --- Low Level Helpers ---
    def set_leds(self, color):
        self.stop_animation = True
        pixels.fill(color)
        pixels.show()

    def set_single_led(self, index, color):
        if 0 <= index < HW_CONF["led_count"]:
            pixels[index] = color
            pixels.show()

    def beep(self, pattern="short"):
        """Simple beep patterns"""
        if pattern == "short":
            buzzer.value = True; time.sleep(0.1); buzzer.value = False
        elif pattern == "success":
            buzzer.value = True; time.sleep(0.1); buzzer.value = False; time.sleep(0.1)
            buzzer.value = True; time.sleep(0.1); buzzer.value = False
        elif pattern == "victory":
            # Ta-Da-Da-Taaaa!
            notes = [0.1, 0.1, 0.1, 0.4]
            gaps = [0.05, 0.05, 0.05, 0.1]
            for i, duration in enumerate(notes):
                buzzer.value = True
                time.sleep(duration)
                buzzer.value = False
                time.sleep(gaps[i])
        elif pattern == "error":
            buzzer.value = True; time.sleep(0.5); buzzer.value = False

    # --- Loops ---
    def _usb_monitor_loop(self):
        """Monitor USB Hotplug using pyudev"""
        try:
            if EMULATION_MODE: return # Skip on Mac/PC without /dev

            context = pyudev.Context()
            monitor = pyudev.Monitor.from_netlink(context)
            monitor.filter_by(subsystem='tty')

            for device in monitor:
                if not self.running: break
                device_node = device.device_node

                # Check if it's a serial device we care about (ttyACM* or ttyUSB*)
                if device_node and ('/dev/ttyACM' in device_node or '/dev/ttyUSB' in device_node):
                    if device.action == 'add':
                        logger.info(f"🔌 Serial device connected: {device_node}")
                        self.serial_port = device_node
                        self.drone_connected = True
                        self.beep("short")
                    elif device.action == 'remove':
                        if device_node == self.serial_port:
                            logger.info(f"❌ Serial device disconnected: {device_node}")
                            self.drone_connected = False
                            self.serial_port = self._detect_serial_port()  # Try to find another
                            if not self.serial_port:
                                self.stop_socat() # Safety cleanup
                                self.stop_bt_proxy()
                            else:
                                logger.info(f"🔌 Switched to: {self.serial_port}")
        except Exception as e:
            logger.error(f"USB Monitor Loop crashed: {e}", exc_info=True)

    def _button_monitor_loop(self):
        """Poll buttons"""
        try:
            while self.running:
                # DUMP Button (Active Low)
                if not btn_dump.value:
                    time.sleep(0.05) # Debounce
                    if not btn_dump.value:
                        logger.info("🔘 Dump Button Pressed")
                        self.trigger_dump()
                        while not btn_dump.value: time.sleep(0.1) # Wait release

                # PAIR Button
                if not btn_pair.value:
                    time.sleep(0.05)
                    if not btn_pair.value:
                        logger.info("🔘 Pair Button Pressed")
                        self.trigger_pair()
                        while not btn_pair.value: time.sleep(0.1)

                time.sleep(0.1)
        except Exception as e:
            logger.error(f"Button Monitor Loop crashed: {e}", exc_info=True)

    def _socat_manager_loop(self):
        """Keep socat TCP proxy running in IDLE mode"""
        try:
            while self.running:
                if self.state == "IDLE" and self.drone_connected:
                    if self.socat_process is None or self.socat_process.poll() is not None:
                        self.start_socat()
                elif self.state != "IDLE" or not self.drone_connected:
                    if self.socat_process:
                        self.stop_socat()
                time.sleep(1)
        except Exception as e:
            logger.error(f"Socat Manager Loop crashed: {e}", exc_info=True)

    def _bt_proxy_manager_loop(self):
        """Keep Bluetooth RFCOMM proxy running in IDLE mode"""
        try:
            self.bt_process = None
            while self.running:
                if self.state == "IDLE" and self.drone_connected:
                    # We use rfcomm watch to listen on channel 1 and bridge to serial
                    if self.bt_process is None or self.bt_process.poll() is not None:
                        try:
                            # Register SPP (Serial Port Profile) first to ensure visibility
                            subprocess.run(["sdptool", "add", "SP"], check=False, stdout=subprocess.DEVNULL)

                            logger.info("🔵 Starting BT RFCOMM Proxy...")
                            # Command: rfcomm watch hci0 1 socat STDIO FILE:/dev/ttyACM0,raw,echo=0
                            cmd = [
                                "rfcomm", "watch", "hci0", "1",
                                "socat", "STDIO", f"FILE:{self.serial_port},b115200,raw,echo=0"
                            ]
                            self.bt_process = subprocess.Popen(cmd)
                        except Exception as e:
                            logger.error(f"BT Proxy Start Failed: {e}")
                            time.sleep(5)
                elif self.state != "IDLE" or not self.drone_connected:
                    self.stop_bt_proxy()

                time.sleep(2)
        except Exception as e:
            logger.error(f"BT Proxy Manager Loop crashed: {e}", exc_info=True)

    def _animation_loop(self):
        """Breathing Blue in IDLE"""
        try:
            brightness = 0.0
            delta = 0.05
            while self.running:
                if self.state == "IDLE" and not self.stop_animation:
                    brightness += delta
                    if brightness >= 0.8: brightness = 0.8; delta = -0.05
                    elif brightness <= 0.1: brightness = 0.1; delta = 0.05

                    b_val = int(255 * brightness)
                    pixels.fill((0, 0, b_val))
                    pixels.show()
                    time.sleep(0.05)
                else:
                    time.sleep(0.2)
        except Exception as e:
            logger.error(f"Animation Loop crashed: {e}", exc_info=True)

    # --- Actions ---
    def start_socat(self):
        try:
            cmd = ["socat", f"TCP-LISTEN:5000,fork,reuseaddr", f"FILE:{self.serial_port},b115200,raw,echo=0"]
            self.socat_process = subprocess.Popen(cmd)
            logger.info("📡 Socat Proxy Started")
        except Exception as e:
            logger.error(f"Socat start failed: {e}")

    def stop_socat(self):
        if self.socat_process:
            self.socat_process.terminate()
            try:
                self.socat_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.socat_process.kill()
            self.socat_process = None
            logger.info("Connection Closed (Socat stopped)")

    def stop_bt_proxy(self):
        if hasattr(self, 'bt_process') and self.bt_process:
            logger.info("Stopping BT Proxy...")
            self.bt_process.terminate()
            try:
                self.bt_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.bt_process.kill()
            self.bt_process = None

    def trigger_pair(self):
        with self.state_lock:
            if self.state != "IDLE":
                return
            self.state = "PAIRING"

        threading.Thread(target=self._perform_pairing).start()

    def _perform_pairing(self):

        self.stop_animation = True
        self.stop_socat()
        self.stop_bt_proxy()

        logger.info("Starting Bluetooth Pairing Mode")
        try:
            # Unblock Bluetooth if soft-blocked (no sudo needed, we run as root)
            subprocess.run(["/usr/sbin/rfkill", "unblock", "bluetooth"], check=False,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)  # Wait for unblock to take effect

            # Use hciconfig as more reliable alternative to bluetoothctl for power
            subprocess.run(["/usr/bin/hciconfig", "hci0", "up"], check=False,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)  # Wait for interface to come up

            # Setup Bluetooth pairing
            subprocess.run(["bluetoothctl", "power", "on"], check=False,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
            subprocess.run(["bluetoothctl", "discoverable", "on"], check=False,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["bluetoothctl", "pairable", "on"], check=False,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["bluetoothctl", "agent", "NoInputNoOutput"], check=False,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["bluetoothctl", "default-agent"], check=False,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            logger.info("Bluetooth pairing mode active for 30 seconds")

            # Blink Purple 30s
            for _ in range(60):
                if not self.running: break
                pixels.fill(COLOR_PURPLE); pixels.show()
                time.sleep(0.25)
                pixels.fill(COLOR_OFF); pixels.show()
                time.sleep(0.25)

        except Exception as e:
            logger.error(f"Pairing Error: {e}")
            self.set_leds(COLOR_RED)
            time.sleep(2)

        with self.state_lock:
            self.state = "IDLE"
        self.stop_animation = False

    def trigger_dump(self):
        with self.state_lock:
            if self.state != "IDLE":
                return
            if not self.drone_connected and not EMULATION_MODE:
                logger.warning("Dump requested but drone not connected")
                self.beep("error")
                return
            self.state = "DUMPING"

        threading.Thread(target=self._perform_extraction).start()

    def _perform_extraction(self):
        self.stop_animation = True
        self.stop_socat()
        self.stop_bt_proxy()

        # Clear previous logs for this extraction
        with self.fc_logs_lock:
            self.fc_logs = []

        # LED Sequence as per State Machine
        pixels.fill(COLOR_OFF); pixels.show()

        try:
            # Step B: Connect (LED 1 Orange)
            self.set_single_led(0, COLOR_ORANGE)
            self.add_log("info", "Opening Serial for Dump...")
            logger.info("Opening Serial for Dump...")

            dump_content = ""
            is_ardupilot = False
            is_betaflight = False

            if not EMULATION_MODE:
                with serial.Serial(self.serial_port, self.baud_rate, timeout=2) as ser:
                    # 1. Wake up & Get Version
                    ser.write(b'#\r\n')
                    time.sleep(0.1)
                    ser.reset_input_buffer()
                    self.add_log("tx", "version")
                    ser.write(b'version\r\n')

                    version_info = ""
                    start_time = time.time()
                    valid_fw = False
                    while time.time() - start_time < 3: # Short timeout for version
                        if ser.in_waiting:
                            try:
                                line = ser.readline().decode('utf-8', errors='ignore')
                                self.add_log("rx", line.strip())

                                # Check for ArduPilot / MAVLink garbage (often shows as non-printable)
                                if "ArduPilot" in line or "ChibiOS" in line:
                                    is_ardupilot = True
                                    version_info += line
                                    valid_fw = True
                                    break

                                version_info += line
                                if "Betaflight" in line:
                                    is_betaflight = True
                                    valid_fw = True
                                elif "INAV" in line or "Emuflight" in line:
                                    valid_fw = True

                                if "GCC" in line or "Config" in line:
                                    break
                            except Exception:
                                # Likely binary data (MAVLink)
                                is_ardupilot = True
                                version_info = "Detected Binary Data (Possible ArduPilot/MAVLink)"
                                valid_fw = True # Assume valid but different protocol
                                break

                    if not valid_fw:
                        # Still save the raw data for debugging
                        self.add_log("error", "Unknown Device or Garbage Data")
                        logger.warning(f"Unknown Device or Garbage Data - Saving raw response for debugging")
                        logger.info(f"Raw Data (first 200 chars): {version_info[:200]}")
                        dump_content = f"--- BEATHA EXTRACTION (UNKNOWN DEVICE) ---\n\n"
                        dump_content += f"Serial Port: {self.serial_port}\n"
                        dump_content += f"Baud Rate: {self.baud_rate}\n\n"
                        dump_content += f"Raw Response from 'version' command:\n{version_info}\n\n"
                        dump_content += "This may indicate:\n"
                        dump_content += "- Wrong baud rate (try 57600, 115200, 230400)\n"
                        dump_content += "- Flight controller in wrong mode (DFU, MSC instead of VCP/Serial)\n"
                        dump_content += "- Unsupported firmware\n"
                        dump_content += "- Flight controller not fully booted (needs battery power)\n"

                        # Save this diagnostic dump
                        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                        dump_filename = f"dump_UNKNOWN_{timestamp}.txt"
                        dump_path = os.path.join(self.dump_dir, dump_filename)
                        with open(dump_path, "w") as f:
                            f.write(dump_content)
                        self.add_log("info", f"Diagnostic dump saved: {dump_filename}")
                        logger.info(f"Diagnostic dump saved: {dump_path}")

                        self.beep("error")
                        self.set_leds(COLOR_RED)
                        time.sleep(2)
                        with self.state_lock:
                            self.state = "IDLE"
                        self.stop_animation = False
                        return

                    self.add_log("info", f"Detected: {version_info[:50]}...")
                    logger.info(f"Detected Firmware Info: {version_info[:50]}...")

                    # Extract version for directory naming
                    fw_version = "unknown"
                    fw_type = "unknown"
                    for line in version_info.split('\n'):
                        if "Betaflight" in line:
                            fw_type = "betaflight"
                            parts = line.split()
                            for p in parts:
                                if p and p[0].isdigit():
                                    fw_version = p
                                    break
                        elif "INAV" in line:
                            fw_type = "inav"
                            parts = line.split()
                            for p in parts:
                                if p and p[0].isdigit():
                                    fw_version = p
                                    break
                        elif "ArduPilot" in line or "Copter" in line or "Plane" in line:
                            fw_type = "ardupilot"
                            parts = line.split()
                            for p in parts:
                                if p and p[0].isdigit():
                                    fw_version = p
                                    break

                    if is_ardupilot:
                        self.add_log("info", "ArduPilot detected - attempting MAVLink file transfer")
                        dump_content = f"--- BEATHA EXTRACTION (ARDUPILOT) ---\n\n{version_info}\n\n"
                        # Note: MAVLink connection must happen outside the serial context
                    elif is_betaflight:
                        # For Betaflight, we can use MSC mode for SD card access
                        # But for CLI dump, we use the standard dump all command
                        self.add_log("info", "Betaflight detected - using CLI dump")

                        # Check if user wants MSC mode (mass storage) for blackbox
                        # For now, we'll stick with CLI dump. MSC would be: echo -e "msc\n" > serial
                        # This would make the FC appear as a USB mass storage device for SD card access

                        # 2. Dump Configuration (Betaflight/INAV)
                        commands = [b'status\r\n', b'resource show all\r\n', b'dump all\r\n']

                        dump_content = f"--- BEATHA EXTRACTION HEADER ---\n{version_info}\n--- END HEADER ---\n\n"

                        # Step C: Read (LED 2 Orange)
                        self.set_single_led(1, COLOR_ORANGE)
                        self.add_log("info", "Reading configuration...")
                        logger.info("Reading Data...")

                        for cmd in commands:
                            cmd_str = cmd.decode().strip()
                            self.add_log("tx", cmd_str)
                            ser.write(cmd)
                            time.sleep(0.1)

                        # Heuristic Read
                        start_time = time.time()
                        last_data_time = start_time
                        silence_threshold = 2.0  # seconds of silence to consider done

                        while time.time() - start_time < 90: # Increased timeout for larger dumps
                            if ser.in_waiting:
                                line = ser.readline().decode('utf-8', errors='ignore')
                                dump_content += line
                                # Don't log every line to avoid flooding, just track progress
                                last_data_time = time.time()
                            else:
                                # Check if we have enough data and sufficient silence
                                if len(dump_content) > 100:
                                    silence_duration = time.time() - last_data_time
                                    if silence_duration >= silence_threshold:
                                        break
                                # Small delay to avoid busy waiting
                                time.sleep(0.1)

                        self.add_log("info", f"Received {len(dump_content)} bytes")
                    else:
                        # INAV or other
                        commands = [b'status\r\n', b'resource show all\r\n', b'dump all\r\n']

                        dump_content = f"--- BEATHA EXTRACTION HEADER ---\n{version_info}\n--- END HEADER ---\n\n"

                        # Step C: Read (LED 2 Orange)
                        self.set_single_led(1, COLOR_ORANGE)
                        self.add_log("info", "Reading configuration...")
                        logger.info("Reading Data...")

                        for cmd in commands:
                            cmd_str = cmd.decode().strip()
                            self.add_log("tx", cmd_str)
                            ser.write(cmd)
                            time.sleep(0.1)

                        # Heuristic Read
                        start_time = time.time()
                        last_data_time = start_time
                        silence_threshold = 2.0

                        while time.time() - start_time < 90:
                            if ser.in_waiting:
                                line = ser.readline().decode('utf-8', errors='ignore')
                                dump_content += line
                                last_data_time = time.time()
                            else:
                                if len(dump_content) > 100:
                                    silence_duration = time.time() - last_data_time
                                    if silence_duration >= silence_threshold:
                                        break
                                time.sleep(0.1)

                        self.add_log("info", f"Received {len(dump_content)} bytes")

                # MAVLink handling for ArduPilot (after serial context closes)
                if is_ardupilot and MAVLINK_AVAILABLE:
                    self.add_log("info", "Attempting MAVLink connection...")
                    try:
                        mav = mavutil.mavlink_connection(self.serial_port, baud=self.baud_rate)
                        mav.wait_heartbeat(timeout=5)
                        self.add_log("info", f"MAVLink heartbeat: system {mav.target_system}")

                        dump_content += f"\nMAVLink Connection Established\n"
                        dump_content += f"System ID: {mav.target_system}\n"
                        dump_content += f"Component ID: {mav.target_component}\n\n"

                        # Note: Full FTP file transfer requires implementing MAVLink FTP protocol
                        # For now, we just establish connection and note that log files exist
                        dump_content += "Note: MAVLink FTP file download not yet implemented.\n"
                        dump_content += "For log downloads, use Mission Planner or MAVProxy.\n"

                        mav.close()
                    except Exception as e:
                        self.add_log("error", f"MAVLink connection failed: {e}")
                        dump_content += f"\nMAVLink connection error: {e}\n"
                elif is_ardupilot and not MAVLINK_AVAILABLE:
                    dump_content += "\npymavlink not installed. Run: pip install pymavlink\n"
            else:
                time.sleep(2) # Mock Delay
                dump_content = "MOCK DUMP CONTENT"
                fw_type = "betaflight"
                fw_version = "4.4.0"
                is_betaflight = True
                self.add_log("info", "Mock dump completed")
                self.set_single_led(1, COLOR_ORANGE)

            # Step D: Save (LED 3 Yellow)
            self.set_single_led(2, COLOR_YELLOW)
            timestamp = time.strftime("%Y%m%d-%H%M%S")

            # Get board name for directory organization
            board_name = None
            if is_betaflight or (not is_ardupilot and fw_type in ['betaflight', 'inav']):
                # Try to get the craft name from CLI
                try:
                    board_name = self.get_board_name()
                except Exception as e:
                    self.add_log("error", f"Could not get board name: {e}")

            # Create organized directory structure
            # Format: <board_name>_<version> or <fw_type>_<version>
            if board_name:
                dir_name = f"{sanitize_dirname(board_name)}_{sanitize_dirname(fw_version)}"
            else:
                dir_name = f"{sanitize_dirname(fw_type)}_{sanitize_dirname(fw_version)}"

            dump_subdir = os.path.join(self.dump_dir, dir_name)
            os.makedirs(dump_subdir, exist_ok=True)

            filename = f"dump_{timestamp}.txt"
            filepath = os.path.join(dump_subdir, filename)

            with open(filepath, "w") as f:
                f.write(dump_content)
            self.add_log("info", f"Dump saved to: {dir_name}/{filename}")
            logger.info(f"Dump saved to {filepath}")

            # Step E: Cloud Sync (LED 4 Green/Red)
            storage_mode = SYS_CONF.get("storage_mode", "cloud_sync") # local_only, cloud_sync

            if storage_mode == "cloud_sync":
                try:
                    if not EMULATION_MODE:
                        subprocess.run(["rclone", "copy", filepath, "gdrive:BF_Dumps"], check=True, timeout=60)
                    logger.info("Cloud Upload Success")
                    self.set_single_led(3, COLOR_GREEN)
                    self.beep("victory")
                except Exception as e:
                    logger.error(f"Cloud Upload Failed: {e}")
                    self.set_single_led(3, COLOR_RED)
                    self.beep("error")
            else:
                # Local Only
                logger.info("Cloud sync skipped (Local Only Mode)")
                self.set_single_led(3, COLOR_GREEN)
                self.beep("victory")

            time.sleep(3) # Hold Status

        except Exception as e:
            logger.error(f"Dump Failed: {e}")
            self.set_leds(COLOR_RED)
            self.beep("error")
            time.sleep(3)

        with self.state_lock:
            self.state = "IDLE"
        self.stop_animation = False


# --- App Lifecycle ---
manager = BeathaManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    manager.start()
    yield
    # Shutdown
    manager.stop()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---

@app.get("/api/status")
def get_status():
    # Get latest dump info
    latest_dump = None
    dump_files = glob.glob(os.path.join(manager.dump_dir, "dump_*.txt"))
    if dump_files:
        dump_files.sort(key=os.path.getmtime, reverse=True)
        latest_file = dump_files[0]
        latest_dump = {
            "filename": os.path.basename(latest_file),
            "timestamp": os.path.getmtime(latest_file),
            "size": os.path.getsize(latest_file)
        }

    return {
        "mode": manager.state,
        "drone_connected": manager.drone_connected,
        "emulation": EMULATION_MODE,
        "wifi_ip": "192.168.4.1", # Placeholder, could fetch real IP
        "serial_port": manager.serial_port,
        "baud_rate": manager.baud_rate,
        "fc_info": manager.fc_info,
        "buttons": {
            "dump": not btn_dump.value,  # Active low
            "pair": not btn_pair.value   # Active low
        },
        "latest_dump": latest_dump
    }

@app.post("/api/action/{action_name}")
def trigger_action(action_name: str):
    if action_name == "dump":
        manager.trigger_dump()
        return {"status": "Dump requested"}
    elif action_name == "pair":
        manager.trigger_pair()
        return {"status": "Pairing requested"}
    else:
        raise HTTPException(status_code=400, detail="Unknown action")

@app.get("/api/config")
def get_config():
    return config["hardware"]

@app.get("/api/dumps")
def list_dumps():
    """List all dump files in the dump directory (including subdirectories)"""
    # Search in root dump dir and one level of subdirectories
    files = glob.glob(os.path.join(manager.dump_dir, "dump_*.txt"))
    files += glob.glob(os.path.join(manager.dump_dir, "*", "dump_*.txt"))

    # Sort by modification time, newest first
    files.sort(key=os.path.getmtime, reverse=True)

    # Return with relative paths from dump_dir
    result = []
    for f in files:
        rel_path = os.path.relpath(f, manager.dump_dir)
        result.append({
            "path": rel_path,
            "filename": os.path.basename(f),
            "dir": os.path.dirname(rel_path) if os.path.dirname(rel_path) else None,
            "timestamp": os.path.getmtime(f),
            "size": os.path.getsize(f)
        })

    return {"files": result}

@app.get("/api/dumps/{filepath:path}")
def get_dump(filepath: str):
    """Get contents of a specific dump file (supports subdirectories)"""
    # Sanitize filepath to prevent directory traversal
    if ".." in filepath:
        raise HTTPException(status_code=400, detail="Invalid filepath")

    full_path = os.path.join(manager.dump_dir, filepath)

    # Ensure the path is still within dump_dir
    if not os.path.realpath(full_path).startswith(os.path.realpath(manager.dump_dir)):
        raise HTTPException(status_code=400, detail="Invalid filepath")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    with open(full_path, "r") as f:
        content = f.read()

    # Extract version info from dump
    version_line = ""
    for line in content.split("\n")[:20]:
        if "Betaflight" in line or "INAV" in line or "EmuFlight" in line or "ArduPilot" in line:
            version_line = line.strip()
            break

    return {
        "filepath": filepath,
        "filename": os.path.basename(filepath),
        "dir": os.path.dirname(filepath) if os.path.dirname(filepath) else None,
        "content": content,
        "version": version_line,
        "size": len(content)
    }

@app.post("/api/config")
def update_config(new_config: dict):
    # (Simplified for brevity - logic same as before)
    return {"status": "Not implemented in this refactor yet"}

@app.get("/api/serial/ports")
def list_serial_ports():
    """List all available serial ports with details"""
    ports = serial.tools.list_ports.comports()
    result = []
    for port in ports:
        score = 0
        # Score calculation for flight controllers
        KNOWN_FC_VIDPID = [
            (0x0483, 0x5740), (0x0483, 0xdf11), (0x10c4, 0xea60),
            (0x0403, 0x6001), (0x0403, 0x6015), (0x2341, 0x0001),
            (0x2341, 0x0043), (0x16c0, 0x0483),
        ]
        if port.vid and port.pid and (port.vid, port.pid) in KNOWN_FC_VIDPID:
            score += 10
        if 'ACM' in port.device:
            score += 5
        elif 'USB' in port.device:
            score += 3
        desc_lower = (port.description or "").lower()
        if any(kw in desc_lower for kw in ['stm32', 'betaflight', 'inav', 'flight', 'cp210']):
            score += 5

        result.append({
            "device": port.device,
            "description": port.description or "Unknown",
            "manufacturer": port.manufacturer or "Unknown",
            "vid": f"{port.vid:04x}" if port.vid else None,
            "pid": f"{port.pid:04x}" if port.pid else None,
            "score": score,
            "is_current": port.device == manager.serial_port
        })

    # Sort by score (highest first)
    result.sort(key=lambda x: x["score"], reverse=True)
    return {"ports": result, "current": manager.serial_port}

@app.post("/api/serial/connect")
def connect_serial(data: dict):
    """Connect to a specific serial port"""
    port = data.get("port")
    baud = data.get("baud_rate", 115200)

    if not port:
        raise HTTPException(status_code=400, detail="Port is required")

    # Check if port exists
    available_ports = [p.device for p in serial.tools.list_ports.comports()]
    if port not in available_ports:
        raise HTTPException(status_code=404, detail=f"Port {port} not found")

    # Stop existing connections
    manager.stop_socat()
    manager.stop_bt_proxy()

    # Update manager
    manager.serial_port = port
    manager.baud_rate = baud
    manager.drone_connected = True
    manager.fc_info = None  # Reset FC info

    # Try to detect FC type
    try:
        fc_info = manager.detect_fc_type()
        logger.info(f"Connected to {port}: {fc_info}")
        return {"status": "connected", "port": port, "baud_rate": baud, "fc_info": fc_info}
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return {"status": "connected", "port": port, "baud_rate": baud, "fc_info": None, "warning": str(e)}

@app.post("/api/serial/disconnect")
def disconnect_serial():
    """Disconnect from current serial port"""
    manager.stop_socat()
    manager.stop_bt_proxy()
    manager.drone_connected = False
    manager.fc_info = None
    logger.info("Serial disconnected by user")
    return {"status": "disconnected"}

@app.get("/api/fc/info")
def get_fc_info():
    """Get flight controller info (type, version)"""
    if not manager.drone_connected or not manager.serial_port:
        return {"connected": False, "fc_info": None}

    fc_info = getattr(manager, 'fc_info', None)
    if not fc_info:
        try:
            fc_info = manager.detect_fc_type()
        except Exception as e:
            return {"connected": True, "fc_info": None, "error": str(e)}

    return {"connected": True, "fc_info": fc_info}

@app.get("/api/logs")
def get_logs():
    """Get recent FC communication logs"""
    return {"logs": list(manager.fc_logs)}

@app.post("/api/fc/msc")
def enter_msc_mode():
    """Put Betaflight FC into MSC (Mass Storage Class) mode.

    This makes the FC appear as a USB drive for direct SD card access.
    After MSC mode, the FC will need to be physically reconnected to return
    to normal serial mode.
    """
    if not manager.drone_connected or not manager.serial_port:
        raise HTTPException(status_code=400, detail="No FC connected")

    fc_info = manager.fc_info
    if fc_info and fc_info.get("type") not in ["Betaflight", "INAV"]:
        raise HTTPException(status_code=400, detail="MSC mode only supported on Betaflight/INAV")

    # Stop proxies before MSC
    manager.stop_socat()
    manager.stop_bt_proxy()

    success = manager.enter_msc_mode()
    if success:
        manager.drone_connected = False  # FC will disconnect when entering MSC
        return {
            "status": "msc_mode_entered",
            "message": "FC is now in USB Mass Storage mode. Connect USB to access SD card. Replug FC to exit MSC mode."
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to enter MSC mode")

@app.post("/api/fc/msc/download")
def download_blackbox_from_msc(data: dict = None):
    """Download blackbox files from an FC in MSC mode.

    Optional body: {"mount_path": "/path/to/mounted/sd"}
    """
    mount_path = data.get("mount_path") if data else None
    files = manager.download_blackbox_msc(mount_path)

    if files:
        return {
            "status": "success",
            "files_downloaded": len(files),
            "files": [os.path.basename(f) for f in files]
        }
    else:
        return {
            "status": "no_files",
            "message": "No blackbox files found. Ensure FC SD card is mounted."
        }

# --- Tests ---
@app.post("/api/test/hardware/{component}")
def test_hardware(component: str, action: str = "on"):
    if component == "buzzer":
        manager.beep("success")
    elif component == "led":
        if action == "red": manager.set_leds(COLOR_RED)
        elif action == "green": manager.set_leds(COLOR_GREEN)
        else: manager.set_leds(COLOR_OFF)
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
