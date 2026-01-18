import json
import os
import sys

CONFIG_PATH = "config.json"

def load_config():
    """Load configuration from JSON file."""
    if not os.path.exists(CONFIG_PATH):
        # print(f"⚠️ Config file not found at {CONFIG_PATH}. Using defaults.") 
        return {
            "hardware": {"led_pin": 18, "button_dump_pin": 23, "button_pair_pin": 24, "buzzer_pin": 25, "led_count": 4, "led_brightness": 0.2},
            "system": {"dump_dir": "/home/pi/dumps", "serial_port": "/dev/ttyACM0"},
            "features": {"emulation_mode_fallback": True}
        }
    
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

config = load_config()
