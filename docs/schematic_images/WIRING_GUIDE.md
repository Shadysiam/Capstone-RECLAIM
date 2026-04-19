# RECLAIM — KiCad Schematic Wiring Guide (Phil's Lab Style)

> **Purpose:** Reference for wiring all labels in the KiCad schematics. Updated to use **Phil's Lab conventions:**
> - **Power symbols** (`+12V`, `+5V`, `+3.3V`, `GND`) placed at every component pin that needs power — press `P` to place
> - **Global labels** (rectangle with pointed edge) for all cross-sheet signals — press `Ctrl+L` to place
> - **Net labels** only for signals that stay on the same sheet — press `L` to place
> - Signal flow: **left → right**, power **top → bottom**
>
> **Label types in these schematics:**
> - `(global_label)` = connects across ALL sheets automatically (shown as pointed rectangles)
> - Power symbols = `+12V`, `GND`, `+3.3V`, `+5V` — built-in KiCad power symbols, global scope
> - GND labels have been **removed** — place `GND` power symbols (press `P`, search "GND") at the positions noted below

---

## Phil's Lab Style Quick Reference

### What changed in the schematic files

| Before | After | How to place in KiCad |
|--------|-------|----------------------|
| `(label "SPI1_SCK" ...)` | `(global_label "SPI1_SCK" (shape output) ...)` | `Ctrl+L` → type name |
| `(label "GND" ...)` | **REMOVED** — place GND power symbol | `P` → search "GND" |
| `(label "VCC_3V3" ...)` | `(global_label "VCC_3V3" (shape passive) ...)` | Already converted |

### GND power symbols to place (where old GND labels were removed)

| Sheet | Position | Near component |
|-------|----------|---------------|
| Product Power Distribution | (245, 125) | Buck 1 area |
| Product Power Distribution | (390, 212) | LDO area |
| Product Power Distribution | (290, 148) | Buck 2 area |
| Product Power Distribution | (157, 215) | E-stop relay area |
| Product STM32 MCU | (135, 228) | Decoupling caps area |
| Prototype Power Distribution | (240, 108) | Buck converter area |
| Prototype Teensy Motor Control | (42, 100) | Motor driver L area |
| Prototype Teensy Motor Control | (42, 195) | Motor driver R area |
| Prototype Peripherals | (58, 118) | IPC area |

### Signal direction shapes on global labels

| Shape | Meaning | Examples |
|-------|---------|---------|
| `output` | MCU drives this signal | SPI1_SCK, CAN1_TX, ESTOP_RELAY_CTRL |
| `input` | MCU receives this signal | SPI1_MISO, CAN1_RX, ENC_L_A, BUMPER_FL |
| `bidirectional` | Both directions | I2C1_SCL, I2C1_SDA, ETHERNET |
| `passive` | Power rail / no direction | VCC_25V, VBAT, MOTOR_PWR_L |

### Phil's Lab rules to follow while wiring

1. **Every VDD/VCC pin** → place `+3.3V` or `+5V` or `+12V` power symbol (press `P`)
2. **Every GND pin** → place `GND` power symbol pointing down (press `P`)
3. **Decoupling caps** → place RIGHT NEXT to the IC, between VDD pin and GND
4. **Short wires only** (2-4 grid squares) between components and their power symbols
5. **Components that share a function** → group together physically on the schematic
6. **No long power bus wires** — just place a new power symbol at each component

---

## Table of Contents

