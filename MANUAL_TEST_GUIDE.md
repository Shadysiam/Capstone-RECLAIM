# RECLAIM Manual Testing Guide

**All commands run from your Mac terminal.** No interactive SSH needed.

**Prerequisites:**
- Connected to MIC-711's WiFi (Mango router)
- `ssh mic` alias configured in `~/.ssh/config`
- Battery connected and charged

---

## QUICK REFERENCE

| Action | Command |
|--------|---------|
| **Stop everything** | `ssh mic "pkill -9 -f waste_tracker; pkill -9 -f teensy_bridge; for p in /dev/ttyACM*; do echo 'ESTOP' > \$p 2>/dev/null; done"` |
| **Emergency stop** | `ssh mic "for p in /dev/ttyACM*; do echo 'ESTOP' > \$p 2>/dev/null; done"` |
| **Rescan** | `ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && ros2 topic pub /rescan std_msgs/msg/String '{data: go}' -1"` |
| **Watch logs** | `ssh mic "tail -f /tmp/tracker.log"` |
| **Check status** | `ssh mic "tail -20 /tmp/tracker.log"` |
| **Check bridge** | `ssh mic "tail -5 /tmp/bridge.log"` |
| **View camera** | `http://192.168.2.2:8081` in browser (TRT server must be running) |
| **Diag monitor** | `python3 diag_monitor.py` (run on Mac, receives UDP from TRT V2) |

---

## FULL SYSTEM — Drive + Arm + Pick & Place (showcase demo)

**Requires 7 terminals on MIC-711.** Use NoMachine to access the MIC-711 desktop for RViz.
Open each terminal in order — wait for the indicated message before proceeding.

### Terminal 1 — Teensy Bridge
```bash
echo 'mic-711' | sudo -S chmod 666 /dev/ttyACM0 && \
source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && \
cd ~/reclaim_ws && source install/setup.bash && \
ros2 run reclaim_control teensy_bridge
```
**Wait for:** `TeensyBridge started`

### Terminal 2 — MoveGroup + RViz (on MIC-711 desktop via NoMachine)
```bash
export DISPLAY=:0 && source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && \
cd ~/reclaim_ws && source install/setup.bash && \
ros2 launch reclaim_arm_moveit_config move_group.launch.py
```
**Wait for:** `You can start planning now!`

### Terminal 3 — Planning Scene (collision objects)
```bash
source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && \
cd ~/reclaim_ws && source install/setup.bash && \
python3 src/reclaim_arm_moveit_config/scripts/load_planning_scene.py
```

### Terminal 4 — TRT Camera Server
```bash
kill $(lsof -t -i:8081) 2>/dev/null; \
env -i HOME=/home/mic-711 PATH=/usr/bin:/usr/local/bin:/bin \
python3.8 ~/reclaim_ws/tests/camera_detect_trt.py \
  --model ~/reclaim_ws/models/waste_yolo11n_v3_best.engine \
  --conf 0.35 --port 8081
```
**Wait for:** `Running...`

### Terminal 5 — Move Arm to Search Pose (in RViz GUI)
In the RViz window (via NoMachine):
1. In the MotionPlanning panel → "Planning" tab
2. Set **Goal State** dropdown → `search`
3. Click **Plan & Execute**
4. Wait for arm to finish moving

### Terminal 6 — Pick & Place Listener
```bash
source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && \
cd ~/reclaim_ws && source install/setup.bash && \
python3 src/reclaim_arm_moveit_config/scripts/pick_and_place.py --listen --port 8081
```

### Terminal 7 — Waste Tracker (starts scanning immediately)
```bash
source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && \
cd ~/reclaim_ws && source install/setup.bash && \
ros2 run reclaim_bringup waste_tracker_trt --ros-args \
  -p trt_url:=http://localhost:8081 \
  -p drive_only:=false
```

### Mac — View Camera Stream
```bash
# Set up SSH tunnel (run once)
lsof -ti:8081 | xargs kill -9 2>/dev/null; ssh -f -N -L 8081:127.0.0.1:8081 mic
# Then open in browser:
open http://127.0.0.1:8081
```

