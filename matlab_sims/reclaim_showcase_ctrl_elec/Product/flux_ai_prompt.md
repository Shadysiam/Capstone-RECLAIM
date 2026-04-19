# Flux AI Prompt — RECLAIM Product PCB

---

## PHASE 1 — SCHEMATIC

### Step 1: Create a New Project in Flux
1. Go to flux.ai → New Project
2. Name it: **RECLAIM-CTRL-R1**
3. Select **4-layer board** when prompted

### Step 2: Import the BOM first
1. File → Import BOM → CSV → select `docs/product_pcb_electrical/bom.csv`
2. Map: Reference → Reference, Value → Value, Footprint → Footprint, MPN → MPN
3. This pre-loads all 60+ components with correct footprints and MPNs so Flux can find them in its library

### Step 3: Paste the schematic prompt below into Flux AI chat

---

## FLUX AI SCHEMATIC PROMPT

```
I need you to generate a complete multi-sheet schematic for a 4-layer robotics controller PCB called RECLAIM-CTRL-R1. All components are already imported from the BOM. Use the net names and connections exactly as specified below. Do not rename nets.

SCHEMATIC ORGANIZATION — use 6 sheets:
- Sheet 1: Power Input, Distribution & E-Stop (Sections 1 + 8)
- Sheet 2: STM32F405 MCU (Section 2)
- Sheet 3: Motor Drivers DRV8243 ×2 (Section 3)
- Sheet 4: CAN Bus + IMU (Sections 4 + 5)
- Sheet 5: Power Monitoring INA226 ×3 (Section 6)
- Sheet 6: LEDs, Work Light & External Connectors (Sections 7 + 9)

Use hierarchical sheet symbols to link sheets. Use net labels (not wire buses) to connect signals across sheets.

---

SHEET 1 — POWER INPUT, DISTRIBUTION & E-STOP

Power architecture — VBAT splits into THREE independent paths at the battery terminal:

PATH 1 — Motor/Arm (relay-switched):
  J_BATTERY Pin1 → VBAT → F1(30A) → VBAT_MOTOR → K1 COM contact
  K1 NO contact → VCC_25V
  VCC_25V → F2L(15A) → MOTOR_PWR_L
  VCC_25V → F2R(15A) → MOTOR_PWR_R
  VCC_25V → F3(10A) → ARM_PWR → J_CAN_ARM Pin1
  VCC_25V → C1(470uF 50V bulk cap, + to VCC_25V, − to GND)
  VCC_25V → R6 Pin1 (INA226 shunt)

PATH 2 — Compute (always on, pre-relay):
  J_BATTERY Pin1 → VBAT → F4(5A) → VBAT_COMPUTE → U1 VIN (25V→12V buck)

PATH 3 — Relay Coil (always on):
  J_BATTERY Pin1 → VBAT → F5(2A) → VBAT_COIL → SW1 Pin1
  SW1 Pin2 → RELAY_COIL_IN → K1 Coil+
  K1 Coil+ → D2 Cathode (flyback diode)
  K1 Coil− → GND
  D2 Anode → GND
  RELAY_COIL_IN → Q1 Drain
  Q1 Source → GND
  Q1 Gate → R11 Pin2 (R11=1k)
  R11 Pin1 → ESTOP_RELAY_CTRL (net label, comes from STM32 PC8 on Sheet 2)
  Q1 Gate → R12 Pin1 (R12=47k pull-down)
  R12 Pin2 → GND

GND rail:
  J_BATTERY Pin2 → GND power symbol (place at battery connector and on every GND pin across all components)

Power rails — buck converter chain (always-on compute path):
  U1 VIN → VBAT_COMPUTE
  U1 VOUT → VCC_12V
  U1 FB → R_FB1A Pin1; R_FB1A Pin2 → VCC_12V; R_FB1A Pin1 → R_FB1B Pin1; R_FB1B Pin2 → GND
  (Sets Vout = 12V: R_FB1A=40.2k, R_FB1B=3.24k)
  U1 GND → GND
  L_BUCK1 between U1 SW node and VCC_12V (22uH)
  D_BUCK1 Anode → GND, Cathode → VCC_12V
  C2(470uF 25V) bulk cap: VCC_12V to GND
  C5(100nF) decoupling: VCC_12V to GND (within 1mm of U1 VCC pin)
  C8(10uF) bootstrap/soft-start cap per LM5116 datasheet

  U2 VIN → VCC_12V
  U2 VOUT → VCC_5V
  U2 FB → R_FB2A Pin1; R_FB2A Pin2 → VCC_5V; R_FB2A Pin1 → R_FB2B Pin1; R_FB2B Pin2 → GND
  (Sets Vout = 5V: R_FB2A=53.6k, R_FB2B=15k)
  U2 GND → GND
  L_BUCK2 between U2 SW and VCC_5V (22uH)
  D_BUCK2 Anode → GND, Cathode → VCC_5V
  C3(470uF 16V) bulk: VCC_5V to GND
  C6(100nF) decoupling: VCC_5V to GND

  U3 VIN → VCC_5V
  U3 VOUT → VCC_3V3
  U3 GND → GND
  C4(470uF 10V) bulk: VCC_3V3 to GND
  C7(100nF) decoupling: VCC_3V3 to GND

Add PWR_FLAG symbols on: VBAT, VCC_25V, VCC_12V, VCC_5V, VCC_3V3, GND (suppresses ERC warnings)

---

SHEET 2 — STM32F405 MCU

Place U4 (STM32F405RGT6 LQFP-64) centrally. Connect all pins as follows.

POWER PINS (all must be connected — do not leave floating):
  All 11 VDD pins → VCC_3V3, each with its own 100nF decoupling cap (C_VDD1×11) within 1mm
  VDDA → VCC_3V3 with 100nF + 1uF decoupling
  VDD_bulk → VCC_3V3 with C_VDD_BULK (4.7uF)
  VCAP1 → C_VCAP1 (1uF) → GND   ← CRITICAL — internal regulator
  VCAP2 → C_VCAP2 (1uF) → GND   ← CRITICAL — internal regulator
  All VSS pins → GND
  VSSA → GND

NRST:
  NRST → R1 Pin1 (R1=10k); R1 Pin2 → VCC_3V3
  NRST → C_NRST (100nF) → GND

BOOT0:
  BOOT0 → R2 Pin1 (R2=10k); R2 Pin2 → GND
  (Add 2-pin header footprint in parallel with R2 to allow DFU mode override)

SWD:
  PA13 → SWDIO → J_SWD Pin1
  PA14 → SWDCK → J_SWD Pin2
  J_SWD Pin3 → VCC_3V3
  J_SWD Pin4 → GND

CRYSTAL:
  PA8/OSC_IN → Y1 Pin1; Y1 Pin2 → PA9/OSC_OUT
  Y1 Pin1 → C9 (22pF) → GND
  Y1 Pin2 → C10 (22pF) → GND

SPI1 BUS (shared — use net labels):
  PA5 → SPI1_SCK
  PA6 → SPI1_MISO
  PA7 → SPI1_MOSI
  PB0 → SPI1_CS_DRV_L
  PB1 → SPI1_CS_DRV_R
  PB2 → SPI1_CS_IMU

CAN BUS:
  PB8 → CAN1_RX
  PB9 → CAN1_TX
  PB12 → CAN2_RX
  PB13 → CAN2_TX

USART2:
  PA2 → USART2_TX → U_USB TX_IN (CP2102N, same sheet or Sheet 6)
  PA3 → USART2_RX → U_USB RX_OUT

ENCODER TIMERS:
  PA0 (TIM2_CH1) → ENC_L_A
  PA1 (TIM2_CH2) → ENC_L_B
  PB4 (TIM3_CH1) → ENC_R_A
  PB5 (TIM3_CH2) → ENC_R_B

I2C1:
  PB6 → I2C1_SCL → R_I2C_SCL Pin2; R_I2C_SCL Pin1 → VCC_3V3 (4.7k pull-up)
  PB7 → I2C1_SDA → R_I2C_SDA Pin2; R_I2C_SDA Pin1 → VCC_3V3 (4.7k pull-up)

ADC (motor current sense):
  PC0 (ADC10) → ADC_ISENSE_L
  PC1 (ADC11) → ADC_ISENSE_R

GPIO:
  PC6 (TIM8_CH1) → WS2812_DATA → R9 Pin1; R9 Pin2 → J_LED_STATUS Pin3
  PC7 (TIM8_CH2) → WORK_LIGHT_PWM
  PC8 → ESTOP_RELAY_CTRL (net label — goes to R11 on Sheet 1)
  PC9 → BUMPER_FL (internal pull-up note in comment)
  PC10 → BUMPER_FR
  PC11 → BUMPER_RL
  PC12 → BUMPER_RR
  PB14 → DRV_FAULT_L (active low input from motor driver)
  PB15 → DRV_FAULT_R

---

SHEET 3 — MOTOR DRIVERS DRV8243 ×2

Place U5L and U5R side by side (mirror layout for left/right symmetry).

LEFT DRIVER (U5L):
  VM (all VM pins) → MOTOR_PWR_L
  VCC → VCC_3V3
  GND → GND
  SCLK → SPI1_SCK
  SDI → SPI1_MOSI
  SDO → SPI1_MISO
  CS → SPI1_CS_DRV_L
  FAULTZ → DRV_FAULT_L (net label back to STM32 PB14)
  OUT1 → J_MOTOR_L Pin1
  OUT2 → J_MOTOR_L Pin2
  J_MOTOR_L Pin3 → GND
  ISENSE → ADC_ISENSE_L; ISENSE → R3L Pin1; R3L Pin2 → GND
  VM bulk: C12L (10uF 50V, 1210) between MOTOR_PWR_L and GND — place within 5mm of VM pin
  VM decoupling: C13L (100nF) between MOTOR_PWR_L and GND
  VCC decoupling: C11L (100nF) between VCC_3V3 and GND — within 1mm of VCC pin
  TVS1L Cathode → MOTOR_PWR_L; TVS1L Anode → GND

RIGHT DRIVER (U5R): identical to U5L but:
  VM → MOTOR_PWR_R (separate net)
  CS → SPI1_CS_DRV_R
  FAULTZ → DRV_FAULT_R (PB15)
  OUT1/OUT2 → J_MOTOR_R
  ISENSE → ADC_ISENSE_R; R3R to GND
  C12R, C13R, C11R, TVS1R (same values, separate net)

---

SHEET 4 — CAN BUS + IMU

CAN ARM TRANSCEIVER (U6A — SN65HVD230):
  VCC → VCC_3V3
  GND → GND
  TXD → CAN1_TX (PB9)
  RXD → CAN1_RX (PB8)
  CANH → CAN_H_ARM
  CANL → CAN_L_ARM
  RS → GND (high-speed mode — MUST be tied to GND)
  C14A (100nF): VCC_3V3 to GND immediately at U6A VCC pin
  CAN_H_ARM → J_CAN_ARM Pin1
  CAN_L_ARM → J_CAN_ARM Pin2
  J_CAN_ARM Pin3 → GND
  R4A (120Ω) between CAN_H_ARM and CAN_L_ARM (board-end termination)

CAN SPARE TRANSCEIVER (U6S — SN65HVD230):
  VCC → VCC_3V3; GND → GND; RS → GND
  TXD → CAN2_TX (PB13); RXD → CAN2_RX (PB12)
  CANH → CAN_H_SPARE; CANL → CAN_L_SPARE
  C14S (100nF) decoupling
  R4S (120Ω) between CAN_H_SPARE and CAN_L_SPARE

IMU (U7 — ICM-42688-P LGA-14):
  VDD → VCC_3V3
  VDDIO → VCC_3V3
  GND → GND
  SCLK → SPI1_SCK
  SDI → SPI1_MOSI
  SDO → SPI1_MISO
  CS → SPI1_CS_IMU (PB2)
  INT1 → R5 Pin1 (DNP 4.7k); R5 Pin2 → VCC_3V3 (DNP — mark as Do Not Populate)
  C15 (100nF): VDD to GND — label "place within 0.5mm of IC"
  C16 (1uF): VDD to GND (bulk)

---

SHEET 5 — POWER MONITORING INA226 ×3

All three INA226 share the I2C bus (I2C1_SCL, I2C1_SDA net labels from Sheet 2).

INA226 #1 — 25V Bus Monitor (U8, addr 0x40):
  IN+ → VCC_25V (shunt high side)
  IN− → VCC_25V_AFTER_SHUNT
  R6 (10mΩ 2512) between VCC_25V and VCC_25V_AFTER_SHUNT
  VBS → VCC_25V (bus voltage sense — connect to high side of shunt)
  VS → VCC_3V3
  GND → GND
  SCL → I2C1_SCL
  SDA → I2C1_SDA
  A0 → GND (address 0x40)
  A1 → GND
  C17 (100nF): VS to GND

INA226 #2 — 12V Bus Monitor (U9, addr 0x41):
  IN+ → VCC_12V
  IN− → VCC_12V_AFTER_SHUNT
  R7 (10mΩ 2512) between VCC_12V and VCC_12V_AFTER_SHUNT
  VBS → VCC_12V
  VS → VCC_3V3; GND → GND
  SCL → I2C1_SCL; SDA → I2C1_SDA
  A0 → VCC_3V3 (address bit = 1)
  A1 → GND
  C18 (100nF): VS to GND

INA226 #3 — 5V Bus Monitor (U10, addr 0x44):
  IN+ → VCC_5V
  IN− → VCC_5V_AFTER_SHUNT
  R8 (10mΩ 2512) between VCC_5V and VCC_5V_AFTER_SHUNT
  VBS → VCC_5V
  VS → VCC_3V3; GND → GND
  SCL → I2C1_SCL; SDA → I2C1_SDA
  A0 → GND
  A1 → VCC_3V3 (address bit = 1)
  C19 (100nF): VS to GND

I2C address summary:
  U8: A1=GND, A0=GND → 0x40
  U9: A1=GND, A0=VCC → 0x41
  U10: A1=VCC, A0=GND → 0x44

---

SHEET 6 — LEDs, WORK LIGHT & CONNECTORS

WS2812B LED Ring:
  J_LED_STATUS Pin1 → VCC_5V
  J_LED_STATUS Pin2 → GND
  J_LED_STATUS Pin3 → R9 Pin2 (R9 Pin1 → WS2812_DATA net label from STM32)
  C20 (100uF, electrolytic) between VCC_5V and GND near J_LED_STATUS

PT4115 Work Light Driver (U11):
  VIN → VCC_12V
  GND → GND
  SW → L_LED Pin1 (22uH inductor switching node)
  L_LED Pin2 → J_LED_WORK Pin1 (LED anode +)
  D_LED Anode → GND; D_LED Cathode → L_LED Pin2 (freewheel diode)
  J_LED_WORK Pin2 → R10 Pin1 (0.1Ω 1206 — sets 1A output: Iout = 0.1/Rset)
  R10 Pin2 → GND
  CS → R10 Pin1 (current sense feedback)
  DIM → WORK_LIGHT_PWM (net label from STM32 PC7)

USB-C / CP2102N UART Bridge:
  J_USB (USB-C) D+ → U_USB D+
  J_USB D− → U_USB D−
  U_USB VBUS → VCC_5V (USB power from 5V rail)
  U_USB GND → GND
  U_USB TX → USART2_RX (PA3 on STM32) ← note: TX of CP2102 goes to RX of STM32
  U_USB RX → USART2_TX (PA2 on STM32)

External Connectors:
  J_JETSON Pin1 → USART2_TX; Pin2 → USART2_RX; Pin3 → VCC_5V (or VCC_12V per harness); Pin4 → GND
  J_LIDAR Pin1 → VCC_12V; Pin2 → GND; Pin3 → ETH_TX+; Pin4 → ETH_TX− (Ethernet magnetics separate)
  J_CAMERA Pin1 → VCC_5V; Pin2 → GND
  J_BUMPER_FL Pin1 → BUMPER_FL; Pin2 → GND
  J_BUMPER_FR Pin1 → BUMPER_FR; Pin2 → GND
  J_BUMPER_RL Pin1 → BUMPER_RL; Pin2 → GND
  J_BUMPER_RR Pin1 → BUMPER_RR; Pin2 → GND

---

SCHEMATIC STANDARDS:
- Use net labels (not long wires) to cross-connect signals between sheets
- Add value labels to all passive components (resistors show ohm value, caps show uF/nF + voltage rating)
- Add "DNP" text note next to R5 (ICM-42688 interrupt pull-up)
- Add a note near VCAP1/VCAP2 caps: "REQUIRED — do not omit — STM32 will not start"
- Add a note near R12 (47k gate pull-down): "Fail-safe: keeps Q1 OFF at power-up before STM32 boots"
- Title block: RECLAIM-CTRL-R1, Rev 1.0, 2026-03-25
- Power symbols: use standard VCC, GND, +3.3V, +5V, +12V symbols consistently
- After generating, run ERC. Expected to pass clean. If warnings about PWR_FLAG, add PWR_FLAG to each power net.
```