1. [Prototype — Power Distribution](#1-prototype--power-distribution)
2. [Prototype — Teensy & Motor Control](#2-prototype--teensy--motor-control)
3. [Prototype — Peripherals & Sensors](#3-prototype--peripherals--sensors)
4. [Product — Power Distribution & E-Stop](#4-product--power-distribution--e-stop)
5. [Product — STM32 MCU](#5-product--stm32-mcu)
6. [Product — Motor Drivers, CAN, IMU & Power Monitors](#6-product--motor-drivers-can-imu--power-monitors)
7. [Product — Connectors, LEDs, USB & Peripherals](#7-product--connectors-leds-usb--peripherals)
8. [Cross-Sheet Net Label Reference](#8-cross-sheet-net-label-reference)

---

## 1. Prototype — Power Distribution

**Sheet:** `Power_Distribution.kicad_sch`
**Page size:** A3

### Components

| Ref | Value | Description |
|-----|-------|-------------|
| J_BAT | Battery 12.8V | ZapLitho LiFePO4 battery connector (2-pin) |
| SW_DC | DC Disconnect | DPST switch / XT60 kill switch |
| F1 | 5A | Fuse — MIC-711 compute channel |
| F2 | 10A | Fuse — Motor driver L channel |
| F3 | 10A | Fuse — Motor driver R channel |
| F4 | 20A | Fuse — Servo buck converter channel |
| U_BUCK | XINGYHENG 12V→6.8V | 20A 300W buck converter for servo bus |
| C_BULK | 10000uF 16V | Bulk electrolytic cap on servo bus |
| WAGO_V1 | 221-415 VCC | Wago lever-nut — servo VCC distribution (row 1) |
| WAGO_V2 | 221-415 VCC | Wago lever-nut — servo VCC distribution (row 2) |
| WAGO_G1 | 221-415 GND | Wago lever-nut — servo GND distribution (row 1) |
| WAGO_G2 | 221-415 GND | Wago lever-nut — servo GND distribution (row 2) |
| J1_PWR | J1 Base | Servo power connector — J1 base rotation (DS3218) |
| J2_PWR | J2 Shoulder | Servo power connector — J2 shoulder (DS3235) |
| J3_PWR | J3 Elbow | Servo power connector — J3 elbow (DS3218) |
| J4_PWR | J4 WristP | Servo power connector — J4 wrist pitch (DS3218) |
| J5_PWR | J5 WristR | Servo power connector — J5 wrist rotate (MG996R) |
| J6_PWR | J6 Gripper | Servo power connector — J6 gripper (DS3218 + LewanSoul) |
| #PWR001 | +12V | Power symbol |
| #PWR002 | GND | Power symbol |
| #PWR003 | PWR_FLAG | ERC power flag |
| #PWR004 | PWR_FLAG | ERC power flag |

### Wiring Instructions

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| J_BAT pin 1 | Label `VBAT` | VBAT | Battery positive terminal |
| J_BAT pin 2 | GND symbol | GND | Battery ground |
| Label `VBAT` | SW_DC pin 1 | VBAT | Battery voltage to switch |
| SW_DC pin 2 | Label `VBAT_SWITCHED` | VBAT_SWITCHED | Switched battery voltage |
| Label `VBAT_SWITCHED` | F1 pin 1 | — | Direct wire to fuse input |
| F1 pin 2 | Label `VBAT_FUSED_1` | VBAT_FUSED_1 | → MIC-711 (on Peripherals sheet) |
| Label `VBAT_SWITCHED` | F2 pin 1 | — | Direct wire |
| F2 pin 2 | Label `VBAT_FUSED_2` | VBAT_FUSED_2 | → Motor driver L (on Teensy sheet) |
| Label `VBAT_SWITCHED` | F3 pin 1 | — | Direct wire |
| F3 pin 2 | Label `VBAT_FUSED_3` | VBAT_FUSED_3 | → Motor driver R (on Peripherals sheet) |
| Label `VBAT_SWITCHED` | F4 pin 1 | — | Direct wire |
| F4 pin 2 | Label `VBAT_FUSED_4` | VBAT_FUSED_4 | → Servo buck (on Teensy sheet) |
| Label `VBAT_FUSED_4` | U_BUCK pin 1 | — | Buck converter VIN+ |
| U_BUCK pin 2 | Label `V_SERVO` | V_SERVO | Buck converter VOUT+ (6.8V) |
| U_BUCK pin 3 | GND symbol | GND | Buck converter VIN− |
| U_BUCK pin 4 | GND symbol | GND | Buck converter VOUT− |
| Label `V_SERVO` | C_BULK pin 1 | — | Bulk cap positive |
| GND symbol | C_BULK pin 2 | — | Bulk cap negative |
| Label `V_SERVO` | WAGO_V1 pin 1 | — | VCC Wago row 1 input |
| Label `V_SERVO` | WAGO_V2 pin 1 | — | VCC Wago row 2 input |
| GND symbol | WAGO_G1 pin 1 | — | GND Wago row 1 input |
| GND symbol | WAGO_G2 pin 1 | — | GND Wago row 2 input |
| WAGO_V1 pin 2 | J1_PWR pin 1 | — | J1 servo VCC |
| WAGO_G1 pin 2 | J1_PWR pin 2 | — | J1 servo GND |
| WAGO_V1 pin 3 | J2_PWR pin 1 | — | J2 servo VCC |
| WAGO_G1 pin 3 | J2_PWR pin 2 | — | J2 servo GND |
| WAGO_V1 pin 4 | J3_PWR pin 1 | — | J3 servo VCC |
| WAGO_G1 pin 4 | J3_PWR pin 2 | — | J3 servo GND |
| WAGO_V2 pin 2 | J4_PWR pin 1 | — | J4 servo VCC |
| WAGO_G2 pin 2 | J4_PWR pin 2 | — | J4 servo GND |
| WAGO_V2 pin 3 | J5_PWR pin 1 | — | J5 servo VCC |
| WAGO_G2 pin 3 | J5_PWR pin 2 | — | J5 servo GND |
| WAGO_V2 pin 4 | J6_PWR pin 1 | — | J6 servo VCC |
| WAGO_G2 pin 4 | J6_PWR pin 2 | — | J6 servo GND |
| +12V symbol | J_BAT pin 1 | +12V | Power flag for ERC |
| PWR_FLAG symbol | VBAT net | — | ERC flag |
| PWR_FLAG symbol | GND net | — | ERC flag |

---

## 2. Prototype — Teensy & Motor Control

**Sheet:** `Teensy_Motor_Control.kicad_sch`
**Page size:** A3

### Components

| Ref | Value | Description |
|-----|-------|-------------|
| U_MCU | Teensy 4.1 | Main microcontroller (Conn_02x24, 48 pins total) |
| U_DRV_L | MD13C R3 | Motor driver left (MD10C, 6-pin connector) |
| U_DRV_R | BTS7960 | Motor driver right (8-pin connector) |
| M_L | JGB37-520 L | Left drive motor connector (6-pin: M1, M2, VCC, GND, OutA, OutB) |
| M_R | JGB37-520 R | Right drive motor connector (6-pin) |
| SIG_J1 | J1 Base P10 | Servo signal wire — Teensy pin 10 |
| SIG_J2 | J2 Shldr P11 | Servo signal wire — Teensy pin 11 |
| SIG_J3 | J3 Elbow P12 | Servo signal wire — Teensy pin 12 |
| SIG_J4 | J4 WrstP P13 | Servo signal wire — Teensy pin 13 |
| SIG_J5 | J5 WrstR P14 | Servo signal wire — Teensy pin 14 |
| SIG_J6 | J6 Grip P15 | Servo signal wire — Teensy pin 15 |
| #PWR101 | +12V | Power symbol |
| #PWR102 | GND | Power symbol |
| #PWR103 | +3V3 | Power symbol |

### Wiring Instructions — Left Motor Driver (U_DRV_L → MD10C)

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `VBAT_FUSED_2` | U_DRV_L pin 1 (VIN) | VBAT_FUSED_2 | 12V from fuse block |
| Label `PWM_L` | U_DRV_L pin 2 (PWM) | PWM_L | → Teensy pin 2 |
| Label `DIR_L` | U_DRV_L pin 3 (DIR) | DIR_L | → Teensy pin 3 |
| Label `MOTOR_L+` | U_DRV_L pin 4 (OUT+) | MOTOR_L+ | Motor terminal |
| Label `MOTOR_L-` | U_DRV_L pin 5 (OUT−) | MOTOR_L- | Motor terminal |
| Label `GND` | U_DRV_L pin 6 (GND) | GND | Ground |

### Wiring Instructions — Right Motor Driver (U_DRV_R → BTS7960)

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `VBAT_FUSED_4` | U_DRV_R pin 1 (VIN) | VBAT_FUSED_4 | 12V from fuse block |
| Label `LPWM_R` | U_DRV_R pin 2 (LPWM) | LPWM_R | → Teensy pin 22 (PWM) |
| Label `RPWM_R` | U_DRV_R pin 3 (RPWM) | RPWM_R | → Teensy pin 20 (DIR) |
| Label `MOTOR_R+` | U_DRV_R pin 4 (OUT+) | MOTOR_R+ | Motor terminal |
| Label `MOTOR_R-` | U_DRV_R pin 5 (OUT−) | MOTOR_R- | Motor terminal |
| Label `BTS_R_EN` | U_DRV_R pin 6 (R_EN) | BTS_R_EN | Enable (tie HIGH or to Teensy) |
| Label `BTS_L_EN` | U_DRV_R pin 7 (L_EN) | BTS_L_EN | Enable (tie HIGH or to Teensy) |
| Label `GND` | U_DRV_R pin 8 (GND) | GND | Ground |

### Wiring Instructions — Teensy 4.1 (U_MCU) Left Side (pins 1–24)

| Teensy Pin | Physical Pin # | Wire To | Net Name |
|------------|---------------|---------|----------|
| Pin 2 (PWM) | Left row | Label `PWM_L` | PWM_L |
| Pin 3 (DIR) | Left row | Label `DIR_L` | DIR_L |
| Pin 6 (ENC_L_A) | Left row | Label `ENC_L_A` | ENC_L_A |
| Pin 7 (ENC_L_B) | Left row | Label `ENC_L_B` | ENC_L_B |
| GND | Left row | Label `GND` | GND |
| 3V | Left row | #PWR103 (+3V3) | +3V3 |

### Wiring Instructions — Teensy 4.1 (U_MCU) Right Side (pins 25–48)

| Teensy Pin | Physical Pin # | Wire To | Net Name |
|------------|---------------|---------|----------|
| Pin 10 | Right row | Label `SERVO_J1` | SERVO_J1 |
| Pin 11 | Right row | Label `SERVO_J2` | SERVO_J2 |
| Pin 12 | Right row | Label `SERVO_J3` | SERVO_J3 |
| Pin 13 | Right row | Label `SERVO_J4` | SERVO_J4 |
| Pin 14 | Right row | Label `SERVO_J5` | SERVO_J5 |
| Pin 15 | Right row | Label `SERVO_J6` | SERVO_J6 |
| Pin 18 (ENC_R_B) | Right row | Label `ENC_R_B` | ENC_R_B |
| Pin 19 (ENC_R_A) | Right row | Label `ENC_R_A` | ENC_R_A |
| Pin 20 (DIR_R) | Right row | Label `RPWM_R` | RPWM_R |
| Pin 22 (PWM_R) | Right row | Label `LPWM_R` | LPWM_R |

### Wiring Instructions — Motor Connectors

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `MOTOR_L+` | M_L pin 1 (M1) | MOTOR_L+ | Left motor terminal 1 |
| Label `MOTOR_L-` | M_L pin 2 (M2) | MOTOR_L- | Left motor terminal 2 |
| M_L pin 3 (VCC) | +3V3 or +5V | — | Encoder power (3.3V from Teensy) |
| M_L pin 4 (GND) | GND | GND | Encoder ground |
| Label `ENC_L_A` | M_L pin 5 (OutA) | ENC_L_A | Left encoder channel A |
| Label `ENC_L_B` | M_L pin 6 (OutB) | ENC_L_B | Left encoder channel B |
| Label `MOTOR_R+` | M_R pin 1 (M1) | MOTOR_R+ | Right motor terminal 1 |
| Label `MOTOR_R-` | M_R pin 2 (M2) | MOTOR_R- | Right motor terminal 2 |
| M_R pin 3 (VCC) | +3V3 | — | Encoder power |
| M_R pin 4 (GND) | GND | GND | Encoder ground |
| Label `ENC_R_A` | M_R pin 5 (OutA) | ENC_R_A | Right encoder channel A |
| Label `ENC_R_B` | M_R pin 6 (OutB) | ENC_R_B | Right encoder channel B |

### Wiring Instructions — Servo Signal Connectors

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `SERVO_J1` | SIG_J1 pin 1 | SERVO_J1 | Base servo signal (Teensy pin 10) |
| Label `SERVO_J2` | SIG_J2 pin 1 | SERVO_J2 | Shoulder servo signal (Teensy pin 11) |
| Label `SERVO_J3` | SIG_J3 pin 1 | SERVO_J3 | Elbow servo signal (Teensy pin 12) |
| Label `SERVO_J4` | SIG_J4 pin 1 | SERVO_J4 | Wrist pitch servo signal (Teensy pin 13) |
| Label `SERVO_J5` | SIG_J5 pin 1 | SERVO_J5 | Wrist rotate servo signal (Teensy pin 14) |
| Label `SERVO_J6` | SIG_J6 pin 1 | SERVO_J6 | Gripper servo signal (Teensy pin 15) |

---

## 3. Prototype — Peripherals & Sensors

**Sheet:** `Peripherals_Sensors.kicad_sch`
**Page size:** A3

### Components

| Ref | Value | Description |
|-----|-------|-------------|
| U_IPC | MIC-711 | Advantech MIC-711 IPC / Jetson Orin NX (8-pin connector) |
| U_HUB | USB Hub | 4-port USB hub (4-pin connector) |
| J_TEENSY_USB | Teensy USB | USB connection from Teensy to MIC-711 (1-pin) |
| U_ROUTER | GL.iNet Mango | Travel router for WiFi (3-pin connector) |
| U_CAM | OAK-D Lite | Depth camera (1-pin USB connector) |
| U_LIDAR | RPLIDAR A1M8 | 360° LiDAR scanner (1-pin USB connector) |
| #PWR201 | +12V | Power symbol |
| #PWR202 | GND | Power symbol |
| #PWR203 | +5V | Power symbol |

### Wiring Instructions

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `VBAT_FUSED_3` | U_IPC pin 1 (12V IN) | VBAT_FUSED_3 | 12V power from fuse block |
| Label `GND` | U_IPC pin 8 (GND) | GND | IPC ground |
| U_IPC pin 2 (ETH) | Label `ETHERNET` | ETHERNET | RJ45 to router |
| U_IPC pin 3 (USB 2.0) | Label `USB_2.0` | USB_2.0 | USB 2.0 port |
| U_IPC pin 4 (USB 3.0) | Label `USB_3.0` | USB_3.0 | USB 3.0 port |
| Label `ETHERNET` | U_ROUTER pin 1 (WAN) | ETHERNET | Ethernet to router |
| Label `V_5V_USB` | U_HUB pin 1 (VCC) | V_5V_USB | USB hub power |
| Label `USB_2.0` | U_HUB pin 2 (upstream) | USB_2.0 | Hub upstream to IPC |
| U_HUB pin 3 (port 1) | J_TEENSY_USB pin 1 | — | Direct wire, Teensy USB |
| U_HUB pin 4 (port 2) | U_ROUTER pin 2 (USB power) | — | Router USB power |
| Label `USB_3.0` | U_CAM pin 1 | USB_3.0 | OAK-D on USB 3.0 (MUST be 3.0) |
| U_HUB pin 3 (port 3) | U_LIDAR pin 1 | — | RPLIDAR via USB hub |
| #PWR201 (+12V) | VBAT_FUSED_3 net | +12V | Power flag |
| #PWR203 (+5V) | V_5V_USB net | +5V | Power flag |

---

## 4. Product — Power Distribution & E-Stop

**Sheet:** `Power_Distribution.kicad_sch`
**Page size:** A3

### Components

| Ref | Value | Description |
|-----|-------|-------------|
| J1 | Conn_01x02 | Battery input connector (XT60) |
| SW1 | SW_Push | Emergency stop push button |
| F1 | 30A | Main fuse |
| F4 | 5A | Compute fuse |
| F5 | 2A | Coil fuse |
| F2L | 15A | Left motor fuse |
| F2R | 15A | Right motor fuse |
| F3 | 10A | Compute fuse |
| K1 | G5LE-1A-DC24 | E-stop relay (SPST-NO) |
| D1 | 1N4007 | Flyback diode across relay coil |
| D2 | 1N4007 | Protection diode |
| Q1 | IRLZ44N | N-channel MOSFET for relay drive |
| R1 | R | Gate resistor |
| R2 | R | Pull-down resistor |
| R11 | 1k | Current limiting |
| R12 | 47k | Pull-down |
| U1 | LM5116SD | Synchronous buck controller — 24V→12V |
| L_BUCK1 | 22uH | Buck 1 inductor |
| D_BUCK1 | SS34 | Buck 1 Schottky diode |
| R_FB1A | 40.2k | Buck 1 feedback divider (top) |
| R_FB1B | 3.24k | Buck 1 feedback divider (bottom) |
| C1 | 470uF | Input filter cap |
| C2 | 470uF 25V | Buck 1 output cap |
| C5 | 100nF | Buck 1 decoupling |
| U2 | TPS5430DDA | Step-down converter — 12V→5V |
| L_BUCK2 | 22uH | Buck 2 inductor |
| D_BUCK2 | SS34 | Buck 2 Schottky diode |
| R_FB2A | 53.6k | Buck 2 feedback divider (top) |
| R_FB2B | 15k | Buck 2 feedback divider (bottom) |
| C3 | 470uF 16V | Buck 2 output cap |
| C6 | 100nF | Buck 2 decoupling |
| U3 | AMS1117-3.3 | LDO regulator — 5V→3.3V |
| C4 | 470uF 10V | LDO output cap |
| C7 | 100nF | LDO input decoupling |
| C8 | 10uF | LDO output decoupling |

### Wiring Instructions — Battery & Fusing

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| J1 pin 1 | Label `VBAT` | VBAT | Battery positive (24V nominal) |
| J1 pin 2 | GND symbol | GND | Battery ground |
| Label `VBAT` | SW1 pin 1 | VBAT | E-stop input |
| SW1 pin 2 | F1 pin 1 | — | To main fuse |
| F1 pin 2 | Label `VBAT_MOTOR` | VBAT_MOTOR | Post-fuse motor bus |
| Label `VBAT_MOTOR` | F2L pin 1 | — | Left motor fuse |
| Label `VBAT_MOTOR` | F2R pin 1 | — | Right motor fuse |
| F2L pin 2 | Label `VCC_25V` | VCC_25V | → Left motor driver (Drivers sheet) |
| F2R pin 2 | Label `VCC_25V` | VCC_25V | → Right motor driver (Drivers sheet) |
| Label `VBAT` | F4 pin 1 | — | Compute fuse |
| F4 pin 2 | Label `VBAT_COMPUTE` | VBAT_COMPUTE | To compute buck input |
| Label `VBAT` | F5 pin 1 | — | Coil fuse |
| F5 pin 2 | Label `VBAT_COIL` | VBAT_COIL | To relay coil circuit |

### Wiring Instructions — E-Stop Relay Circuit

**K1 (G5LE-1A) pin map:** Pin 1 = Coil+, Pin 2 = Coil−, Pin 3 = COM, Pin 4 = NO
**Q1 (IRLZ44N) pin map:** Pin 1 = Gate, Pin 2 = Drain, Pin 3 = Source
**D1/D2 (1N4007) pin map:** Pin 1 = Anode (A), Pin 2 = Cathode (K)

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `ESTOP_RELAY_CTRL` | R11 pin 1 | ESTOP_RELAY_CTRL | From STM32 GPIO |
| R11 pin 2 | R12 pin 1 | — | Voltage divider junction |
| R12 pin 1 | Q1 pin 1 | — | MOSFET gate drive |
| R12 pin 2 | GND symbol | GND | Pull-down to ground |
| Q1 pin 3 | GND symbol | GND | MOSFET source |
| Q1 pin 2 | K1 pin 2 | — | MOSFET drain → relay coil− |
| Label `VBAT_COIL` | K1 pin 1 | — | Fused battery → relay coil+ |
| D1 pin 1 | Q1 pin 2 | — | Flyback diode anode → coil low side |
| D1 pin 2 | K1 pin 1 | — | Flyback diode cathode → coil high side |
| Label `VBAT_MOTOR` | K1 pin 3 | — | Power in → relay COM |
| K1 pin 4 | Label `RELAY_COIL_IN` | RELAY_COIL_IN | Relay NO → power out when energized |

### Wiring Instructions — Buck Converter 1 (LM5116, 24V→12V)

**U1 (LM5116) key pins:** VIN, SW, FB, GND, VCC (check symbol for exact pin #s)
**D_BUCK1 (SS34):** Pin 1 = Anode, Pin 2 = Cathode

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `VBAT_COMPUTE` | U1 VIN pin | — | Input voltage |
| C1 pin 1 | U1 VIN pin | — | Input cap |
| C1 pin 2 | GND symbol | GND | Input cap ground |
| U1 SW pin | L_BUCK1 pin 1 | — | Switch node through inductor |
| L_BUCK1 pin 2 | Label `VCC_12V` | VCC_12V | 12V regulated output |
| D_BUCK1 pin 1 | GND symbol | GND | Schottky diode anode |
| D_BUCK1 pin 2 | U1 SW pin | — | Schottky diode cathode → switch node |
| R_FB1A pin 1 | Label `VCC_12V` | — | Feedback top |
| R_FB1A pin 2 | R_FB1B pin 1 | — | Feedback divider mid |
| R_FB1B pin 2 | GND symbol | GND | Feedback bottom |
| R_FB1A pin 2 (junction) | U1 FB pin | — | Feedback to regulator |
| C2 pin 1 | Label `VCC_12V` | — | Output cap |
| C2 pin 2 | GND symbol | GND | |
| C5 pin 1 | U1 VCC pin | — | Decoupling |
| C5 pin 2 | GND symbol | GND | |

### Wiring Instructions — Buck Converter 2 (TPS5430, 12V→5V)

**U2 (TPS5430) key pins:** VIN, PH (switch node), VSENSE (FB), GND, BOOT
**D_BUCK2 (SS34):** Pin 1 = Anode, Pin 2 = Cathode

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `VCC_12V` | U2 VIN pin | — | Input from Buck 1 |
| U2 PH pin | L_BUCK2 pin 1 | — | Switch node through inductor |
| L_BUCK2 pin 2 | Label `VCC_5V` | VCC_5V | 5V regulated output |
| D_BUCK2 pin 1 | GND symbol | GND | Schottky anode |
| D_BUCK2 pin 2 | U2 PH pin | — | Schottky cathode → switch node |
| R_FB2A pin 1 | Label `VCC_5V` | — | Feedback top |
| R_FB2A pin 2 | R_FB2B pin 1 | — | Feedback mid |
| R_FB2B pin 2 | GND symbol | GND | Feedback bottom |
| R_FB2A pin 2 (junction) | U2 VSENSE pin | — | Feedback to regulator |
| C3 pin 1 | Label `VCC_5V` | — | Output cap |
| C3 pin 2 | GND symbol | GND | |
| C6 pin 1 | U2 VIN pin | — | Decoupling |
| C6 pin 2 | GND symbol | GND | |

### Wiring Instructions — LDO (AMS1117, 5V→3.3V)

**U3 (AMS1117-3.3) pin map:** Pin 1 = GND/Adjust, Pin 2 = VOUT, Pin 3 = VIN

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `VCC_5V` | U3 pin 3 | — | VIN input from Buck 2 |
| U3 pin 2 | Label `VCC_3V3` | VCC_3V3 | VOUT 3.3V regulated |
| U3 pin 1 | GND symbol | GND | Ground |
| C4 pin 1 | Label `VCC_3V3` | — | Output cap |
| C4 pin 2 | GND symbol | GND | |
| C7 pin 1 | U3 pin 3 | — | Input decoupling |
| C7 pin 2 | GND symbol | GND | |
| C8 pin 1 | U3 pin 2 | — | Output decoupling |
| C8 pin 2 | GND symbol | GND | |

---

## 5. Product — STM32 MCU

**Sheet:** `STM32_MCU.kicad_sch`
**Page size:** A3

### Components

| Ref | Value | Description |
|-----|-------|-------------|
| U4 | STM32F405RGT6 | Main MCU (64-pin LQFP) |
| Y1 | 8MHz | HSE crystal oscillator |
| C9 | 22pF | Crystal load cap 1 |
| C10 | 22pF | Crystal load cap 2 |
| U_USB | CP2102N | USB-to-UART bridge |
| J_SWD | SWD Header | SWD debug connector (4-pin) |
| J_USB | USB-C | USB-C connector |
| R1 | 10k | BOOT0 pull-down |
| R2 | 10k | BOOT1 pull-down |
| R_I2C_SCL | 4.7k | I2C SCL pull-up to 3.3V |
| R_I2C_SDA | 4.7k | I2C SDA pull-up to 3.3V |
| C_VDD1 | 100nF | VDD decoupling #1 |
| C_VDD_BULK | 4.7uF | VDD bulk decoupling |
| C_VCAP1 | 1uF | VCAP1 filter |
| C_VCAP2 | 1uF | VCAP2 filter |
| C_NRST | 100nF | NRST filter cap |

### Wiring Instructions — Crystal

**Y1 (8MHz crystal):** Pin 1 = OSC_IN side, Pin 2 = OSC_OUT side

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Y1 pin 1 | U4 PH0 (OSC_IN) | — | HSE input |
| Y1 pin 2 | U4 PH1 (OSC_OUT) | — | HSE output |
| C9 pin 1 | Y1 pin 1 | — | Load cap to OSC_IN |
| C9 pin 2 | GND symbol | GND | |
| C10 pin 1 | Y1 pin 2 | — | Load cap to OSC_OUT |
| C10 pin 2 | GND symbol | GND | |

### Wiring Instructions — STM32 Pin Assignments

| STM32 Pin | Net Label | Direction | Destination |
|-----------|-----------|-----------|-------------|
| PA5 (SPI1_SCK) | `SPI1_SCK` | Output | → DRV8243 L/R, IMU (Drivers sheet) |
| PA6 (SPI1_MISO) | `SPI1_MISO` | Input | ← DRV8243 L/R, IMU |
| PA7 (SPI1_MOSI) | `SPI1_MOSI` | Output | → DRV8243 L/R, IMU |
| PB0 | `SPI1_CS_DRV_L` | Output | → DRV8243 Left chip select |
| PB1 | `SPI1_CS_DRV_R` | Output | → DRV8243 Right chip select |
| PB2 | `SPI1_CS_IMU` | Output | → ICM-42688-P chip select |
| PA11 (CAN1_RX) | `CAN1_RX` | Input | ← SN65HVD230 #1 (arm CAN) |
| PA12 (CAN1_TX) | `CAN1_TX` | Output | → SN65HVD230 #1 |
| PB5 (CAN2_TX) | `CAN2_TX` | Output | → SN65HVD230 #2 (sensor CAN) |
| PB6 (CAN2_RX) | `CAN2_RX` | Input | ← SN65HVD230 #2 |
| PA2 (USART2_TX) | `USART2_TX` | Output | → CP2102N RXD, Jetson (Connectors sheet) |
| PA3 (USART2_RX) | `USART2_RX` | Input | ← CP2102N TXD, Jetson |
| PB8 (I2C1_SCL) | `I2C1_SCL` | Bidir | ↔ INA226 monitors (Drivers sheet) |
| PB9 (I2C1_SDA) | `I2C1_SDA` | Bidir | ↔ INA226 monitors |
| PC0 (ENC_L_A) | `ENC_L_A` | Input | ← Left encoder A (Drivers sheet) |
| PC1 (ENC_L_B) | `ENC_L_B` | Input | ← Left encoder B |
| PC2 (ENC_R_A) | `ENC_R_A` | Input | ← Right encoder A |
| PC3 (ENC_R_B) | `ENC_R_B` | Input | ← Right encoder B |
| PA8 | `ESTOP_RELAY_CTRL` | Output | → Relay MOSFET gate (Power sheet) |

### Wiring Instructions — USB Bridge (CP2102N)

**U_USB (CP2102N) key pins:** Check symbol for exact pin #s — TXD, RXD, D+, D−, VDD, GND

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| U_USB TXD pin | Label `USART2_RX` | USART2_RX | CP2102N TX → STM32 RX |
| U_USB RXD pin | Label `USART2_TX` | USART2_TX | STM32 TX → CP2102N RX |
| U_USB D+ pin | J_USB pin 2 | — | USB data+ |
| U_USB D− pin | J_USB pin 3 | — | USB data− |
| U_USB VDD pin | +3.3V symbol | — | 3.3V power |
| U_USB GND pin | GND symbol | GND | |
| J_USB pin 1 | +5V symbol | — | USB VBUS 5V |
| J_USB pin 4 | GND symbol | GND | |

### Wiring Instructions — Decoupling & Boot

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| C_VDD1 pin 1 | +3.3V symbol | VCC_3V3 | Place close to U4 VDD pin |
| C_VDD1 pin 2 | GND symbol | GND | |
| C_VDD_BULK pin 1 | +3.3V symbol | VCC_3V3 | Bulk cap near MCU |
| C_VDD_BULK pin 2 | GND symbol | GND | |
| C_VCAP1 pin 1 | U4 VCAP1 pin | — | Internal regulator filter |
| C_VCAP1 pin 2 | GND symbol | GND | |
| C_VCAP2 pin 1 | U4 VCAP2 pin | — | Internal regulator filter |
| C_VCAP2 pin 2 | GND symbol | GND | |
| C_NRST pin 1 | U4 NRST pin | — | Reset filter |
| C_NRST pin 2 | GND symbol | GND | |
| R1 pin 1 | U4 BOOT0 pin | — | BOOT0 pull-down |
| R1 pin 2 | GND symbol | GND | Normal boot from flash |
| R2 pin 1 | U4 BOOT1 pin | — | BOOT1 pull-down |
| R2 pin 2 | GND symbol | GND | |
| R_I2C_SCL pin 1 | +3.3V symbol | — | I2C pull-up |
| R_I2C_SCL pin 2 | Label `I2C1_SCL` | I2C1_SCL | |
| R_I2C_SDA pin 1 | +3.3V symbol | — | I2C pull-up |
| R_I2C_SDA pin 2 | Label `I2C1_SDA` | I2C1_SDA | |

### SWD Debug Header

| J_SWD Pin | Wire To | Notes |
|-----------|---------|-------|
| Pin 1 | +3.3V symbol | Target voltage reference |
| Pin 2 | U4 PA13 pin | SWDIO debug data |
| Pin 3 | U4 PA14 pin | SWCLK debug clock |
| Pin 4 | GND symbol | Ground |

---

## 6. Product — Motor Drivers, CAN, IMU & Power Monitors

**Sheet:** `Drivers_CAN_IMU_Power.kicad_sch`
**Page size:** A3

### Components

| Ref | Value | Description |
|-----|-------|-------------|
| U5L | DRV8243SQDGQRQ1 | SPI-controlled H-bridge — Left motor |
| U5R | DRV8243SQDGQRQ1 | SPI-controlled H-bridge — Right motor |
| U6A | SN65HVD230DR | CAN transceiver #1 (arm bus) |
| U6S | SN65HVD230DR | CAN transceiver #2 (sensor bus) |
| U7 | ICM-42688-P | 6-axis IMU (SPI) |
| U8 | INA226AIDGST | Current/power monitor — Motor bus |
| U9 | INA226AIDGST | Current/power monitor — 12V compute |
| U10 | INA226AIDGST | Current/power monitor — 5V servo |
| J_CAN_ARM | CAN Arm | CAN bus connector to arm controller |
| J_MOTOR_L | Motor L | Left motor power connector (3-pin) |
| J_MOTOR_R | Motor R | Right motor power connector (3-pin) |
| J_ENC_L | Encoder L | Left encoder connector (4-pin) |
| J_ENC_R | Encoder R | Right encoder connector (4-pin) |
| C11L/C12L/C13L | Decoupling | DRV8243 Left bypass caps |
| C11R/C12R/C13R | Decoupling | DRV8243 Right bypass caps |
| TVS1L/TVS1R | SMBJ28A | TVS protection diodes |
| R3L/R3R | 10mΩ | Current sense resistors |
| R4A/R4S | 120Ω | CAN bus termination resistors |
| C14A/C14S | 100nF | CAN transceiver decoupling |
| R5 | 4.7k | IMU CS pull-up |
| C15/C16 | 100nF/1uF | IMU decoupling |
| R6/R7/R8 | 10mΩ | INA226 shunt resistors |
| C17/C18/C19 | 100nF | INA226 decoupling |

### Wiring Instructions — DRV8243 Left (U5L)

**U5L (DRV8243) pin names are on the symbol.** Use the pin names shown on the IC to find the correct pin #.

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `MOTOR_PWR_L` | U5L VM pin | MOTOR_PWR_L | Motor power input (24V) |
| Label `SPI1_SCK` | U5L SCLK pin | SPI1_SCK | SPI clock from STM32 |
| Label `SPI1_MOSI` | U5L SDI pin | SPI1_MOSI | SPI data in |
| Label `SPI1_MISO` | U5L SDO pin | SPI1_MISO | SPI data out |
| Label `SPI1_CS_DRV_L` | U5L nSCS pin | SPI1_CS_DRV_L | Chip select (active low) |
| U5L OUT1 pin | J_MOTOR_L pin 1 | — | Motor terminal 1 |
| U5L OUT2 pin | J_MOTOR_L pin 2 | — | Motor terminal 2 |
| J_MOTOR_L pin 3 | GND symbol | GND | Motor ground |
| C11L pin 1 | U5L DVDD pin | — | Digital decoupling |
| C11L pin 2 | GND symbol | GND | |
| C12L pin 1 | U5L VM pin | — | Motor supply decoupling |
| C12L pin 2 | GND symbol | GND | |
| C13L pin 1 | U5L AVDD pin | — | Analog decoupling |
| C13L pin 2 | GND symbol | GND | |
| TVS1L pin 1 | U5L VM pin | — | TVS anode to VM |
| TVS1L pin 2 | GND symbol | — | TVS cathode to GND |
| R3L pin 1 | U5L GND pin | — | Sense resistor (IC side) |
| R3L pin 2 | GND symbol | — | Sense resistor (ground side) |

### Wiring Instructions — DRV8243 Right (U5R)

*Same topology as U5L, substituting:*
- `MOTOR_PWR_R` for VM
- `SPI1_CS_DRV_R` for nSCS
- J_MOTOR_R for motor connector
- C11R/C12R/C13R, TVS1R, R3R for passives

### Wiring Instructions — CAN Transceivers

**U6A/U6S (SN65HVD230) pin names are on the symbol:** TXD, RXD, CANH, CANL, VCC, GND, Rs

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `CAN1_TX` | U6A TXD pin | CAN1_TX | From STM32 CAN1_TX |
| Label `CAN1_RX` | U6A RXD pin | CAN1_RX | To STM32 CAN1_RX |
| U6A CANH pin | Label `CAN_H_ARM` | CAN_H_ARM | CAN bus high |
| U6A CANL pin | Label `CAN_L_ARM` | CAN_L_ARM | CAN bus low |
| U6A VCC pin | +3.3V symbol | — | 3.3V power |
| U6A GND pin | GND symbol | GND | |
| R4A pin 1 | U6A CANH pin | — | 120Ω termination |
| R4A pin 2 | U6A CANL pin | — | |
| C14A pin 1 | U6A VCC pin | — | Decoupling |
| C14A pin 2 | GND symbol | GND | |
| Label `CAN_H_ARM` | J_CAN_ARM pin 1 | CAN_H_ARM | To arm CAN connector |
| Label `CAN_L_ARM` | J_CAN_ARM pin 2 | CAN_L_ARM | |
| J_CAN_ARM pin 3 | GND symbol | GND | CAN ground |
| Label `CAN2_TX` | U6S TXD pin | CAN2_TX | From STM32 CAN2_TX |
| Label `CAN2_RX` | U6S RXD pin | CAN2_RX | To STM32 CAN2_RX |
| *(U6S: same wiring as U6A — R4S for termination, C14S for decoupling)* | | | |

### Wiring Instructions — IMU (U7 ICM-42688-P)

**U7 (ICM-42688-P) pin names are on the symbol:** SCLK, SDI, SDO, nCS, VDD, VDDIO, GND

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `SPI1_SCK` | U7 SCLK pin | SPI1_SCK | SPI clock |
| Label `SPI1_MOSI` | U7 SDI pin | SPI1_MOSI | SPI data in |
| Label `SPI1_MISO` | U7 SDO pin | SPI1_MISO | SPI data out |
| Label `SPI1_CS_IMU` | U7 nCS pin | SPI1_CS_IMU | Chip select |
| U7 VDD pin | +3.3V symbol | — | Power |
| U7 GND pin | GND symbol | GND | |
| C15 pin 1 | U7 VDD pin | — | Decoupling |
| C15 pin 2 | GND symbol | GND | |
| C16 pin 1 | U7 VDDIO pin | — | IO voltage decoupling |
| C16 pin 2 | GND symbol | GND | |
| R5 pin 1 | +3.3V symbol | — | CS pull-up (deselect) |
| R5 pin 2 | U7 nCS pin | — | |

### Wiring Instructions — INA226 Power Monitors

**U8/U9/U10 (INA226) pin names on symbol:** IN+, IN−, VS, SCL, SDA, A0, A1, GND, ALERT

| Monitor | Shunt R | Decoupling C | Monitored Bus | I2C Addr | Measurement |
|---------|---------|-------------|---------------|----------|-------------|
| U8 | R6 (10mΩ) | C17 (100nF) | `VCC_25V` bus | A0=GND, A1=GND (0x40) | Motor bus current |
| U9 | R7 (10mΩ) | C18 (100nF) | `VCC_12V` bus | A0=VS, A1=GND (0x41) | Compute current |
| U10 | R8 (10mΩ) | C19 (100nF) | `VCC_5V` bus | A0=GND, A1=VS (0x44) | Servo current |

*For each INA226 (example using U8/R6/C17):*

| Wire From | Wire To | Notes |
|-----------|---------|-------|
| R6 pin 1 | Bus power in (high side) | Shunt in series with bus |
| R6 pin 2 | Bus power out (load side) | |
| U8 IN+ pin | R6 pin 1 | Sense high side |
| U8 IN− pin | R6 pin 2 | Sense low side |
| U8 VS pin | +3.3V symbol | Supply voltage |
| U8 SCL pin | Label `I2C1_SCL` | I2C clock |
| U8 SDA pin | Label `I2C1_SDA` | I2C data |
| U8 GND pin | GND symbol | |
| U8 ALERT pin | *(leave NC or add no-connect flag)* | Optional interrupt |
| C17 pin 1 | U8 VS pin | Decoupling |
| C17 pin 2 | GND symbol | |

### Wiring Instructions — Encoder Connectors

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| J_ENC_L pin 1 | +3.3V symbol | — | Encoder power (3.3V) |
| J_ENC_L pin 2 | GND symbol | GND | |
| J_ENC_L pin 3 | Label `ENC_L_A` | ENC_L_A | → STM32 encoder input |
| J_ENC_L pin 4 | Label `ENC_L_B` | ENC_L_B | |
| J_ENC_R pin 1 | +3.3V symbol | — | |
| J_ENC_R pin 2 | GND symbol | GND | |
| J_ENC_R pin 3 | Label `ENC_R_A` | ENC_R_A | |
| J_ENC_R pin 4 | Label `ENC_R_B` | ENC_R_B | |

---

## 7. Product — Connectors, LEDs, USB & Peripherals

**Sheet:** `Connectors_LED_USB.kicad_sch`
**Page size:** A3

### Components

| Ref | Value | Description |
|-----|-------|-------------|
| U11 | PT4115 | LED constant-current driver |
| L_LED | 22uH | LED driver inductor |
| D_LED | SS34 | LED driver diode |
| R9 | 470Ω | LED current set resistor |
| R10 | 0.1Ω | LED sense resistor |
| C20 | 100uF | LED driver cap |
| J_LED_WORK | Work Light | High-power work light connector |
| J_LED_STATUS | LED Status | RGB/status LED connector (3-pin) |
| J_JETSON | Jetson | Jetson communication connector (4-pin: TX, RX, VCC, GND) |
| J_LIDAR | LiDAR | RPLIDAR connector (4-pin: USB D+, D−, VCC, GND) |
| J_CAMERA | Camera | OAK-D Lite connector (2-pin: USB, GND) |
| J_BUMPER_FL | Bumper FL | Front-left bumper switch (2-pin) |
| J_BUMPER_FR | Bumper FR | Front-right bumper switch |
| J_BUMPER_RL | Bumper RL | Rear-left bumper switch |
| J_BUMPER_RR | Bumper RR | Rear-right bumper switch |

### Wiring Instructions — LED Driver (PT4115)

**U11 (PT4115) pin names on symbol:** VIN, SW, DIM, CSN, GND
**D_LED (SS34):** Pin 1 = Anode, Pin 2 = Cathode

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `VCC_12V` | L_LED pin 1 | VCC_12V | 12V input |
| L_LED pin 2 | U11 VIN pin | — | Through inductor |
| U11 SW pin | D_LED pin 2 | — | Switch node → diode cathode |
| D_LED pin 1 | GND symbol | GND | Diode anode to ground |
| U11 DIM pin | R9 pin 1 | — | Dimming/enable |
| R9 pin 2 | +5V symbol | — | Pull-up for always-on |
| U11 CSN pin | R10 pin 1 | — | Current sense |
| R10 pin 2 | GND symbol | GND | |
| U11 SW pin | J_LED_WORK pin 1 | — | LED anode (through inductor) |
| J_LED_WORK pin 2 | R10 pin 1 | — | LED cathode → sense R |
| C20 pin 1 | U11 VIN pin | — | Input filtering |
| C20 pin 2 | GND symbol | GND | |

### Wiring Instructions — Status LED

| Wire From | Wire To | Notes |
|-----------|---------|-------|
| J_LED_STATUS pin 1 | +5V symbol | LED power |
| J_LED_STATUS pin 2 | *(STM32 GPIO via net label)* | Control signal |
| J_LED_STATUS pin 3 | GND symbol | |

### Wiring Instructions — Communication Connectors

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| Label `USART2_TX` | J_JETSON pin 1 | USART2_TX | STM32 TX → Jetson RX |
| Label `USART2_RX` | J_JETSON pin 2 | USART2_RX | Jetson TX → STM32 RX |
| J_JETSON pin 3 | +5V symbol | — | Jetson power |
| J_JETSON pin 4 | GND symbol | GND | |
| J_LIDAR pin 1 | +5V symbol | — | RPLIDAR power |
| J_LIDAR pin 2 | GND symbol | GND | |
| J_LIDAR pin 3 | *(USB D+)* | — | USB data |
| J_LIDAR pin 4 | *(USB D−)* | — | USB data |
| J_CAMERA pin 1 | +5V symbol | — | OAK-D power (via USB) |
| J_CAMERA pin 2 | GND symbol | GND | |

### Wiring Instructions — Bumper Switches

| Wire From | Wire To | Net Name | Notes |
|-----------|---------|----------|-------|
| J_BUMPER_FL pin 1 | Label `BUMPER_FL` | BUMPER_FL | → STM32 GPIO (active low) |
| J_BUMPER_FL pin 2 | GND symbol | GND | Normally open switch |
| J_BUMPER_FR pin 1 | Label `BUMPER_FR` | BUMPER_FR | |
| J_BUMPER_FR pin 2 | GND symbol | GND | |
| J_BUMPER_RL pin 1 | Label `BUMPER_RL` | BUMPER_RL | |
| J_BUMPER_RL pin 2 | GND symbol | GND | |
| J_BUMPER_RR pin 1 | Label `BUMPER_RR` | BUMPER_RR | |
| J_BUMPER_RR pin 2 | GND symbol | GND | |

---

## 8. Cross-Sheet Net Label Reference

Labels with the same name across sheets are electrically connected in KiCad (within the same hierarchical project). Here's the complete cross-sheet net map:

### Prototype Cross-Sheet Nets

| Net Label | Sheet 1 (Source) | Sheet 2 (Destination) | Description |
|-----------|-----------------|----------------------|-------------|
| `VBAT_FUSED_1` | Power Distribution (F1 out) | Peripherals (MIC-711 power) | Compute power rail |
| `VBAT_FUSED_2` | Power Distribution (F2 out) | Teensy (MD10C L power) | Left motor driver power |
| `VBAT_FUSED_3` | Power Distribution (F3 out) | Peripherals (MIC-711/router) | Peripheral power rail |
| `VBAT_FUSED_4` | Power Distribution (F4 out) | Teensy (BTS7960 R power) | Right motor driver power |
| `GND` | All sheets | All sheets | Common ground |
| `V_SERVO` | Power Distribution (buck out) | — (stays on same sheet) | 6.8V servo bus |
| `SERVO_J1`–`SERVO_J6` | Teensy (MCU pins) | — (stays on same sheet) | Servo signal wires |
| `ENC_L_A/B`, `ENC_R_A/B` | Teensy (MCU pins ↔ motor connectors) | — | Encoder signals |
| `PWM_L`, `DIR_L` | Teensy (MCU pins ↔ MD10C) | — | Left motor control |
| `LPWM_R`, `RPWM_R` | Teensy (MCU pins ↔ BTS7960) | — | Right motor control |

### Product Cross-Sheet Nets

| Net Label | Sheets Connected | Description |
|-----------|-----------------|-------------|
| `VBAT` | Power Distribution | Raw battery voltage |
| `VCC_25V` | Power Dist → Drivers | Motor bus (post-fuse) |
| `VCC_12V` | Power Dist → Drivers, Connectors | 12V regulated rail |
| `VCC_5V` | Power Dist → Drivers, Connectors | 5V regulated rail |
| `VCC_3V3` | Power Dist → STM32, Drivers | 3.3V regulated rail |
| `GND` | All 4 sheets | Common ground |
| `SPI1_SCK` | STM32 → Drivers (DRV8243 L/R, IMU) | SPI clock bus |
| `SPI1_MOSI` | STM32 → Drivers | SPI data out |
| `SPI1_MISO` | STM32 ← Drivers | SPI data in |
| `SPI1_CS_DRV_L` | STM32 → Drivers (U5L) | Left driver select |
| `SPI1_CS_DRV_R` | STM32 → Drivers (U5R) | Right driver select |
| `SPI1_CS_IMU` | STM32 → Drivers (U7) | IMU select |
| `CAN1_TX` | STM32 → Drivers (U6A) | CAN1 transmit |
| `CAN1_RX` | STM32 ← Drivers (U6A) | CAN1 receive |
| `CAN2_TX` | STM32 → Drivers (U6S) | CAN2 transmit |
| `CAN2_RX` | STM32 ← Drivers (U6S) | CAN2 receive |
| `I2C1_SCL` | STM32 ↔ Drivers (INA226 ×3) | I2C clock |
| `I2C1_SDA` | STM32 ↔ Drivers (INA226 ×3) | I2C data |
| `USART2_TX` | STM32 → Connectors (Jetson) | UART transmit |
| `USART2_RX` | STM32 ← Connectors (Jetson) | UART receive |
| `ESTOP_RELAY_CTRL` | STM32 → Power Dist (relay circuit) | E-stop control GPIO |
| `ENC_L_A/B` | STM32 ← Drivers (encoder connectors) | Left encoder |
| `ENC_R_A/B` | STM32 ← Drivers (encoder connectors) | Right encoder |
| `BUMPER_FL/FR/RL/RR` | Connectors → (to STM32 via label) | Bumper switch inputs |
| `MOTOR_PWR_L` | Drivers (U5L VM) | Left motor power in |
| `MOTOR_PWR_R` | Drivers (U5R VM) | Right motor power in |
| `CAN_H_ARM` / `CAN_L_ARM` | Drivers (U6A ↔ J_CAN_ARM) | CAN differential pair |

---

## Quick Reference: KiCad Wiring Tips

1. **Start a wire:** Hover over a pin or label endpoint, press `W`
2. **End a wire:** Click on the destination pin or label
3. **Net labels auto-connect:** Two labels with the same name on the same sheet (or across hierarchical sub-sheets) are electrically connected — no wire needed between them
4. **Add a net label:** Press `L`, type the net name exactly as shown above
5. **Add a power symbol:** Press `P`, search for `+12V`, `GND`, `+3V3`, `+5V`, `PWR_FLAG`
6. **Run ERC:** After wiring, go to **Inspect → Electrical Rules Checker** to verify all connections
7. **Junction dots:** If a wire crosses another wire or T-connects, KiCad should auto-add a junction dot. If not, press `J` to manually add one
8. **No-connect flags:** For unused IC pins, press `Q` to add a no-connect flag (X symbol) to suppress ERC warnings

---

*Generated for RECLAIM — MSE 4499 Capstone, Western University*
*Last updated: 2026-04-11*