### Mac — View Arm in Foxglove (optional)
Open Foxglove app → Connect to `ws://192.168.2.2:8765` → Add 3D panel → Load URDF

### Mac — NoMachine (see RViz on MIC-711 desktop)
Open NoMachine → Connect to 192.168.2.2 → You see the MIC-711 desktop with RViz

### Shutdown Full System
```bash
# On MIC-711 (any terminal):
pkill -9 -f waste_tracker
pkill -9 -f pick_and_place
pkill -9 -f camera_detect_trt
pkill -9 -f move_group
pkill -9 -f teensy_bridge
echo 'ESTOP' > /dev/ttyACM0 2>/dev/null
```

---

## START — TRT V2 (30fps, recommended)

**Requires TRT server already running** (friend starts it, or see "Start TRT Server" below).

### Step 1: Start bridge
```bash
ssh mic "pkill -9 -f teensy_bridge" 2>/dev/null; sleep 2; \
echo 'mic-711' | ssh mic "sudo -S chmod 666 /dev/ttyACM*" 2>/dev/null; \
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && cd ~/reclaim_ws && source install/setup.bash && TEENSY_PORT=\$(ls /dev/ttyACM* 2>/dev/null | head -1) && echo \"Using \$TEENSY_PORT\" && nohup ros2 run reclaim_control teensy_bridge --ros-args --params-file src/reclaim_control/config/teensy_bridge.yaml -p serial_port:=\$TEENSY_PORT > /tmp/bridge.log 2>&1 &"; \
sleep 2; ssh mic "tail -3 /tmp/bridge.log"
```

### Step 2: Start TRT V2 tracker
```bash
ssh mic "pkill -9 -f waste_tracker" 2>/dev/null; sleep 2; \
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && cd ~/reclaim_ws && source install/setup.bash && nohup ros2 run reclaim_bringup waste_tracker_trt_v2 --ros-args -p drive_only:=true > /tmp/tracker.log 2>&1 &"; \
echo "Starting TRT V2..."; sleep 3; ssh mic "tail -5 /tmp/tracker.log"
```

### Step 3: Monitor on Mac (separate terminal tab)
```bash
python3 diag_monitor.py
```

### One-liner start (bridge + TRT V2)
```bash
ssh mic "pkill -9 -f waste_tracker; pkill -9 -f teensy_bridge" 2>/dev/null; sleep 3; \
echo 'mic-711' | ssh mic "sudo -S chmod 666 /dev/ttyACM*" 2>/dev/null; \
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && cd ~/reclaim_ws && source install/setup.bash && TEENSY_PORT=\$(ls /dev/ttyACM* 2>/dev/null | head -1) && nohup ros2 run reclaim_control teensy_bridge --ros-args --params-file src/reclaim_control/config/teensy_bridge.yaml -p serial_port:=\$TEENSY_PORT > /tmp/bridge.log 2>&1 &"; \
sleep 2; \
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && cd ~/reclaim_ws && source install/setup.bash && nohup ros2 run reclaim_bringup waste_tracker_trt_v2 --ros-args -p drive_only:=true > /tmp/tracker.log 2>&1 &"; \
echo "Starting..."; sleep 3; ssh mic "tail -5 /tmp/tracker.log"
```

---

## START — V1 (own camera, original)

