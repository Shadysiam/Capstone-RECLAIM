# RECLAIM Product — System Block Diagram
**Date:** March 25, 2026

---

## Power Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    25.6V LiFePO4 Battery (20Ah)                     │
│                         + BMS (30A)                                 │
└──────────────┬──────────────────────────────────────────────────────┘
               │ XT90 connector + antispark
               │
               ▼
    ┌──────────────────┐
    │  Latching E-STOP │──── Mushroom button (NC contact)
    │  + Power Relay   │
    └────────┬─────────┘
             │
    ┌────────▼──────────────────────────────────────────────────────┐
    │                    Main 25.6V Bus (fused)                      │
    └──┬──────────┬──────────────┬──────────────┬───────────────────┘
       │          │              │               │
       ▼          ▼              ▼               ▼
  [CubeMars   [DRV8243 L]  [DRV8243 R]    [25V→12V Buck]
   AK series   Drive Motor  Drive Motor     10A, 120W
   via CAN]    Left         Right           │
                                            ├──── Jetson Orin NX (12V, 25W)
                                            ├──── Livox Mid-360 (12V, 8W)
                                            │
                                        [12V→5V Buck]
                                            3A, 15W
                                            │
                                            ├──── USB Hub / Peripherals
                                            │
                                        [5V→3.3V LDO]
                                            500mA
                                            │
                                            ├──── STM32F405
                                            ├──── ICM-42688-P
                                            ├──── SN65HVD230 ×2
                                            └──── INA226 ×3
```

---

## Signal Architecture

```
                        ┌─────────────────────────────────┐
                        │         Jetson Orin NX           │
                        │  (ROS2 Humble, Nav2, YOLO)       │
                        └──────────────┬──────────────────┘
                                       │
                              micro-ROS over USB-UART
                                       │
                        ┌──────────────▼──────────────────────────────────┐
                        │              STM32F405RGT6                       │
                        │         (100Hz real-time control)                │
                        │                                                  │
                        │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────┐   │
                        │  │TIM2  │  │TIM3  │  │TIM1  │  │ CAN1/2   │   │
                        │  │Enc L │  │Enc R │  │Spare │  │ ARM bus  │   │
                        │  └──┬───┘  └──┬───┘  └──────┘  └────┬─────┘   │
                        │     │         │                       │         │
                        │  ┌──▼─────────▼──────┐    ┌──────────▼──────┐  │
                        │  │   SPI1 Bus        │    │  SN65HVD230     │  │
                        │  │ DRV8243L + DRV8243R│    │  CAN Transceiver│  │
                        │  │ ICM-42688-P (IMU) │    └──────────┬──────┘  │
                        │  └───────────────────┘               │         │
                        │                                  CAN_H/CAN_L   │
                        │  ┌──────────────────┐                │         │
                        │  │  UART1 / GPIO    │    ┌───────────▼──────┐  │
                        │  │  WS2812B LEDs    │    │  CubeMars Arm    │  │
                        │  │  PT4115 PWM dim  │    │  AK70-10 (J1)    │  │
                        │  │  Bumper switches │    │  AK80-9  (J2)    │  │
                        │  │  E-stop feedback │    │  AK60-6  (J3)    │  │
                        │  └──────────────────┘    │  AK10-9  (J4)    │  │
                        │                          │  AK10-9  (J5)    │  │
                        │  ┌──────────────────┐    │  XM430   (J6)    │  │
                        │  │  I2C1 Bus        │    └──────────────────┘  │
                        │  │  INA226 ×3       │                          │
                        │  │  (power monitor) │                          │
                        │  └──────────────────┘                          │
                        └────────────────────────────────────────────────┘

     ┌──────────┐        ┌──────────┐        ┌───────────┐
     │ OAK-D Pro│        │Livox     │        │ WS2812B   │
     │ (USB3.0) │        │Mid-360   │        │ LED Ring  │
     │ → Jetson │        │(Ethernet)│        │ (Status)  │
     └──────────┘        │→ Jetson  │        └───────────┘
                         └──────────┘
```

---

## PCB Schematic Sections

### Section 1 — Power Input & Distribution
```
Net list:
  VBAT         = 25.6V battery positive
  GND          = Common ground
  VCC_25V      = Post-relay main bus
  VCC_12V      = After 25V→12V buck
  VCC_5V       = After 12V→5V buck
  VCC_3V3      = After 5V→3.3V LDO

Components:
  J1           = XT90 battery connector (VBAT, GND)
  SW1          = E-stop mushroom (NC, in series with VBAT)
  K1           = Power relay (Omron G5LE, 16A, 12V coil)
  F1           = 30A main fuse (VBAT to relay)
  F2           = 15A motor fuse (VCC_25V to DRV8243)
  F3           = 10A arm fuse (VCC_25V to CAN arm connector)
  F4           = 5A compute fuse (VCC_25V to buck)
  U1           = 25V→12V buck (LM2596 or TPS5430, 10A)
  U2           = 12V→5V buck (TPS5430, 3A)
  U3           = 5V→3.3V LDO (AMS1117-3.3, 1A)
  C1-C4        = Bulk caps on each rail (470uF, 25V rated or higher)
  C5-C8        = Ceramic decoupling (100nF per IC)
