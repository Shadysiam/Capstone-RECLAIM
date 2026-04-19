# Camera Placement Plan — RECLAIM

> Decisions and specs for mounting the OAK-D Lite on the robot. Read this before designing the mount in CAD.

## Decision: Front Base Plate Mount (Eye-to-Hand)

Mount the OAK-D Lite on the front face of the arm base plate, below J1. The camera is fixed to the robot chassis (not the arm itself), so it does not move when the arm moves.

**Why eye-to-hand over eye-in-hand:**
- Simpler calibration (one static transform instead of a moving kinematic chain)
- Camera only needs a clear view before the arm moves
- Less wiring complexity, no cable routing through rotating joints

**Workflow:**
1. Robot drives toward waste, stops ~50cm away
2. Camera captures scene while arm is in home position (clear FOV)
3. YOLO detects waste, stereo depth gives 3D coordinates
4. Coordinates transformed from camera frame to arm base frame via static TF
5. Arm moves to pick. Camera view is occluded by the arm during pickup, but we already have the coordinates we need.

## Camera Selection

**OAK-D Lite, Auto-Focus version recommended.**

Reason: Objects will be at 30-50cm from the camera during pickup. Auto-focus handles close-range better. Fixed-focus is optimized for 50cm+ and vibrating platforms (not our use case).

## Depth Range Constraint

From Luxonis documentation (OAK-D Lite, 480P extended disparity):

| Range | Accuracy | Notes |
|-------|----------|-------|
| 20-40cm | Works but >2% error | Absolute minimum depth range |
| **40cm - 3m** | **Sub-2% error** | **Ideal operating range** |
| >3m | Increasing error | Not relevant for pickup |

**This means the camera-to-waste distance should be >= 40cm for reliable depth.** Mounting low on the base plate may put objects at only ~30cm, which is below ideal. Two options:

### Option A: Low Mount (Base Plate)
- Camera at ~15cm above ground
- Object on ground at ~30cm from camera
- Marginal depth accuracy, but may be acceptable for pickup (we only need ~2cm precision for gripper alignment)
- Simplest mechanically

### Option B: Tower Mount (Behind Arm)
- Camera on a vertical post behind the arm, ~40cm above ground
- Tilted ~45 degrees downward
- Object on ground at ~47cm from camera (within ideal range)
- Better depth accuracy
- More complex mechanically, adds height to robot

**Current plan: Try Option A first.** Test depth accuracy at 30cm using `camera_detect.py`. If depth error is too large for reliable pickup, switch to Option B.

## OAK-D Lite Mounting Hardware

- **Back panel:** 2x M4 screw holes, 75mm VESA spacing (center-to-center)
- **Bottom:** 1x 1/4-20 UNC tripod mount
- **Camera dimensions:** ~91 x 28 x 17.5mm
- **Stereo baseline:** 7.5cm

For the base plate mount, the 1/4-20 tripod mount on the bottom is probably easiest. A simple L-bracket with a 1/4-20 bolt would work.

## Camera Intrinsics (for depth-to-3D conversion)

OAK-D Lite specs:
- RGB: 4208x3120, 81 DFOV
- Stereo: 640x480, 73 HFOV, 58 VFOV (per mono camera)
- Combined: ~69 HFOV, ~54 VFOV for depth

Exact intrinsics (fx, fy, cx, cy) are device-specific and read at runtime from the camera's EEPROM via DepthAI API.

## Static Transform: Camera to J1

This transform needs to be measured after the mount is built and the arm is assembled in CAD.

```
# Transform chain
map -> odom -> base_link -> camera_link -> camera_optical_frame

# The static TF we need to define:
base_link -> camera_link
```

**To measure:** Once the mount is CAD'd, extract the (x, y, z) offset and (roll, pitch, yaw) rotation from the camera optical center to the J1 rotation axis. This goes into a static transform publisher in the launch file.

## CAD Tasks

1. **Design camera mount bracket** — L-bracket or plate that attaches to arm base plate, holds OAK-D Lite via 1/4-20 bolt or M4 screws
2. **Model OAK-D Lite** — Use dimensions from Luxonis (91 x 28 x 17.5mm, 7.5cm baseline, mounting holes)
3. **Integrate into full arm assembly CAD** — Position camera mount on base plate, verify no collision with arm in home position and during pickup sequence
4. **Extract camera-to-J1 transform** — Measure offset from CAD for the static TF
5. **Verify FOV clearance** — Ensure the camera's 69x54 degree FOV covers the ground area in front of the robot at the expected pickup distance

## Open Questions

- Exact chassis height (depends on final frame design with 7" wheels)
- Whether 30cm depth accuracy is good enough (test empirically)
- Camera tilt angle (0 degrees = horizontal, need slight downward tilt to see ground)
- Cable routing from camera to MIC-711 (USB3 cable, max ~3m)
