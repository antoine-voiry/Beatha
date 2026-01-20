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
import pyudev
from datetime import datetime
from contextlib import asynccontextmanager
from src.backend.config_loader import config

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
try:
    import board
    import neopixel
    from digitalio import DigitalInOut, Direction, Pull
    EMULATION_MODE = False
    logger.info("✅ GPIO Libraries Loaded (Live Mode)")
except ImportError:
    if config["features"]["emulation_mode_fallback"]:
        EMULATION_MODE = True
        logger.warning("⚠️  Hardware Not Found: Running in Emulation Mode")
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
        self.serial_port = SYS_CONF["serial_port"] # e.g., /dev/ttyACM0
        self.baud_rate = SYS_CONF.get("baud_rate", 115200)

        # Ensure dump dir
        self.dump_dir = SYS_CONF["dump_dir"]
        if EMULATION_MODE:
            self.dump_dir = "./dumps_mock"
        else:
            # Expand ~ to user home directory
            self.dump_dir = os.path.expanduser(self.dump_dir)
        os.makedirs(self.dump_dir, exist_ok=True)

    def start(self):
        """Start background threads"""
        self.running = True
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

            # Initial Check
            self.drone_connected = os.path.exists(self.serial_port)
            logger.info(f"USB Initial Check: {self.drone_connected}")

            for device in monitor:
                if not self.running: break
                if device.device_node == self.serial_port:
                    if device.action == 'add':
                        logger.info("🔌 Drone Connected")
                        self.drone_connected = True
                        self.beep("short")
                    elif device.action == 'remove':
                        logger.info("❌ Drone Disconnected")
                        self.drone_connected = False
                        self.stop_socat() # Safety cleanup
                        self.stop_bt_proxy()
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
        
        # LED Sequence as per State Machine
        pixels.fill(COLOR_OFF); pixels.show()
        
        try:
            # Step B: Connect (LED 1 Orange)
            self.set_single_led(0, COLOR_ORANGE)
            logger.info("Opening Serial for Dump...")
            
            dump_content = ""
            is_ardupilot = False

            if not EMULATION_MODE:
                with serial.Serial(self.serial_port, self.baud_rate, timeout=2) as ser:
                    # 1. Wake up & Get Version
                    ser.write(b'#\r\n')
                    time.sleep(0.1)
                    ser.reset_input_buffer()
                    ser.write(b'version\r\n')

                    version_info = ""
                    start_time = time.time()
                    valid_fw = False
                    while time.time() - start_time < 3: # Short timeout for version
                        if ser.in_waiting:
                            try:
                                line = ser.readline().decode('utf-8', errors='ignore')
                                # Check for ArduPilot / MAVLink garbage (often shows as non-printable)
                                if "ArduPilot" in line or "ChibiOS" in line:
                                    is_ardupilot = True
                                    version_info += line
                                    valid_fw = True
                                    break

                                version_info += line
                                if "Betaflight" in line or "INAV" in line or "Emuflight" in line:
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
                        logger.info(f"Diagnostic dump saved: {dump_path}")

                        self.beep("error")
                        self.set_leds(COLOR_RED)
                        time.sleep(2)
                        with self.state_lock:
                            self.state = "IDLE"
                        self.stop_animation = False
                        return

                    logger.info(f"Detected Firmware Info: {version_info[:50]}...")

                    if is_ardupilot:
                         dump_content = f"--- BEATHA EXTRACTION (ARDUPILOT DETECTED) ---\n\n{version_info}\n\n⚠️ NOTE: Full parameter dump for ArduPilot requires MAVLink protocol which is not yet supported in this version.\n"
                    else:
                        # 2. Dump Configuration (Betaflight/INAV)
                        # Added 'status' and 'resource show all' for motor info
                        commands = [b'status\r\n', b'resource show all\r\n', b'dump all\r\n']

                        dump_content = f"--- BEATHA EXTRACTION HEADER ---\n{version_info}\n--- END HEADER ---\n\n"

                        # Step C: Read (LED 2 Orange)
                        self.set_single_led(1, COLOR_ORANGE)
                        logger.info("Reading Data...")

                        for cmd in commands:
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
                                last_data_time = time.time()
                            else:
                                # Check if we have enough data and sufficient silence
                                if len(dump_content) > 100:
                                    silence_duration = time.time() - last_data_time
                                    if silence_duration >= silence_threshold:
                                        break
                                # Small delay to avoid busy waiting
                                time.sleep(0.1)
            else:
                time.sleep(2) # Mock Delay
                dump_content = "MOCK DUMP CONTENT"
                self.set_single_led(1, COLOR_ORANGE)

            # Step D: Save (LED 3 Yellow)
            self.set_single_led(2, COLOR_YELLOW)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"dump_{timestamp}.txt"
            filepath = os.path.join(self.dump_dir, filename)
            
            with open(filepath, "w") as f:
                f.write(dump_content)
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
    """List all dump files in the dump directory"""
    files = glob.glob(os.path.join(manager.dump_dir, "dump_*.txt"))
    # Return just filenames, sorted by newest
    files.sort(key=os.path.getmtime, reverse=True)
    return {"files": [os.path.basename(f) for f in files]}

@app.get("/api/dumps/{filename}")
def get_dump(filename: str):
    """Get contents of a specific dump file"""
    # Sanitize filename to prevent directory traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = os.path.join(manager.dump_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    with open(filepath, "r") as f:
        content = f.read()

    # Extract version info from dump
    version_line = ""
    for line in content.split("\n")[:20]:
        if "Betaflight" in line or "INAV" in line or "EmuFlight" in line or "ArduPilot" in line:
            version_line = line.strip()
            break

    return {
        "filename": filename,
        "content": content,
        "version": version_line,
        "size": len(content)
    }

@app.post("/api/config")
def update_config(new_config: dict):
    # (Simplified for brevity - logic same as before)
    return {"status": "Not implemented in this refactor yet"}

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
