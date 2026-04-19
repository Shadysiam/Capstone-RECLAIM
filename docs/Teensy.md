# Teensy 4.1 — RECLAIM Reference

## Connection

- **USB Device:** `/dev/ttyACM0` on MIC-711
- **Baud Rate:** 115200
- **USB Bus:** Bus 001 (USB 2.0)
- **lsusb ID:** `16c0:0486 Van Ooijen Technische Informatica Teensyduino`

## Pin Map

| Pin | Function | Component | Wire Color (from Cirkit guide) |
|-----|----------|-----------|-------------------------------|
| 2 | PWM (speed) | MD10C #1 — Left motor | — |
| 3 | DIR (direction) | MD10C #1 — Left motor | — |
| 4 | PWM (speed) | MD10C #2 — Right motor | — |
| 5 | DIR (direction) | MD10C #2 — Right motor | — |
| 6 | Encoder Ch A | Left motor encoder | — |
| 7 | Encoder Ch B | Left motor encoder | — |
| 8 | Encoder Ch A | Right motor encoder | — |
| 9 | Encoder Ch B | Right motor encoder | — |
| 10 | Servo PWM | Base rotation (MG996R) | — |
| 11 | Servo PWM | Shoulder (MG996R) | — |
| 12 | Servo PWM | Elbow (MG996R) | — |
| 13 | Servo PWM | Wrist Pitch (MG996R) | — |
| 14 | Servo PWM | Wrist Rotate (MG996R) | — |
| 15 | Servo PWM | Gripper (MG996R) | — |
| 3V | Encoder VCC | Both encoders (3.3V) | — |
| GND | Ground | Ground bus | — |

**Encoder power:** 3.3V from Teensy 3V pin. Output signals are 3.3V, directly compatible with Teensy GPIO. Do NOT use 5V — Teensy GPIO is NOT 5V tolerant. If signals are noisy at 3.3V, add a BOB-12009 level shifter.

## Motor Drivers (2x Cytron MD10C)