```bash
ssh mic "pkill -9 -f waste_tracker; pkill -9 -f teensy_bridge; pkill -9 -f python3" 2>/dev/null; \
sleep 3; \
echo 'mic-711' | ssh mic "sudo -S chmod 666 /dev/ttyACM*" 2>/dev/null; \
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && cd ~/reclaim_ws && source install/setup.bash && TEENSY_PORT=\$(ls /dev/ttyACM* 2>/dev/null | head -1) && echo \"Using \$TEENSY_PORT\" && nohup ros2 run reclaim_control teensy_bridge --ros-args --params-file src/reclaim_control/config/teensy_bridge.yaml -p serial_port:=\$TEENSY_PORT > /tmp/bridge.log 2>&1 &"; \
sleep 2; \
ssh mic "rm -f /tmp/tracker.log && source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && export LD_PRELOAD='/home/mic-711/miniforge3/envs/ros_env/lib/libstdc++.so.6:/home/mic-711/miniforge3/envs/ros_env/lib/python3.11/site-packages/torch/lib/libc10.so:/home/mic-711/miniforge3/envs/ros_env/lib/libgomp.so.1' && cd ~/reclaim_ws && source install/setup.bash && nohup ros2 run reclaim_bringup waste_tracker --ros-args --params-file src/reclaim_bringup/config/waste_tracker.yaml > /tmp/tracker.log 2>&1 &"; \
echo "Waiting 8s for camera..."; sleep 8; \
ssh mic "tail -5 /tmp/tracker.log"
```

---

## START — TRT V1 (30fps, conservative tuning)

```bash
ssh mic "pkill -9 -f waste_tracker" 2>/dev/null; sleep 2; \
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && cd ~/reclaim_ws && source install/setup.bash && nohup ros2 run reclaim_bringup waste_tracker_trt --ros-args -p drive_only:=true > /tmp/tracker.log 2>&1 &"; \
echo "Starting TRT V1..."; sleep 3; ssh mic "tail -5 /tmp/tracker.log"
```

---

## SWITCH TRACKERS (bridge stays running)

```bash
# Kill current tracker
ssh mic "pkill -9 -f waste_tracker" 2>/dev/null; sleep 2

# Then start whichever one you want:

# TRT V2 (recommended):
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && cd ~/reclaim_ws && source install/setup.bash && nohup ros2 run reclaim_bringup waste_tracker_trt_v2 --ros-args -p drive_only:=true > /tmp/tracker.log 2>&1 &"

# TRT V1:
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && cd ~/reclaim_ws && source install/setup.bash && nohup ros2 run reclaim_bringup waste_tracker_trt --ros-args -p drive_only:=true > /tmp/tracker.log 2>&1 &"

# Original V1 (own camera — kills TRT server camera access):
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && export LD_PRELOAD='/home/mic-711/miniforge3/envs/ros_env/lib/libstdc++.so.6:/home/mic-711/miniforge3/envs/ros_env/lib/python3.11/site-packages/torch/lib/libc10.so:/home/mic-711/miniforge3/envs/ros_env/lib/libgomp.so.1' && cd ~/reclaim_ws && source install/setup.bash && nohup ros2 run reclaim_bringup waste_tracker --ros-args --params-file src/reclaim_bringup/config/waste_tracker.yaml > /tmp/tracker.log 2>&1 &"
```

---

## STOP

### Stop tracker only (bridge keeps running)
```bash
ssh mic "pkill -9 -f waste_tracker"
```

### Stop everything
```bash
ssh mic "pkill -9 -f waste_tracker; pkill -9 -f teensy_bridge; for p in /dev/ttyACM*; do echo 'ESTOP' > \$p 2>/dev/null; done"; echo "Stopped."
```

### Emergency stop (instant motor kill, no process kill)
```bash
ssh mic "for p in /dev/ttyACM*; do echo 'ESTOP' > \$p 2>/dev/null; done"
```

---

## START TRT SERVER (if friend isn't running it)

```bash
ssh mic "nohup env -i HOME=/home/mic-711 PATH=/usr/local/bin:/usr/bin:/bin /usr/bin/python3.8 ~/reclaim_ws/tests/camera_detect_trt.py --model models/waste_yolo11n_v3_best.engine --conf 0.15 --port 8081 > /tmp/trt_server.log 2>&1 &"; \
sleep 5; ssh mic "tail -5 /tmp/trt_server.log"
```

### Stop TRT server
```bash
ssh mic "pkill -9 -f camera_detect_trt"
```

### Check TRT server
```bash
ssh mic "curl -s http://localhost:8081/detection" | python3 -m json.tool
```

---

## VIEW CAMERA

### Browser (Mac)
Open `http://192.168.2.2:8081` — live MJPEG from TRT server with bounding boxes.

