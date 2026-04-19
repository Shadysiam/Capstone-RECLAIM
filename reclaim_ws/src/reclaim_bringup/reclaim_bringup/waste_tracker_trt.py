#!/usr/bin/env python3
"""
waste_tracker_trt.py — TRT API version of the waste tracker.

Same autonomous state machine as waste_tracker.py, but polls the TRT detection
server's HTTP API at localhost:8081/detection instead of running its own camera.

The TRT server (Python 3.8 + TensorRT) runs camera + YOLO at 30 FPS.
This node handles DRIVING ONLY (SCAN → TURN → APPROACH → ALIGN).
Arm pickup is handled by pick_and_place.py via /pickup_request topic.

Data flow:
  TRT server (30 FPS) → HTTP /detection → this node → /cmd_vel → motors
  After ALIGN: publishes /pickup_request → pick_and_place.py handles arm

Usage:
  ros2 run reclaim_bringup waste_tracker_trt --ros-args \
      -p trt_url:=http://localhost:8081 \
      -p drive_only:=true

Authors: Shady Siam, Issa Ahmed
"""

from __future__ import annotations

import json
import math
import threading
import time
import urllib.request
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple

import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import String


# ══════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════

CLASS_NAMES = {
    0: 'plastic_bottle', 1: 'aluminum_can', 2: 'cardboard',
    3: 'plastic_container', 4: 'cup', 5: 'chip_bag',
    6: 'styrofoam_container', 7: 'napkin', 8: 'paper_bag',
    9: 'apple', 10: 'orange',
}

BIN_MAP = {
    'plastic_bottle': 'recyclable', 'aluminum_can': 'recyclable',
    'cardboard': 'recyclable', 'plastic_container': 'recyclable',
    'cup': 'landfill', 'chip_bag': 'landfill',
    'styrofoam_container': 'landfill', 'napkin': 'compost',
    'paper_bag': 'compost', 'apple': 'compost', 'orange': 'compost',
}


class State(Enum):
    IDLE = auto()
    SCAN = auto()
    TURN_TO_TARGET = auto()
    APPROACH = auto()
    ALIGN = auto()
    PICK = auto()


@dataclass
class Detection:
    """A single detected waste item with 3D position."""
    class_name: str
    confidence: float
    cam_x: float
    cam_y: float
    cam_z: float
    robot_x: float
    robot_y: float
    robot_z: float
    cx_px: int
    cy_px: int
    bbox_w: float
    bbox_h: float

    @property
    def distance_mm(self) -> float:
        """Use cam_z (depth) for driving distance — base_link coords only valid at arm home pose."""
        return self.cam_z

    @property
    def bearing_rad(self) -> float:
        """Approximate bearing from pixel offset — used for scan sorting only."""
        return math.atan2(self.cam_x, self.cam_z) if self.cam_z > 0 else 0.0


# ══════════════════════════════════════════════════════════════════════
#  WasteTracker ROS2 Node
# ══════════════════════════════════════════════════════════════════════