```

### Section 2 — STM32F405 MCU
```
Net list:
  NRST         = Reset pin (100nF to GND)
  BOOT0        = Boot mode select (pull to GND for normal boot)
  PA0-PA15     = GPIO bank A
  PB0-PB15     = GPIO bank B
  PC0-PC15     = GPIO bank C

Key pin assignments:
  PA8          = TIM1_CH1 — Encoder L Ch A
  PA9          = TIM1_CH2 — Encoder L Ch B
  PB4          = TIM3_CH1 — Encoder R Ch A
  PB5          = TIM3_CH2 — Encoder R Ch B

  PA5          = SPI1_SCK  — shared SPI bus
  PA6          = SPI1_MISO
  PA7          = SPI1_MOSI
  PB0          = SPI1_CS1  — DRV8243 Left CS
  PB1          = SPI1_CS2  — DRV8243 Right CS
  PB2          = SPI1_CS3  — ICM-42688-P CS

  PB8          = CAN1_RX   — Arm CAN bus
  PB9          = CAN1_TX
  PB12         = CAN2_RX   — Spare CAN bus
  PB13         = CAN2_TX

  PA2          = USART2_TX — micro-ROS to Jetson
  PA3          = USART2_RX

  PC6          = TIM8_CH1  — WS2812B data
  PC7          = TIM8_CH2  — PT4115 PWM dim
  PC8          = GPIO OUT  — E-stop relay control
  PC9-PC12     = GPIO IN   — Bumper switches (×4, pull-up)

  PB6          = I2C1_SCL  — INA226 bus
  PB7          = I2C1_SDA

  PA13         = SWDIO     — Debug/programming
  PA14         = SWDCK
  NRST         = Reset

Components:
  U4           = STM32F405RGT6 (LQFP-64)
  Y1           = 8MHz crystal (main clock → PLL to 168MHz)
  C9-C10       = 22pF load caps for crystal
  R1           = 10k pull-up on NRST
  R2           = 10k pull-down on BOOT0
  J2           = SWD debug header (4-pin: SWDIO, SWDCK, VCC, GND)
  J3           = USB Type-C (USART2 bridge via CP2102N)
```

### Section 3 — Motor Drivers (DRV8243 ×2)
```
For each channel (Left and Right identical):

Net list:
  VM           = VCC_25V (motor power)
  VCC          = VCC_3V3 (logic power)
  SPI_CS       = Chip select from STM32
  SPI_SCLK     = SPI clock
  SPI_SDI      = SPI data in
  SPI_SDO      = SPI data out
  FAULTZ       = Fault output (active low, to STM32 GPIO)
  OUT1, OUT2   = H-bridge outputs to motor
  ISENSE       = Current sense output (to STM32 ADC)

Components:
  U5           = DRV8243HPWPRQ1 (PWP-17 package)
  R3           = 10mΩ current sense resistor (0.5W)
  C11          = 100nF VCC decoupling
  C12          = 10uF VM bulk cap
  C13          = 100nF VM decoupling
  TVS1         = SMBJ28A TVS diode (VM rail, clamp motor back-EMF)
  J4           = Motor output connector (3-pin: OUT1, OUT2, GND)
  J5           = Encoder connector (6-pin: A, B, VCC_3V3, GND, ×2)
```

### Section 4 — CAN Bus Interface
```
Two identical transceivers (Arm CAN + Spare):

Components:
  U6           = SN65HVD230DR (SO-8)
  R4           = 120Ω termination resistor (between CAN_H and CAN_L)
  C14          = 100nF decoupling on VCC pin
  J6           = CAN arm connector (3-pin: CAN_H, CAN_L, GND)
                 Daisy chained: J1→AK70-10→AK80-9→AK60-6→AK10-9→AK10-9→XM430
```

### Section 5 — IMU (ICM-42688-P)
```
Components:
  U7           = ICM-42688-P (LGA-14)
  C15          = 100nF decoupling
  C16          = 1uF bulk cap
  R5           = DNP (interrupt pull-up, optional)

Notes:
  - Mount as close to PCB center of mass as possible
  - Align chip X/Y axes with robot X/Y axes
  - Keep away from motor driver switching noise
  - Use ground plane pour directly under chip
```

### Section 6 — Power Monitoring (INA226 ×3)
```
One per rail: 25V bus, 12V bus, 5V bus

Components per channel:
  U8-U10       = INA226AIDGST (SOT-23-8)
  R6-R8        = 10mΩ shunt resistor (1%, 1W)
  C17-C19      = 100nF decoupling