- PWM frequency: 20kHz recommended
- DIR pin: HIGH = forward, LOW = reverse
- Accepts 3.3V logic directly from Teensy (no level shifter needed)
- NOT MDD10A (that's a dual-channel board, we have two single-channel MD10C)

## Servos (6x MG996R)

- All joints use the same servo model (MG996R)
- Powered by XINGYHENG 20A 300W buck converter (12V in, ~6V out)
- Power distributed via 4x Wago 221-415 lever-nuts
- 4700-10000uF bulk capacitor on servo power bus (prevents brownout on simultaneous movement)
- PWM signal from Teensy pins 10-15 (3.3V logic, MG996R accepts this)

| Servo Pin | Joint | Safe Range (degrees) |
|-----------|-------|---------------------|
| 10 | Base rotation | TBD (test tomorrow) |
| 11 | Shoulder | TBD (test tomorrow) |
| 12 | Elbow | TBD (test tomorrow) |
| 13 | Wrist Pitch | TBD (test tomorrow) |
| 14 | Wrist Rotate | TBD (test tomorrow) |
| 15 | Gripper | TBD (test tomorrow) |

## Encoders (JGB37-520 motors)

- Hall-effect quadrature encoders (2 channels per motor)
- 6-pin connector per motor: M1, M2 (motor power), VCC, GND, OutA, OutB (encoder)
- Counts per revolution: TBD (need to measure)
- Use hardware interrupts on Teensy for accurate counting

## Flashing Firmware

PlatformIO is pip-installed on the MIC-711 at `/home/mic-711/.local/bin/pio` (NOT in the conda env). Use `$(which pio)` or the full path when running with `sudo`.

**Project location:** `~/reclaim_ws/tests/teensy_hello/` (basic serial test)
**Active firmware:** `~/reclaim_ws/src/reclaim_control/firmware/`

### platformio.ini

```ini
[env:teensy41]
platform = teensy
board = teensy41
framework = arduino
upload_protocol = teensy-cli
monitor_speed = 115200
```

### CRITICAL: Flash Procedure (EXACT steps that work)

Flashing MUST be done on the MIC-711 (not Mac — Mac USB hub causes detection issues).
PlatformIO is installed in the `ros_env` conda environment on the MIC-711.

**The ONLY flash command that works:**
```bash
# Step 1: Fix permissions on hidraw devices (REQUIRED every time)
sudo chmod 666 /dev/hidraw*

# Step 2: Flash with sudo (REQUIRED — without sudo it ALWAYS fails with "Permission denied")
cd ~/reclaim_ws/tests/teensy_hello    # or whatever project directory
sudo $(which pio) run --target upload
```

**Why `sudo` is required:** The `teensy_loader_cli` needs raw USB access to the HID bootloader device. Even with udev rules and chmod, it fails without sudo. Don't waste time trying without sudo.

**Why `$(which pio)` is needed:** `sudo` doesn't inherit the conda PATH, so `sudo pio` gives "command not found". The `$(which pio)` resolves to the full path before sudo runs it.

**When prompted "press the reset button":** Press the small physical pushbutton on the Teensy board. This puts it in bootloader mode so the loader can flash it.

**Common errors and fixes:**

| Error | Fix |
|-------|-----|
| `Found device but unable to open` | Run `sudo chmod 666 /dev/hidraw*`, then unplug/replug Teensy, retry with `sudo` |
| `Permission denied` | You forgot `sudo`. Use `sudo $(which pio) run --target upload` |
| `Unable to open /dev/ttyACM0 for reboot request` | Normal warning when reflashing. Teensy reboots into bootloader, press the button |
| `sudo: pio: command not found` | Use `sudo $(which pio)` not `sudo pio` |
| `Waiting for Teensy device...` forever | Press the physical button on the Teensy |
| ModemManager grabbing the port | `sudo systemctl stop ModemManager && sudo systemctl disable ModemManager` |

**Non-interactive SSH flash command (for agents):**
```bash
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && cd ~/reclaim_ws/tests/teensy_hello && sudo chmod 666 /dev/hidraw* && sudo \$(which pio) run --target upload"
```
Note: User must press the Teensy button when prompted. This cannot be automated.

### Permissions

Udev rules on the MIC-711:
```
/etc/udev/rules.d/99-teensy.rules:
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="16c0", MODE="0666"
```

Even with this rule, `sudo` is still required for flashing. The rule helps but doesn't fully solve it.

For serial access after flashing:
```bash
sudo chmod 666 /dev/ttyACM0
```

### Serial communication from MIC-711

```python
import serial
s = serial.Serial('/dev/ttyACM0', 115200, timeout=2)
line = s.readline().decode().strip()  # read
s.write(b'command\n')                  # write
s.close()
```

**Non-interactive SSH serial command (for agents):**
```bash
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && sudo chmod 666 /dev/ttyACM0 && python3 -c \"import serial; s=serial.Serial('/dev/ttyACM0',115200,timeout=2); import time; time.sleep(1); [print(s.readline().decode().strip()) for _ in range(3)]; s.close()\""
```

## Available Firmware

All firmware lives in `reclaim_ws/src/reclaim_control/firmware/`.

### teensy_hello (basic serial test)
- Location: `~/reclaim_ws/tests/teensy_hello/`
- Sends `[heartbeat] uptime=Ns` every second
- Echoes back any received serial messages as `[echo] <message>`
- Blinks built-in LED as heartbeat indicator
- **Status:** Flashed and verified March 6, 2026. Serial comms confirmed at 115200 baud.

### servo_test (interactive 6-servo calibration tool)
- Location: `reclaim_ws/src/reclaim_control/firmware/servo_test/`
- **Raw microsecond control** with per-servo calibration and joint zero references
- MG996R servos rated 0-270°, pulse range 400-2600us
- Servos start **DETACHED** (no PWM on boot) — prevents spaz on power-up
- Motor driver pins (2-5) driven LOW on boot — prevents drive motors from spinning

**Controls:**
- `1`-`6` = select servo (1=Base, 2=Shoulder, 3=Elbow, 4=WristPitch, 5=WristRotate, 6=Gripper)
- `d`/`a` = +/- 10us (coarse), `D`/`A` = +/- 2us (fine)
- `c` = center (1500us)
- `[` = set current pulse as calMin (0°), `]` = set current pulse as calMax (270°)
- `z` = set JOINT 0° reference (attaches servo at 1500us if not yet active — hold the arm!)
- `m` = save JOINT MIN (relative degrees), `M` = save JOINT MAX (relative degrees)
- `p` = print all positions, `h` = help

**Calibration workflow:**
1. Manually position each servo to its physical center by hand
2. Press `z` to attach at 1500us and set joint zero reference (minimizes initial jump)
3. Use `d`/`a` to find mechanical limits in each direction
4. Press `m` at min limit, `M` at max limit to record relative joint range
5. Optionally press `[`/`]` to set pulse calibration endpoints

- **Status:** Extensively updated March 8, 2026. All 6 servos respond on pins 10-15. Motor spaz-on-boot fixed. Safe angle ranges still TBD (calibration not yet performed).
- **TODO:** Calibrate all 6 joints using the workflow above. Record values and update arm_commander.

### arm_commander (production arm controller with quintic interpolation)
- Location: `reclaim_ws/src/reclaim_control/firmware/arm_commander/`
- Serial protocol: `SET a1 a2 a3 a4 a5 a6 [T_ms]`, `GET`, `TEACH <name>`, `HOME`, `STOP`, `NUDGE <joint> <deg>`, `LIMITS`, `HELP`
- Quintic (minimum-jerk) interpolation at 50Hz for smooth acceleration/deceleration
- Configurable safe angle limits per joint (edit SAFE_MIN/SAFE_MAX arrays in source)
- Responds `MOVING ... T=Nms` on move start, `DONE` + `ANGLES ...` on completion
- Companion tool: `scripts/pose_teacher.py` (interactive CLI for teaching and saving poses to `config/poses.yaml`)
- **Status:** Written March 8, 2026. NOT yet flashed. Flash this after finding safe limits with servo_test.

### motor_encoder_test (automated + manual motor control)
- Location: `reclaim_ws/src/reclaim_control/firmware/motor_encoder_test/`
- **main.cpp:** Automated test. Runs left motor (pins 2/3) forward at 50%, stop, reverse at 50%, stop, then speed ramp 0-255. Reads encoder ticks (pins 6/7) throughout and calculates RPM (assumes 210 ticks/rev: 7 PPR, 30:1 gearbox).
- **manual_control.cpp:** Interactive WASD control. `w` forward, `s` reverse, `x` stop, `+/-` speed, `r` reset encoder count. Prints ticks every 200ms while running.
- **Status:** Auto test verified March 7, 2026. Motor forward/reverse works. Encoder ticks read correctly. ~660 ticks/200ms at 50% PWM. Manual control firmware written but not yet tested interactively.

## URDF

A minimal kinematic URDF skeleton is at `reclaim_ws/src/reclaim_control/urdf/reclaim_arm.urdf`. It defines all 6 joints with correct axis orientations but uses PLACEHOLDER link lengths. You must measure the physical arm and replace the TODO values before using it with MoveIt2.

Measurements needed (in meters): base-to-shoulder height, shoulder-to-elbow length, elbow-to-wrist length, wrist-to-gripper offset.

## Verified Test Results

| Test | Result | Date |
|------|--------|------|
| USB detection on MIC-711 | `/dev/ttyACM0`, 115200 baud | March 6 |
| Serial heartbeat + echo | Working | March 6 |
| Servo response (all 6 pins 10-15) | Working | March 6 |
| Motor auto test (forward/reverse/ramp) | Working (left motor + encoder) | March 7 |
| Servo raw us control + joint zero | Working (firmware updated) | March 8 |
| Motor manual control | Firmware written, NOT yet tested | — |
| Servo calibration (safe ranges) | NOT YET DONE | — |

## Remaining Hardware Tasks

1. Wire motors to MD10C drivers (motor power from 12V fuse block), MD10C signal to Teensy pins 2-5
2. Wire encoder outputs to Teensy pins 6-9 (encoder VCC from Teensy 3.3V pin)
3. Flash and run `motor_encoder_test` to verify motor direction and encoder counting
4. Measure actual encoder counts per revolution (firmware assumes 210, verify this)
5. Find safe angle ranges for each servo joint using `servo_test` or `pose_teacher.py limits`
6. Update SAFE_MIN/SAFE_MAX in `arm_commander` firmware with real limits, then flash it
7. Teach named poses (home, pre_pick, pick_down, bin1/2/3_pre, bin1/2/3_drop) using `pose_teacher.py`
8. Measure arm link lengths and update URDF placeholder values
9. Build micro-ROS firmware that publishes `/odom` and subscribes to `/cmd_vel` + `/arm/command`
