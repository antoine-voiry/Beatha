# Wiring Guide - Project Beatha

## ⚠️ The Master Reference
**Follow these steps exactly.** This guide uses a "Phase" approach to ensure reliability.

![Pi Zero Pinout](https://gpiozero.readthedocs.io/en/stable/_images/pinout_pi_zero.png)
*(Reference: Standard Pi Zero W GPIO Header)*

---

## Phase 1: The "Backside" (The Hard Part)
*Start here while the board is easy to move around.*

1.  **Flip the Pi Zero W over** (Chips facing down).
2.  **Locate PP22 and PP23** (Directly behind the USB data port).
3.  **Tin the Pads:** Touch your iron and a tiny bit of solder to PP22 and PP23 to make a small shiny "pillow" on each.
4.  **Solder Green Wire (Data+):** Connect to **PP22**.
    *   *Check:* Ensure it doesn't touch PP23.
5.  **Solder White Wire (Data-):** Connect to **PP23**.
    *   *Check:* Ensure it doesn't touch PP22.
6.  **Secure the Wire:** Use a dab of hot glue or tape on the wires near the solder points so a tug on the cable doesn't rip the pads off.

---

## Phase 2: The "Topside" (The Hat)
*Flip the board back over (Chips facing up).*

### The Power (Umbilical Input)
*   **Black Wire (GND):** Solder to **Pin 6** (3rd pin down, outer row).
*   **Red Wire (5V):**
    *   **If using Diode:** Solder the **Stripe Side (Cathode)** to **Pin 2** (Top right corner, outer row). Solder the Red wire to the Black Body Side (Anode).
    *   **If NO Diode:** Solder Red wire directly to **Pin 2**.

### The Peripherals

**LED Strip:**
*   **Red (5V):** **Pin 4**.
*   **Black (GND):** **Pin 9** (or any free GND).
*   **Data In:** **Pin 12** (GPIO 18).

**Button 1 (Start/Dump):**
*   **Leg 1:** **Pin 16** (GPIO 23).
*   **Leg 2:** **Pin 14** (GND).

**Button 2 (Func/Pair):**
*   **Leg 1:** **Pin 18** (GPIO 24).
*   **Leg 2:** **Pin 20** (GND).

**Buzzer:**
*   **Positive (+):** **Pin 22** (GPIO 25).
*   **Negative (-):** **Pin 25** (GND).

---

## Phase 3: The "Smoke Test" (Inspection)
**Before you plug ANYTHING in:**

1.  **Visual Check:** Look closely at **Pin 2** and **Pin 4** (The 5V pins). Make sure they are not accidentally bridged to any other pins with a blob of solder.
2.  **The Diode Check:** If you used a Schottky, is the **Silver Stripe** pointing **TOWARDS the Raspberry Pi**? (Stripe = Pin 2).
3.  **The Data Check:** Are Green (PP22) and White (PP23) separate? If they touch, USB won't work.

### Ready to power up?
1.  **Step 1:** Plug the Umbilical into the Drone.
2.  **Step 2:** Plug a battery into the Drone.
3.  **Expected Result:** The Drone lights up, and a few seconds later, the Pi's green activity LED should start flickering.