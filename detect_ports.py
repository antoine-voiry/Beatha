#!/usr/bin/env python3
"""
Smart serial port detection similar to Betaflight Configurator
"""
import serial.tools.list_ports

def detect_flight_controller_ports():
    """
    Detect flight controller serial ports using the same logic as Betaflight Configurator.

    Betaflight Configurator looks for:
    - USB CDC ACM devices (ttyACM*)
    - CP210x devices (ttyUSB*)
    - FTDI devices (ttyUSB*)
    - STM32 Virtual COM Port
    - Known VID:PID combinations for common flight controllers
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
        (0x1fc9, 0x0083),  # NXP
    ]

    ports = serial.tools.list_ports.comports()
    fc_ports = []

    for port in ports:
        score = 0
        reason = []

        # Check if it's a known VID:PID
        if port.vid and port.pid:
            if (port.vid, port.pid) in KNOWN_FC_VIDPID:
                score += 10
                reason.append(f"Known FC VID:PID {hex(port.vid)}:{hex(port.pid)}")

        # Check device type
        if 'ACM' in port.device:
            score += 5
            reason.append("USB CDC ACM device")
        elif 'USB' in port.device:
            score += 3
            reason.append("USB Serial device")

        # Check description for common keywords
        desc_lower = port.description.lower() if port.description else ""
        if any(kw in desc_lower for kw in ['stm32', 'betaflight', 'inav', 'arduino', 'flight']):
            score += 5
            reason.append("Description suggests FC")

        # Check manufacturer
        mfr_lower = port.manufacturer.lower() if port.manufacturer else ""
        if any(kw in mfr_lower for kw in ['stm', 'silicon labs', 'ftdi', 'arduino']):
            score += 3
            reason.append(f"Known manufacturer: {port.manufacturer}")

        if score > 0:
            fc_ports.append({
                'device': port.device,
                'description': port.description,
                'manufacturer': port.manufacturer,
                'vid': port.vid,
                'pid': port.pid,
                'score': score,
                'reason': reason
            })

    # Sort by score (highest first)
    fc_ports.sort(key=lambda x: x['score'], reverse=True)

    return fc_ports

if __name__ == '__main__':
    print("Detecting flight controller ports...")
    print()

    fc_ports = detect_flight_controller_ports()

    if not fc_ports:
        print("❌ No flight controller detected")
    else:
        for i, port in enumerate(fc_ports, 1):
            print(f"{i}. {port['device']} (Score: {port['score']})")
            print(f"   Description: {port['description']}")
            print(f"   Manufacturer: {port['manufacturer']}")
            if port['vid'] and port['pid']:
                print(f"   VID:PID: {hex(port['vid'])}:{hex(port['pid'])}")
            print(f"   Reasons: {', '.join(port['reason'])}")
            print()

        print(f"✅ Best match: {fc_ports[0]['device']}")
