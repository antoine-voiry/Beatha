from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import os
import glob
import time
import threading
import logging
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
    
    class Direction: INPUT = 0
    class Pull: UP = 0
    
    class MockNeoPixel:
        def __init__(self, pin, n, brightness=0.2, auto_write=False):
            self.n = n
        def fill(self, color): pass
        def show(self): pass
        def __setitem__(self, key, value): pass

    class neopixel:
        NeoPixel = MockNeoPixel
    
    # Mock Board
    class Board:
        def __getattr__(self, name):
            if name.startswith("D"):
                return int(name[1:])
            raise AttributeError(f"Board has no attribute {name}")
    board = Board()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration Application
HW_CONF = config["hardware"]
SYS_CONF = config["system"]

DUMP_DIR = SYS_CONF["dump_dir"]
if EMULATION_MODE:
    DUMP_DIR = "./dumps_mock"
    os.makedirs(DUMP_DIR, exist_ok=True)

# Hardware Init
LED_PIN = getattr(board, f"D{HW_CONF['led_pin']}")
BTN_DUMP_PIN = getattr(board, f"D{HW_CONF['button_dump_pin']}")
BTN_PAIR_PIN = getattr(board, f"D{HW_CONF['button_pair_pin']}")
BUZZER_PIN = getattr(board, f"D{HW_CONF['buzzer_pin']}")

# Initialize Peripherals (Global Access)
pixels = neopixel.NeoPixel(LED_PIN, HW_CONF["led_count"], brightness=HW_CONF["led_brightness"], auto_write=False)
btn_dump = DigitalInOut(BTN_DUMP_PIN)
btn_dump.direction = Direction.INPUT
btn_dump.pull = Pull.UP

btn_pair = DigitalInOut(BTN_PAIR_PIN)
btn_pair.direction = Direction.INPUT
btn_pair.pull = Pull.UP

buzzer = DigitalInOut(BUZZER_PIN)
buzzer.direction = Direction.OUTPUT # Buzzer is Output
buzzer.value = False

@app.get("/api/config")
def get_config():
    """Return hardware configuration"""
    return config["hardware"]

@app.get("/api/status")
def get_status():
    """Check if Drone is Connected and System Status"""
    drone_connected = os.path.exists(SYS_CONF["serial_port"])
    return {
        "drone_connected": drone_connected,
        "mode": "IDLE", # TODO: Hook into FSM
        "wifi_ip": "192.168.4.1", # Default AP IP
        "emulation": EMULATION_MODE,
        "buttons": {
            "dump": not btn_dump.value if not EMULATION_MODE else False, # Active Low
            "pair": not btn_pair.value if not EMULATION_MODE else False
        }
    }

@app.post("/api/config")
def update_config(new_config: dict):
    """Update Hardware Configuration and Restart"""
    import json
    try:
        # Reload current config from disk to be safe
        with open("config.json", "r") as f:
            current_conf = json.load(f)
        
        # Update hardware section if provided, otherwise assume full hardware config
        # The frontend sends the content of 'hardware' key.
        if "led_pin" in new_config: 
             current_conf["hardware"].update(new_config)
        elif "hardware" in new_config:
             current_conf["hardware"] = new_config["hardware"]
        else:
             # Fallback: assume the whole dict is the hardware config if it fits the schema
             current_conf["hardware"].update(new_config)
        
        with open("config.json", "w") as f:
            json.dump(current_conf, f, indent=2)
            
        # Trigger Restart
        def restart_server():
            time.sleep(1)
            logger.info("♻️ Restarting Backend...")
            os.kill(os.getpid(), signal.SIGTERM)
            
        threading.Thread(target=restart_server).start()
        
        return {"status": "Configuration saved. Restarting..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test/hardware/{component}")
def test_hardware(component: str, action: str = "on"):
    """Test Hardware Components (LED, Buzzer)"""
    if component == "buzzer":
        if action == "on":
            # ESC Startup Melody Simulation (Rhythmic)
            # 3 short beeps, pause, 2 long beeps
            
            # Beep 1
            buzzer.value = True
            time.sleep(0.08)
            buzzer.value = False
            time.sleep(0.08)
            
            # Beep 2
            buzzer.value = True
            time.sleep(0.08)
            buzzer.value = False
            time.sleep(0.08)
            
            # Beep 3
            buzzer.value = True
            time.sleep(0.08)
            buzzer.value = False
            time.sleep(0.3) # Pause
            
            # Long Beep 1 (Low)
            buzzer.value = True
            time.sleep(0.25)
            buzzer.value = False
            time.sleep(0.1)

            # Long Beep 2 (High)
            buzzer.value = True
            time.sleep(0.25)
            buzzer.value = False
            
            return {"status": "Played ESC Startup Melody"}
    elif component == "led":
        if action == "red":
            pixels.fill((255, 0, 0))
        elif action == "green":
            pixels.fill((0, 255, 0))
        else:
            pixels.fill((0, 0, 0)) # Off
        pixels.show()
        return {"status": f"LED set to {action}"}
    
    return {"error": "Invalid component"}

@app.get("/api/logs")
def get_logs():
    """Get recent system logs"""
    return {"logs": ["System started", "Waiting for drone..."]}

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Uvicorn Server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
