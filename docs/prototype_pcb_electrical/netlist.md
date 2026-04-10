# RECLAIM Prototype — Complete Netlist
**Date:** April 10, 2026
**Revision:** 1.0
**Format:** Human-readable per-net listing for schematic entry in KiCad

---

## Net Naming Conventions

| Net Name      | Voltage | Description                                    |
|---------------|---------|------------------------------------------------|
| VBAT          | 12.8V   | Battery positive terminal                      |
| GND           | 0V      | Common ground                                  |
| VBAT_FUSED_1  | 12.8V   | Post-fuse ch1 — XINGYHENG buck (5A)           |
| VBAT_FUSED_2  | 12.8V   | Post-fuse ch2 — Cytron MD13C R3 (10A)         |
| VBAT_FUSED_3  | 12.8V   | Post-fuse ch3 — MIC-711 IPC (10A)             |
| VBAT_FUSED_4  | 12.8V   | Post-fuse ch4 — BTS7960 (20A)                 |
| V_SERVO       | 6.8V    | Buck output — servo power rail                 |
| V_5V_USB      | 5V      | MIC-711 USB ports (powers router, Teensy)      |

---

## Section 1 — Power Input & Distribution

### Net: VBAT
- Battery positive terminal
- DC Disconnect switch Pin 1 (input/battery side)

### Net: VBAT_SWITCHED
- DC Disconnect switch Pin 2 (load side)
- Fuse Block common bus (input)

### Net: VBAT_FUSED_1 (5A — servo buck)
- Fuse Block Ch1 output (5A blade fuse)
- U_BUCK VIN+ (XINGYHENG buck input positive)

### Net: VBAT_FUSED_2 (10A — left motor driver)
- Fuse Block Ch2 output (10A blade fuse)
- U_DRV_L Power+ (Cytron MD13C R3 motor power input)

### Net: VBAT_FUSED_3 (10A — MIC-711)
- Fuse Block Ch3 output (10A blade fuse)
- U_IPC VCC terminal (MIC-711 2-pin power connector positive)

### Net: VBAT_FUSED_4 (20A — right motor driver)
- Fuse Block Ch4 output (20A blade fuse)
- U_DRV_R B+ (BTS7960 motor power input)

### Net: GND
- Battery negative terminal
- DC Disconnect switch Pin 3 (ground passthrough, if used)
- Fuse Block common ground bus
- U_BUCK GND
- U_DRV_L GND
- U_DRV_R GND
- U_IPC GND terminal (MIC-711 2-pin power connector negative)
- Teensy GND pin
- All servo GND (via Wago GND rail)
- C_BULK negative
- Encoder GND pins (both motors)

---

## Section 2 — Servo Power Rail

### Net: V_SERVO (6.8V)
- U_BUCK VOUT+ (buck converter output positive)
- C_BULK positive (10,000µF bulk cap)
- Wago 221-415 #1 input (VCC distribution)
- → J1 servo VCC (DS3218 Base)
- → J2 servo VCC (DS3235 Shoulder)
- → J3 servo VCC (DS3218 Elbow)
- Wago 221-415 #2 input (VCC distribution)
- → J4 servo VCC (DS3218 Wrist Pitch)
- → J5 servo VCC (MG996R Wrist Rotate)
- → J6 servo VCC (DS3218 Gripper)

### Net: GND (servo return)
- U_BUCK VOUT− (buck converter output negative)
- C_BULK negative
- Wago 221-415 #3 input (GND distribution)
- → J1-J3 servo GND
- Wago 221-415 #4 input (GND distribution)
- → J4-J6 servo GND

---

## Section 3 — Motor Drivers & Motors

### Left Motor — Cytron MD13C R3

#### Net: MOTOR_L+
- U_DRV_L Motor A output
- M_L motor pin M1

#### Net: MOTOR_L−
- U_DRV_L Motor B output
- M_L motor pin M2

#### Net: PWM_L (Teensy pin 2)
- Teensy 4.1 Pin 2
- U_DRV_L PWM input

#### Net: DIR_L (Teensy pin 3)
- Teensy 4.1 Pin 3
- U_DRV_L DIR input

### Right Motor — BTS7960

#### Net: MOTOR_R+
- U_DRV_R Motor M+ output
- M_R motor pin M1

#### Net: MOTOR_R−
- U_DRV_R Motor M− output
- M_R motor pin M2

#### Net: LPWM_R (Teensy pin 23)
- Teensy 4.1 Pin 23
- U_DRV_R LPWM input

#### Net: RPWM_R (Teensy pin 22 — DIR pin repurposed)
- Teensy 4.1 Pin 22
- U_DRV_R RPWM input

#### Net: BTS_R_EN (3.3V enable)
- Teensy 4.1 3.3V pin
- U_DRV_R R_EN input