I2C addresses:
  INA226 #1 (25V rail): A0=GND, A1=GND → addr 0x40
  INA226 #2 (12V rail): A0=VCC, A1=GND → addr 0x41
  INA226 #3 (5V rail):  A0=GND, A1=VCC → addr 0x44
```

### Section 7 — Status LED & Work Light
```
WS2812B LED Ring:
  R9           = 470Ω series resistor on data line (prevent reflections)
  C20          = 100uF across power pins (close to LED ring)
  J7           = 3-pin connector (5V, GND, DATA)
  PWR          = VCC_5V (WS2812B runs at 5V, data from 3.3V STM32 OK)

Work Light (Cree XHP35):
  U11          = PT4115 (constant current LED driver)
  R10          = 0.1Ω set resistor (sets current to ~1A = 350 lumens)
  L1           = 22uH inductor (PT4115 switching)
  D1           = SS34 Schottky diode (PT4115 freewheel)
  LED1         = Cree XHP35 (on thermal pad, bolt to chassis)
  J8           = 2-pin LED connector
  PWM input    = From STM32 PC7 (dimming)
```

### Section 8 — Safety & E-Stop
```
E-Stop circuit:
  SW1          = Latching mushroom (NC contacts, in VBAT line)
  K1           = Omron G5LE relay (16A, 12V coil)
  Q1           = IRLZ44N MOSFET (relay coil driver, from STM32 PC8)
  D2           = 1N4007 flyback diode across relay coil
  R11          = 1kΩ gate resistor for Q1

Bumper switches (×4):
  SW2-SW5      = Microswitch (NO, one per corner)
                 Connected to PC9-PC12 with internal pull-ups enabled
                 Any switch triggered → STM32 GPIO interrupt → E-stop

Logic:
  Normal:      STM32 PC8 HIGH → Q1 ON → Relay coil energized → K1 NC open
               (relay bypassed, power flows through NC contact of mushroom)

  E-stop hit:  Mushroom opens NC → power cut regardless of software
  Software stop: STM32 PC8 LOW → Q1 OFF → Relay de-energizes → motor power cut
```

### Section 9 — External Connectors
```
J_JETSON     = 4-pin (USB-C or UART: TX, RX, VCC_5V, GND)
J_LIDAR      = 3-pin (12V, GND, Ethernet via magnetics to RJ45)
J_CAMERA     = 2-pin (USB3.0 to Jetson directly, power only from PCB)
J_CAN_ARM    = 3-pin (CAN_H, CAN_L, GND) — to first CubeMars joint
J_MOTOR_L    = 3-pin (OUT1, OUT2, GND)
J_MOTOR_R    = 3-pin (OUT1, OUT2, GND)
J_ENC_L      = 6-pin (A, B, VCC, GND, ×2 for quadrature)
J_ENC_R      = 6-pin
J_LED_STATUS = 3-pin (5V, GND, DATA)
J_LED_WORK   = 2-pin (LED+, LED-)
J_ESTOP      = 2-pin (mushroom switch contacts)
J_BUMPER_FL  = 2-pin (front-left bumper)
J_BUMPER_FR  = 2-pin (front-right bumper)
J_BUMPER_RL  = 2-pin (rear-left bumper)
J_BUMPER_RR  = 2-pin (rear-right bumper)
J_SWD        = 4-pin (SWDIO, SWDCK, VCC, GND) — programming header
J_BATTERY    = XT90 (VBAT+, GND)
```

---

## PCB Layer Stack (4-layer recommended)
```
Layer 1 (Top):     Signal + components
Layer 2 (Inner 1): Ground plane (solid pour)
Layer 3 (Inner 2): Power planes (split: 25V zone, 12V zone, 5V zone)
Layer 4 (Bottom):  Signal + connectors
```

## PCB Design Rules
```
Min trace width:   0.2mm (signal), 2mm (5V/12V), 4mm (25V/motor), 6mm (battery)
Min clearance:     0.2mm (signal), 0.5mm (power to signal)
Via size:          0.6mm drill, 1.0mm pad (signal), 1.2mm drill, 2.0mm pad (power)
Thermal relief:    Required on all power plane connections
Copper pour:       Ground on all layers in unused areas
Motor driver:      Keep motor current loop tight (VM cap to IC to motor connector)
IMU:               Pour ground island under chip, single via to main ground
Crystal:           No traces under crystal, ground guard ring
CAN traces:        Differential pair, 120Ω impedance, equal length
```

---

## Next Steps
1. [ ] Create schematic in KiCad/Flux — start with power section
2. [ ] Assign footprints to all components
3. [ ] Define board outline (size TBD based on robot chassis)
4. [ ] Place components — MCU center, power edge, connectors perimeter
5. [ ] Route power planes first, then signals
6. [ ] DRC check
7. [ ] Gerber export → JLCPCB quote
