# RECLAIM Navigation & Controls — Deep Dive

## How Every Constant Was Determined

### Wheel Radius: 0.05232m

**Method**: Iterative calibration. Command the robot to drive forward 50cm (using encoder counts). Measure actual distance with tape measure.

```
expected_distance = (ticks / 7560) * 2pi * r
```

If the robot drove 54.5cm when we expected 50cm, the radius is too big. Adjust:
```
r_new = r_old * (expected / actual) = 0.048 * (50 / 54.5) = 0.04404
```

Iterated 5 times until forward and reverse distance matched within ~1cm over 50cm. Final value: **0.05232m**.

### Wheel Separation: 0.470m

**Method**: 360 degree spin test. Command the robot to spin in place for exactly one full rotation (using encoder-based yaw). Measure the actual rotation.

```
yaw_per_tick = (2pi * wheel_radius) / (ticks_per_rev * wheel_separation)
```

If the robot overshot 360 by 18 degrees with wheel_sep = 0.494, the separation is too large:
```
sep_new = sep_old * (actual_rotation / expected_rotation) = 0.494 * (378 / 360) = 0.470
```

### Ticks Per Rev: 7560

**Method**: Hardware spec confirmed by measurement. JGB37-520 has:
- 7 PPR (pulses per revolution) base encoder
- 270:1 gearbox
- Quadrature decoding (x4)
```
7 * 270 * 4 = 7560 ticks per output shaft revolution
```

Verified by marking the wheel, spinning one full revolution by hand, and reading TICKS from serial.

### P Gain (Kp = 0.003 turn, 0.002 approach)

**Method**: Empirical tuning starting from theoretical estimate.

Relationship: `angular_velocity = Kp * pixel_offset`

Image is 640px wide, so max offset from center is 320px.

At Kp = 0.003: `max_w = 0.003 * 320 = 0.96 rad/s` (capped at 0.20)

Tuning logic:
- Too high -> oscillation (overshoots center, corrects back, overshoots again)
- Too low -> sluggish (takes many seconds to center, target might move)
- 0.003 produces 0.30 rad/s at 100px offset -- aggressive enough to center in ~1s
- 0.002 for approach because at 0.25 m/s forward speed, fast angular corrections cause visible swerving

### Motor Deadband: 0.04 rad/s

**Method**: Observation. Send decreasing angular velocities and watch when the motors stop responding. Below ~0.04 rad/s, the wheel speed commands translate to PWM values too low to overcome stiction in the motor + gearbox. Hardware limitation of the JGB37-520 with 270:1 reduction.

### EMA Alpha: 0.5

**Method**: Tradeoff analysis between responsiveness and smoothness.

```
alpha = 0.5:  50% raw, 50% previous   -> settles in ~3 frames (100ms)
alpha = 0.3:  30% raw, 70% previous   -> settles in ~6 frames (200ms)
alpha = 0.8:  80% raw, 20% previous   -> settles in ~1 frame (barely filters)
```

At 30fps, raw data has ~8px noise. Alpha 0.5 cuts noise in half without noticeable lag. 0.3 was too sluggish, 0.8 barely filtered.

### Heading Hold Kp: 2.0

**Method**: Straight-line driving test (2m).

- Kp = 1.0: corrects slowly, robot drifts ~5cm over 2m
- Kp = 2.0: snaps back within ~200ms, drift < 1cm over 2m
- Kp = 4.0: overcorrects, visible wobble

### Scan Speed: 0.3 rad/s

Full 360 takes `6.28 / 0.3 = ~21 seconds`. At 30fps, camera captures ~3 frames per degree of rotation.

### Approach Max Speed: 0.25 m/s

Motors' no-load speed is 37 RPM:
```
max_wheel_speed = 0.05232 * 2pi * 37/60 = 0.203 m/s
```

0.25 m/s is achievable during straight driving where both wheels share load.

### Stop Distance: 200mm (base_x)

Arm's working range: gripper reaches approximately 150-250mm from J1 base joint. 200mm puts the object in the middle of reachable zone.

### S-curve Ramp: 1.5 seconds

Cosine ramp has zero acceleration at start and end (no jerk):

```
v(t) = v_target * 0.5 * (1 - cos(pi * t / 1.5))
a(t) = v_target * pi/(2*1.5) * sin(pi * t / 1.5)
```

At t=0: a = 0 (no jerk). At t=0.75s: a = max. At t=1.5s: a = 0 (smooth).

### Max Acceleration: 0.3 m/s^2

Prevents wheel slip on smooth floors. Going from 0 to 0.20 m/s in one tick (33ms) would require 6 m/s^2 -- wheels slip on tile. At 0.3 m/s^2, takes ~0.67s.

### Confidence Threshold: 0.50

YOLO standard. 0.30 catches more but also picks up shadows/stains. 0.70 misses partially occluded objects.

### Confirm Threshold: 3 frames

At 20Hz, 3 frames = 150ms. Real objects persist for hundreds of frames. Noise rarely lasts >1-2 frames.

---

## The Full Control Hierarchy

### Layer 1: Teensy Firmware (Lowest Level)

Receives `SETVEL 0.108 0.132` over USB serial. Runs PI controller on each wheel:

