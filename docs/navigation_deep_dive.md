# RECLAIM — Navigation & Controls Deep Dive

## How Every Constant Was Determined

### Wheel Radius: 0.05232m

**How we got it**: Iterative calibration. Command the robot to drive forward 50cm (using encoder counts). Measure the actual distance with a tape measure.

```
expected_distance = (ticks / 7560) * 2pi * r
```

If the robot drove 54.5cm when we expected 50cm, the radius is too big. Adjust:
```
r_new = r_old * (expected / actual) = 0.048 * (50 / 54.5) = 0.04404
```

This was iterated 5 times until forward and reverse distance matched within ~1cm over 50cm. Final value: **0.05232m**.

### Wheel Separation: 0.470m

**How we got it**: 360 spin test. Command the robot to spin in place for exactly one full rotation (using encoder-based yaw). Measure the actual rotation.

```
yaw_per_tick = (2pi * wheel_radius) / (ticks_per_rev * wheel_separation)
```

If the robot overshot 360 by 18 degrees with `wheel_sep = 0.494`, the separation is too large. The wheels are closer than we thought, so each tick produces more rotation than expected:
```
sep_new = sep_old * (actual_rotation / expected_rotation) = 0.494 * (378 / 360) = 0.470
```

### Ticks Per Rev: 7560

**How we got it**: Hardware spec confirmed by measurement. The JGB37-520 has:
- 7 PPR (pulses per revolution) base encoder
- 270:1 gearbox
- Quadrature decoding (x4)
```
7 * 270 * 4 = 7560 ticks per output shaft revolution
```

Verified by marking the wheel, spinning one full revolution by hand, and reading TICKS from serial.

### P Gain (Kp = 0.003 turn, 0.002 approach)

**How it was tuned**: Start with a guess, then adjust empirically.

The relationship is: `angular_velocity = Kp * pixel_offset`

Image is 640px wide, so max offset from center is 320px.

At Kp = 0.003: `max_w = 0.003 * 320 = 0.96 rad/s` (capped at 0.20)

The thought process:
- Too high: oscillation (overshoots center, corrects back, overshoots again)
- Too low: sluggish (takes many seconds to center, target might move)
- 0.003 produces 0.30 rad/s at 100px offset — aggressive enough to center in ~1s
- 0.002 for approach because at 0.25 m/s forward speed, fast angular corrections cause visible swerving

### Motor Deadband: 0.04 rad/s

**How we got it**: Observation. Send decreasing angular velocities and watch when the motors stop responding. Below ~0.04 rad/s, the wheel speed commands translate to PWM values too low to overcome stiction in the motor + gearbox. This is a **hardware limitation** of the JGB37-520 with 270:1 reduction — the gearbox has high stiction at low speeds.

### EMA Alpha: 0.5

**How we chose it**: Tradeoff between responsiveness and smoothness.

```
alpha = 0.5:  50% raw, 50% previous   -> settles in ~3 frames (100ms)
alpha = 0.3:  30% raw, 70% previous   -> settles in ~6 frames (200ms)
alpha = 0.8:  80% raw, 20% previous   -> settles in ~1 frame (barely filters)
```

