# Bill of Materials (BOM) - Project Beatha

![Visual Reference: Core components (Schottky Diode not pictured)](assets/scavenge_parts.jpg)
*Visual Reference: Core components. (Note: The required Schottky Diode for LiPo safety is not pictured).*

This document lists all hardware components required to build the Project Beatha field recovery tool.

## Core Components

| Component | Quantity | Description | Notes |
| :--- | :--- | :--- | :--- |
| **Raspberry Pi Zero W v1.1** | 1 | Single-board computer | Minimum Requirement. |
| **Micro SD Card** | 1 | Storage for OS and Dumps | 16GB or larger recommended. Class 10. |
| **5V Power Supply** | 1 | Power Source | High quality 5V USB power supply (2A+ recommended) to power Pi and Drone. |

## Interface & Peripherals

| Component | Quantity | Description | Notes |
| :--- | :--- | :--- | :--- |
| **Prototyping Board** | 1 | 20x80mm Perfboard or Pi Zero Hat | To mount buttons, LEDs, and headers (Avoids direct soldering to Pi). |
| **WS2812B LED Strip** | 1 strip | Visual Status Indicator | A small strip or stick of 4 individual LEDs (NeoPixels). |
| **Momentary Push Button** | 2 | Trigger Switches | One for Dump, One for BT Pairing. |
| **Active Buzzer** | 1 | 5V Active Buzzer | **(Optional)** For audible status beeps. |
| **Connecting Wires** | Varies | Jumpers / Silicone Wire | For connecting GPIO to peripherals. |

## Cables & Connectivity

| Component | Quantity | Description | Notes |
| :--- | :--- | :--- | :--- |
| **USB Data Cable** | 1 | USB-A to USB-C/Micro (Drone dependent) | To be cut and soldered to Pi PP pads. |
| **Micro-USB Cable** | 1 | Power Cable | For connecting Power Supply to Pi PWR port. |
| **USB OTG Adapter** | 1 | Micro-USB to USB-A | **(Optional)** For testing without soldering. |

## Protection (Optional Safety Upgrade)

| Component | Quantity | Description | Notes |
| :--- | :--- | :--- | :--- |
| **Schottky Diode** | 1 | **1N5817**, **1N5819**, or **SR1100** | **Optional.** Prevents back-feeding if LiPo is connected. |

## Shopping Helper (Reference Links)
*Note: These links point to Amazon.com (US) for visual reference. Please search for these exact terms on your local electronics supplier or Amazon store (e.g., Amazon.co.uk, Amazon.de, AliExpress).*

*   **Controller:** [Raspberry Pi Zero W](https://www.amazon.com/s?k=Raspberry+Pi+Zero+W)
*   **Protection:** [1N5817 / 1N5819 Schottky Diode](https://www.amazon.com/s?k=1N5817+1N5819+Schottky+Diode)
*   **LEDs:** [WS2812B 4-Bit Stick or Strip](https://www.amazon.com/s?k=WS2812B+led+stick+4+bit)
*   **Audio:** [Active Buzzer 5V](https://www.amazon.com/s?k=5v+active+buzzer+pcb+module)
*   **Mounting:** [Double Sided PCB Prototype Board](https://www.amazon.com/s?k=double+sided+pcb+prototype+board+2x8cm)
*   **Connectivity:** [Micro USB OTG Cable](https://www.amazon.com/s?k=Micro+USB+OTG+Cable)
*   **Wiring:** [Silicone Wire 30AWG](https://www.amazon.com/s?k=30AWG+Silicone+Wire)

## Optional / Recommended

| Component | Quantity | Description | Notes |
| :--- | :--- | :--- | :--- |
| **Enclosure** | 1 | 3D Printed Case | To protect the electronics in the field. |
| **Heat Shrink** | - | Insulation | For insulating the cut wire in the USB cable and soldered joints. |
