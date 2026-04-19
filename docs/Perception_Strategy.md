# Perception Strategy — RECLAIM

> This doc captures all research, decisions, and implementation details for the perception pipeline. Every perception-related agent should read this before writing code.

## Problem Statement

First training attempt (Approach 1) failed badly:
- Recyclable AP50 = 0.45
- Compost AP50 = 0.00
- Landfill AP50 = 0.02

**Root cause: data imbalance, NOT model architecture.** TACO has almost no compost images, and Flickr download links are broken. The 3-class broad taxonomy (recyclable/compost/landfill) is also visually incoherent. "Recyclable" covers glass bottles, aluminum cans, and cardboard, which share no visual features.

## Key Decision: Fine-Grained Classes Mapped to Bins

**Train on 10-15 specific item classes, then map to bins via a lookup table.** This is strongly supported by the literature and gives three advantages:
1. Better per-class accuracy from visually coherent classes
2. Flexibility to change bin assignments without retraining
3. More interpretable results for demo

```python
BIN_MAP = {
    # Recyclable bin
    'plastic_bottle': 'recyclable', 'aluminum_can': 'recyclable',
    'glass_bottle': 'recyclable', 'cardboard': 'recyclable',
    'paper': 'recyclable', 'metal_lid': 'recyclable',
    # Compost bin
    'banana_peel': 'compost', 'food_waste': 'compost',
    'napkin': 'compost', 'paper_cup': 'compost',
    # Landfill bin
    'chip_bag': 'landfill', 'wrapper': 'landfill',
    'styrofoam': 'landfill', 'plastic_bag': 'landfill',
    'cigarette': 'landfill',
}
```

This taxonomy can be adjusted based on what datasets are available. The exact classes matter less than having visually distinct, balanced classes.

## Datasets to Use

| Dataset | Images | Classes | Why |
|---------|--------|---------|-----|
| **detect-waste (merged)** | 28,000+ | 7 unified | Best merged corpus, includes TACO + 6 others. `github.com/wimlds-trojmiasto/detect-waste` |
| **GARBAGE CLASSIFICATION 3 (Roboflow)** | 10,000+ | 7 material types | `universe.roboflow.com/material-identification/garbage-classification-3` |
| **Drinking Waste** | 9,640 | 4 beverage containers | Good for recyclable bottles/cans. `kaggle.com/datasets/arkadiyhacks/drinking-waste-classification` |
| **RealWaste** | 4,752 | 9 classes inc. food organics | Critical for compost class. `archive.ics.uci.edu/dataset/908/realwaste` |
| **ZeroWaste (CVPR 2022)** | 4,503 | 4 recyclable types | `github.com/dbash/zerowaste` |

**For merging datasets:** Use FiftyOne (`pip install fiftyone`) for format conversion and dataset merging.

**Minimum target: 300 images per class.** Duplicate/augment minority classes to reach this.

## Training Configuration (YOLOv8n)

```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")  # COCO pretrained
model.train(
    data="waste.yaml",
    epochs=100,
    imgsz=640,
    fl_gamma=1.5,          # Enable focal loss (default 0.0 = disabled)
    image_weights=True,     # Sample images by class frequency
    copy_paste=0.3,         # Paste minority instances into other images
    mosaic=1.0,             # Combines 4 images — increases minority exposure
    mixup=0.15,             # Blend images together
    optimizer='AdamW',      # Better than SGD for small datasets
    lr0=0.001,              # Lower LR for fine-tuning
    freeze=10,              # Freeze backbone for first pass (30 epochs), then unfreeze
    patience=50,            # Early stopping
)
```

**Key augmentation**: `copy_paste=0.3` is the single most impactful technique for long-tail class distributions (CVPR 2021, Ghiasi et al.).

**Offline augmentation for minority classes** (3-5x copies using Albumentations):
```python
import albumentations as A
transform = A.Compose([
    A.RandomBrightnessContrast(p=0.5),
    A.GaussNoise(p=0.3),
    A.MotionBlur(blur_limit=7, p=0.3),
    A.RandomShadow(p=0.3),
    A.CLAHE(p=0.3),
], bbox_params=A.BboxParams(format='yolo'))
```

**Target accuracy: mAP50 >= 0.70.** Published results show 0.70-0.85 is achievable with balanced data on YOLOv8n.

## Fallback: Two-Stage Pipeline

If single-stage YOLO underperforms after fixing data:
1. Train YOLOv8 as binary "waste" vs "background" detector (high recall)
2. Crop detected regions
3. Classify crops with MobileNetV2 trained on balanced image-level datasets
4. This approach achieved 97.8% classification accuracy (Edge Impulse) and 70% AP + 75% classification (detect-waste project)

## OAK-D Lite Depth Pipeline

### SpatialDetectionNetwork (Recommended)

The OAK-D Lite can run YOLO + stereo depth on-device, outputting (X, Y, Z) in millimeters for every detection. This is the recommended approach.

**On-device performance:**
- YOLOv8n @ 416x416: ~31 FPS on Myriad X
- YOLOv8n @ 640x640: ~14 FPS on Myriad X

**Depth accuracy:** <2% error within 3m (±2cm at 1m, ±4cm at 2m). Min depth ~35cm standard, ~20cm with extended disparity. Sufficient for pickup at 0.5-2.0m.

**To use SpatialDetectionNetwork, the model must be converted to .blob format:**
```bash
# Export to ONNX
yolo export model=best.pt format=onnx imgsz=416 simplify=True opset=12

# Convert to blob via blobconverter
pip install blobconverter
```
```python
import blobconverter
blob_path = blobconverter.from_onnx(
    model="best.onnx",
    data_type="FP16",
    shaves=6,
    optimizer_params=["--mean_values=[0,0,0]", "--scale_values=[255,255,255]"]
)
```