---

### Step 4: ERC Check — Before Going to PCB

After Flux generates the schematic, run **ERC (Electrical Rules Check)**:

**Must be zero errors before proceeding to PCB:**
- Unconnected pins
- Duplicate net names
- Short circuits between power rails

**Warnings you can ignore:**
- PWR_FLAG warnings — add PWR_FLAG symbols to VBAT, VCC_25V, VCC_12V, VCC_5V, VCC_3V3, GND
- R5 DNP warning (intentional)

**Manually verify these before approving the schematic:**
- [ ] VCAP1 and VCAP2 each have a 1uF cap to GND (STM32 will not start without these)
- [ ] All 11 STM32 VDD pins connected to VCC_3V3 with individual 100nF caps
- [ ] BOOT0 pulled to GND via R2 (10k)
- [ ] NRST has 100nF cap to GND and 10k pull-up
- [ ] Relay K1 uses NO contact (Normally Open) — not NC
- [ ] Q1 gate has both R11 (1k series) AND R12 (47k pull-down to GND)
- [ ] D2 flyback diode: Cathode to RELAY_COIL_IN, Anode to GND
- [ ] CAN transceiver RS pin tied to GND on both U6A and U6S
- [ ] INA226 addresses correct: U8=0x40, U9=0x41, U10=0x44
- [ ] R5 marked DNP on schematic