class WasteTracker(Node):
    def __init__(self):
        super().__init__('waste_tracker')

        # ── ROS Parameters ────────────────────────────────────────────
        self.declare_parameter('trt_url', 'http://localhost:8081')
        self.declare_parameter('confidence', 0.35)
        self.declare_parameter('poll_rate_hz', 20.0)

        # SCAN parameters
        self.declare_parameter('scan_angular_vel', 0.3)
        self.declare_parameter('scan_full_rotation', 6.28)

        # APPROACH parameters
        self.declare_parameter('approach_linear_vel', 0.12)
        self.declare_parameter('approach_angular_gain', 0.003)
        self.declare_parameter('approach_linear_gain', 0.0003)
        self.declare_parameter('approach_stop_distance_mm', 400.0)

        # ALIGN parameters
        self.declare_parameter('align_pixel_tolerance', 30)
        self.declare_parameter('align_angular_vel', 0.15)
        self.declare_parameter('align_stable_frames', 5)
        self.declare_parameter('align_min_depth_mm', 150.0)
        self.declare_parameter('align_max_depth_mm', 450.0)

        # Obstacle avoidance
        self.declare_parameter('obstacle_min_depth_mm', 300.0)
        self.declare_parameter('drive_only', True)  # Default: driving only, arm handled separately

        # ── Read parameters ───────────────────────────────────────────
        self.trt_url = self.get_parameter('trt_url').value.rstrip('/')
        self.confidence = self.get_parameter('confidence').value
        self.poll_rate_hz = self.get_parameter('poll_rate_hz').value
        self.last_trt_timestamp = 0.0

        self.scan_vel = self.get_parameter('scan_angular_vel').value
        self.scan_target = self.get_parameter('scan_full_rotation').value

        self.approach_max_v = self.get_parameter('approach_linear_vel').value
        self.approach_w_gain = self.get_parameter('approach_angular_gain').value
        self.approach_v_gain = self.get_parameter('approach_linear_gain').value
        self.approach_stop_dist = self.get_parameter('approach_stop_distance_mm').value

        self.align_px_tol = self.get_parameter('align_pixel_tolerance').value
        self.align_w = self.get_parameter('align_angular_vel').value
        self.align_stable_needed = self.get_parameter('align_stable_frames').value
        self.align_min_depth = self.get_parameter('align_min_depth_mm').value
        self.align_max_depth = self.get_parameter('align_max_depth_mm').value

        self.obstacle_min = self.get_parameter('obstacle_min_depth_mm').value
        self.drive_only = self.get_parameter('drive_only').value

        # ── State machine ─────────────────────────────────────────────
        self.state = State.IDLE
        self.scan_start_yaw = 0.0
        self.scan_accumulated = 0.0
        self.scan_detections: List[Detection] = []
        self.current_target: Optional[Detection] = None
        self.align_stable_count = 0
        self.current_yaw = 0.0
        self.prev_yaw = None
        self.items_collected = 0
        self.drive_only_done = False
        self.filtered_angular_z = 0.0
        self.last_angular_z = 0.0
        self.target_lost_count = 0
        self.target_lost_threshold = 50

        # Detection confirmation
        self.confirm_count = 0
        self.confirm_threshold = 3
        self.confirm_candidate = None

        # Smoothing constants
        self.angular_deadband = 0.02
        self.angular_ramp_rate = 0.3
        self.angular_alpha = 0.18

        # PID controller
        self.pid_integral = 0.0
        self.pid_prev_error = 0.0
        self.pid_kp = 0.0010
        self.pid_ki = 0.00004
        self.pid_kd = 0.0004
        self.pid_integral_max = 50.0
        self.pid_dt = 0.05

        # Kalman filter
        if HAS_CV2:
            self._init_kalman()

        # Camera state
        self.camera_lock = threading.Lock()
        self.latest_detections: List[Detection] = []
        self.obstacle_ahead = False
        self.camera_ready = False
        self.camera_frame_count = 0
        self.image_width = 640
        self.image_height = 480

        # ── ROS publishers / subscribers ──────────────────────────────
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.state_pub = self.create_publisher(String, '/robot_state', 10)
        self.pickup_pub = self.create_publisher(String, '/pickup_request', 10)

        self.create_subscription(Odometry, '/odom', self._odom_cb, 10)
        self.create_subscription(String, '/rescan', self._rescan_cb, 10)

        # ── Timers ────────────────────────────────────────────────────
        self.create_timer(0.05, self._tick)
        self.create_timer(0.5, self._publish_state)

        # ── Start TRT polling thread ──────────────────────────────────
        self.camera_thread = threading.Thread(target=self._trt_poll_loop, daemon=True)
        self.camera_thread.start()

        self.get_logger().info(
            f'WasteTracker TRT: url={self.trt_url}, '
            f'conf={self.confidence}, poll={self.poll_rate_hz}Hz, '
            f'drive_only={self.drive_only}')

    # ==================================================================
    #  Callbacks
    # ==================================================================

    def _rescan_cb(self, msg: String):
        self.get_logger().info('=== RESCAN triggered ===')
        self._stop_motors()
        self.drive_only_done = False
        self.target_lost_count = 0
        self.current_target = None
        self._pid_reset()
        if HAS_CV2:
            self._kalman_reset()
        self._enter_scan()

    def _odom_cb(self, msg: Odometry):
        q = msg.pose.pose.orientation
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self.current_yaw = math.atan2(siny, cosy)

    # ==================================================================
    #  TRT polling thread
    # ==================================================================

    def _trt_poll_loop(self):
        poll_interval = 1.0 / self.poll_rate_hz
        detection_url = f'{self.trt_url}/detection'
        connected = False
        consecutive_errors = 0

        while rclpy.ok():
            try:
                req = urllib.request.Request(detection_url)
                req.add_header('Connection', 'close')
                with urllib.request.urlopen(req, timeout=0.5) as resp:
                    data = json.loads(resp.read().decode())

                consecutive_errors = 0

                if not connected:
                    connected = True
                    self.camera_ready = True
                    self.get_logger().info(f'TRT server connected at {self.trt_url}')

                if data.get('status') == 'no_detection':
                    with self.camera_lock:
                        self.latest_detections = []
                        self.obstacle_ahead = False
                        self.camera_frame_count += 1
                    time.sleep(poll_interval)
                    continue

                ts = data.get('timestamp', 0.0)
                # Skip stale detections (same as last)
                if ts <= self.last_trt_timestamp:
                    time.sleep(poll_interval * 0.5)
                    continue
                # Skip old detections (older than 1 second)
                if time.time() - ts > 1.0:
                    with self.camera_lock:
                        self.latest_detections = []
                        self.camera_frame_count += 1
                    time.sleep(poll_interval)
                    continue
                self.last_trt_timestamp = ts

                conf = float(data.get('confidence', 0.0))
                class_name = data.get('class', 'unknown')

                cam_x = float(data.get('cam_x_mm', 0.0))
                cam_y = float(data.get('cam_y_mm', 0.0))
                cam_z = float(data.get('cam_z_mm', 0.0))

                robot_x = float(data.get('base_x_mm', 0.0))
                robot_y = float(data.get('base_y_mm', 0.0))
                robot_z = float(data.get('base_z_mm', 0.0))

                bbox = data.get('bbox', [0, 0, 0, 0])
                x1, y1, x2, y2 = bbox
                cx_px = int((x1 + x2) / 2)
                cy_px = int((y1 + y2) / 2)
                bbox_w = float(x2 - x1)
                bbox_h = float(y2 - y1)

                if cam_z < 1 or conf < 0.01:
                    with self.camera_lock:
                        self.latest_detections = []
                        self.obstacle_ahead = False
                        self.camera_frame_count += 1
                    time.sleep(poll_interval)
                    continue

                det = Detection(
                    class_name=class_name, confidence=conf,
                    cam_x=cam_x, cam_y=cam_y, cam_z=cam_z,
                    robot_x=robot_x, robot_y=robot_y, robot_z=robot_z,
                    cx_px=cx_px, cy_px=cy_px,
                    bbox_w=bbox_w, bbox_h=bbox_h,
                )

                # Filter: floor-level objects only
                img_area = self.image_width * self.image_height
                tracking = self.state in (State.TURN_TO_TARGET, State.APPROACH, State.ALIGN)
                max_depth = 3000 if tracking else 2500
                max_bbox_frac = 0.40 if tracking else 0.25
                min_cy_frac = 0.20 if tracking else 0.25

                detections = []
                passes_depth = det.cam_z < max_depth
                passes_cy = det.cy_px > self.image_height * min_cy_frac
                bbox_area = det.bbox_w * det.bbox_h
                passes_max_bbox = bbox_area < img_area * max_bbox_frac
                passes_min_bbox = bbox_area > img_area * 0.003

                if passes_depth and passes_cy and passes_max_bbox and passes_min_bbox:
                    detections.append(det)
                    if self.camera_frame_count % 20 == 0:
                        self.get_logger().info(
                            f'DET OK: {class_name} conf={conf:.2f} '
                            f'depth={det.cam_z:.0f}mm cx={cx_px} cy={cy_px}')
                elif self.camera_frame_count % 100 == 0:
                    self.get_logger().info(
                        f'FILTER REJECT: {class_name} conf={conf:.2f} '
                        f'depth={det.cam_z:.0f}({passes_depth}) '
                        f'cy={det.cy_px}({passes_cy}) '
                        f'bbox={bbox_area:.0f}({passes_max_bbox},{passes_min_bbox})')

                obstacle = cam_z > 0 and cam_z < self.obstacle_min

                with self.camera_lock:
                    self.latest_detections = detections
                    self.obstacle_ahead = obstacle
                    self.camera_frame_count += 1

            except urllib.error.URLError:
                consecutive_errors += 1
                if consecutive_errors == 1:
                    self.get_logger().warn(f'TRT server unreachable at {detection_url}')
                elif consecutive_errors % 100 == 0:
                    self.get_logger().warn(f'TRT server unreachable ({consecutive_errors} failures)')
            except json.JSONDecodeError as e:
                self.get_logger().warn(f'TRT API bad JSON: {e}')
            except Exception as e:
                self.get_logger().warn(f'TRT poll error: {e}')

            time.sleep(poll_interval)

    # ==================================================================
    #  State machine tick (20 Hz)
    # ==================================================================

    def _tick(self):
        if not self.camera_ready:
            return

        if self.state == State.IDLE and self.items_collected == 0 and not self.drive_only_done:
            self._enter_scan()
            return

        if self.state == State.SCAN:
            self._tick_scan()
        elif self.state == State.TURN_TO_TARGET:
            self._tick_turn_to_target()
        elif self.state == State.APPROACH:
            self._tick_approach()
        elif self.state == State.ALIGN:
            self._tick_align()

    # ── SCAN ──────────────────────────────────────────────────────────

    def _enter_scan(self):
        self.state = State.SCAN
        self.scan_start_yaw = self.current_yaw
        self.scan_accumulated = 0.0
        self.prev_yaw = self.current_yaw
        self.scan_detections.clear()
        self.confirm_count = 0
        self.confirm_candidate = None
        self.get_logger().info('=== SCAN: starting 360 rotation ===')

    def _tick_scan(self):
        if self.prev_yaw is not None:
            delta = self.current_yaw - self.prev_yaw
            delta = math.atan2(math.sin(delta), math.cos(delta))
            if abs(delta) > 0.005:
                if delta > 0:
                    self.scan_accumulated += delta
                else:
                    self.scan_accumulated += abs(delta) * 0.3
        self.prev_yaw = self.current_yaw

        with self.camera_lock:
            frame_dets = list(self.latest_detections)

        img_area = self.image_width * self.image_height
        frame_dets = [d for d in frame_dets
                      if d.cam_z < 2500
                      and d.cy_px > self.image_height * 0.25
                      and (d.bbox_w * d.bbox_h) < img_area * 0.25
                      and (d.bbox_w * d.bbox_h) > img_area * 0.002]

        for det in frame_dets:
            is_dup = False
            for existing in self.scan_detections:
                if (existing.class_name == det.class_name and
                        abs(existing.cam_z - det.cam_z) < 200):
                    if det.confidence > existing.confidence:
                        self.scan_detections.remove(existing)
                    else:
                        is_dup = True
                    break
            if not is_dup:
                self.scan_detections.append(det)

        if frame_dets:
            nearby = [d for d in frame_dets
                      if d.cam_z < 2500 and d.cy_px > self.image_height * 0.15]
            if nearby:
                best = min(nearby, key=lambda d: d.cam_z)
                if best.confidence >= 0.35:
                    if (self.confirm_candidate is not None and
                            best.class_name == self.confirm_candidate[0] and
                            abs(best.cx_px - self.confirm_candidate[1]) < 80 and
                            abs(best.cam_z - self.confirm_candidate[3]) < 500):
                        self.confirm_count += 1
                        self.confirm_candidate = (best.class_name, best.cx_px,
                                                   best.cy_px, best.cam_z)
                    else:
                        self.confirm_count = 1
                        self.confirm_candidate = (best.class_name, best.cx_px,
                                                   best.cy_px, best.cam_z)

                    if self.confirm_count >= self.confirm_threshold:
                        self._stop_motors()
                        self.current_target = best
                        self.confirm_count = 0
                        self.confirm_candidate = None
                        self.get_logger().info(
                            f'SCAN: locked on {best.class_name} '
                            f'(conf={best.confidence:.2f}, depth={best.cam_z:.0f}mm)')
                        self._enter_turn_to_target()
                        return
            else:
                self.confirm_count = 0
                self.confirm_candidate = None

        twist = Twist()
        if self.confirm_count > 0:
            twist.angular.z = self.scan_vel * 0.4
        else:
            twist.angular.z = self.scan_vel
        self.cmd_vel_pub.publish(twist)

        if self.scan_accumulated >= self.scan_target:
            self._stop_motors()
            if not self.scan_detections:
                self.get_logger().info('SCAN complete — no targets. Rescanning...')
                self._enter_scan()
                return
            self.scan_detections.sort(key=lambda d: d.distance_mm)
            self.current_target = self.scan_detections[0]
            self.get_logger().info(
                f'SCAN complete — {len(self.scan_detections)} targets. '
                f'Nearest: {self.current_target.class_name} '
                f'@ {self.current_target.distance_mm:.0f}mm')
            self._enter_turn_to_target()

    # ── TURN_TO_TARGET ────────────────────────────────────────────────

    def _enter_turn_to_target(self):
        self.state = State.TURN_TO_TARGET
        self.filtered_angular_z = 0.0
        self.last_angular_z = 0.0
        self.target_lost_count = 0
        self._pid_reset()
        if HAS_CV2:
            self._kalman_reset()
        self._stop_motors()
        self.get_logger().info(
            f'=== TURN_TO_TARGET: {self.current_target.class_name} ===')

    def _tick_turn_to_target(self):
        with self.camera_lock:
            frame_dets = list(self.latest_detections)

        target_det = self._find_target_in_detections(frame_dets)

        if target_det is None and frame_dets:
            target_class = self.current_target.class_name if self.current_target else None
            same_class = [d for d in frame_dets if d.class_name == target_class]
            if same_class:
                target_det = same_class[0]
            else:
                target_det = max(frame_dets, key=lambda d: d.confidence)

        if target_det is None:
            self.target_lost_count += 1
            if self.target_lost_count >= self.target_lost_threshold:
                self._stop_motors()
                self.get_logger().warn('TURN: target lost — rescanning')
                self._enter_scan()
            elif HAS_CV2:
                pred_cx, _ = self._kalman_predict()
                img_cx = self.image_width / 2.0
                pred_offset = max(-100, min(100, pred_cx - img_cx))
                if abs(pred_offset) > 20:
                    angular_z = self._pid_angular(pred_offset)
                    angular_z = max(-0.08, min(0.08, angular_z))
                    angular_z = self._smooth_angular(angular_z)
                    twist = Twist()
                    twist.angular.z = angular_z
                    self.cmd_vel_pub.publish(twist)
                else:
                    self._stop_motors()
            return

        self.target_lost_count = 0
        self.current_target = target_det

        if HAS_CV2:
            filtered_cx, _ = self._kalman_update(float(target_det.cx_px),
                                                  float(target_det.cy_px))
        else:
            filtered_cx = float(target_det.cx_px)

        img_cx = self.image_width / 2.0
        pixel_offset = filtered_cx - img_cx

        if abs(pixel_offset) > 20:
            corrected_offset = pixel_offset - 20.0 * (1.0 if pixel_offset > 0 else -1.0)
            raw_angular_z = self._pid_angular(corrected_offset)
            raw_angular_z = max(-0.12, min(0.12, raw_angular_z))
            angular_z = self._smooth_angular(raw_angular_z)
            twist = Twist()
            twist.angular.z = angular_z
            self.cmd_vel_pub.publish(twist)
        else:
            self._smooth_angular(0.0)
            self._stop_motors()
            self.get_logger().info(f'TURN: centered ({pixel_offset:.0f}px) → approach')
            self._enter_approach()

    # ── APPROACH ──────────────────────────────────────────────────────

    def _enter_approach(self):
        self.state = State.APPROACH
        self.filtered_angular_z = 0.0
        self.last_angular_z = 0.0
        self.target_lost_count = 0
        self._pid_reset()
        self._stop_motors()
        self.get_logger().info(
            f'=== APPROACH: {self.current_target.class_name} ===')

    def _tick_approach(self):
        with self.camera_lock:
            frame_dets = list(self.latest_detections)

        target_det = self._find_target_in_detections(frame_dets)

        if target_det is None:
            self.target_lost_count += 1
            if self.target_lost_count >= self.target_lost_threshold:
                self._stop_motors()
                last_depth = self.current_target.cam_z if self.current_target else 9999
                if last_depth < 500:
                    self.get_logger().info(
                        f'APPROACH: lost at close range ({last_depth:.0f}mm) — stopping')
                    if self.drive_only:
                        self.drive_only_done = True
                    self.state = State.IDLE
                else:
                    self.get_logger().warn('APPROACH: target lost — rescanning')
                    self._enter_scan()
            elif HAS_CV2:
                pred_cx, _ = self._kalman_predict()
                img_cx = self.image_width / 2.0
                pred_offset = max(-100, min(100, pred_cx - img_cx))
                angular_z = self._pid_angular(pred_offset)
                angular_z = max(-0.08, min(0.08, angular_z))
                angular_z = self._smooth_angular(angular_z)
                twist = Twist()
                twist.linear.x = 0.04
                twist.angular.z = angular_z
                self.cmd_vel_pub.publish(twist)
            return

        self.target_lost_count = 0
        self.current_target = target_det

        if HAS_CV2:
            filtered_cx, _ = self._kalman_update(float(target_det.cx_px),
                                                  float(target_det.cy_px))
        else:
            filtered_cx = float(target_det.cx_px)

        img_cx = self.image_width / 2.0
        pixel_offset = filtered_cx - img_cx

        if abs(pixel_offset) < 15:
            angular_z = self._smooth_angular(0.0)
        else:
            corrected_offset = pixel_offset - 15.0 * (1.0 if pixel_offset > 0 else -1.0)
            raw_angular_z = self._pid_angular(corrected_offset)
            raw_angular_z = max(-0.10, min(0.10, raw_angular_z))
            angular_z = self._smooth_angular(raw_angular_z)

        dist = target_det.cam_z
        if dist <= self.approach_stop_dist:
            self._stop_motors()
            self._enter_align()
            return

        dist_ratio = (dist - self.approach_stop_dist) / 1100.0
        dist_ratio = max(0.0, min(1.0, dist_ratio))
        linear_x = 0.04 + (self.approach_max_v - 0.04) * dist_ratio
        linear_x = max(0.04, min(self.approach_max_v, linear_x))

        twist = Twist()
        twist.linear.x = linear_x
        twist.angular.z = angular_z
        self.cmd_vel_pub.publish(twist)

    # ── ALIGN ─────────────────────────────────────────────────────────

    def _enter_align(self):
        self.state = State.ALIGN
        self.align_stable_count = 0
        self.align_lost_count = 0
        self.get_logger().info('=== ALIGN: fine-positioning ===')

    def _tick_align(self):
        with self.camera_lock:
            frame_dets = list(self.latest_detections)

        target_det = self._find_target_in_detections(frame_dets)

        if target_det is None and frame_dets:
            target_class = self.current_target.class_name if self.current_target else ''
            same_class = [d for d in frame_dets if d.class_name == target_class]
            if same_class:
                target_det = same_class[0]
            else:
                target_det = max(frame_dets, key=lambda d: d.confidence)

        if target_det is None:
            self.align_lost_count = getattr(self, 'align_lost_count', 0) + 1
            if self.align_lost_count >= 15:
                self._stop_motors()
                last_depth = self.current_target.cam_z if self.current_target else 9999
                if last_depth < 500:
                    self.get_logger().info(f'ALIGN: lost at close range — stopping')
                    if self.drive_only:
                        self.drive_only_done = True
                    self.state = State.IDLE
                else:
                    self.get_logger().warn('ALIGN: target lost — rescanning')
                    self._enter_scan()
            return

        self.align_lost_count = 0
        self.current_target = target_det

        if HAS_CV2:
            filtered_cx, _ = self._kalman_update(float(target_det.cx_px),
                                                  float(target_det.cy_px))
        else:
            filtered_cx = float(target_det.cx_px)

        img_cx = self.image_width / 2.0
        pixel_offset = filtered_cx - img_cx

        if abs(pixel_offset) > self.align_px_tol:
            angular_z = self._pid_angular(pixel_offset)
            angular_z = max(-self.align_w, min(self.align_w, angular_z))
            angular_z = self._smooth_angular(angular_z)
            twist = Twist()
            twist.angular.z = angular_z
            self.cmd_vel_pub.publish(twist)
            self.align_stable_count = 0
            return

        self._stop_motors()

        depth = target_det.cam_z
        if depth > self.align_max_depth:
            twist = Twist()
            twist.linear.x = 0.04
            self.cmd_vel_pub.publish(twist)
            self.align_stable_count = 0
            return

        self.align_stable_count += 1
        if self.align_stable_count >= self.align_stable_needed:
            self.get_logger().info(
                f'ALIGN: locked on {target_det.class_name} '
                f'@ {depth:.0f}mm, offset={pixel_offset:.0f}px')
            if self.drive_only:
                self.get_logger().info('ALIGN: drive_only — stopping (PICK disabled)')
                self._stop_motors()
                self.drive_only_done = True
                self.state = State.IDLE
            else:
                self._enter_pick()

    # ── PICK (publishes request for pick_and_place.py) ────────────────

    def _enter_pick(self):
        self.state = State.PICK
        self._stop_motors()

        target = self.current_target
        if target is None:
            self.get_logger().error('PICK: no target')
            self._enter_scan()
            return

        bin_name = BIN_MAP.get(target.class_name, 'landfill')
        self.get_logger().info(
            f'=== PICK: requesting pickup of {target.class_name} → {bin_name} ===')

        # Publish pickup request for pick_and_place.py to handle
        msg = String()
        msg.data = json.dumps({
            'class': target.class_name,
            'bin': bin_name,
            'robot_x_mm': target.robot_x,
            'robot_y_mm': target.robot_y,
            'robot_z_mm': target.robot_z,
            'cam_z_mm': target.cam_z,
        })
        self.pickup_pub.publish(msg)
        self.get_logger().info('PICK: published /pickup_request — waiting for completion')

        # TODO: Subscribe to /pickup_complete to know when arm is done
        # For now, wait a fixed time then rescan
        time.sleep(30.0)
        self.items_collected += 1
        self._enter_scan()

    # ==================================================================
    #  Helper methods
    # ==================================================================

    def _init_kalman(self):
        self.kf = cv2.KalmanFilter(4, 2)
        dt = self.pid_dt
        self.kf.transitionMatrix = np.array([
            [1, 0, dt, 0], [0, 1, 0, dt],
            [0, 0, 1, 0], [0, 0, 0, 1],
        ], dtype=np.float32)
        self.kf.measurementMatrix = np.array([
            [1, 0, 0, 0], [0, 1, 0, 0],
        ], dtype=np.float32)
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 3.0
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 25.0
        self.kf.errorCovPost = np.eye(4, dtype=np.float32) * 100.0
        self.kf.statePost = np.array([320, 240, 0, 0], dtype=np.float32)
        self.kalman_initialized = False

    def _kalman_predict(self) -> Tuple[float, float]:
        prediction = self.kf.predict()
        return float(prediction[0]), float(prediction[1])

    def _kalman_update(self, cx: float, cy: float) -> Tuple[float, float]:
        if not self.kalman_initialized:
            self.kf.statePost = np.array([cx, cy, 0, 0], dtype=np.float32)
            self.kalman_initialized = True
            return cx, cy
        self.kf.predict()
        measurement = np.array([cx, cy], dtype=np.float32)
        corrected = self.kf.correct(measurement)
        return float(corrected[0]), float(corrected[1])

    def _kalman_reset(self):
        self.kalman_initialized = False
        self.kf.statePost = np.array([320, 240, 0, 0], dtype=np.float32)
        self.kf.errorCovPost = np.eye(4, dtype=np.float32) * 100.0

    def _pid_angular(self, pixel_error: float) -> float:
        p_term = self.pid_kp * pixel_error
        self.pid_integral += pixel_error * self.pid_dt
        self.pid_integral = max(-self.pid_integral_max,
                                min(self.pid_integral_max, self.pid_integral))
        i_term = self.pid_ki * self.pid_integral
        d_term = self.pid_kd * (pixel_error - self.pid_prev_error) / self.pid_dt
        self.pid_prev_error = pixel_error
        angular_z = -(p_term + i_term + d_term)
        return max(-0.3, min(0.3, angular_z))

    def _pid_reset(self):
        self.pid_integral = 0.0
        self.pid_prev_error = 0.0

    def _smooth_angular(self, raw_angular_z: float, dt: float = 0.05) -> float:
        # EMA filter
        raw_angular_z = (self.angular_alpha * raw_angular_z +
                        (1.0 - self.angular_alpha) * self.filtered_angular_z)
        self.filtered_angular_z = raw_angular_z

        # Smooth taper near zero
        if abs(raw_angular_z) < self.angular_deadband:
            scale = (raw_angular_z / self.angular_deadband) ** 2
            raw_angular_z = raw_angular_z * scale

        # Sinusoidal ramp limiter
        max_delta = self.angular_ramp_rate * dt
        delta = raw_angular_z - self.last_angular_z
        if abs(delta) > max_delta:
            t = max_delta / abs(delta)
            smooth_t = 0.5 * (1.0 - math.cos(math.pi * t))
            raw_angular_z = self.last_angular_z + delta * smooth_t

        self.last_angular_z = raw_angular_z
        return raw_angular_z

    def _find_target_in_detections(self, detections: List[Detection]) -> Optional[Detection]:
        if not detections or self.current_target is None:
            return None

        ref_cx = self.current_target.cx_px
        ref_cy = self.current_target.cy_px

        # Position match (wider during TURN since object moves fast in frame)
        match_radius = 150 if self.state == State.TURN_TO_TARGET else 80
        nearby = [d for d in detections
                  if abs(d.cx_px - ref_cx) < match_radius and abs(d.cy_px - ref_cy) < match_radius]
        if nearby:
            nearby.sort(key=lambda d: (d.cx_px - ref_cx)**2 + (d.cy_px - ref_cy)**2)
            return nearby[0]

        # Class match
        target_class = self.current_target.class_name
        candidates = [d for d in detections if d.class_name == target_class]
        if candidates:
            candidates.sort(key=lambda d: (d.cx_px - ref_cx)**2 + (d.cy_px - ref_cy)**2)
            return candidates[0]

        # Any nearby detection
        if detections:
            detections_sorted = sorted(detections, key=lambda d:
                            (d.cx_px - ref_cx)**2 + (d.cy_px - ref_cy)**2)
            max_radius = 300 if self.state in (State.ALIGN, State.TURN_TO_TARGET) else 200
            if ((detections_sorted[0].cx_px - ref_cx)**2 +
                (detections_sorted[0].cy_px - ref_cy)**2) < max_radius**2:
                return detections_sorted[0]

        return None

    def _stop_motors(self):
        self.cmd_vel_pub.publish(Twist())

    def _publish_state(self):
        msg = String()
        info = f'{self.state.name}'
        if self.state == State.SCAN:
            progress = min(100, int(self.scan_accumulated / self.scan_target * 100))
            info += f' ({progress}%, {len(self.scan_detections)} found)'
        elif self.state in (State.TURN_TO_TARGET, State.APPROACH, State.ALIGN) and self.current_target:
            info += f' {self.current_target.class_name} @ {self.current_target.cam_z:.0f}mm'
        info += f' | collected: {self.items_collected}'
        msg.data = info
        self.state_pub.publish(msg)

    def destroy_node(self):
        self._stop_motors()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = WasteTracker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
