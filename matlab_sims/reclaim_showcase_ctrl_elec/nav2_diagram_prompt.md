# Nav2 Product Control Architecture — Diagram Prompt
# Send this to Claude to generate the product controls visual

---

## PROMPT

Create a clean, professional vertical control architecture diagram for a capstone engineering
presentation slide. This is for RECLAIM — an autonomous indoor waste collection robot.

The diagram must visually match a Simulink block diagram aesthetic — clean rectangular boxes,
simple directional arrows, minimal decoration, engineering-style labels. No gradients, no 3D
effects, no icons.

---

## COLOUR PALETTE (use exactly these hex values)

Software layers:  fill #EFF6FF (very light blue),  border #2563EB (blue),  2px solid
Hardware layers:  fill #F3F4F6 (light grey),        border #374151 (dark grey), 2px solid
Arm sidebar:      fill #FFFBEB (light amber),        border #D97706 (amber),    2px dashed
Signal arrows:    colour #374151 (dark grey), 1.5px, small filled arrowhead
Signal labels:    colour #16A34A (dark green), italic, 9pt, beside each arrow
Background:       white #FFFFFF
Font:             Helvetica or Arial throughout (matches Simulink default font)

---

## DIAGRAM CONTENT

Title above diagram (bold, 13pt, #1a1a2e):
"RECLAIM PRODUCT — Nav2 Autonomy Stack"

LAYERS — stacked vertically, each box 580px wide, 85px tall, 6px rounded corners:

BOX 1 — SOFTWARE — blue fill/border:
  Title (bold 11pt): "Behaviour Tree  |  ROS2 Nav2"
  Body (10pt): "Mission orchestration: Navigate → Detect → Pick → Sort → Repeat"

  ↓ arrow, label: "goal pose  (x, y, θ)"

BOX 2 — SOFTWARE — blue fill/border:
  Title (bold 11pt): "SLAM Toolbox  +  Livox Mid-360 3D LiDAR"
  Body (10pt): "Occupancy grid mapping  |  Particle filter localisation"

  ↓ arrow, label: "costmap  +  robot pose"

BOX 3 — SOFTWARE — blue fill/border:
  Title (bold 11pt): "Global Planner  (Smac / A*)"
  Body (10pt): "Static layer  |  Obstacle layer  |  Inflation layer (robot footprint)"

  ↓ arrow, label: "reference path"

BOX 4 — SOFTWARE — blue fill/border:
  Title (bold 11pt): "Local Controller  —  Regulated Pure Pursuit"
  Body (10pt): "Lookahead distance  |  Curvature limiting  |  Velocity scaling near obstacles"

  ↓ arrow, label: "cmd_vel  (geometry_msgs/Twist)"

BOX 5 — HARDWARE — grey fill/border:
  Title (bold 11pt): "STM32F405  |  PI Velocity Controller  @  1 kHz"
  Body (10pt): "Kp, Ki per wheel  |  Feed-forward Kf  |  DRV8243 motor drivers"

  ↓ arrow, label: "PWM  0–255"
  ↑ arrow (feedback, right side), label: "encoder ticks  @  100 Hz"

BOX 6 — HARDWARE — grey fill/border:
  Title (bold 11pt): "Pololu 37D  12V  100:1  +  Quadrature Encoders"
  Body (10pt): "64 CPR × 100:1 = 6400 ticks/rev  |  Odometry → /odom"

---

ARM SIDEBAR — amber fill/dashed border:
Position: to the RIGHT of boxes 4 and 5, vertically spanning same height, 160px wide

Content (10pt, top to bottom):
  ARM SUBSYSTEM
  ─────────────
  OAK-D Pro
  Eye-in-hand

  YOLOv8n
  30 fps TensorRT

  6DOF CubeMars
  Actuators

  CAN Bus 1 Mbit/s
  STM32 CAN1
  SN65HVD230

Dashed horizontal arrow FROM Box 4 TO sidebar top, label: "pick trigger"
Dashed horizontal arrow FROM sidebar bottom TO Box 5, label: "arm done"

---

LEGEND — bottom right, small (9pt):
  ■ blue = Software layer
  ■ grey = Hardware layer
  ■ amber dashed = Arm subsystem
  → solid = ROS2 topic / signal
  ⇢ dashed = subsystem trigger

---

## OUTPUT REQUIREMENTS

- Output as Python code using matplotlib that generates a high-resolution PNG (300 DPI)
- Save as: reclaim_product_nav2_diagram.png
- Total diagram size: 800px × 1000px at 96dpi (renders as ~8.3 × 10.4 inches at 96dpi)
- Do NOT use placeholder text — use exactly the layer content specified above
- All text must be fully readable at 100% zoom — no overlapping, no clipping
- Boxes must have consistent spacing: 20px gap between each layer box