Or use Luxonis online tool: `tools.luxonis.com`

**Critical: Use ONNX opset 12 and OpenVINO 2021.4** for best Myriad X compatibility.

### Alternative: YOLO on Jetson GPU + Depth from OAK-D

If SpatialDetectionNetwork doesn't work (e.g., blob conversion fails):
- Stream RGB + depth from OAK-D to Jetson
- Run YOLO on Jetson GPU with TensorRT (~52-66 FPS at 640x640)
- Sample depth at bounding box center
- Convert pixel (cx, cy, z_mm) to 3D using camera intrinsics

This adds complexity (manual depth sampling, RGB-depth alignment) but gives more flexibility with model choice.

### Jetson TensorRT Benchmarks (Orin NX)

| Model | Precision | Resolution | FPS | mAP50 (COCO) |
|-------|-----------|-----------|-----|---------------|
| YOLOv8n | FP16 | 640x640 | ~52 | 52.5 |
| YOLOv8n | INT8 | 640x640 | ~66 | ~51.5 |
| YOLOv8s | FP16 | 640x640 | ~35 | 61.8 |

Export for TensorRT:
```python
model = YOLO("best.pt")
model.export(format="engine", imgsz=640, half=True, int8=True, device=0)
```

## YOLO26 Status: DO NOT USE YET

YOLO26n is ~3 mAP points better than YOLOv8n but:
- **Myriad X .blob compatibility is UNVERIFIED** as of March 2026
- Luxonis tools.luxonis.com does not list YOLO26 support
- NMS-free output tensor format may break DepthAI's YOLO parser
- The 3 mAP gain is negligible compared to 20-30 point gain from data fixes

**Decision: Stick with YOLOv8n for the demo.** Only switch if someone verifies blob conversion works.

## DepthAI v3 API Reminders

DepthAI 3.3.0 is installed. The v3 API is different from v2. See CLAUDE.md for the full v2→v3 migration reference.

**NOTE:** The SpatialDetectionNetwork code examples in the research doc use v2 API patterns (ColorCamera, XLinkOut, setBoardSocket, etc.). These WILL NOT WORK with DepthAI v3. When implementing SpatialDetectionNetwork, check DepthAI v3 docs at `docs.luxonis.com/software-v3/depthai/` for the correct v3 equivalents. The concepts are the same but the method names changed.

## Coordinate Transform: Camera → Robot

Transform chain: `map → odom → base_link → camera_link → camera_optical_frame`

- `map → odom`: from SLAM Toolbox / AMCL
- `odom → base_link`: from wheel odometry (Teensy encoders)
- `base_link → camera_link`: static transform (camera mount position)
- `camera_link → camera_optical_frame`: automatic from depthai-ros URDF

```python
import tf2_ros
from geometry_msgs.msg import PointStamped

tf_buffer = tf2_ros.Buffer()
tf_listener = tf2_ros.TransformListener(tf_buffer, node)

# Transform detection from camera frame to map frame
point = PointStamped()
point.header.frame_id = 'oak_rgb_camera_optical_frame'
point.point.x, point.point.y, point.point.z = x_cam, y_cam, z_cam
map_point = tf_buffer.transform(point, 'map', timeout=Duration(seconds=1.0))
```

## Navigation to Waste

Use `nav2_simple_commander` to navigate to 0.5m from detected waste, then visual servo for final alignment using YOLO bounding box centering via `/cmd_vel`.

## Arm Pickup Strategy

**UPDATE (March 2026): Pursuing MoveIt2 for IK-based picking.**

The original plan was to skip MoveIt2 and use pre-defined joint poses only. We're now pursuing MoveIt2 so the arm can compute inverse kinematics to reach arbitrary 3D positions detected by the camera. The pre-defined pose sequences (PICKUP command in firmware) remain as a fallback.

**Full pipeline:**
1. Camera detects waste via YOLO, stereo depth gives 3D position in camera frame
2. tf2 transforms coordinates from camera frame to arm base frame (static transform)
3. MoveIt2 computes IK solution for the target position
4. ros2_control hardware interface sends joint commands to Teensy via serial
5. Gripper closes (angle determined by object class or bounding box width)
6. Arm lifts and moves to appropriate bin using pre-defined bin poses

**Fallback (if MoveIt2 timeline slips):** Use pre-defined pose sequences with the PICKUP firmware command. Robot drives to ~30cm from waste, arm executes fixed pick sequence. Less precise but already working.

See `Camera_Placement_Plan.md` for camera mounting details and the camera-to-arm transform.

## Reference Repos

| Repo | Why it's useful |
|------|----------------|
| **MARIO-COM** (`github.com/bharadwaj-chukkala/MARIO-COM`) | Closest match: ROS2 + TurtleBot3 + Nav2 + arm pickup |
| **detect-waste** (`github.com/wimlds-trojmiasto/detect-waste`) | Best merged dataset + training scripts |
| **RoboSort** (`github.com/qppd/robo-sort`) | YOLO + LIDAR + 6DOF arm, serial protocol |
| **Trash Sorting Robot** (`github.com/bandofpv/Trash-Sorting-Robot`) | SSD + RPi + Dobot Arm, full BOM |
| **WasteGAN** (`github.com/bach05/wastegan`) | Synthetic data for rare waste classes (+30% minority improvement) |
| **Waste Detection YOLOv8** (`github.com/boss4848/waste-detection`) | YOLOv8 + Streamlit + Colab notebook |