At 30fps, the raw data is already fairly clean (~8px noise). Alpha 0.5 cuts the noise in half without adding noticeable lag. Chosen by testing — 0.3 was too sluggish (robot couldn't track a moving target), 0.8 was barely different from raw.

### Heading Hold Kp: 2.0

**How it was tuned**: Drive the robot straight for 2m. Watch if it drifts.

- Kp = 1.0: corrects slowly, robot drifts ~5cm over 2m
- Kp = 2.0: snaps back within ~200ms, drift < 1cm over 2m
- Kp = 4.0: overcorrects, visible wobble

2.0 is the sweet spot — strong enough to counteract castor drag immediately, not so strong it oscillates.

### Scan Speed: 0.3 rad/s

**How it was chosen**: Full 360 takes `6.28 / 0.3 = ~21 seconds`. This gives the camera enough time to see objects at each angle — at 30fps, the camera captures ~3 frames per degree of rotation. Too fast and you miss objects. Too slow and the scan takes forever.

### Approach Max Speed: 0.25 m/s

**Why this value**: The motors' no-load speed is 37 RPM:
```
max_wheel_speed = 0.05232 * 2pi * 37/60 = 0.203 m/s
```

At 0.25 m/s, one wheel (during a turn) would need to go faster than this — so the actual achievable straight-line speed is slightly above 0.20. 0.25 is aggressive but achievable because during straight driving both wheels share the load.

### Stop Distance: 200mm (base_x)

**Why**: This is the arm's working range. The gripper can reach approximately 150-250mm from the J1 base joint. Stopping at 200mm puts the object right in the middle of the arm's reachable zone. This is measured from the camera-to-base_link transform, not raw camera depth.

### S-curve Ramp: 1.5 seconds

**Why cosine, why 1.5s**:

Linear ramp (v increases at constant rate) has **discontinuous acceleration** — at t=0 acceleration jumps from 0 to some value, causing a jerk. Cosine ramp has **zero acceleration at start and end**:

```
v(t) = v_target * 0.5 * (1 - cos(pi * t / 1.5))
a(t) = v_target * pi/(2*1.5) * sin(pi * t / 1.5)
```

At t=0: `a = 0` (no jerk). At t=0.75s: `a = max` (peak acceleration). At t=1.5s: `a = 0` (smooth arrival at target speed).

1.5s was chosen to balance smoothness vs responsiveness. At 0.20 m/s, 1.5s means the robot covers ~15cm during ramp-up. Too long and the robot seems sluggish. Too short and you still get a jolt.

### Max Acceleration: 0.3 m/s^2

**Why**: At the bridge level, this prevents wheel slip on smooth floors. Going from 0 to 0.20 m/s in one tick (33ms) would require 6 m/s^2 — the wheels would slip on tile/laminate floors. At 0.3 m/s^2, it takes ~0.67s to reach full speed — smooth and grippy.

### Confidence Threshold: 0.50

**Why**: YOLO outputs a confidence score 0-1. At 0.50, roughly half of real trash is detected with very few false positives. Lower (0.30) catches more trash but also picks up floor stains, shadows. Higher (0.70) misses partially occluded objects. 0.50 is the standard YOLO threshold.

### Confirm Threshold: 3 frames

**Why**: At 20Hz polling, 3 frames = 150ms. A real object will persist for hundreds of frames. Noise/reflections rarely last more than 1-2 frames. 3 is the minimum that reliably filters flicker without adding noticeable delay (you don't want the robot to rotate past the object waiting for confirmation).

---

## The Full System Architecture

### The Physical System

Differential drive robot — two powered wheels with encoders, two passive castors. The left and right motors are independently controlled:

- **Both wheels same speed** -> drives straight
- **Right faster than left** -> arcs left
- **Wheels opposite directions** -> spins in place

The fundamental equation (inverse kinematics):
```
v_left  = v - w * 0.235
v_right = v + w * 0.235
```

The `0.235` is half the wheel separation (0.470m / 2).

### The Control Hierarchy (Bottom to Top)

```
Layer 3:  WHAT to do     waste_tracker_trt.py    "see trash, drive to it"
Layer 2:  HOW to move    teensy_bridge.py        "v=0.12, w=0.05 -> left/right wheel speeds"
Layer 1:  MAKE it move   Teensy firmware          "target velocity -> PWM via PI loop"
```

#### Layer 1: Teensy (Lowest Level)

The Teensy receives `SETVEL 0.108 0.132` over USB serial. It runs a **PI controller** on each wheel:

```
error = target_velocity - measured_velocity
PWM += Kp * error + Ki * integral(error)
```

The measured velocity comes from the encoders. 7560 ticks per wheel revolution, sampled at ~100Hz on the Teensy. It converts ticks/sec to m/s using:

```
velocity = (ticks_per_sec / 7560) * 2pi * 0.05232
```

This is a **closed-loop velocity controller** — it adjusts PWM to match the target speed regardless of battery voltage, floor friction, or load.

#### Layer 2: Teensy Bridge (Middle Level)

ROS2 node on the MIC-711. Does three things:

**a) Velocity conversion** — takes `/cmd_vel` (Twist message with v and w) and converts to left/right wheel velocities using the diff drive equation.

**b) Heading hold** — when the tracker says "drive straight" (`w ~ 0`), the bridge:
1. Records the current heading from odometry
2. Every tick, measures the actual heading
3. If the robot drifts, computes: `w_correction = 2.0 * (target_heading - actual_heading)`
4. Adds this correction to the wheel commands

