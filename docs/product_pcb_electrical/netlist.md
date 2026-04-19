# RECLAIM Product PCB — Complete Netlist
**Date:** March 25, 2026
**Revision:** 1.0
**Format:** Human-readable per-net listing for schematic entry in KiCad / Flux

---

## Net Naming Conventions

| Net Name      | Voltage | Description                                          |
|---------------|---------|------------------------------------------------------|
| VBAT          | 25.6V   | Battery positive — split at source into two paths    |
| VBAT_MOTOR    | 25.6V   | Motor/arm path: VBAT → F1 → Relay K1 COM            |
| VBAT_COMPUTE  | 25.6V   | Compute path: VBAT → F4 → U1 buck (always on)       |
| VBAT_COIL     | 25.6V   | Relay coil path: VBAT → F5 → SW1(mushroom) → Q1     |
| GND           | 0V      | Common ground                                        |
| VCC_25V       | 25.6V   | Post-relay motor bus (K1 NO contact output)          |
| VCC_12V       | 12V     | After 25V→12V buck (U1)                              |
| VCC_5V        | 5V      | After 12V→5V buck (U2)                               |
| VCC_3V3       | 3.3V    | After 5V→3.3V LDO (U3)                              |

### CRITICAL: Power Architecture Split

The VBAT line is split at the battery terminal into THREE independent paths:

1. **VBAT_MOTOR** → F1(30A) → Relay K1 COM → K1 NO → VCC_25V motor bus
   - Motors + arm only; cut by relay on software stop
2. **VBAT_COMPUTE** → F4(5A) → U1 25V→12V buck → always on
   - Jetson + STM32 + LiDAR; never cut by relay; powered at all times
3. **VBAT_COIL** → F5(2A) → SW1(mushroom NC) → Q1 Drain → K1 Coil → GND
   - Low-current coil circuit; mushroom opens this → relay de-energizes → motors cut

This solves the chicken-and-egg problem: the 12V compute rail comes from VBAT_COMPUTE
directly (pre-relay), so the STM32 and Q1 are powered before the relay closes.
The relay coil (24V Omron G5LE) is driven directly from VBAT_COIL (25.6V, within coil spec).

---

## Section 1 — Power Input & Distribution

### Net: VBAT
- J_BATTERY Pin 1 (battery positive terminal)
- F1 Pin 1 (30A motor/arm fuse input)
- F4 Pin 1 (5A compute fuse input) ← always-on compute path
- F5 Pin 1 (2A relay coil fuse input) ← always-on coil path

### Net: VBAT_MOTOR (post F1, pre-relay)
- F1 Pin 2
- K1 COM contact (relay input)

### Net: VBAT_COMPUTE (always on, post F4)
- F4 Pin 2
- U1 VIN (25V→12V buck for Jetson/LiDAR) ← compute always powered

### Net: VBAT_COIL (always on, post F5, through mushroom)
- F5 Pin 2
- SW1 Pin 1 (mushroom switch input — NC contact)
- SW1 Pin 2 → RELAY_COIL_IN

### Net: RELAY_COIL_IN (post mushroom, to Q1)
- SW1 Pin 2 (mushroom output)
- Q1 Drain (MOSFET pulls coil current to GND through coil)
- K1 Coil+ (relay coil positive terminal; 24V coil, powered from ~25.6V VBAT_COIL)
- D2 Cathode (flyback diode cathode)