If that doesn't work, use SSH tunnel:
```bash
ssh -f -N -L 8081:localhost:8081 mic
# Then open http://localhost:8081
```

### Foxglove (for V1 only — V1 publishes debug image to ROS2)
```bash
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && nohup ros2 launch foxglove_bridge foxglove_bridge_launch.xml > /tmp/foxglove.log 2>&1 &"
# Open Foxglove Studio → ws://192.168.2.2:8765 → Image panel → /perception/debug_image
```

---

## MONITORING

### Live tracker log
```bash
ssh mic "tail -f /tmp/tracker.log"
```

### Live diagnostics dashboard (TRT V2 only)
```bash
python3 diag_monitor.py
```
Shows: state, target, depth, pixel offset bar, motor commands, detection rate, lost count.
Auto-saves to `diag_log_*.jsonl` on your Mac.

### Check tuning log (TRT V2 only — on MIC-711)
```bash
# View current tuning parameters
ssh mic "cat /tmp/tracker_tuning_params.txt"

# Download tuning CSV to Mac for analysis
scp mic:/tmp/tracker_tuning.csv ~/Documents/RECLAIM/
```

### Run summary (TRT V2 — printed automatically when run completes)
Look for `RUN SUMMARY` in the tracker log after it reaches ALIGN/IDLE.

---

## RESCAN (restart state machine without restarting processes)

```bash
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && ros2 topic pub /rescan std_msgs/msg/String '{data: go}' -1"
```

---

## EDIT → SYNC → REBUILD → RESTART

### Sync TRT V2 only
```bash
# 1. Stop tracker
ssh mic "pkill -9 -f waste_tracker" 2>/dev/null; sleep 2

# 2. Sync file
rsync -avz ~/Documents/RECLAIM/reclaim_ws/src/reclaim_bringup/reclaim_bringup/waste_tracker_trt_v2.py \
  mic:~/reclaim_ws/src/reclaim_bringup/reclaim_bringup/

# 3. Build
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && cd ~/reclaim_ws && colcon build --packages-select reclaim_bringup --symlink-install"

# 4. Restart
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && cd ~/reclaim_ws && source install/setup.bash && nohup ros2 run reclaim_bringup waste_tracker_trt_v2 --ros-args -p drive_only:=true > /tmp/tracker.log 2>&1 &"; \
sleep 3; ssh mic "tail -5 /tmp/tracker.log"
```

### Sync V1 only
```bash
ssh mic "pkill -9 -f waste_tracker" 2>/dev/null; sleep 2; \
rsync -avz ~/Documents/RECLAIM/reclaim_ws/src/reclaim_bringup/reclaim_bringup/waste_tracker.py \
  mic:~/reclaim_ws/src/reclaim_bringup/reclaim_bringup/; \
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && cd ~/reclaim_ws && colcon build --packages-select reclaim_bringup"
```

### Sync camera server (DEPTH_MAX change)
```bash
rsync -avz ~/Documents/RECLAIM/reclaim_ws/tests/camera_detect_trt.py mic:~/reclaim_ws/tests/
```

### Full safe sync (excludes friend's files)
```bash
./sync.sh reclaim_bringup
```

---

## TELEOP & DIRECT MOTOR

### Keyboard teleop
```bash
ssh -t mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && ros2 run teleop_twist_keyboard teleop_twist_keyboard"
```
Keys: `i`=forward, `,`=back, `j`=left, `l`=right, `k`=stop, `q`/`z`=speed up/down

### Direct motor commands (bypasses ROS)
```bash
ssh mic "echo 'SETVEL 0.10 0.10' > \$(ls /dev/ttyACM* | head -1)"   # forward
ssh mic "echo 'SETVEL -0.10 0.10' > \$(ls /dev/ttyACM* | head -1)"  # spin left
ssh mic "echo 'SETVEL 0.0 0.0' > \$(ls /dev/ttyACM* | head -1)"     # stop
ssh mic "echo 'TICKS' > \$(ls /dev/ttyACM* | head -1)"               # read encoders
ssh mic "for p in /dev/ttyACM*; do echo 'ESTOP' > \$p 2>/dev/null; done"  # E-STOP
```