Once ERC is clean and checklist passes → proceed to PCB layout (Phase 2 prompt below).

---

## PHASE 2 — PCB LAYOUT & ROUTING

### Step 5: Create a New Project in Flux
1. Go to flux.ai → New Project
2. Name it: **RECLAIM-CTRL-R1**
3. Select **4-layer board** when prompted
4. Board size: start with 160mm × 120mm (adjust after placement)

---

### Step 2: Import the BOM
1. In Flux: **File → Import BOM → CSV**
2. Select: `docs/product_pcb_electrical/bom.csv`
3. Map columns: Reference → Reference, Value → Value, Footprint → Footprint, MPN → MPN
4. All 60 components will be imported with correct footprints and MPNs

---

### Step 3: Enter the Schematic

Use `docs/product_pcb_electrical/netlist.md` as your reference. Enter sections in this order:

**Order matters — start with power, then MCU, then peripherals:**
1. Power Input & Distribution (Section 1 of netlist)
2. E-Stop circuit (Section 8 of netlist) — shares relay K1 with Section 1
3. STM32F405 MCU (Section 2)
4. Motor Drivers DRV8243 ×2 (Section 3)
5. CAN Bus SN65HVD230 ×2 (Section 4)
6. IMU ICM-42688-P (Section 5)
7. Power Monitoring INA226 ×3 (Section 6)
8. LED & Work Light (Section 7)
9. External Connectors (Section 9)

