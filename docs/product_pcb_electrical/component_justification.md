# RECLAIM Product — Component Selection & Justification
**Date:** March 25, 2026
**Status:** Finalized for PCB design phase

---

## Why No PCB for the Prototype

The short answer: **you don't know what you don't know yet.**

When RECLAIM started, these were all unknowns:
- Whether the Cytron MD10C would be powerful enough or need replacing
- Whether Teensy 4.1 had enough pins and processing for both motors AND arm
- What voltage the servo rail needed (ended up being 6V, not 5V)
- How many Wago connectors would actually be needed
- Whether the LiDAR and camera would even work together on the same USB bus

Every one of those required a physical change — swapping a component, rewiring a rail, adding a connector. On a custom PCB, each of those changes is a new board spin ($150-500 and 2-3 weeks lead time). On a breadboard/module setup, it's 20 minutes with a screwdriver.

**Prototype philosophy:**
- Modules are expensive per-unit but cheap to replace and reconfigure
- Wiring is messy but infinitely flexible
- Fuse block is bulky but fuse ratings can change same day
- Teensy is $35 but if fried, plug in another one

**Things that actually changed mid-prototype:**
1. Motor driver choice (learned 3.3V logic compatibility requirement)
2. Power distribution (added 6V buck mid-project for servos)
3. Serial protocol tuning (discovered Teensy serial contention with odom + drive)
4. Encoder wiring (learned 3.3V vs 5V tolerance issue)
5. Arm servo selection (changed gripper to LewanSoul claw mid-project)

None of that is predictable upfront. A PCB at prototype stage would have meant 4-5 board respins.

## Why PCB is Right for the Product

**1. Size and weight** — Current power distribution takes ~30×20×10cm. Equivalent PCB: 15×10×2cm.

**2. Reliability** — Every Wago connector, JST crimp, and spade terminal is a potential failure point. PCB traces don't come loose. Soldered connections don't vibrate apart.

**3. Repeatability** — To build a second prototype robot today requires rewiring everything by hand. With a PCB, order 10 boards, populate them, done.

**4. Integration** — STM32 talks to DRV8243 via controlled-impedance SPI trace 2cm away. Lower noise, faster communication, no flying leads picking up motor EMI.

**5. Safety features** — Hardware overcurrent protection, reverse polarity protection, and E-stop logic can't easily be added to a module system. On a PCB these are designed in from day one.

**6. Cost at scale** — Cytron MD10C: $20×2 = $40. DRV8243 on PCB: $3×2 = $6. Every component is 5-10× cheaper without the module markup.

---

## Finalized Component List

| Subsystem | Component | Confirmed |
|-----------|-----------|-----------|
| Compute | Jetson Orin NX (reComputer J4012) | ✅ |
| MCU | STM32F405RGT6 | ✅ |
| Drive motors | Pololu 37D 12V 100:1 w/ 64CPR encoders | ✅ |
| Motor drivers | 2× DRV8243 (on PCB) | ✅ |
| Arm | CubeMars AK70-10, AK80-9, AK60-6, 2×AK10-9 | ✅ |
| Gripper | ROBOTIS XM430 | ✅ |
| Camera | OAK-D Pro (eye-in-hand) | ✅ |
| LiDAR | Livox Mid-360 3D LiDAR | ✅ |
| Battery | 25.6V 20Ah LiFePO4 | ✅ |
| Status light | WS2812B 16-LED ring | ✅ |
| Work light | Cree XHP35 + PT4115 driver | ✅ |
| IMU | ICM-42688-P (on PCB) | ✅ |
| CAN transceiver | SN65HVD230 (on PCB) | ✅ |
| E-stop | Latching mushroom + power relay | ✅ |
| Power monitoring | INA226 per rail | ✅ |
| Cliff detection | Under review — see notes | 🔄 |
| Bumper switches | 4× microswitch | ✅ |

---

## Component Justification

### MCU — STM32F405RGT6

