# reclaim_control — Change Log

## 2026-03-22 — Wheel radius calibration iteration 4

### Firmware (`firmware/arm_commander/src/main.cpp`)
- `WHEEL_RADIUS`: 0.055 → 0.048m (robot was driving ~40cm for ~50cm expected)
- `PLANT_K_L`: 0.001230 → 0.001073 (scaled proportionally with radius)
- `PLANT_K_R`: 0.001096 → 0.000956 (scaled proportionally with radius)
- `PLANT_TAU_L/R`: unchanged (0.0503 / 0.0463)

### Config (`config/teensy_bridge.yaml`)
- `wheel_radius`: 0.055 → 0.048m (must match firmware)

---

## 2026-03-21 — PI controller tuning & BTS7960 integration

### Firmware
- BTS7960 right motor driver support: RPWM=pin22, LPWM=pin23
  - Pin 20 does NOT support PWM on Teensy 4.1 — moved LPWM to pin 23
  - BTS7960 R_EN/L_EN must be wired to 3.3V
- PI velocity controller with pole placement (ζ=0.7, ωn=1.5/τ)
  - Reduced from ωn=6/τ → 3/τ → 1.5/τ to eliminate oscillation
  - Anti-windup, low-pass velocity filter (α=0.3), feedforward
  - Ramp rate limiter: PI_RAMP_RATE=0.5 m/s² for smooth starts
  - Encoder velocity negated (encoders count negative for forward motion)
  - Safety timeout keepalive moved inside piControllerUpdate()
- SETVEL command for closed-loop velocity control
- Encoder ISRs from dual_motor_test.cpp (verified working)
- DRIVE, TICKS, RESET_TICKS, ESTOP serial commands

### Config
- `wheel_separation`: 0.494m (measured center-to-center)
- `wheel_radius`: started at 0.086m (physical), iterated: 0.067 → 0.055
- `ticks_per_rev`: 7560 (7 PPR × 270:1 × 4 quadrature) — NOT YET VERIFIED empirically
- `use_closed_loop`: true (sends SETVEL instead of DRIVE)
- `max_acceleration`: 0.3 m/s²

### Bridge (`reclaim_control/teensy_bridge.py`)
- Subscribes /cmd_vel → SETVEL (closed-loop) or DRIVE (open-loop)
- Publishes /odom from encoder ticks with differential drive kinematics
- PTY proxy at /tmp/teensy_arm for arm serial sharing
- Encoder sign fix (negated d_left, d_right)
- Ramp limiter on cmd_vel

---

## Known Issues
- **Wheel radius calibration incomplete**: Physical measurement (8.6cm) doesn't match calibrated value (4.8cm). Suggests `ticks_per_rev` may be wrong — verify by spinning wheel one revolution and reading TICKS.
- **Forward/backward distance asymmetry**: Robot goes ~40cm forward but ~45.5cm backward for same command. Likely castor drag difference.
- **Slight right turn on forward drive**: Castor alignment issue, not motor/firmware.
- **Teensy flash pattern**: Consistently fails first attempt. Sequence: reset → flash → fails → reset → flash → succeeds.