---

### Step 4: Run ERC (Electrical Rules Check)
Before going to layout, run ERC in Flux and fix all errors.

**Expected warnings you can ignore:**
- PWR_FLAG warnings on power nets (add PWR_FLAG symbols to each rail to suppress)
- DNP component warnings (R5 is do-not-populate by design)

**Errors that must be fixed:**
- Any unconnected pin
- Any duplicate net name
- Short circuits between power rails

---

### Step 5: Give Flux AI This Prompt for PCB Layout

Copy and paste the following prompt into Flux AI when starting the auto-layout and auto-route:

---

## Flux AI Layout & Route Prompt

```
I have a 4-layer mixed-signal PCB for a robotics controller. Please lay out and route this board with the following constraints:

BOARD SPECIFICATIONS:
- Size: 160mm × 120mm (adjust if needed for component fit)
- Layer stack: Top = signal + components, Inner1 = solid GND plane (no splits), Inner2 = power planes (split zones), Bottom = signal + connectors
- The board must mount inside a robot chassis. All external connectors must be on the board perimeter.

COMPONENT PLACEMENT PRIORITIES (place in this order):

1. STM32F405RGT6 (U4) — center of board. This is the hub; everything routes from here.

2. DRV8243 motor drivers (U5L, U5R) — bottom half of board, left and right sides. Motor output connectors (J_MOTOR_L, J_MOTOR_R) must be on the bottom edge. Encoder connectors (J_ENC_L, J_ENC_R) adjacent to motor connectors.

3. ICM-42688-P IMU (U7) — near PCB center of mass, as close to U4 as SPI routing allows. Must be isolated from motor drivers (keep 10mm+ away from U5L/U5R switching nodes).

4. SN65HVD230 CAN transceivers (U6A, U6S) — right side of board, near CAN arm connector (J_CAN_ARM) on right edge.

5. INA226 power monitors (U8, U9, U10) — near their respective shunt resistors (R6, R7, R8) on the I2C bus. Group them together.

6. Relay K1 (Omron G5LE) — top-left corner of board. This is a large THT component. Keep 20mm+ away from U4 (STM32) and U7 (IMU) — relay magnetic field interferes.

7. Buck converters U1, U2 and LDO U3 — top-right quadrant. U1 and U2 need airflow — do not place under other components. Thermal vias under exposed pads.

8. PT4115 work light driver (U11), inductor L_LED, diode D_LED — small cluster, top area.

9. XT90 battery connector (J_BATTERY) — top edge center. This is the largest connector.

10. SWD debug header (J_SWD), USB-C (J_USB) — top edge, right of battery connector.

CONNECTOR PLACEMENT (all on board perimeter):
- Top edge: J_BATTERY (center), J_SWD, J_USB
- Bottom edge: J_MOTOR_L, J_MOTOR_R, J_ENC_L, J_ENC_R, J_LED_STATUS, J_LED_WORK
- Right edge: J_CAN_ARM, J_JETSON, J_LIDAR
- Left edge: J_BUMPER_FL, J_BUMPER_FR, J_BUMPER_RL, J_BUMPER_RR, J_CAMERA

CRITICAL ROUTING CONSTRAINTS — these override any auto-routing decisions:

1. MOTOR POWER TRACES (MOTOR_PWR_L, MOTOR_PWR_R, VCC_25V):
   - Minimum trace width: 4mm
   - Route as short as possible: fuse → DRV8243 VM pin → TVS diode → motor connector
   - Place 10uF VM bulk caps (C12L, C12R) within 5mm of VM pins — BEFORE routing these nets

2. BATTERY / VCC_25V MAIN TRACES:
   - Minimum trace width: 6mm for VBAT
   - 4mm for VCC_25V bus to fuses

3. VCC_12V / VCC_5V TRACES:
   - Minimum 2mm for VCC_12V
   - Minimum 1mm for VCC_5V

4. VCC_3V3 / SIGNAL TRACES:
   - 0.5mm for VCC_3V3 power distribution
   - 0.2mm minimum for all signal traces

5. CAN DIFFERENTIAL PAIR (CAN_H_ARM and CAN_L_ARM):
   - Route as a differential pair — both traces same width (0.2mm), same length, same spacing (0.2mm gap)
   - Match length to within 0.5mm end-to-end
   - Target 120Ω differential impedance
   - Do NOT route these near motor driver switching nodes or power traces
   - Keep pair together from U6A transceiver to J_CAN_ARM connector

6. IMU ISOLATION (U7 ICM-42688-P):
   - On Inner1 (GND layer), pour a dedicated ground island directly under U7
   - Connect this island to main GND with a single via — do not stitch it to the main pour
   - Keep all motor driver switching nodes (U5L SW pin, U5R SW pin) at least 10mm from U7

7. CRYSTAL (Y1):
   - No signal traces routed under the crystal body
   - Add a GND copper guard ring around Y1 and load caps C9, C10
   - Short as possible traces from Y1 to STM32 OSC_IN / OSC_OUT pins

8. DECOUPLING CAPACITORS:
   - All 100nF decoupling caps must be within 1mm of their IC supply pin
   - STM32 has 11 VDD pins — place one C_VDD cap per pin, each within 1mm
   - C_VCAP1 and C_VCAP2 must be placed within 2mm of VCAP1 and VCAP2 STM32 pins
   - DRV8243 VCC decoupling (C11L, C11R) within 1mm of VCC pin

9. RELAY CLEARANCE:
   - Keep K1 (Omron relay) at least 20mm from U4 (STM32) and U7 (IMU)
   - Route flyback diode D2 within 10mm of relay coil pins

10. POWER PLANE SPLITS (Inner2):
    - Zone 1: VCC_25V — motor driver area (bottom half)
    - Zone 2: VCC_12V — compute area (top-right)
    - Zone 3: VCC_5V — logic area (center)
    - Maintain 0.5mm clearance between zones at all split boundaries

11. THERMAL VIAS:
    - U1 (LM5116): place 9× thermal vias (3×3 grid) under exposed pad, connect to Inner2 VCC_12V plane
    - U2 (TPS5430): place 4× thermal vias under exposed pad
    - U3 (AMS1117): thermal tab is VCC_3V3, place 4× thermal vias

12. VIA SIZES:
    - Signal vias: 0.6mm drill, 1.0mm pad
    - Power vias (VCC_12V, VCC_5V): 1.2mm drill, 2.0mm pad
    - High-current vias (VBAT, VCC_25V): 1.5mm drill, 2.5mm pad

13. COPPER POUR:
    - GND pour on all 4 layers in all unused areas
    - Stitch GND pour vias every 5-8mm across the board
    - Do NOT pour VCC_25V in the signal area — keep to Inner2 zone only

GENERAL ROUTING RULES:
- No 90° trace corners — use 45° or curved
- No traces crossing the crystal guard ring
- SPI bus (SPI1_SCK/MISO/MOSI): keep traces as equal length as possible to U4 (within 5mm)
- All GND returns for high-current paths must use wide traces (not just via to ground plane)
- Power traces should avoid routing under/near the IMU and crystal

After routing, run DRC with these minimum rules:
- Min trace width: 0.2mm
- Min clearance: 0.2mm signal, 0.5mm power-to-signal
- Min via drill: 0.4mm
- Min via annular ring: 0.1mm
- Min copper-to-edge: 0.5mm
```