---

## CALIBRATION TESTS

### Straight line (0.5m at 0.1 m/s, sinusoidal profile)
```bash
scp ~/Documents/RECLAIM/reclaim_ws/tests/cal_straight.py mic:/tmp/ 2>/dev/null; \
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && cd ~/reclaim_ws && source install/setup.bash && python3 /tmp/cal_straight.py"
```

### 360° spin test
```bash
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && ros2 topic pub /cmd_vel geometry_msgs/msg/Twist '{angular: {z: 0.25}}' -r 10 --times 260"
# Then stop:
ssh mic "source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_env && ros2 topic pub /cmd_vel geometry_msgs/msg/Twist '{angular: {z: 0.0}}' -1"
```

---

## PROCESS CHECK

```bash
# What's running?
ssh mic "pgrep -fa 'waste_tracker\|teensy_bridge\|camera_detect\|foxglove'"

# What's holding the serial port?
ssh mic "ls -la /dev/ttyACM* 2>/dev/null && lsof /dev/ttyACM* 2>/dev/null"

# What's holding the camera?
ssh mic "lsof /dev/video* 2>/dev/null"
```

---

## TUNING REFERENCE

### TRT V2 — Code parameters (waste_tracker_trt_v2.py)
| Parameter | Value | Effect |
|-----------|-------|--------|
| `pid_kp` | 0.0012 | Higher = faster centering, more jitter |
| `pid_ki` | 0.0 | Disabled (causes drift) |
| `pid_kd` | 0.0 | Disabled (amplifies noise) |
| `angular_alpha` | 0.45 | EMA smoothing — lower = smoother, more lag |
| `angular_ramp_rate` | 0.6 | Angular accel limit — lower = smoother starts |
| `angular_deadband` | 0.015 | Smooth taper zone — lower = more responsive |
| `bbox_alpha` | 0.5 | Bbox smoothing — lower = less flicker, more lag |
| `Kalman Q` | 2.0 | Process noise — higher = more responsive |
| `Kalman R` | 10.0 | Measurement noise — lower = trust data more |
| `target_lost_threshold` | 30 | Frames before rescan (1s at 30fps) |
| `det_hold_max` | 4 | Hold detection during gaps (133ms) |
| `confirm_threshold` | 3 | Frames to confirm target |
| `approach_max_v` | 0.12 | Max forward speed (m/s) |
| `scan_vel` | 0.3 | Scan rotation speed (rad/s) |

### V1 — Code parameters (waste_tracker.py)
| Parameter | Value | Effect |
|-----------|-------|--------|
| `pid_kp` | 0.0010 | Proportional gain |
| `pid_ki` | 0.00008 | Integral gain (steady-state fix) |
| `pid_kd` | 0.0006 | Derivative gain (damping) |
| `angular_alpha` | 0.25 | Heavier EMA (noisier 10fps data) |
| `angular_ramp_rate` | 0.3 | Lower ramp for 20Hz tick |

### TRT Server — CLI args
| Arg | Default | Effect |
|-----|---------|--------|
| `--conf` | 0.35 | YOLO threshold (try 0.15 for more detections) |
| `--burst` | 5 | Depth averaging frames |
| `--port` | 8081 | HTTP port |
| `--model` | waste_yolo11n_v3_best.engine | Model path |

---

## AVAILABLE TRACKERS

| Command | Description | Camera | FPS |
|---------|-------------|--------|-----|
| `waste_tracker` | V1 original | Own OAK-D | ~10 |
| `waste_tracker_v2` | Experimental stop-look-drive | Own OAK-D | ~10 |
| `waste_tracker_trt` | TRT V1 (conservative) | TRT server | 30 |
| `waste_tracker_trt_v2` | TRT V2 (optimized) | TRT server | 30 |

**Note:** V1/V2 (own camera) and TRT trackers are mutually exclusive for the camera.
If TRT server is running, use `waste_tracker_trt` or `waste_tracker_trt_v2`.
If running V1/V2, the TRT server must NOT be running (both can't access OAK-D).