Even though the tracker says "go straight," the bridge actively fights castor drift.

**c) Odometry** — polls encoder ticks at 10Hz, computes position:
```
delta_left  = (delta_ticks_L / 7560) * 2pi * 0.05232   # meters left wheel
delta_right = (delta_ticks_R / 7560) * 2pi * 0.05232   # meters right wheel
delta_distance = (delta_left + delta_right) / 2          # center displacement
delta_theta    = (delta_right - delta_left) / 0.470      # heading change
x += delta_distance * cos(theta)
y += delta_distance * sin(theta)
theta += delta_theta
```

This is **dead reckoning** — accumulates position from wheel movements. Drifts over time but accurate enough for scan completion and heading hold.

**d) Ramp limiter** — caps acceleration at 0.3 m/s^2. Prevents jerky starts.

#### Layer 3: Waste Tracker (Top Level — The Brain)

Finite state machine with visual servoing.

---

## The State Machine In Detail

### State 1: SCAN

**Purpose**: Find waste on the ground by rotating in place.

**How it works**:
1. Commands `w = 0.3 rad/s` (CCW rotation, ~21 seconds for 360 degrees)
2. Every tick, reads yaw from odometry to track rotation progress
3. TRT poll thread gets detections in parallel
4. Each tick checks: "did I see anything?"

**Scan accumulation hack**: Castors scrub during rotation causing brief backward yaw jumps. Reverse yaw counted at 30% to prevent premature "360 complete".

**Detection confirmation**: Requires 3 consistent frames — same class, cx within 80px, depth within 500mm. During confirmation, scan slows to 40%.

If full 360 with no lock: picks nearest from scan list.

### State 2: TURN_TO_TARGET

**Purpose**: Rotate to center the target in the camera frame.

**Core equation**:
```
pixel_offset = target_cx - 320
angular_vel = -0.003 * pixel_offset
```

100px right of center -> w = -0.30 rad/s (turn right)
50px left of center  -> w = +0.15 rad/s (turn left)

Negative sign: camera x-axis is opposite to rotation direction.

**Motor deadband override**: If |w| < 0.04, force to 0.04. Motors physically can't spin slower.

**EMA smoothing**: `w = 0.5 * raw + 0.5 * previous`. Filters bbox jitter.

**Transition**: |pixel_offset| < 50px -> APPROACH.

**When lost**: Coasts at last angular velocity. After 50 frames -> rescan.

### State 3: APPROACH

**Purpose**: Drive toward target while keeping it centered.

**Speed control**:
```
dist_ratio = (cam_z - 250) / 1100     # normalized 0 to 1
v = 0.04 + (0.25 - 0.04) * dist_ratio
```
At 1350mm: v = 0.25 m/s (full). At 800mm: v = 0.145. At 250mm: v = 0.04 (minimum).

**Softer steering**: Kp = 0.002 (not 0.003). Less swerving at speed.

**S-curve startup ramp**:
```
ramp = 0.5 * (1 - cos(pi * elapsed / 1.5))
v *= ramp
w *= ramp
```
Zero jerk at start and end. Both linear and angular ramped.