---

### Step 6: Manual Review Checklist After Flux AI Routes

Go through this list after the AI finishes — these are the things AI routers most often get wrong:

- [ ] VCAP1 and VCAP2 caps placed within 2mm of STM32 pins (critical for startup)
- [ ] All 11 STM32 VDD decoupling caps present and within 1mm of their VDD pin
- [ ] CAN_H and CAN_L routed as matched-length differential pair
- [ ] IMU ground island is isolated (single via to main GND, not stitched)
- [ ] Crystal has no traces underneath it
- [ ] Motor VM bulk caps (C12L, C12R) within 5mm of DRV8243 VM pins
- [ ] D2 flyback diode adjacent to relay coil pins
- [ ] R12 (Q1 gate pull-down) populated — prevents relay closing at power-up before STM32 boots
- [ ] VCC_25V and VBAT traces are 4mm+ width
- [ ] All bumper switch connectors on board edge (robot chassis clearance)
- [ ] XT90 battery connector on board edge with sufficient clearance for mating connector
- [ ] Thermal vias present under U1, U2, U3 exposed pads
- [ ] SWD header accessible (not blocked by other components — needed for programming)

---

### Step 7: Export for JLCPCB
1. Flux: **Export → Gerbers** — select JLCPCB preset
2. Export: Top copper, Bottom copper, Inner1 (GND), Inner2 (Power), Top Silkscreen, Bottom Silkscreen, Top Paste, Bottom Paste, Edge cuts, Drill file
3. Also export: **BOM + Pick-and-Place** for JLCPCB SMT assembly service
4. Zip all files → upload to jlcpcb.com
5. Select: 4-layer, 1.6mm thickness, HASL-lead-free, green solder mask