**Why not keep Teensy 4.1?**
The Teensy is a hobbyist dev board. Problems for product:
- Dev board mounted on carrier — wasteful, second failure surface
- No hardware CAN bus — would need external MCP2515 SPI CAN controller
- USB connector only interface — fragile in vibration/EMI environments

**Why STM32F405 over other STM32s:**
- Cortex-M4 at 168MHz with FPU — handles 1kHz control loops comfortably
- Hardware CAN1 + CAN2 — two independent CAN buses for CubeMars + spare
- 3× hardware encoder timers (TIM1, TIM2, TIM3) — zero CPU overhead tick counting
- micro-ROS production-tested on STM32F4 — reference platform for micro-ROS team
- Same chip as Pixhawk v1/v2 — most battle-tested robotics controller ever built
- $5 in quantity vs $35 Teensy

**Why not STM32H743?** Overkill — F405 handles 100Hz loops with headroom. H743 adds complexity for no practical benefit here.

**Why not RP2040?** No hardware CAN. PIO is clever but a workaround for missing hardware.

### IMU — ICM-42688-P

**Why add an IMU at all?**
Prototype relies entirely on wheel encoders for odometry. Known failure modes:
- Wheel slip when starting/stopping
- Castor drag causing yaw drift (observed — why heading hold exists)
- Accumulated encoder error over long distances

IMU adds gyroscope yaw rate for sensor fusion — gyro sees instantaneous angular velocity with no slip, no tick accumulation. Critical for accurate 360° scans.

**Why ICM-42688-P specifically:**

| IMU | Gyro noise | ODR | Interface |
|-----|-----------|-----|-----------|
| MPU-6050 | 0.005°/s/√Hz | 1kHz | I2C only |
| LSM6DSO | 0.004°/s/√Hz | 6.6kHz | SPI/I2C |
| **ICM-42688-P** | **0.0028°/s/√Hz** | **32kHz** | **SPI** |

Lowest noise floor of any consumer MEMS IMU. Used in DJI flight controllers. Gyro noise directly translates to target position error during scans.

### Motor Drivers — DRV8243

**Why not keep Cytron MD10C?**
MD10C is a module with its own PCB, connectors, mounting — wasteful for product. More importantly:

| Feature | Cytron MD10C | DRV8243 on PCB |
|---------|-------------|----------------|
| Current sensing | None | Built-in (±5%) |
| Fault reporting | LED only | SPI register + fault pin |
| Thermal shutdown | Unknown | Yes, programmable |
| Overcurrent protection | External fuse only | Cycle-by-cycle limiting |
| Closed-loop torque | No (no current feedback) | Yes |
| Size | 55×37mm external | 5×6mm on PCB |
| Cost | $20 each | $3 each |

Current sensing enables: stall detection, torque-limited driving, surface estimation (carpet vs tile shows different motor current signatures).

**Why not DRV8874?** Only 6A continuous — borderline for Pololu 37D stall (~5A). DRV8243 is 8A continuous, 12A peak — proper headroom.

### Two Lights — Status vs Work

**Different purposes entirely:**

**Status light (WS2812B ring):**
- Tells the story of what robot is doing without reading a terminal
- Operators know at a glance if robot is working, stuck, or errored
- Safety signaling: solid red = hardware fault, don't approach
- One GPIO pin, no external driver
- Color scheme: Blue=SCAN, Yellow=APPROACH, Green=ALIGNED, Red=ERROR

**Work light (Cree XHP35 + PT4115):**
- OAK-D Pro needs adequate illumination for reliable YOLO detection
- Post-event venues can be dim (loading docks, large dark halls)
- 350 lumens aimed at floor 30° ahead — detection confidence improves significantly on dark objects
- PT4115 constant-current driver — brightness set by one resistor, MCU can PWM-dim for power saving
- Tested in prototype: detection confidence dropped ~15% in dim conditions

### CAN Bus — Why It's Right for CubeMars

**Protocol comparison:**