**Dual stop condition**:
- Primary: `base_x <= 200mm` (from camera-to-base_link transform)
- Fallback: `cam_z <= 250mm`

**When lost**: Coast forward at 0.04 m/s. If lost too long at close range -> stop (probably at target).

### State 4: ALIGN

**Purpose**: Final precise centering before arm pickup.

Same P controller as TURN (Kp = 0.003, deadband override), but:
- Must be centered within 30px
- If base_x > 250mm, creep forward at 0.04 m/s
- Need 5 stable frames before declaring done

When done: publishes to `/pickup_request` for arm.

---

## The Detection Pipeline

### TRT Poll Thread (20Hz background)

```
HTTP GET /detection -> JSON parse -> confidence check -> spatial filter -> store
```

### Filtering

| Filter | Scan | Tracking | Why |
|--------|------|----------|-----|
| Max depth | 2500mm | 3000mm | Don't chase far objects during scan |
| Min cy (top of image) | 25% | 20% | Top of frame = not on floor |
| Max bbox area | 15% | 25% | Large = walls, people |
| Min bbox area | 0.3% | 0.3% | Tiny = noise |

### Target Matching (_find_target_in_detections)

Three-tier fallback:
1. **Position match**: Detection within 80px (150px during TURN) of last known position
2. **Class match**: Same class name, closest to last position
3. **Any nearby**: Any detection within 200-300px radius

---

## Showcase Talking Points

### 30-second version:
"The robot scans by rotating in place. When the camera detects waste confirmed over 3 frames, it locks on and uses a P controller to center the object in the camera frame. Then it drives toward it with distance-proportional speed and smooth cosine acceleration. A softer controller gain during approach prevents swerving. The teensy bridge converts the velocity commands to differential wheel speeds and adds heading hold to fight castor drift. The whole system runs at 20-30Hz."

### If they ask about smoothing:
"At 30 FPS, the raw bbox center has about 8 pixels of noise. We apply an EMA filter with alpha 0.5 to cut that in half, then cap the angular velocity and enforce a motor deadband of 0.04 rad/s — below that, the motors physically can't spin. The teensy bridge adds another layer with a 0.3 m/s^2 acceleration limit."

### If they ask about the P controller:
"We use two P gains — 0.003 during turning for aggressive centering, and 0.002 during approach to reduce swerving. The output is angular velocity in rad/s, proportional to how many pixels the target is off-center. 100 pixels off-center produces 0.3 rad/s of rotation."

### If they ask why not PID:
"At 30 FPS, the measurements are clean enough that integral and derivative terms add more problems than they solve. The integral causes windup when the target is temporarily lost, and the derivative amplifies noise. Pure P with EMA smoothing is sufficient."

---

## Learning Plan

### Phase 1: Fundamentals (30 min)

**Topics:**
1. Differential drive kinematics — v, w -> left/right wheel speeds
2. Dead reckoning odometry — ticks -> position
3. P controller — error * gain = output
4. EMA filter — what alpha does, responsiveness vs smoothness tradeoff

**Questions:**
1. The robot needs to drive at 0.15 m/s while turning left at 0.10 rad/s. What are the left and right wheel velocities?
2. The left encoder reads 3780 more ticks than last reading, right reads 3780. How far did the robot move? Did it turn?
3. The target is 80px to the right of center. With Kp = 0.003, what angular velocity is commanded? Which direction?
4. Your EMA has alpha = 0.5, current filtered value is 0.10 rad/s, new raw value is 0.20 rad/s. What's the new filtered value?

### Phase 2: State Machine Logic (30 min)

**Topics:**
1. State transitions — triggers
2. SCAN confirmation — why 3 frames, resets
3. APPROACH speed profile — distance to speed mapping
4. Target matching — 3-tier fallback
5. Lost target handling — coast vs rescan vs stop

