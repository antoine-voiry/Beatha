import time
import os
import sys
import subprocess
import threading
import signal
import serial
import board
import neopixel
from digitalio import DigitalInOut, Direction, Pull

# Configuration
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200
SOCAT_PORT = 5000
DUMP_DIR = "/home/pi/dumps"
RCLONE_REMOTE = "gdrive:BF_Dumps"

# GPIO Configuration
LED_PIN = board.D18
NUM_LEDS = 4
BUTTON_PIN = board.D23
PAIR_BUTTON_PIN = board.D24

# LED Colors (GRB format for some strips, RGB for others - adjust if needed)
COLOR_OFF = (0, 0, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_ORANGE = (255, 100, 0) # Approximation
COLOR_YELLOW = (255, 255, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (255, 0, 0)
COLOR_PURPLE = (180, 0, 255)

# Initialize LEDs
pixels = neopixel.NeoPixel(LED_PIN, NUM_LEDS, brightness=0.2, auto_write=False)

# Initialize Buttons
btn = DigitalInOut(BUTTON_PIN)
btn.direction = Direction.INPUT
btn.pull = Pull.UP

btn_pair = DigitalInOut(PAIR_BUTTON_PIN)
btn_pair.direction = Direction.INPUT
btn_pair.pull = Pull.UP

class StateMachine:
    def __init__(self):
        self.state = "IDLE"
        self.socat_process = None
        self.running = True
        self.animation_thread = None
        self.stop_animation = False
        
        # Ensure dump directory exists
        if not os.path.exists(DUMP_DIR):
            os.makedirs(DUMP_DIR)

    def start_animation(self):
        self.stop_animation = False
        self.animation_thread = threading.Thread(target=self._animate_leds)
        self.animation_thread.start()

    def stop_animation_thread(self):
        self.stop_animation = True
        if self.animation_thread and self.animation_thread.is_alive():
            self.animation_thread.join()

    def _animate_leds(self):
        """Handle 'Breathing' animation for Idle state."""
        brightness = 0.0
        delta = 0.05
        while not self.stop_animation:
            if self.state == "IDLE":
                # Breathing Blue on all LEDs
                brightness += delta
                if brightness >= 0.8:
                    brightness = 0.8
                    delta = -0.05
                elif brightness <= 0.1:
                    brightness = 0.1
                    delta = 0.05
                
                # Apply brightness to blue
                b_val = int(255 * brightness)
                pixels.fill((0, 0, b_val))
                pixels.show()
                time.sleep(0.05)
            else:
                # If not idle, stop this specific animation loop
                break

    def set_leds(self, colors):
        """Set specific colors for the 4 LEDs."""
        self.stop_animation_thread()
        for i in range(min(len(colors), NUM_LEDS)):
            pixels[i] = colors[i]
        pixels.show()

    def start_socat(self):
        """Start the socat TCP proxy."""
        if self.socat_process is None:
            # Check if serial port exists first to avoid spamming errors
            if os.path.exists(SERIAL_PORT):
                try:
                    cmd = [
                        "socat",
                        f"TCP-LISTEN:{SOCAT_PORT},fork,reuseaddr",
                        f"FILE:{SERIAL_PORT},b{BAUD_RATE},raw,echo=0"
                    ]
                    # Start in background
                    self.socat_process = subprocess.Popen(cmd)
                    print(f"Started socat on port {SOCAT_PORT}")
                except Exception as e:
                    print(f"Failed to start socat: {e}")
            else:
                # Device not connected yet, that's fine.
                pass

    def stop_socat(self):
        """Stop the socat process."""
        if self.socat_process:
            print("Stopping socat...")
            self.socat_process.terminate()
            try:
                self.socat_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.socat_process.kill()
            self.socat_process = None
            
    def perform_pairing(self):
        print("Starting Pairing Mode")
        self.state = "PAIRING"
        self.stop_animation_thread()
        self.stop_socat() # Temporarily stop socat
        
        try:
            # Enable discovery and pairability
            subprocess.run(["bluetoothctl", "power", "on"], check=False)
            subprocess.run(["bluetoothctl", "discoverable", "on"], check=False)
            subprocess.run(["bluetoothctl", "pairable", "on"], check=False)
            subprocess.run(["bluetoothctl", "agent", "NoInputNoOutput"], check=False)
            subprocess.run(["bluetoothctl", "default-agent"], check=False)
            
            print("Bluetooth discoverable for 30 seconds...")
            
            # Fast Blue Blink for 30s
            for _ in range(60): # 60 * 0.5s = 30s
                pixels.fill(COLOR_PURPLE) # Purple for Pairing
                pixels.show()
                time.sleep(0.25)
                pixels.fill(COLOR_OFF)
                pixels.show()
                time.sleep(0.25)
                
                # Allow exit if pairing button pressed again? (Optional, kept simple for now)

            # Reset BT state (optional, or leave on)
            # subprocess.run(["bluetoothctl", "discoverable", "off"], check=False)

        except Exception as e:
            print(f"Pairing setup failed: {e}")
            pixels.fill(COLOR_RED)
            pixels.show()
            time.sleep(2)

        # Return to Idle
        self.state = "IDLE"
        self.start_animation()

    def perform_extraction(self):
        print("Starting Extraction Mode")
        self.state = "EXTRACTION"
        self.stop_animation_thread()
        
        # Step A: Stop socat
        self.stop_socat()
        
        # Reset LEDs
        pixels.fill(COLOR_OFF)
        pixels.show()

        # Step B: Connect (LED 1 Orange)
        pixels[0] = COLOR_ORANGE
        pixels.show()
        
        ser = None
        dump_content = ""
        
        try:
            # Wait a moment for port to be free
            time.sleep(1)
            
            if not os.path.exists(SERIAL_PORT):
                raise Exception("Flight controller not connected")

            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
            
            # Send wake up / command
            ser.write(b'#\r\n')
            time.sleep(0.1)
            ser.reset_input_buffer()
            ser.write(b'dump all\r\n')
            
            # Step C: Read (LED 2 Orange)
            pixels[1] = COLOR_ORANGE
            pixels.show()
            
            # Heuristic reading
            start_time = time.time()
            while True:
                if time.time() - start_time > 60: # 60s timeout
                    raise Exception("Timeout reading dump")
                
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8', errors='ignore')
                    dump_content += line
                    # Check for end of dump heuristics often used in CLI
                    # Usually ends with '# ' or implies completion
                    if "# name" in line or "# master" in line: 
                        # This usually appears at the end of a dump or diff
                        pass 
                    
                    # A robust way to detect idle after dump is a short timeout 
                    # but simple string matching is faster if known.
                    # Betaflight 'dump all' usually ends with the prompt or statistics.
                    # Let's rely on a read timeout if we stop getting data, 
                    # but we are in a loop.
                    
                else:
                    # No data waiting
                    # If we have substantial content, assume done? 
                    # Better: Readline handles timeout. If we get empty strings after having content.
                    if len(dump_content) > 100:
                        break
                    
            ser.close()
            ser = None

            # Step D: Save to file (LED 3 Yellow)
            pixels[2] = COLOR_YELLOW
            pixels.show()
            
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"dump_{timestamp}.txt"
            filepath = os.path.join(DUMP_DIR, filename)
            
            with open(filepath, "w") as f:
                f.write(dump_content)
            
            print(f"Saved dump to {filepath}")

            # Step E: Cloud Sync (rclone)
            # We initiate it, success depends on result
            try:
                subprocess.run(
                    ["rclone", "copy", filepath, RCLONE_REMOTE],
                    check=True,
                    timeout=60
                )
                # Success: LED 4 Green
                pixels[3] = COLOR_GREEN
                pixels.show()
            except Exception as e:
                print(f"Cloud sync failed: {e}")
                # Fail: LED 4 Red
                pixels[3] = COLOR_RED
                pixels.show()

        except Exception as e:
            print(f"Extraction failed: {e}")
            # Indicate general failure on LED 4 if not reached
            pixels[3] = COLOR_RED
            pixels.show()
            if ser:
                ser.close()

        # Step F: Hold status for 3 seconds
        time.sleep(3)
        
        # Return to Idle
        self.state = "IDLE"
        self.start_animation()
        # Check socat restart in main loop

    def run(self):
        print("Project Beatha Initialized.")
        self.start_animation()

        while self.running:
            try:
                # Debounce button logic (Dump)
                if not btn.value: # Active Low
                    # Wait to confirm press
                    time.sleep(0.05)
                    if not btn.value:
                        self.perform_extraction()
                        while not btn.value: time.sleep(0.1)

                # Debounce button logic (Pairing)
                if not btn_pair.value: # Active Low
                     time.sleep(0.05)
                     if not btn_pair.value:
                         self.perform_pairing()
                         while not btn_pair.value: time.sleep(0.1)

                
                # Maintain Socat in Idle
                if self.state == "IDLE":
                    if self.socat_process is None or self.socat_process.poll() is not None:
                        # Process not running, try to start
                        self.start_socat()

                time.sleep(0.1)

            except KeyboardInterrupt:
                self.running = False
                self.stop_socat()
                self.stop_animation_thread()
                pixels.fill(COLOR_OFF)
                pixels.show()
                print("\nShutting down.")

if __name__ == "__main__":
    app = StateMachine()
    app.run()