| Protocol | Update rate | Feedback | Wiring | Used by CubeMars |
|---------|-------------|---------|--------|-----------------|
| PWM (prototype) | 50Hz | None | 1 wire/joint | No |
| RS-485/Dynamixel | 57.6k-4Mbps | Yes | Daisy chain | No |
| EtherCAT | 100Mbps | Yes | Complex | No |
| **CAN bus** | **1Mbps** | **Yes** | **Daisy chain** | **Yes — native** |

CAN bus advantages:
- All 6 actuators on one twisted pair — daisy chained joint to joint
- Bidirectional: each actuator sends position, velocity, torque, temperature every cycle
- Error detection: CRC + acknowledgment + error counters built into protocol
- Electrically robust: differential signaling, immune to motor EMI
- At 1kHz per joint: 6 × 64bit × 1000 = 384kbps — well under 1Mbps limit

**CAN transceiver (SN65HVD230):** $0.80 IC that converts STM32's 3.3V CAN_TX/CAN_RX to differential CAN_H/CAN_L. Mandatory — handles bus termination, common-mode rejection, STM32 protection.

### Safety — Cliff Detection Discussion

**The case for cliff sensors (VL53L1X pointing down at robot edges):**
- Post-event venues can have stage drops, loading dock platforms, ramp edges
- Even with Nav2 + a map, if the robot drifts or the map is slightly wrong it could approach an edge
- Cliff sensors are a hardware failsafe independent of software

**The case against (for our specific use case):**
- Venues will be mapped before deployment — Nav2 will have known boundaries
- The Livox Mid-360 3D LiDAR already detects drops as geometry changes
- The robot operates at low speed (0.57 m/s) — stopping distance is short
- Adding 4× VL53L1X + routing adds PCB complexity for a low-probability scenario

**Can the OAK-D Pro handle this?**
Partially — the depth camera detects geometry changes ahead of the robot. But limitations:
- Eye-in-hand mount: camera moves with arm, FOV changes during picks
- Blind spot directly below and beside the robot
- Depth accuracy degrades at edges with low texture
- Already saturated processing YOLO at 30fps

**Decision:** Livox Mid-360 + Nav2 boundary enforcement is the primary cliff protection.
Add bumper switches as contact-level fallback. VL53L1X cliff sensors are optional —
add PCB footprints but don't populate initially. Validate in venue testing.

---

## Safety Architecture Summary

**Layer 1 — Mapping (Nav2):** Robot knows venue boundaries, won't plan paths near edges

**Layer 2 — LiDAR safety zones:**
- 0-0.5m: E-stop
- 0.5-1.5m: Slow to 0.1 m/s
- ISO 3691-4 compliant mobile robot behavior

**Layer 3 — Contact (bumper switches):** 4× microswitch bumpers → hardware interrupt to MCU → instant E-stop

**Layer 4 — Hardware E-stop:** Latching mushroom button → MOSFET cuts motor driver EN pins → independent of software

**Layer 5 — Status lighting:** Solid red + buzzer when any safety layer triggers

---

## Power Architecture

**Battery:** 25.6V 20Ah LiFePO4 (~512Wh, ~4 hours typical)

**Why 25.6V (2S) instead of 12.8V:**
- Halves current draw at same power → thinner wires, less heat
- CubeMars actuators optimal at 24V
- Drive motors run at 24V → faster, more torque than 12V equivalent
- Jetson needs 12V buck anyway (already needed)

**Rails:**
| Rail | Voltage | Load | Source |
|------|---------|------|--------|
| Main | 25.6V | CubeMars arm | Direct battery |
| Motor | 25.6V | Drive motors via DRV8243 | Direct battery |
| Compute | 12V | Jetson Orin NX | Buck converter |
| Logic | 5V | USB peripherals | Buck from 12V |
| MCU | 3.3V | STM32, IMU, transceivers | LDO from 5V |

**Power monitoring:** INA226 on each rail — I2C, 0.1% accuracy, reports voltage + current to STM32 → published to ROS2 → battery state estimation + alerts.
