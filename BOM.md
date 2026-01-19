# Bill of Materials (BOM)

This project is designed to be built with "Scavenged Parts" or easily accessible components.

## Core Components

| Component | Quantity | Description | Estimated Cost |
| :--- | :---: | :--- | :---: |
| **Raspberry Pi Zero W** | 1 | v1.1 or newer. (Pi Zero 2 W also works but is overkill). | ~$15 |
| **Micro SD Card** | 1 | 8GB or larger. High endurance recommended. | ~$5 |
| **Micro USB Cable (Data)** | 1 | To be sacrificed/cut. Must have data lines! | ~$2 |
| **Power Bank** | 1 | 5V 2A+ output to power the Pi. | - |

## Interface "Hat" Components

| Component | Quantity | Description | Notes |
| :--- | :---: | :--- | :---: |
| **Prototyping Board** | 1 | 20x80mm or similar perfboard. | |
| **Tactile Buttons** | 2 | Momentary push buttons (6x6mm). | 1 for Dump, 1 for Pair. |
| **WS2812B LED Strip** | 1 | Strip of 4 LEDs. | "NeoPixels" |
| **Active Buzzer** | 1 | 5V Active Buzzer. | Optional but recommended. |
| **Wires** | - | 28AWG or 30AWG silicone wire. | |
| **Header Pins** | 1 | 2x20 Male Header (if Pi doesn't have headers). | |

## 3D Printed Parts

The case is designed to be compact and rugged. STL files are located in `assets/3dmodels/`.

*   **`beatha_bottom.stl`**: Main body holding the Pi and wiring.
*   **`beatha_lid.stl`**: Top cover with cutouts for LEDs and Buttons.

## Tools Required

*   Soldering Iron & Solder
*   Wire Strippers / Cutters
*   Hot Glue Gun (for strain relief)
*   3D Printer (or use a printing service)