```
error = target_velocity - measured_velocity
PWM += Kp * error + Ki * integral(error)
```

Measured velocity from encoders: 7560 ticks/rev, sampled at ~100Hz.
```
velocity = (ticks_per_sec / 7560) * 2pi * 0.05232
```

### Layer 2: Teensy Bridge (Middle Level)

ROS2 node on MIC-711. Four responsibilities:

**a) Velocity conversion** -- differential drive inverse kinematics:
```
v_left  = v - w * 0.235
v_right = v + w * 0.235
```

**b) Heading hold** -- locks heading when driving straight:
```python
if abs(v) > 0.005 and abs(w) < 0.02:
    heading_error = target_heading - actual_heading
    w = 2.0 * heading_error
```

**c) Ramp limiter** -- caps acceleration at 0.3 m/s^2

**d) Odometry** -- dead reckoning from encoder ticks at 10Hz:
```
delta_distance = (delta_left + delta_right) / 2
delta_theta    = (delta_right - delta_left) / 0.470
x += delta_distance * cos(theta)
y += delta_distance * sin(theta)
```

### Layer 3: Waste Tracker (Top Level -- The Brain)

State machine with visual servoing:

**SCAN**: Rotate at 0.3 rad/s. Confirm detections over 3 frames. Lock on nearest.

**TURN_TO_TARGET**: P controller centers target in camera frame.
```
pixel_offset = target_cx - 320
angular_vel = -0.003 * pixel_offset
```

**APPROACH**: Drive forward (speed proportional to distance) while steering to keep centered.
```
v = 0.04 + (0.25 - 0.04) * dist_ratio
w = -0.002 * pixel_offset
```

**ALIGN**: Final precise centering. 5 stable frames within 30px of center.

### The 4-Stage Smoothing Pipeline

```
Raw bbox -> Bbox EMA (alpha=0.5) -> P controller -> Angular EMA (alpha=0.45) -> Deadband taper -> Sinusoidal ramp -> cmd_vel
```

---

## Knowledge Test

### Phase 1: Fundamentals

1. Robot needs v=0.15 m/s, w=0.10 rad/s. What are left/right wheel velocities?
   **Answer**: v_left = 0.15 - 0.10*0.235 = 0.1265 m/s, v_right = 0.15 + 0.10*0.235 = 0.1735 m/s

2. Left encoder reads 3780 more ticks, right reads 3780. How far? Turn?
   **Answer**: Distance = (3780/7560) * 2pi * 0.05232 = 0.1645m. No turn -- both equal.

3. Target 80px right of center, Kp=0.003. Angular velocity? Direction?
   **Answer**: w = -0.003 * 80 = -0.24 rad/s. Turns right (clockwise, negative).

4. EMA alpha=0.5, current=0.10 rad/s, new raw=0.20 rad/s. New filtered?
   **Answer**: 0.5 * 0.20 + 0.5 * 0.10 = 0.15 rad/s

### Phase 2: State Machine Logic

5. SCAN: cup detected 2 frames, lost 1 frame, detected again. Lock on?
   **Answer**: No -- confirm resets on loss (no gap tolerance in friend's version).

6. APPROACH, cam_z=700mm. Forward speed? (before ramp)
   **Answer**: dist_ratio = (700-250)/1100 = 0.409. v = 0.04 + 0.21*0.409 = 0.126 m/s

7. APPROACH, target lost, cam_z was 400mm. What happens?
   **Answer**: Lost at close range (<500mm) for 50 frames -> IDLE. Probably at target.

8. TURN, detection 250px from last known. Returned by _find_target_in_detections?
   **Answer**: Yes -- during TURN, max_radius = 300px. 250 < 300.

### Phase 3: Smoothing & Controls

9. Why is Ki harmful if target disappears for 20 frames?
   **Answer**: Integral winds up during loss (error stays large). When target reappears, accumulated integral causes huge overshoot.

10. t=0.5s into approach (ramp_time=1.5s). Fraction of full speed?
    **Answer**: ramp = 0.5*(1-cos(pi*0.5/1.5)) = 0.5*(1-cos(60deg)) = 0.5*0.5 = 0.25 (25%)

11. P controller outputs 0.02 rad/s. What gets sent to motors?
    **Answer**: 0.02 < 0.04 deadband, overridden to 0.04 rad/s.

12. Driving straight at 0.12 m/s, heading drifts 0.05 rad. Heading hold output?
    **Answer**: w = 2.0 * 0.05 = 0.10 rad/s corrective rotation.

### Phase 4: System Integration

13. TRT server down for 3s during APPROACH?
    **Answer**: latest_detections stays empty. target_lost_count hits 50 (2.5s). Decides based on last depth.

14. Why Connection: close on HTTP requests?
    **Answer**: Prevents stale keep-alive state. Each request is fresh.

15. Tracker crashes but bridge keeps running?
    **Answer**: cmd_vel timeout fires after 0.5s. Motors stop safely.

16. Wheel radius wrong by 10% -- what breaks?
    **Answer**: Odometry position is off, but yaw uses ratio of left/right so mostly unaffected. Approach stop uses cam_z not odometry so still fine. Main break is distance estimation.