### Net: VCC_25V (post-relay — motor bus, switched)
- K1 NO contact (Normally Open — CLOSES when relay energized = normal operation)
- F2L Pin 1 (15A left motor fuse input)
- F2R Pin 1 (15A right motor fuse input)
- F3 Pin 1 (10A arm fuse input)
- C1 Pin + (bulk cap positive)
- R6 Pin 1 (INA226 #1 shunt high side — 25V rail monitor)

**E-Stop Logic (CORRECTED):**
- Normal: PC8 HIGH → Q1 ON → coil energized → K1 NO closes → VCC_25V live → motors powered
- Software stop: PC8 LOW → Q1 OFF → coil de-energizes → NO opens → VCC_25V dead → motors cut
- Hardware E-stop: mushroom pressed → SW1 opens → coil loses power → NO opens → motors cut
- Fail-safe: any STM32 crash/power loss → Q1 OFF → relay drops → motors cut automatically

### Net: GND
- J_BATTERY Pin 2 (battery negative)
- K1 Coil− (relay coil return)
- D2 Anode (flyback diode anode)
- Q1 Source
- C1 Pin − through all bulk/decoupling caps
- U1, U2, U3 GND
- U4 VSS (all VSS pins), U4 VSSA
- U5L GND, U5R GND (all GND pins)
- U6A GND, U6S GND
- U7 GND
- U8 GND, U9 GND, U10 GND (INA226 ×3)
- U11 GND
- J_SWD Pin 4
- J_JETSON Pin 4
- J_LIDAR Pin 2
- J_CAN_ARM Pin 3
- J_MOTOR_L Pin 3, J_MOTOR_R Pin 3
- J_ENC_L Pin 4, J_ENC_R Pin 4
- J_LED_STATUS Pin 2
- J_BUMPER_FL/FR/RL/RR Pin 2
- All decoupling cap negative pins

### Net: MOTOR_PWR_L (left motor, post F2L)
- F2L Pin 2 (20A — updated from 15A for 42PG-775-92 motors, 5A rated / 24.5A stall, DRV8243 OCP handles stall)
- U5L VM (all VM pins)
- C12L Pin + (bulk cap)
- TVS1L Cathode

### Net: MOTOR_PWR_R (right motor, post F2R — SEPARATE from L)
- F2R Pin 2 (20A — updated from 15A for 42PG-775-92)
- U5R VM (all VM pins)
- C12R Pin +
- TVS1R Cathode

### Net: ARM_PWR (arm CAN power, post F3)
- F3 Pin 2
- J_CAN_ARM Pin 1 (optional power — CubeMars joints self-powered via separate harness)

### Net: VCC_12V
- U1 VOUT (25V→12V buck output — from always-on compute path)
- C2 Pin + (bulk cap)
- C5 Pin + (decoupling)
- U2 VIN (12V→5V buck)
- J_LIDAR Pin 1 (12V to Livox Mid-360, 8W)
- J_JETSON Pin 3 (12V to Jetson Orin NX, 25W)
- U11 VIN (PT4115 work light driver)
- R7 Pin 1 (INA226 #2 shunt high side)

### Net: VCC_12V_AFTER_SHUNT
- R7 Pin 2
- U9 IN+ (INA226 #2)

### Net: VCC_5V
- U2 VOUT
- C3 Pin +
- C6 Pin +
- U3 VIN (5V→3.3V LDO)
- J_LED_STATUS Pin 1 (5V to WS2812B ring)
- C20 Pin + (WS2812B bulk cap)
- J_CAMERA Pin 1 (5V USB power for OAK-D Pro)
- R8 Pin 1 (INA226 #3 shunt high side)

### Net: VCC_5V_AFTER_SHUNT
- R8 Pin 2
- U10 IN+ (INA226 #3)

### Net: VCC_3V3
- U3 VOUT
- C4 Pin +
- C7 Pin +
- U4 VDD (all 11 VDD pins — one 100nF cap each)
- U4 VDDA (analog supply)
- U4 VCAP1 → C_VCAP1 (1uF to GND) ← REQUIRED for internal regulator
- U4 VCAP2 → C_VCAP2 (1uF to GND) ← REQUIRED for internal regulator
- U5L VCC, U5R VCC (DRV8243 logic supply)
- U6A VCC, U6S VCC (CAN transceivers)
- U7 VDD, U7 VDDIO (ICM-42688-P)
- U8 VS, U9 VS, U10 VS (INA226 logic supply)
- J_SWD Pin 3 (ST-Link VCC reference)
- J_ENC_L Pin 3, J_ENC_R Pin 3 (encoder 3.3V supply)
- R_I2C_SCL Pin 1 (pull-up resistor to VCC_3V3)
- R_I2C_SDA Pin 1
- U9 A0 (INA226 #2 address pin 0 = HIGH = VCC_3V3 → addr 0x41)
- U10 A1 (INA226 #3 address pin 1 = HIGH = VCC_3V3 → addr 0x44)

---

## Section 2 — STM32F405 MCU Connections

### STM32 to SPI1 Bus (shared)
- Net: SPI1_SCK  → U4 PA5, U5L SCLK, U5R SCLK, U7 SCLK
- Net: SPI1_MISO → U4 PA6, U5L SDO, U5R SDO, U7 SDO
- Net: SPI1_MOSI → U4 PA7, U5L SDI, U5R SDI, U7 SDI
- Net: SPI1_CS_DRV_L → U4 PB0, U5L CS (active low)
- Net: SPI1_CS_DRV_R → U4 PB1, U5R CS (active low)
- Net: SPI1_CS_IMU   → U4 PB2, U7 CS (active low)

### STM32 to CAN Bus
- Net: CAN1_RX → U4 PB8, U6A RXD
- Net: CAN1_TX → U4 PB9, U6A TXD
- Net: CAN2_RX → U4 PB12, U6S RXD
- Net: CAN2_TX → U4 PB13, U6S TXD
- Net: CAN_H_ARM → U6A CANH, J_CAN_ARM Pin 1, R4A Pin 1
- Net: CAN_L_ARM → U6A CANL, J_CAN_ARM Pin 2, R4A Pin 2
- Net: CAN_H_SPARE → U6S CANH, R4S Pin 1 (loop back or expose on connector)
- Net: CAN_L_SPARE → U6S CANL, R4S Pin 2

### STM32 to USART2 (Jetson micro-ROS)
- Net: USART2_TX → U4 PA2, U_USB TX_IN (CP2102N)
- Net: USART2_RX → U4 PA3, U_USB RX_OUT
- Net: USB_D+ → U_USB D+, J3 D+
- Net: USB_D− → U_USB D−, J3 D−

### STM32 to Encoder Timers
- Net: ENC_L_A → U4 PA0 (TIM2_CH1), J_ENC_L Pin 1   ← TIM2 is 32-bit, better for high tick counts
- Net: ENC_L_B → U4 PA1 (TIM2_CH2), J_ENC_L Pin 2
- Net: ENC_R_A → U4 PB4 (TIM3_CH1), J_ENC_R Pin 1
- Net: ENC_R_B → U4 PB5 (TIM3_CH2), J_ENC_R Pin 2

### STM32 to I2C1 (INA226 power monitors)
- Net: I2C1_SCL → U4 PB6, U8 SCL, U9 SCL, U10 SCL, R_I2C_SCL Pin 2 (pull-up to VCC_3V3)
- Net: I2C1_SDA → U4 PB7, U8 SDA, U9 SDA, U10 SDA, R_I2C_SDA Pin 2 (pull-up to VCC_3V3)
Note: Both SCL and SDA need 4.7kΩ pull-ups to VCC_3V3 (R_I2C_SCL and R_I2C_SDA). Without these the I2C bus will not work.

### STM32 GPIO
- Net: WS2812_DATA → U4 PC6 (TIM8_CH1), R9 Pin 1
  - R9 Pin 2 → J_LED_STATUS Pin 3 (data to LED ring)
- Net: WORK_LIGHT_PWM → U4 PC7 (TIM8_CH2), U11 PWM_DIM (PT4115)
- Net: ESTOP_RELAY_CTRL → U4 PC8, R11 Pin 1
  - R11 Pin 2 → Q1 Gate
- Net: BUMPER_FL → U4 PC9 (internal pull-up), J_BUMPER_FL Pin 1
- Net: BUMPER_FR → U4 PC10, J_BUMPER_FR Pin 1
- Net: BUMPER_RL → U4 PC11, J_BUMPER_RL Pin 1
- Net: BUMPER_RR → U4 PC12, J_BUMPER_RR Pin 1

### STM32 SWD Debug
- Net: SWDIO → U4 PA13, J2 Pin 1, J_SWD Pin 1
- Net: SWDCK → U4 PA14, J2 Pin 2, J_SWD Pin 2
- Net: MCU_NRST → U4 NRST, R1 Pin 1, C (100nF to GND)
  - R1 Pin 2 → VCC_3V3

### STM32 VCAP (REQUIRED — internal voltage regulator)
- Net: VCAP1 → U4 VCAP1, C_VCAP1 Pin + (1uF to GND)
- Net: VCAP2 → U4 VCAP2, C_VCAP2 Pin + (1uF to GND)
NOTE: Without VCAP caps the STM32 will fail to start. These are mandatory per datasheet.

### STM32 NRST Filter
- Net: MCU_NRST → U4 NRST, R1 Pin 1, C_NRST Pin + (100nF to GND)
  - R1 Pin 2 → VCC_3V3

### STM32 BOOT0
- Net: BOOT0 → U4 BOOT0, R2 Pin 1
  - R2 Pin 2 → GND (normal boot; add 2-pin jumper header to allow DFU mode override)

---

## Section 3 — Motor Drivers (DRV8243)

### Left Motor Driver (U5L) — Full Net List
- U5L VM → MOTOR_PWR_L
- U5L VCC → VCC_3V3
- U5L GND → GND
- U5L SCLK → SPI1_SCK
- U5L SDI → SPI1_MOSI
- U5L SDO → SPI1_MISO
- U5L CS → SPI1_CS_DRV_L (PB0)
- U5L FAULTZ → Net: DRV_FAULT_L → U4 GPIO (choose free pin, e.g. PB14)
- U5L OUT1 → J_MOTOR_L Pin 1 (motor terminal A)
- U5L OUT2 → J_MOTOR_L Pin 2 (motor terminal B)
- U5L ISENSE → R3L Pin 1 (sense resistor)
  - R3L Pin 2 → GND (shunt to GND)
  - ISENSE net → U4 ADC input (e.g. PC0 = ADC10)

### Right Motor Driver (U5R) — Full Net List
- U5R VM → MOTOR_PWR_R
- U5R VCC → VCC_3V3
- U5R GND → GND
- U5R SCLK → SPI1_SCK
- U5R SDI → SPI1_MOSI
- U5R SDO → SPI1_MISO
- U5R CS → SPI1_CS_DRV_R (PB1)
- U5R FAULTZ → Net: DRV_FAULT_R → U4 GPIO (e.g. PB15)
- U5R OUT1 → J_MOTOR_R Pin 1
- U5R OUT2 → J_MOTOR_R Pin 2
- U5R ISENSE → R3R Pin 1
  - R3R Pin 2 → GND
  - ISENSE net → U4 ADC input (e.g. PC1 = ADC11)

### TVS Diode Connections
- TVS1L Anode → GND
- TVS1L Cathode → MOTOR_PWR_L (clamp at 28V)
- TVS1R Anode → GND
- TVS1R Cathode → MOTOR_PWR_R

---

## Section 4 — CAN Bus Interface

### Arm CAN (U6A)
- U6A VCC → VCC_3V3
- U6A GND → GND
- U6A TXD → CAN1_TX (PB9)
- U6A RXD → CAN1_RX (PB8)
- U6A CANH → CAN_H_ARM
- U6A CANL → CAN_L_ARM
- U6A RS → GND (high speed mode; RS pin must be tied to GND)
- C14A: VCC_3V3 to GND (decoupling, placed immediately at IC)

### Spare CAN (U6S)
- U6S VCC → VCC_3V3
- U6S GND → GND
- U6S TXD → CAN2_TX (PB13)
- U6S RXD → CAN2_RX (PB12)
- U6S CANH → CAN_H_SPARE
- U6S CANL → CAN_L_SPARE
- U6S RS → GND
- C14S: VCC_3V3 to GND

### Termination Resistors
- R4A: CAN_H_ARM to CAN_L_ARM (120Ω, board end termination)
- R4S: CAN_H_SPARE to CAN_L_SPARE (120Ω)

---

## Section 5 — IMU (ICM-42688-P)

- U7 VDD → VCC_3V3
- U7 GND → GND
- U7 VDDIO → VCC_3V3
- U7 SCLK → SPI1_SCK
- U7 SDI → SPI1_MOSI
- U7 SDO → SPI1_MISO
- U7 CS → SPI1_CS_IMU (PB2)
- U7 INT1 → R5 Pin 1 (DNP; optional interrupt)
  - R5 Pin 2 → VCC_3V3 (DNP)
- C15: VDD to GND (100nF, place <0.5mm from IC)
- C16: VDD to GND (1uF bulk)

---

## Section 6 — Power Monitoring (INA226 ×3)

### INA226 #1 — 25V Bus Monitor (U8, addr 0x40)
- U8 VBS → VCC_25V (before shunt, bus voltage reference)
- U8 IN+ → VCC_25V (shunt high side)
- U8 IN− → Net: VCC_25V_AFTER_SHUNT → R6 Pin 2 (shunt low side)
- R6 Pin 1 → VCC_25V
- U8 VS → VCC_3V3 (logic supply)
- U8 GND → GND
- U8 SCL → I2C1_SCL (PB6)
- U8 SDA → I2C1_SDA (PB7)
- U8 A0 → GND (addr bit 0 = 0)
- U8 A1 → GND (addr bit 1 = 0) → 0x40
- C17: VS to GND (decoupling)

### INA226 #2 — 12V Bus Monitor (U9, addr 0x41)
- U9 IN+ → VCC_12V (shunt high side)
- U9 IN− → VCC_12V_AFTER_SHUNT → downstream 12V loads
- R7: VCC_12V to VCC_12V_AFTER_SHUNT
- U9 VS → VCC_3V3
- U9 GND → GND
- U9 SCL → I2C1_SCL
- U9 SDA → I2C1_SDA
- U9 A0 → VCC_3V3 (addr bit 0 = 1)
- U9 A1 → GND (addr bit 1 = 0) → 0x41
- C18: VS to GND

### INA226 #3 — 5V Bus Monitor (U10, addr 0x44)
- U10 IN+ → VCC_5V (shunt high side)
- U10 IN− → VCC_5V_AFTER_SHUNT
- R8: VCC_5V to VCC_5V_AFTER_SHUNT
- U10 VS → VCC_3V3
- U10 GND → GND
- U10 SCL → I2C1_SCL
- U10 SDA → I2C1_SDA
- U10 A0 → GND (addr bit 0 = 0)
- U10 A1 → VCC_3V3 (addr bit 1 = 1) → 0x44
- C19: VS to GND

---

## Section 7 — Status LED & Work Light

### WS2812B LED Ring
- J_LED_STATUS Pin 1 → VCC_5V
- J_LED_STATUS Pin 2 → GND
- J_LED_STATUS Pin 3 (DATA) → R9 Pin 2
  - R9 Pin 1 → WS2812_DATA (PC6)
- C20: VCC_5V to GND (100uF, place near J_LED_STATUS)

### Work Light (Cree XHP35 via PT4115)
- U11 VIN → VCC_12V (PT4115 powered from 12V always-on compute rail)
- U11 GND → GND
- U11 SW → L_LED Pin 1 (switching node)   ← inductor renamed L_LED to avoid conflict with buck inductors
  - L_LED Pin 2 → J_LED_WORK Pin 1 (LED anode)
- D_LED Anode → GND
- D_LED Cathode → L_LED Pin 2 (freewheel diode on switching node output)
- J_LED_WORK Pin 2 (LED cathode) → R10 Pin 1 (current sense)
  - R10 Pin 2 → GND
- U11 CS → R10 Pin 1 (current sense feedback to PT4115)
- U11 DIM → WORK_LIGHT_PWM (PC7)

---

## Section 8 — Safety & E-Stop

### E-Stop Relay Circuit (CORRECTED — uses NO contact, fail-safe design)
- K1 COM → VBAT_MOTOR (post F1 motor fuse)
- K1 NO → VCC_25V (NO = Normally Open; CLOSES only when coil energized = motors powered)
- K1 Coil+ → RELAY_COIL_IN (comes from SW1 mushroom output)
- K1 Coil− → GND
- D2 Cathode → RELAY_COIL_IN (flyback: absorbs coil energy when Q1 turns off)
- D2 Anode → GND
- Q1 Drain → RELAY_COIL_IN (Q1 completes coil circuit to GND)
- Q1 Gate → R11 Pin 2 (R11 Pin 1 → ESTOP_RELAY_CTRL = PC8)
- Q1 Source → GND
- R12 Gate-to-GND pull-down (47kΩ): Q1 Gate to GND — ensures OFF at power-up before STM32 boots

### E-Stop Logic (FAIL-SAFE — power requires active energization)
- Power ON: PC8 HIGH → Q1 ON → K1 coil energized → NO closes → motors powered
- Software stop: PC8 LOW → Q1 OFF → coil lost → NO opens → motors cut
- Hardware E-stop: mushroom pressed → SW1 opens → coil current path broken → NO opens → cut
- STM32 crash or brown-out: PC8 floats/LOW → Q1 OFF → relay drops → motors cut (FAIL-SAFE)
- Battery disconnect: all rails lost → coil lost → motors cut

### Bumper Switches (NO microswitches — triggered = LOW)
- J_BUMPER_FL Pin 1 → BUMPER_FL → U4 PA0 ... wait, PA0 is ENC_L. Use PC9.
  - Correct: J_BUMPER_FL Pin 1 → BUMPER_FL → U4 PC9 (internal pull-up enabled in firmware)
- J_BUMPER_FL Pin 2 → GND
- J_BUMPER_FR → PC10, J_BUMPER_RL → PC11, J_BUMPER_RR → PC12
- In firmware: enable STM32 internal pull-ups on PC9-PC12. Normal = HIGH. Bumper hit = LOW (switch closes to GND)

### Bumper Switches
- J_BUMPER_FL Pin 1 → BUMPER_FL → U4 PC9 (with internal pull-up)
- J_BUMPER_FL Pin 2 → GND
- J_BUMPER_FR Pin 1 → BUMPER_FR → U4 PC10
- J_BUMPER_FR Pin 2 → GND
- J_BUMPER_RL Pin 1 → BUMPER_RL → U4 PC11
- J_BUMPER_RL Pin 2 → GND
- J_BUMPER_RR Pin 1 → BUMPER_RR → U4 PC12
- J_BUMPER_RR Pin 2 → GND

---

## Section 9 — External Connectors Summary

| Connector | Pin 1 | Pin 2 | Pin 3 | Pin 4 |
|-----------|-------|-------|-------|-------|
| J_BATTERY | VBAT+ | GND | - | - |
| J_JETSON | USART2_TX | USART2_RX | VCC_5V or VCC_12V | GND |
| J_LIDAR | VCC_12V | GND | ETH_TX+ | ETH_TX− |
| J_CAMERA | VCC_5V | GND | - | - |
| J_CAN_ARM | CAN_H_ARM | CAN_L_ARM | GND | - |
| J_MOTOR_L | OUT1_L | OUT2_L | GND | - |
| J_MOTOR_R | OUT1_R | OUT2_R | GND | - |
| J_ENC_L | ENC_L_A | ENC_L_B | VCC_3V3 | GND |
| J_ENC_R | ENC_R_A | ENC_R_B | VCC_3V3 | GND |
| J_LED_STATUS | VCC_5V | GND | WS2812_DATA | - |
| J_LED_WORK | LED_ANODE | LED_CATHODE | - | - |
| J_ESTOP | VBAT_IN | VBAT_SWITCHED | - | - |
| J_BUMPER_FL | BUMPER_FL | GND | - | - |
| J_BUMPER_FR | BUMPER_FR | GND | - | - |
| J_BUMPER_RL | BUMPER_RL | GND | - | - |
| J_BUMPER_RR | BUMPER_RR | GND | - | - |
| J_SWD | SWDIO | SWDCK | VCC_3V3 | GND |

---

## I2C Address Summary

| Device | A1 | A0 | Address |
|--------|----|----|---------|
| INA226 #1 (25V bus) | GND | GND | 0x40 |
| INA226 #2 (12V bus) | GND | VCC | 0x41 |
| INA226 #3 (5V bus) | VCC | GND | 0x44 |

---

## STM32F405 Pin Assignment Summary (LQFP-64)

| STM32 Pin | Net Name | Function | Direction |
|-----------|----------|----------|-----------|
| PA2 | USART2_TX | micro-ROS to Jetson | OUT |
| PA3 | USART2_RX | micro-ROS from Jetson | IN |
| PA5 | SPI1_SCK | Shared SPI clock | OUT |
| PA6 | SPI1_MISO | SPI data in | IN |
| PA7 | SPI1_MOSI | SPI data out | OUT |
| PA0 | ENC_L_A | Left encoder A (TIM2_CH1) — 32-bit timer | IN |
| PA1 | ENC_L_B | Left encoder B (TIM2_CH2) | IN |
| PA13 | SWDIO | SWD debug | IO |
| PA14 | SWDCK | SWD clock | IN |
| PB0 | SPI1_CS_DRV_L | DRV8243 Left chip select | OUT |
| PB1 | SPI1_CS_DRV_R | DRV8243 Right chip select | OUT |
| PB2 | SPI1_CS_IMU | ICM-42688-P chip select | OUT |
| PB4 | ENC_R_A | Right encoder A (TIM3_CH1) | IN |
| PB5 | ENC_R_B | Right encoder B (TIM3_CH2) | IN |
| PB6 | I2C1_SCL | INA226 clock | OUT |
| PB7 | I2C1_SDA | INA226 data | IO |
| PB8 | CAN1_RX | Arm CAN receive | IN |
| PB9 | CAN1_TX | Arm CAN transmit | OUT |
| PB12 | CAN2_RX | Spare CAN receive | IN |
| PB13 | CAN2_TX | Spare CAN transmit | OUT |
| PB14 | DRV_FAULT_L | DRV8243 Left fault (active low) | IN |
| PB15 | DRV_FAULT_R | DRV8243 Right fault (active low) | IN |
| PC0 | ADC_ISENSE_L | Left motor current sense (ADC10) | AIN |
| PC1 | ADC_ISENSE_R | Right motor current sense (ADC11) | AIN |
| PC6 | WS2812_DATA | LED ring data (TIM8_CH1 PWM) | OUT |
| PC7 | WORK_LIGHT_PWM | PT4115 dimming (TIM8_CH2 PWM) | OUT |
| PC8 | ESTOP_RELAY_CTRL | Relay control via MOSFET | OUT |
| PC9 | BUMPER_FL | Front-left bumper (pull-up) | IN |
| PC10 | BUMPER_FR | Front-right bumper (pull-up) | IN |
| PC11 | BUMPER_RL | Rear-left bumper (pull-up) | IN |
| PC12 | BUMPER_RR | Rear-right bumper (pull-up) | IN |

---

## Critical Layout Notes

1. **Motor current loop** — Place C12L/C12R (10uF VM bulk) and TVS1L/TVS1R within 5mm of U5L/U5R VM pins. Route VM → cap → TVS → motor output in a tight loop.

2. **IMU isolation** — Pour a ground island (solid copper) directly under U7 on Layer 2. Single via to main ground plane. Keep >5mm from motor driver switching nodes.

3. **Crystal guard** — No signal traces under Y1. Add a ground guard ring around crystal and load caps C9/C10.

4. **CAN differential pair** — Route CAN_H and CAN_L as a matched-length differential pair. Aim for 120Ω differential impedance (use 0.2mm trace, 0.2mm gap on 4-layer). Equal length to within 0.5mm.

5. **Decoupling placement** — All 100nF decoupling caps must be within 1mm of the IC supply pin they decouple. STM32 has 11 VDD pins — each needs its own 100nF cap.

6. **Ground copper pour** — Fill all unused space on all layers with GND copper. Stitch vias every 5mm between layers.

7. **Power trace widths** (IPC-2221 for 25°C rise):
   - VBAT / VCC_25V motor branch: min 4mm (carries up to 15A motors + 10A arm)
   - VCC_12V: min 2mm (10A max)
   - VCC_5V: min 1mm (3A max)
   - VCC_3V3: min 0.5mm (500mA max)
   - Signal traces: 0.2mm minimum

8. **E-stop relay** — Keep K1 away from MCU and IMU. Relay switching creates magnetic field. Minimum 20mm clearance from U4 and U7.

9. **Connector placement** — All external connectors on PCB perimeter. Battery connector top-edge center. Motor connectors bottom. CAN arm connector side-edge.

10. **Thermal** — U1 and U2 bucks need thermal vias under exposed pad to inner copper pour. PT4115 U11 similarly needs thermal relief (but Cree LED is off-board on chassis).
