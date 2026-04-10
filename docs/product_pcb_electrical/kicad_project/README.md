# RECLAIM PCB — KiCad Project

## Files in This Directory

| File | Purpose |
|------|---------|
| `RECLAIM_PCB/RECLAIM_PCB.kicad_pro` | KiCad project file (design rules, net classes, layer stack) |
| `RECLAIM_PCB/RECLAIM_PCB.kicad_sch` | Main schematic (all 9 sections, annotated) |
| `RECLAIM_PCB/fp-lib-table` | Footprint library table (maps to KiCad 7 standard libs) |
| `RECLAIM_PCB/sym-lib-table` | Symbol library table |
| `../bom.csv` | Complete BOM with MPN, footprint, value for every component |
| `../netlist.md` | Human-readable netlist — every pin-to-net connection |
| `../block_diagram.md` | System block diagrams (power + signal architecture) |
| `../component_justification.md` | Why each component was selected |

## How to Open in KiCad 7

1. Open KiCad 7 application
2. **File → Open Project** → select `RECLAIM_PCB/RECLAIM_PCB.kicad_pro`
3. In the KiCad project manager, open the schematic editor (`.kicad_sch`)

## How to Open in Flux (flux.ai)

1. Go to flux.ai → New Project
2. Import BOM: **File → Import → CSV BOM** → select `../bom.csv`
3. For the schematic, use `netlist.md` as a reference to draw connections

## Schematic Entry Order (recommended)

Start with the sections as they appear in `block_diagram.md`:

1. **Section 1 — Power Input & Distribution** ← START HERE
   - J_BATTERY, SW1, F1, K1, F2-F4
   - U1 (TPS5430 25V→12V), U2 (TPS5430 12V→5V), U3 (AMS1117 5V→3.3V)
   - Bulk caps C1-C4, decoupling C5-C8, buck inductors, freewheeling diodes

2. **Section 8 — E-Stop** ← Draw with Section 1 (shares relay K1)
   - Q1 (IRLZ44N), D2 (1N4007), R11 (1k gate resistor)
   - Bumper switch connectors J_BUMPER_FL/FR/RL/RR

3. **Section 2 — STM32F405 MCU**
   - U4 (STM32F405RGT6 LQFP-64)
   - Crystal Y1 + load caps C9/C10
   - Pull-up R1 (NRST), pull-down R2 (BOOT0)
   - SWD header J2, USB-C J3, CP2102N U_USB

4. **Section 3 — Motor Drivers**
   - U5L/U5R (DRV8243) × 2 identical sections
   - Sense resistors R3L/R3R, TVS diodes TVS1L/TVS1R
   - Motor output connectors J_MOTOR_L/R, encoder connectors J_ENC_L/R

5. **Section 4 — CAN Bus**
   - U6A/U6S (SN65HVD230) × 2
   - Termination R4A/R4S (120Ω)
   - CAN arm connector J_CAN_ARM

6. **Section 5 — IMU**
   - U7 (ICM-42688-P LGA-14)
   - Decoupling C15/C16

7. **Section 6 — Power Monitoring**
   - U8/U9/U10 (INA226) × 3
   - Shunt resistors R6/R7/R8 (10mΩ)
   - I2C address config via A0/A1 pins

8. **Section 7 — LED & Work Light**
   - WS2812B connector J_LED_STATUS, series R9, bulk C20
   - PT4115 U11, inductor L1, freewheeling D1, set resistor R10
   - Work light connector J_LED_WORK

## STM32F405 LQFP-64 Pin Assignment Quick Reference

Full table in `netlist.md`. Key assignments:
- PA2/PA3: USART2 TX/RX → Jetson micro-ROS
- PA5/6/7: SPI1 SCK/MISO/MOSI
- PA8/PA9: TIM1 encoder Left
- PB0/PB1/PB2: SPI CS for DRV_L, DRV_R, ICM
- PB4/PB5: TIM3 encoder Right
- PB6/PB7: I2C1 SCL/SDA → INA226×3
- PB8/PB9: CAN1 Arm bus
- PB12/PB13: CAN2 Spare
- PC6/PC7: TIM8 WS2812B / PT4115 PWM
- PC8: E-stop relay control
- PC9-PC12: Bumper switches

## Net Classes (already configured in .kicad_pro)

| Net Class | Track Width | Used For |
|-----------|------------|---------|
| Battery_Main | 6mm | VBAT, GND battery return |
| Power_25V_Motor | 4mm | VCC_25V, MOTOR_PWR_L/R |
| Power_5V_12V | 2mm | VCC_12V, VCC_5V |
| Default (3.3V + signal) | 0.25mm | VCC_3V3, all signals |
| CAN_Differential | 0.2mm | CAN_H/CAN_L pairs |

## PCB Layer Stack

```
Layer 1 (Top):     Signal + SMD components
Layer 2 (Inner 1): Ground plane — SOLID pour, no splits
Layer 3 (Inner 2): Power planes — split zones: 25V | 12V | 5V
Layer 4 (Bottom):  Signal + THT components + connectors
```

## DRC Rules Summary

- Min trace: 0.2mm signal / 2mm 5V-12V / 4mm 25V-motor / 6mm battery
- Min clearance: 0.2mm signal-to-signal / 0.5mm power-to-signal
- Via: 0.6mm drill / 1.0mm pad (signal) — 1.2mm drill / 2.0mm pad (power)
- Thermal relief: required on all power plane connections
- IMU: dedicated ground island, single via stitch
- Crystal: no traces underneath, ground guard ring
- CAN pairs: matched length to within 0.5mm, 120Ω differential impedance
