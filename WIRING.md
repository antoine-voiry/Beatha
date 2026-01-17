# Wiring Guide - Project Beatha

This guide details the physical connections required for Project Beatha.

## ⚠️ Power Warning (The "PC vs Pi" Difference)
**Why can't I just plug it in like my PC?**
Your PC has expensive protection circuits that prevent external voltage from damaging it. **The Raspberry Pi Zero W does NOT.** Its USB port is connected directly to its power rail.
*   **Result:** If you plug a LiPo into the drone, voltage can flow backwards into the Pi and destroy it.
*   **Rule:** **NEVER** plug a battery into the Drone while it is connected to the Pi (unless you installed the optional diode).

---

## Part 1: Drone Connection (Direct Soldered)

This method connects the USB lines directly to the "Test Pads" (PP) on the **BACK** of the Raspberry Pi Zero W.

### 🖼️ Reference Images & Pinouts
For the most accurate visual reference, please verify pads against these resources:
*   **Official Raspberry Pi Zero W Schematics:** [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
*   **Interactive Pinout:** [Pinout.xyz](https://pinout.xyz/) (Note: Use this for the GPIO header).

### Wiring Instructions
1.  Cut a standard USB data cable.
2.  Strip the 4 wires (Red, White, Green, Black).
3.  Solder them to the corresponding Test Pads on the back of the Pi Zero W.

| USB Wire Color | Signal | Pi Connection Point | Note |
| :--- | :--- | :--- | :--- |
| **Red** | 5V | **PP1** (or 5V Pin) | Powers the Drone from the Pi. |
| **White** | Data - | **PP22** | Solder directly to pad. |
| **Green** | Data + | **PP23** | Solder directly to pad. |
| **Black** | GND | **PP6** (or GND Pin) | Common Ground. |

*(Note: PP numbers are printed in small white text on the back of the PCB).*

---

## Part 2: User Interface (GPIO Hat)

These connections are made to the **GPIO Header** on the **FRONT** of the Pi.

### 🗺️ GPIO Pinout Reference
We strongly recommend using **[pinout.xyz](https://pinout.xyz/)** to identify the pins.

### Wiring Table (Using Prototyping Board)

| Component | Pin Name | Connect To (Physical Pin) |
| :--- | :--- | :--- |
| **LED Stick** | DIN | **Pin 12** (GPIO 18) |
| | 5V | **Pin 2 or 4** |
| | GND | **Pin 6, 9, 14...** |
| **Dump Button** | Signal | **Pin 16** (GPIO 23) |
| | GND | **Pin 6, 9, 14...** |
| **Pair Button** | Signal | **Pin 18** (GPIO 24) |
| | GND | **Pin 6, 9, 14...** |
| **Buzzer** | + | **Pin 22** (GPIO 25) |
| | - | **Pin 6, 9, 14...** |

---

## Optional: Safety Diode (For LiPo Usage)
If you plan to plug a LiPo battery into the drone while the Pi is connected:
1.  **Cut** the RED wire in your USB cable.
2.  Solder a **Schottky Diode** (1N5817) in line.
    *   **Striped Side (Cathode)** -> Towards Drone.
    *   **Black Side (Anode)** -> Towards Pi (PP1).

## Alternative: USB OTG
*For testing only:* You can use a Micro-USB OTG adapter in the **Data Port** instead of soldering to the PP pads. This is bulkier but requires zero soldering on the USB lines.