#### Net: BTS_L_EN (3.3V enable)
- Teensy 4.1 3.3V pin
- U_DRV_R L_EN input

Note: R_EN and L_EN tied directly to 3.3V (always enabled). Pin 20 does NOT support PWM on Teensy 4.1 — LPWM moved to pin 23.

---

## Section 4 — Encoders

### Left Encoder (JGB37-520)

#### Net: ENC_L_A (Teensy pin 6)
- Teensy 4.1 Pin 6
- M_L encoder output A

#### Net: ENC_L_B (Teensy pin 7)
- Teensy 4.1 Pin 7
- M_L encoder output B

#### Net: ENC_L_VCC (3.3V)
- Teensy 4.1 3V pin
- M_L encoder VCC

### Right Encoder (JGB37-520)

#### Net: ENC_R_A (Teensy pin 19)
- Teensy 4.1 Pin 19
- M_R encoder output A

#### Net: ENC_R_B (Teensy pin 18)
- Teensy 4.1 Pin 18
- M_R encoder output B

#### Net: ENC_R_VCC (3.3V)
- Teensy 4.1 3V pin
- M_R encoder VCC

Note: Encoders powered at 3.3V from Teensy 3V pin. Outputs 3.3V logic, directly compatible with Teensy GPIO (NOT 5V tolerant).

---

## Section 5 — Servo Signal Lines

All servo signal wires from Teensy PWM pins through extension cables (~60cm, 24AWG).

| Net Name    | Teensy Pin | Servo   | Joint           |
|-------------|------------|---------|-----------------|
| SERVO_J1    | Pin 10     | DS3218  | Base rotation   |
| SERVO_J2    | Pin 11     | DS3235  | Shoulder        |
| SERVO_J3    | Pin 12     | DS3218  | Elbow           |
| SERVO_J4    | Pin 13     | DS3218  | Wrist Pitch     |
| SERVO_J5    | Pin 14     | MG996R  | Wrist Rotate    |
| SERVO_J6    | Pin 15     | DS3218  | Gripper         |

---

## Section 6 — Compute & Peripherals

### MIC-711 Connections
| Port         | Device              | Cable    |
|--------------|---------------------|----------|
| 2-pin power  | Fuse block ch3      | 14AWG    |
| Ethernet     | GL.iNet Mango       | RJ45     |
| USB 3.0      | OAK-D Lite          | USB 3.0  |
| USB 2.0 (hub)| USB Hub             | USB-A    |
| USB 2.0      | RPLIDAR A1M8        | USB-A    |

### USB Hub Connections
| Port    | Device           |
|---------|------------------|
| Input   | MIC-711 USB 2.0  |
| Port 1  | Teensy 4.1       |
| Port 2  | GL.iNet Mango    |

### Teensy 4.1 Pin Summary
| Pin  | Function        | Connected To              |
|------|-----------------|---------------------------|
| 2    | PWM             | MD13C R3 PWM (left motor) |
| 3    | DIR             | MD13C R3 DIR (left motor) |
| 6    | Encoder A       | Left encoder Ch A         |
| 7    | Encoder B       | Left encoder Ch B         |
| 10   | Servo PWM       | J1 DS3218 Base            |
| 11   | Servo PWM       | J2 DS3235 Shoulder        |
| 12   | Servo PWM       | J3 DS3218 Elbow           |
| 13   | Servo PWM       | J4 DS3218 Wrist Pitch     |
| 14   | Servo PWM       | J5 MG996R Wrist Rotate    |
| 15   | Servo PWM       | J6 DS3218 Gripper         |
| 18   | Encoder B       | Right encoder Ch B        |
| 19   | Encoder A       | Right encoder Ch A        |
| 22   | RPWM            | BTS7960 RPWM (right motor)|
| 23   | LPWM            | BTS7960 LPWM (right motor)|
| 3V   | 3.3V out        | Encoder VCC, BTS R_EN/L_EN|
| GND  | Ground          | Common ground bus          |
| USB  | Serial 115200   | USB hub → MIC-711          |

---

## Notes

1. **Asymmetric motor drivers**: Left=MD13C R3 (PWM+DIR), Right=BTS7960 (LPWM+RPWM). Different due to ESD damage to original right MD13C R3.
2. **Pin 20 issue**: Pin 20 does NOT support PWM on Teensy 4.1. BTS7960 LPWM moved to pin 23.
3. **Servo brownout**: Long 24AWG extension cables cause voltage drop. Buck set to 6.8V to compensate. 10,000µF cap helps but J5/J6 still twitch under load.
4. **DC Disconnect**: Manual battery isolator between battery and fuse block. Only E-stop mechanism on prototype (no relay/software stop).
5. **OAK-D must be on USB 3.0 port** — will not function properly on USB 2.0.
