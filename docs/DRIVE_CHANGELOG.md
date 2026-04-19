# RECLAIM Drive System — Changelog & Tracking

All changes to the drive/tracking system. Updated after every edit session.

---

## Files We Own

| File | Location | Description |
|------|----------|-------------|
| `waste_tracker.py` | `reclaim_ws/src/reclaim_bringup/reclaim_bringup/` | V1 — own camera, original visual servoing |
| `waste_tracker_v2.py` | same | V2 experimental — stop-look-drive (not used) |
| `waste_tracker_trt.py` | same | TRT V1 — polls TRT server, conservative 10fps tuning |
| `waste_tracker_trt_v2.py` | same | TRT V2 — 30fps optimized, P-only, diagnostics |
| `teensy_bridge.py` | `reclaim_ws/src/reclaim_control/reclaim_control/` | Bridge between ROS2 cmd_vel and Teensy serial |
| `teensy_bridge.yaml` | `reclaim_ws/src/reclaim_control/config/` | Bridge config (calibrated wheel params) |
| `waste_tracker.yaml` | `reclaim_ws/src/reclaim_bringup/config/` | Tracker YAML config |
| `camera_detect_trt.py` | `reclaim_ws/tests/` | TRT camera server (friend's, we changed DEPTH_MAX only) |
| `diag_monitor.py` | repo root | Mac-side UDP diagnostic receiver |
| `sync.sh` | repo root | Rsync wrapper (updated to exclude URDF/tests/models) |
| `MANUAL_TEST_GUIDE.md` | repo root | Manual commands for starting/stopping/testing |

## Files Friend Owns (DO NOT MODIFY without coordinating)

| File | Description |
|------|-------------|
| `camera_detect_trt.py` | TRT camera server — Python 3.8, TensorRT, 30fps |
| `pick_and_place.py` | MoveIt2 arm pickup pipeline |
| `reclaim_arm_moveit_config/` | Arm URDF, MoveIt config, calibration |
| `reclaim_servo_hardware/` | Servo hardware interface |

---

## Current Active Version: `waste_tracker_trt_v2.py`

### Architecture
```
TRT Server (Python 3.8, port 8081)     waste_tracker_trt_v2 (Python 3.11, ROS2)
  OAK-D camera (640x480)                  Polls HTTP /detection at 30Hz
  YOLO TensorRT @ 30fps          →         Bbox EMA smoothing
  Stereo depth (burst 5 frames)            Kalman filter (4-state)
  Best detection JSON                      P-only controller
  MJPEG stream :8081/stream               Sinusoidal ramp + smooth taper
                                           cmd_vel → Teensy bridge → motors
                                           UDP diagnostics → Mac :9999
```

### Current Tuning Parameters (TRT V2)

| Parameter | Value | Notes |
|-----------|-------|-------|
| poll_rate_hz | 30 | Matches TRT server frame rate |
| tick_timer | 33ms | ~30Hz |
| Kp | 0.0012 | P-only, no I/D |
| Ki | 0.0 | Disabled — causes windup |
| Kd | 0.0 | Disabled — amplifies noise |
| EMA alpha | 0.45 | Fast response for clean 30fps data |
| ramp_rate | 0.6 rad/s^2 | Compensates for 3x tick rate |
| deadband | 0.015 | Smooth taper (quadratic fade) |
| bbox_alpha | 0.5 | Bbox center EMA smoothing |
| Kalman Q | 2.0 | Process noise (tighter model) |
| Kalman R | 10.0 | Measurement noise (trust 30fps) |
| lost_threshold | 30 frames | 1 second at 30fps |
| det_hold_max | 4 frames | ~133ms hold during gaps |
| confirm_threshold | 3 frames | With gap tolerance (3 miss allowed) |
| scan_confirm_conf | 0.30 | Lower for 30fps (was 0.35) |
| TURN clamp | +/-0.12 rad/s | Max rotation speed during centering |
| APPROACH clamp | +/-0.10 rad/s | Max correction during approach |
| Coast clamp | +/-0.08 rad/s | Max during Kalman prediction |
| approach_stop_dist | 400mm | Switch to ALIGN |
| approach_max_v | 0.12 m/s | Max forward speed |
| scan_vel | 0.3 rad/s | Rotation speed during scan |

### Ground Filtering (floor-only detection)

| Filter | SCAN | Tracking (TURN/APPROACH/ALIGN) |
|--------|------|-------------------------------|
| Image position (cy_px) | Bottom 75% (cy > 0.25*H) | Bottom 80% (cy > 0.20*H) |
| Max depth | 2500mm | 3000mm |
| Max bbox area | 25% of image | 40% of image |
| Min bbox area | 0.2% of image | 0.3% of image |
| TRT server depth range | 150-3000mm | same |

---

## Change Log

### Session: March 24, 2026

#### waste_tracker.py (V1) — Local + MIC-711
- [x] Replaced hard angular deadband with smooth quadratic taper
- [x] Added sinusoidal ramp limiter (S-curve acceleration)
- [x] Added ByteTrack persistent tracking via model.track() with fallback to model()
- [x] Track ID matching priority in _find_target_in_detections()
- [x] Locked target highlighted cyan in debug feed
- [x] Reset tracked_id on rescan and scan entry
- [x] Synced to MIC-711 and built

#### waste_tracker_trt.py (TRT V1) — Local + MIC-711
- [x] Created from V1, adapted for HTTP polling of TRT server
- [x] Fixed distance_mm to use cam_z (was base_link transform, only valid at arm home pose)
- [x] Fixed bearing_rad to use cam_x/cam_z
- [x] Friend cleaned: removed dead camera_to_robot(), get_depth_for_bbox(), determine_grip(), build_pickup_commands()
- [x] PICK publishes to /pickup_request topic instead of raw serial
- [x] drive_only=True default
- [x] Uploaded to MIC-711, entry point added, built

#### waste_tracker_trt_v2.py (TRT V2) — Local + MIC-711
- [x] P-only controller (dropped Ki, Kd)
- [x] Kp 0.0010 → 0.0012
- [x] EMA alpha 0.18 → 0.45
- [x] Ramp rate 0.3 → 0.6
- [x] Deadband 0.02 → 0.015
- [x] Kalman Q 3.0 → 2.0, R 25.0 → 10.0
- [x] Poll rate 20Hz → 30Hz
- [x] Tick timer 50ms → 33ms
- [x] pid_dt 0.05 → 0.033
- [x] target_lost_threshold 50 → 30
- [x] Added bbox EMA smoothing (alpha=0.5)
- [x] Added detection hold (4 frames / 133ms)
- [x] Added confirmation gap tolerance (3 miss frames)
- [x] Lowered scan confirm conf 0.35 → 0.30
- [x] Added sinusoidal approach speed curve
- [x] Added UDP diagnostics to Mac (port 9999)
- [x] Added CSV tuning log (/tmp/tracker_tuning.csv)
- [x] Added parameter snapshot (/tmp/tracker_tuning_params.txt)
- [x] Added per-run performance stats + summary
- [x] Added state duration tracking
- [x] Added detection rate tracking (rolling 1s window)
- [x] Uploaded to MIC-711, entry point added, built
- [x] Added ground filtering (floor-only, no background objects)
- [x] Aspect ratio filter for non-floor objects
- [x] smooth_angular dt default updated 0.05 → 0.033

#### camera_detect_trt.py — Local + MIC-711
- [x] DEPTH_MAX_MM 600 → 3000 (for driving range, was arm-only)
- [x] Uploaded to MIC-711

#### teensy_bridge.py — Local + MIC-711
- [x] Serial auto-reconnect after 20 consecutive timeouts
- [x] Heading hold Kp 1.0 → 2.0, threshold 0.01 → 0.02 rad/s
- [x] Odom rate 20Hz → 10Hz

#### sync.sh — Local only
- [x] Added --exclude for *.urdf, urdf/, tests/, test/, models/, maps/

#### diag_monitor.py — Local only (Mac tool)
- [x] Created: UDP receiver, color-coded dashboard
- [x] Visual offset bar
- [x] Auto-saves to .jsonl for post-analysis

#### MANUAL_TEST_GUIDE.md — Local + MIC-711
- [x] Rewritten with fast start/stop commands
- [x] Added rescan command
- [x] Added Foxglove instructions
- [x] Added tuning reference tables

---

## Known Issues

| Issue | Status | Notes |
|-------|--------|-------|
| Castor scrub during in-place rotation | Open | Hardware fix: single center castor, or pivot turns |
| Encoders/odom not confirmed working under load | Open | TICKS response may fail during SETVEL contention |
| Detection range ~1.2m typical (want 2-2.5m) | Partially fixed | TRT 30fps + lower conf should help, DEPTH_MAX raised to 3000 |
| Residual jerkiness in corrections | Improved | Smooth taper + sinusoidal ramp + P-only should eliminate most |
| TRT server caches last detection | Fixed | 500ms timeout in server + 1s age check in tracker |
| Zombie processes after kill | Mitigated | ESTOP command, explicit pkill patterns |

## Upcoming / Ideas

- [ ] Test TRT V2 with 30fps pipeline end-to-end
- [ ] Pivot turns for scanning (one wheel stopped)
- [ ] Nav2 integration for search area + smooth path planning
- [ ] Encoder accuracy verification (mark-on-wheel test)
- [ ] Tune TRT server --conf to 0.15 (let tracker do filtering)
- [ ] Add track_id to TRT server API (model.track())