**Questions:**
5. During SCAN, the robot detects a cup at 1500mm for 2 frames, loses it for 1 frame, then sees it again. Does it lock on?
6. In APPROACH, cam_z reads 700mm. What forward speed is commanded (before ramp)?
7. The robot is in APPROACH and loses the target. cam_z was 400mm. What happens?
8. During TURN, a detection is 250px from last known position. Does _find_target_in_detections return it?

### Phase 3: Smoothing & Controls (30 min)

**Topics:**
1. Why P-only (not PID) at 30fps
2. S-curve ramp math — cosine profile, zero jerk
3. Motor deadband — physical cause and software fix
4. Heading hold — fighting castor drift
5. Two-Kp strategy — softer gain during approach

**Questions:**
9. Why would Ki be harmful if the target disappears for 20 frames then comes back?
10. At t = 0.5s into approach (ramp_time = 1.5s), what fraction of full speed is the robot at?
11. P controller outputs 0.02 rad/s. What actually gets sent to motors?
12. Robot drives straight at 0.12 m/s, heading drifts 0.05 rad. What does heading hold produce?

### Phase 4: System Integration (20 min)

**Topics:**
1. Thread safety — camera_lock, two threads
2. TRT communication — HTTP polling, stale detection, DEPTH_MAX_MM
3. ROS2 topic flow — /cmd_vel, /odom, /robot_state, /pickup_request
4. Calibration chain — how constants feed into each other

**Questions:**
13. What happens if the TRT server goes down for 3 seconds during APPROACH?
14. Why does the poll thread use `Connection: close` on HTTP requests?
15. The cmd_vel timeout is 0.5s. What if the tracker crashes but bridge keeps running?
16. If wheel_radius is wrong by 10%, which behaviors break?

---

## Answers

1. `v_left = 0.15 - 0.10 * 0.235 = 0.1265 m/s`, `v_right = 0.15 + 0.10 * 0.235 = 0.1735 m/s`
2. Distance = `(3780/7560) * 2pi * 0.05232 = 0.1645m`. No turn — both wheels moved equally.
3. `w = -0.003 * 80 = -0.24 rad/s`. Turns right (clockwise).
4. `0.5 * 0.20 + 0.5 * 0.10 = 0.15 rad/s`
5. No — confirm count reaches 2, then resets to 0 when detection disappears (no gap tolerance in this version).
6. `dist_ratio = (700-250)/1100 = 0.409`. `v = 0.04 + 0.21 * 0.409 = 0.126 m/s`
7. Lost at close range (<500mm) for 50 frames -> `drive_only_done = True`, goes IDLE. Probably already at target.
8. During TURN, max_radius = 300px. 250 < 300. Yes, returns it.
9. While target is gone, pixel error stays large, integral winds up. When target reappears, accumulated integral causes huge overshoot — robot spins way past center.
10. `ramp = 0.5 * (1 - cos(pi * 0.5/1.5)) = 0.5 * (1 - cos(60deg)) = 0.5 * 0.5 = 0.25`. 25% speed.
11. 0.02 < 0.04 (deadband), overridden to 0.04 rad/s in the error direction. Without this, motors wouldn't move.
12. `w = 2.0 * 0.05 = 0.10 rad/s` corrective rotation.
13. Poll returns URLError, consecutive_errors increments. latest_detections stays empty. target_lost_count increments. After 50 frames (2.5s), decides based on last depth.
14. Prevents HTTP keep-alive accumulating stale state. Each request is fresh.
15. cmd_vel_timeout fires after 0.5s of no messages. Sends SETVEL 0.0 0.0. Motors stop safely.
16. Odometry position is wrong (thinks it moved more/less). BUT: scan yaw uses left/right ratio (unaffected by radius). Approach stop uses cam_z (unaffected). Heading hold uses yaw (unaffected). Main break: if other nodes rely on /odom position.

---

## Known Issue: DEPTH_MAX_MM = 600

The TRT server (`camera_detect_trt.py`) only reports detections within 600mm. This limits driving — the tracker can't see targets until very close. Needs to be changed to 3000mm for driving range. Will change later.
