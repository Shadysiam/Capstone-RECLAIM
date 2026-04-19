# IEEE Figure Captions — Design Documentation

Copy-paste these into the report. Number sequentially within each section.

---

## Prototype Schematics

**Fig. X.** Prototype power distribution schematic. LiFePO4 12.8 V 22 Ah battery feeds a DPST DC switch, 6-way fuse block (30 A, 5 A, 5 A, 2 A), and XINGYHENG 20 A buck converter (6.8 V output) supplying servo bus via Wago 221-415 lever-nut connectors.
`Prototype_Power_Distribution.pdf`

**Fig. X.** Prototype Teensy 4.1 motor-control schematic. Cytron MD13C R3 (left motor) and BTS7960 (right motor) H-bridge drivers interface with Teensy 4.1 via PWM/DIR signals. Six servo PWM outputs (J1–J6) and two quadrature encoder inputs (left/right) are routed through net labels.
`Prototype_Teensy_Motor_Control.pdf`

**Fig. X.** Prototype peripheral and sensor connections. Advantech MIC-711 (Jetson Orin NX) connects via Ethernet (GL.iNet router), USB 3.0 (OAK-D Lite stereo camera), and USB 2.0 (RPLIDAR A1M8, Teensy 4.1).
`Prototype_Peripherals_Sensors.pdf`

---

## Product Schematics

**Fig. X.** Product power distribution and E-stop schematic. 25.6 V 100 Ah LiFePO4 battery, DC push-switch, fuse block (30 A main, 5 A, 2 A), relay-based E-stop circuit with flyback diode, LM51652 buck controller (12 V output), and post-regulation LDO (3.3 V). Total budget: 2,560 Wh.
`Product_Power_Distribution.pdf`

**Fig. X.** Product STM32F405RGT6 MCU schematic. 8 MHz crystal oscillator (C8/C10 load caps), SPI bus (SCK, MOSI, MISO) with chip-select lines for DRV8243 and IMU, dual CAN bus (CAN1/CAN2), USART2, I2C1 (4.7 k pull-ups), and quadrature encoder inputs (ENC_L_A/B, ENC_R_A/B).
`Product_STM32_MCU.pdf`

**Fig. X.** Product motor driver, CAN transceiver, and IMU schematic. Dual DRV8243-Q1 smart half-bridge gate drivers, CAN transceiver, 6-axis IMU, and associated decoupling capacitor network. Fault and enable lines routed to STM32 GPIO via net labels.
`Product_Drivers_CAN_IMU_Power.pdf`

**Fig. X.** Product connector, LED indicator, and USB schematic. Board-edge connectors for motors, encoders, servos, and external sensors. Status LEDs, USB Type-C connector for programming/debug, and UART debug header.
`Product_Connectors_LED_USB.pdf`

---

## Simulink / Control System Figures

**Fig. X.** Simulink block diagram of the prototype PI closed-loop velocity controller. The discrete-time loop operates at 50 Hz on the Teensy 4.1 with gains K_p = 940 and K_i = 38,230, PWM saturation (−255 to 255), and a first-order DC motor plant model (JGB37-520). Encoder feedback provides 7,560 ticks/rev odometry.
`Simulink_Prototype_Controls.png`

**Fig. X.** PI velocity controller step and ramp response. (Left) Step response at 0.20 m/s showing 52 ms rise time and 176 ms settling time for the closed-loop system versus open-loop PWM. (Center) Approach speed comparison at 0.12 m/s and 0.20 m/s setpoints. (Right) Ramp limiter effect at 0.3 m/s^2 limiting acceleration to prevent wheel slip.
`Simulink_Motor_Response_Prototype.jpg`

**Fig. X.** Closed-loop frequency response (Bode magnitude plot) of the PI-controlled drive system. The −3 dB bandwidth is 6.2 Hz, confirming adequate disturbance rejection for indoor navigation at speeds up to 0.20 m/s.
`Simulink_Bode_Plot.png`

---

## Notes

- Replace "Fig. X." with the actual figure number in context (e.g., Fig. 8.3.1).
- All schematics are vector PDFs — scale without quality loss.
- Simulink images are raster PNG/JPG — embed at native resolution.
