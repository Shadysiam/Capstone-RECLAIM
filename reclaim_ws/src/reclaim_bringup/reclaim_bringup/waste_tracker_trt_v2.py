#!/usr/bin/env python3
"""
waste_tracker_trt_v2.py — 30 FPS optimized TRT tracker with smooth motion.

Architecture:
  States: IDLE -> SCAN -> PURSUE -> FINAL_APPROACH -> PICK
  - PURSUE replaces old TURN+APPROACH: curved arc toward target, no stop between
  - FINAL_APPROACH: slow precise centering with cosine deceleration to zero
  - All transitions carry forward velocity — no hard stop/start jolts

Motion pipeline (per tick):
  raw bbox -> EMA smooth -> feed-forward predict -> P controller
  -> speed-dependent angular limit -> angular EMA -> sinusoidal ramp -> cmd_vel

TRT comms:
  Persistent HTTP connection, health tracking, adaptive poll rate.

Data flow:
  TRT server (30 FPS) -> HTTP /detection -> this node -> /cmd_vel -> motors
  After FINAL_APPROACH: publishes /pickup_request -> pick_and_place.py handles arm

Usage:
  python3 waste_tracker_trt_v2.py
  ros2 run reclaim_bringup waste_tracker_trt_v2

Authors: Shady Siam, Issa Ahmed
"""

from __future__ import annotations

import http.client
import json
import math
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple

import numpy as np

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import String


# ======================================================================
#  Constants
# ======================================================================

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
    PURSUE = auto()           # curved arc: turn + drive simultaneously
    FINAL_APPROACH = auto()   # slow precise centering + deceleration
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
        return self.cam_z

    @property
    def bearing_rad(self) -> float:
        return math.atan2(self.cam_x, self.cam_z) if self.cam_z > 0 else 0.0


# ======================================================================
#  WasteTracker ROS2 Node
# ======================================================================

class WasteTracker(Node):
    def __init__(self):
        super().__init__('waste_tracker')

        # -- ROS Parameters ------------------------------------------------
        self.declare_parameter('trt_url', 'http://localhost:8081')
        self.declare_parameter('confidence', 0.35)
        self.declare_parameter('poll_rate_hz', 30.0)

        self.declare_parameter('scan_angular_vel', 0.3)
        self.declare_parameter('scan_full_rotation', 6.28)

        self.declare_parameter('pursue_max_linear', 0.20)
        self.declare_parameter('pursue_min_linear', 0.03)
        self.declare_parameter('pursue_stop_distance_mm', 450.0)

        self.declare_parameter('final_approach_speed', 0.04)
        self.declare_parameter('final_approach_pixel_tol', 25)
        self.declare_parameter('final_approach_stable_frames', 5)
        self.declare_parameter('final_approach_max_depth_mm', 450.0)

        self.declare_parameter('obstacle_min_depth_mm', 300.0)
        self.declare_parameter('drive_only', True)

        # -- Read parameters -----------------------------------------------
        self.trt_url = self.get_parameter('trt_url').value.rstrip('/')
        self.confidence = self.get_parameter('confidence').value
        self.poll_rate_hz = self.get_parameter('poll_rate_hz').value

        self.scan_vel = self.get_parameter('scan_angular_vel').value
        self.scan_target = self.get_parameter('scan_full_rotation').value

        self.pursue_max_v = self.get_parameter('pursue_max_linear').value
        self.pursue_min_v = self.get_parameter('pursue_min_linear').value
        self.pursue_stop_dist = self.get_parameter('pursue_stop_distance_mm').value

        self.fa_speed = self.get_parameter('final_approach_speed').value
        self.fa_px_tol = self.get_parameter('final_approach_pixel_tol').value
        self.fa_stable_needed = self.get_parameter('final_approach_stable_frames').value
        self.fa_max_depth = self.get_parameter('final_approach_max_depth_mm').value

        self.obstacle_min = self.get_parameter('obstacle_min_depth_mm').value
        self.drive_only = self.get_parameter('drive_only').value

        # -- State machine -------------------------------------------------
        self.state = State.IDLE
        self.scan_start_yaw = 0.0
        self.scan_accumulated = 0.0
        self.scan_detections: List[Detection] = []
        self.current_target: Optional[Detection] = None
        self.current_yaw = 0.0
        self.prev_yaw = None
        self.items_collected = 0
        self.drive_only_done = False
        self.target_lost_count = 0
        self.target_lost_threshold = 30  # 1s at 30fps

        # Carried-forward velocity for smooth transitions
        self.current_linear = 0.0
        self.current_angular = 0.0

        # Detection confirmation (with gap tolerance)
        self.confirm_count = 0
        self.confirm_threshold = 3
        self.confirm_candidate = None
        self.confirm_miss_count = 0
        self.confirm_miss_max = 3

        # Scan deceleration on lock
        self.scan_decel_start = None
        self.scan_decel_duration = 0.5
        self.scan_decel_start_vel = 0.0

        # Detection hold
        self.det_hold_frames = 0
        self.det_hold_max = 4

        # -- Controller tuning ---------------------------------------------
        self.kp_pursue = 0.0012
        self.kp_final = 0.0015

        self.angular_min_cmd = 0.04
        self.angular_alpha = 0.45
        self.angular_deadband = 0.015
        self.angular_ramp_rate = 0.6
        self.filtered_angular_z = 0.0
        self.last_angular_z = 0.0
        self.tick_dt = 0.033

        # Speed-dependent angular limiting
        self.angular_limit_at_max_speed = 0.06
        self.angular_limit_at_min_speed = 0.25

        # S-curve pursue startup ramp
        self.pursue_start_time = 0.0
        self.pursue_ramp_duration = 1.0

        # Deceleration zone
        self.decel_zone_start = 900.0
        self.decel_zone_end = 450.0

        # Bbox EMA smoothing
        self.smooth_cx = None
        self.smooth_cy = None
        self.bbox_alpha = 0.5

        # Feed-forward prediction
        self.prev_raw_cx = None
        self.prev_raw_cx_time = None
        self.ff_gain = 0.3

        # FINAL_APPROACH state
        self.fa_stable_count = 0
        self.fa_lost_count = 0

        # Camera state
        self.camera_lock = threading.Lock()
        self.latest_detections: List[Detection] = []
        self.obstacle_ahead = False
        self.camera_ready = False
        self.camera_frame_count = 0
        self.image_width = 640
        self.image_height = 480

        # -- TRT connection health -----------------------------------------
        self.trt_connected = False
        self.trt_response_times = deque(maxlen=30)
        self.trt_errors = 0
        self.trt_total_polls = 0
        self.trt_conn = None
        self.trt_host = 'localhost'
        self.trt_port = 8081
        self._parse_trt_url()

        # -- Diagnostics ---------------------------------------------------
        self.declare_parameter('diag_ip', '192.168.2.1')
        self.declare_parameter('diag_port', 9999)
        self.diag_ip = self.get_parameter('diag_ip').value
        self.diag_port = self.get_parameter('diag_port').value
        self.diag_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.diag_interval = 0.25
        self.diag_last_send = 0.0

        # Performance tracking
        self.det_rate_window = deque(maxlen=30)
        self.last_cmd_angular = 0.0
        self.last_cmd_linear = 0.0
        self.state_enter_time = time.time()

        # -- Tuning log ----------------------------------------------------
        self.tuning_log_path = '/tmp/tracker_tuning.csv'
        self._init_tuning_log()
        self.tuning_log_interval = 0.1
        self.tuning_log_last = 0.0

        # -- Per-run performance stats -------------------------------------
        self.run_stats = {
            'scan_time': 0.0,
            'pursue_time': 0.0,
            'fa_time': 0.0,
            'total_lost_frames': 0,
            'total_det_frames': 0,
            'max_offset_px': 0,
            'pursue_corrections': 0,
            'pursue_zero_corrections': 0,
            'max_angular_cmd': 0.0,
            'max_linear_cmd': 0.0,
        }

        # -- ROS publishers / subscribers ----------------------------------
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.state_pub = self.create_publisher(String, '/robot_state', 10)
        self.pickup_pub = self.create_publisher(String, '/pickup_request', 10)

        self.create_subscription(Odometry, '/odom', self._odom_cb, 10)
        self.create_subscription(String, '/rescan', self._rescan_cb, 10)

        # -- Timers --------------------------------------------------------
        self.create_timer(0.033, self._tick)
        self.create_timer(0.5, self._publish_state)

        # -- Start TRT polling thread --------------------------------------
        self.camera_thread = threading.Thread(target=self._trt_poll_loop, daemon=True)
        self.camera_thread.start()

        self.get_logger().info(
            f'WasteTracker TRT v2 [SMOOTH]: '
            f'Kp_pursue={self.kp_pursue}, Kp_final={self.kp_final}, '
            f'min_cmd={self.angular_min_cmd}, '
            f'v_max={self.pursue_max_v}, decel={self.decel_zone_start}-{self.decel_zone_end}mm, '
            f'conf={self.confidence}, poll={self.poll_rate_hz}Hz, '
            f'diag->{self.diag_ip}:{self.diag_port}, '
            f'drive_only={self.drive_only}')

    # ==================================================================
    #  TRT URL parsing
    # ==================================================================

    def _parse_trt_url(self):
        url = self.trt_url.replace('http://', '').replace('https://', '')
        if ':' in url:
            parts = url.split(':')
            self.trt_host = parts[0]
            self.trt_port = int(parts[1].split('/')[0])
        else:
            self.trt_host = url.split('/')[0]
            self.trt_port = 8081

    # ==================================================================
    #  Callbacks
    # ==================================================================

    def _rescan_cb(self, msg: String):
        self.get_logger().info('=== RESCAN triggered ===')
        self._smooth_stop()
        self.drive_only_done = False
        self.target_lost_count = 0
        self.current_target = None
        self.filtered_angular_z = 0.0
        self.last_angular_z = 0.0
        self._reset_bbox_smooth()
        self._reset_ff()
        self._enter_scan()

    def _odom_cb(self, msg: Odometry):
        q = msg.pose.pose.orientation
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self.current_yaw = math.atan2(siny, cosy)

    # ==================================================================
    #  TRT polling thread (persistent HTTP)
    # ==================================================================

    def _trt_poll_loop(self):
        poll_interval = 1.0 / self.poll_rate_hz
        consecutive_errors = 0

        while rclpy.ok():
            t0 = time.time()
            try:
                if self.trt_conn is None:
                    self.trt_conn = http.client.HTTPConnection(
                        self.trt_host, self.trt_port, timeout=0.5)

                self.trt_conn.request('GET', '/detection')
                resp = self.trt_conn.getresponse()
                raw = resp.read()

                elapsed_ms = (time.time() - t0) * 1000
                self.trt_response_times.append(elapsed_ms)
                self.trt_total_polls += 1
                consecutive_errors = 0

                data = json.loads(raw.decode())

                if not self.trt_connected:
                    self.trt_connected = True
                    self.camera_ready = True
                    self.get_logger().info(
                        f'TRT connected: {self.trt_host}:{self.trt_port} '
                        f'({elapsed_ms:.0f}ms)')

                self._process_trt_response(data)

            except (http.client.HTTPException, ConnectionError, OSError):
                self.trt_conn = None
                consecutive_errors += 1
                self.trt_errors += 1
                if consecutive_errors == 1:
                    self.get_logger().warn(
                        f'TRT connection lost ({self.trt_host}:{self.trt_port})')
                elif consecutive_errors % 100 == 0:
                    self.get_logger().warn(
                        f'TRT unreachable ({consecutive_errors} failures)')
            except json.JSONDecodeError as e:
                self.get_logger().warn(f'TRT bad JSON: {e}')
            except Exception as e:
                self.trt_conn = None
                self.get_logger().warn(f'TRT poll error: {e}')

            elapsed = time.time() - t0
            sleep_time = max(0.001, poll_interval - elapsed)
            time.sleep(sleep_time)

    def _process_trt_response(self, data: dict):
        if data.get('status') == 'no_detection':
            with self.camera_lock:
                self.det_hold_frames += 1
                if self.det_hold_frames > self.det_hold_max:
                    self.latest_detections = []
                self.obstacle_ahead = False
                self.camera_frame_count += 1
            return

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
            return

        det = Detection(
            class_name=class_name, confidence=conf,
            cam_x=cam_x, cam_y=cam_y, cam_z=cam_z,
            robot_x=robot_x, robot_y=robot_y, robot_z=robot_z,
            cx_px=cx_px, cy_px=cy_px,
            bbox_w=bbox_w, bbox_h=bbox_h,
        )

        # Ground filtering
        img_area = self.image_width * self.image_height
        tracking = self.state in (State.PURSUE, State.FINAL_APPROACH)
        max_depth = 3000 if tracking else 2500
        max_bbox_frac = 0.40 if tracking else 0.25
        min_cy_frac = 0.20 if tracking else 0.25

        passes_depth = det.cam_z < max_depth
        passes_cy = det.cy_px > self.image_height * min_cy_frac
        bbox_area = det.bbox_w * det.bbox_h
        passes_max_bbox = bbox_area < img_area * max_bbox_frac
        passes_min_bbox = bbox_area > img_area * 0.003

        aspect = det.bbox_h / max(det.bbox_w, 1)
        passes_aspect = aspect < 3.0
        bbox_bottom = y2
        passes_bottom = bbox_bottom > self.image_height * 0.40

        detections = []
        if (passes_depth and passes_cy and passes_max_bbox and
                passes_min_bbox and passes_aspect and passes_bottom):
            detections.append(det)
            self.det_hold_frames = 0
            if self.camera_frame_count % 30 == 0:
                self.get_logger().info(
                    f'DET: {class_name} conf={conf:.2f} '
                    f'd={det.cam_z:.0f}mm cx={cx_px} ar={aspect:.1f}')
        elif self.camera_frame_count % 100 == 0:
            self.get_logger().info(
                f'REJECT: {class_name} conf={conf:.2f} '
                f'd={det.cam_z:.0f}({passes_depth}) '
                f'cy={det.cy_px}({passes_cy}) '
                f'ar={aspect:.1f}({passes_aspect}) bot={bbox_bottom}({passes_bottom})')

        obstacle = 0 < cam_z < self.obstacle_min

        with self.camera_lock:
            self.latest_detections = detections
            self.obstacle_ahead = obstacle
            self.camera_frame_count += 1

    # ==================================================================
    #  State machine tick (~30 Hz)
    # ==================================================================

    def _tick(self):
        if not self.camera_ready:
            return

        if self.state == State.IDLE and self.items_collected == 0 and not self.drive_only_done:
            self._enter_scan()
            return

        if self.state == State.SCAN:
            self._tick_scan()
        elif self.state == State.PURSUE:
            self._tick_pursue()
        elif self.state == State.FINAL_APPROACH:
            self._tick_final_approach()

        self._send_diag()

    # -- SCAN ----------------------------------------------------------

    def _enter_scan(self):
        self.state = State.SCAN
        self.state_enter_time = time.time()
        self.scan_start_yaw = self.current_yaw
        self.scan_accumulated = 0.0
        self.prev_yaw = self.current_yaw
        self.scan_detections.clear()
        self.confirm_count = 0
        self.confirm_candidate = None
        self.confirm_miss_count = 0
        self.scan_decel_start = None
        self._reset_bbox_smooth()
        self._reset_ff()
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

        # Scan deceleration in progress
        if self.scan_decel_start is not None:
            elapsed = time.time() - self.scan_decel_start
            if elapsed >= self.scan_decel_duration:
                self._send_vel(0.0, 0.0)
                self.run_stats['scan_time'] += time.time() - self.state_enter_time
                self._enter_pursue()
                return
            t = elapsed / self.scan_decel_duration
            decel_ratio = 0.5 * (1.0 + math.cos(math.pi * t))
            angular_z = self.scan_decel_start_vel * decel_ratio
            self._send_vel(0.0, angular_z)
            return

        # Check for lock during scan
        if frame_dets:
            nearby = [d for d in frame_dets
                      if d.cam_z < 2500 and d.cy_px > self.image_height * 0.15]
            if nearby:
                best = min(nearby, key=lambda d: d.cam_z)
                self.confirm_miss_count = 0
                if best.confidence >= 0.30:
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
                        self.current_target = best
                        self.confirm_count = 0
                        self.confirm_candidate = None
                        self.get_logger().info(
                            f'SCAN: locked {best.class_name} '
                            f'(conf={best.confidence:.2f}, d={best.cam_z:.0f}mm) '
                            f'-- decelerating')
                        self.scan_decel_start = time.time()
                        self.scan_decel_start_vel = self.current_angular
                        return
            else:
                self.confirm_miss_count += 1
                if self.confirm_miss_count > self.confirm_miss_max:
                    self.confirm_count = 0
                    self.confirm_candidate = None

        if self.confirm_count > 0:
            target_w = self.scan_vel * 0.4
        else:
            target_w = self.scan_vel

        w = self._ramp_toward(self.current_angular, target_w, 0.3 * self.tick_dt)
        self._send_vel(0.0, w)

        if self.scan_accumulated >= self.scan_target:
            self._smooth_stop()
            if not self.scan_detections:
                self.get_logger().info('SCAN complete -- no targets. Rescanning...')
                self._enter_scan()
                return
            self.scan_detections.sort(key=lambda d: d.distance_mm)
            self.current_target = self.scan_detections[0]
            self.get_logger().info(
                f'SCAN complete -- {len(self.scan_detections)} targets. '
                f'Nearest: {self.current_target.class_name} '
                f'@ {self.current_target.distance_mm:.0f}mm')
            self.run_stats['scan_time'] += time.time() - self.state_enter_time
            self._enter_pursue()

    # -- PURSUE (curved arc -- replaces TURN + APPROACH) ---------------

    def _enter_pursue(self):
        self.state = State.PURSUE
        self.state_enter_time = time.time()
        self.pursue_start_time = time.time()
        self.target_lost_count = 0
        self.filtered_angular_z = 0.0
        self.last_angular_z = 0.0
        self._reset_bbox_smooth()
        self._reset_ff()
        self.get_logger().info(
            f'=== PURSUE: {self.current_target.class_name} '
            f'@ {self.current_target.cam_z:.0f}mm ===')

    def _tick_pursue(self):
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
            self.run_stats['total_lost_frames'] += 1
            if self.target_lost_count >= self.target_lost_threshold:
                self._smooth_stop()
                last_depth = self.current_target.cam_z if self.current_target else 9999
                if last_depth < 500:
                    self.get_logger().info(
                        f'PURSUE: lost at close range ({last_depth:.0f}mm)')
                    if self.drive_only:
                        self.drive_only_done = True
                    self.state = State.IDLE
                else:
                    self.get_logger().warn('PURSUE: target lost -- rescanning')
                    self._enter_scan()
            else:
                v = self.current_linear * 0.95
                w = self.current_angular * 0.90
                self._send_vel(v, w)
            return

        self.target_lost_count = 0
        self.current_target = target_det
        self.det_rate_window.append(time.time())
        self.run_stats['total_det_frames'] += 1

        # -- Smoothing pipeline --
        raw_cx = float(target_det.cx_px)
        raw_cy = float(target_det.cy_px)

        # 1. Bbox EMA
        scx, scy = self._smooth_bbox(raw_cx, raw_cy)

        # 2. Feed-forward prediction
        predicted_cx = self._feed_forward(scx)

        # 3. Pixel offset from center
        img_cx = self.image_width / 2.0
        pixel_offset = predicted_cx - img_cx
        self.run_stats['max_offset_px'] = max(
            self.run_stats['max_offset_px'], abs(int(pixel_offset)))

        # 4. P controller
        if abs(pixel_offset) < 10:
            raw_w = 0.0
            self.run_stats['pursue_zero_corrections'] += 1
        else:
            raw_w = -self.kp_pursue * pixel_offset
            self.run_stats['pursue_corrections'] += 1

        # 5. Distance-based speed with deceleration zone
        dist = target_det.cam_z

        if dist <= self.pursue_stop_dist:
            self.run_stats['pursue_time'] += time.time() - self.state_enter_time
            self._enter_final_approach()
            return

        if dist < self.decel_zone_start:
            zone_ratio = (dist - self.decel_zone_end) / (self.decel_zone_start - self.decel_zone_end)
            zone_ratio = max(0.0, min(1.0, zone_ratio))
            speed_ratio = 0.5 * (1.0 - math.cos(math.pi * zone_ratio))
            target_v = self.pursue_min_v + (self.pursue_max_v - self.pursue_min_v) * speed_ratio
        else:
            target_v = self.pursue_max_v

        # 6. S-curve startup ramp
        elapsed = time.time() - self.pursue_start_time
        if elapsed < self.pursue_ramp_duration:
            ramp = 0.5 * (1.0 - math.cos(math.pi * elapsed / self.pursue_ramp_duration))
            target_v *= ramp
            raw_w *= ramp

        # 7. Speed-dependent angular limiting
        speed_frac = (target_v - self.pursue_min_v) / max(0.01, self.pursue_max_v - self.pursue_min_v)
        speed_frac = max(0.0, min(1.0, speed_frac))
        max_angular = (self.angular_limit_at_min_speed +
                       (self.angular_limit_at_max_speed - self.angular_limit_at_min_speed) * speed_frac)
        raw_w = max(-max_angular, min(max_angular, raw_w))

        # 8. Motor deadband override
        if 0 < abs(raw_w) < self.angular_min_cmd and abs(pixel_offset) > 15:
            raw_w = self.angular_min_cmd * (-1.0 if pixel_offset > 0 else 1.0)

        # 9. Angular EMA + sinusoidal ramp
        angular_z = self._smooth_angular(raw_w)

        # 10. Smooth linear toward target speed
        linear_x = self._ramp_toward(self.current_linear, target_v, 0.15 * self.tick_dt)

        self._send_vel(linear_x, angular_z)

        self.run_stats['max_angular_cmd'] = max(
            self.run_stats['max_angular_cmd'], abs(angular_z))
        self.run_stats['max_linear_cmd'] = max(
            self.run_stats['max_linear_cmd'], linear_x)

        self._write_tuning_log(raw_cx=raw_cx, raw_w=raw_w)

    # -- FINAL_APPROACH (slow precise centering) -----------------------

    def _enter_final_approach(self):
        self.state = State.FINAL_APPROACH
        self.state_enter_time = time.time()
        self.fa_stable_count = 0
        self.fa_lost_count = 0
        self.target_lost_count = 0
        self.get_logger().info('=== FINAL_APPROACH: centering ===')

    def _tick_final_approach(self):
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
            self.fa_lost_count += 1
            if self.fa_lost_count >= 15:
                self._smooth_stop()
                last_depth = self.current_target.cam_z if self.current_target else 9999
                if last_depth < 500:
                    self.get_logger().info('FA: lost at close range -- stopping')
                    if self.drive_only:
                        self.drive_only_done = True
                    self.state = State.IDLE
                    self._print_run_summary()
                else:
                    self.get_logger().warn('FA: target lost -- rescanning')
                    self._enter_scan()
            else:
                v = self.current_linear * 0.90
                w = self.current_angular * 0.85
                self._send_vel(v, w)
            return

        self.fa_lost_count = 0
        self.current_target = target_det

        img_cx = self.image_width / 2.0
        pixel_offset = float(target_det.cx_px) - img_cx

        if abs(pixel_offset) > self.fa_px_tol:
            raw_w = -self.kp_final * pixel_offset
            raw_w = max(-0.12, min(0.12, raw_w))
            if abs(raw_w) < self.angular_min_cmd:
                raw_w = self.angular_min_cmd * (-1.0 if pixel_offset > 0 else 1.0)
            angular_z = self._smooth_angular(raw_w)
            self.fa_stable_count = 0
        else:
            angular_z = self._smooth_angular(0.0)

        depth = target_det.cam_z
        if depth > self.fa_max_depth:
            target_v = self.fa_speed
        elif abs(pixel_offset) <= self.fa_px_tol:
            target_v = 0.0
        else:
            target_v = 0.0

        linear_x = self._ramp_toward(self.current_linear, target_v, 0.05 * self.tick_dt)
        self._send_vel(linear_x, angular_z)

        if abs(pixel_offset) <= self.fa_px_tol and depth <= self.fa_max_depth:
            self.fa_stable_count += 1
            if self.fa_stable_count >= self.fa_stable_needed:
                self._smooth_stop()
                self.get_logger().info(
                    f'FA: locked {target_det.class_name} '
                    f'@ {depth:.0f}mm, offset={pixel_offset:.0f}px')
                self.run_stats['fa_time'] += time.time() - self.state_enter_time
                if self.drive_only:
                    self.get_logger().info('FA: drive_only -- stopping')
                    self.drive_only_done = True
                    self.state = State.IDLE
                    self._print_run_summary()
                else:
                    self._enter_pick()

    # -- PICK ----------------------------------------------------------

    def _enter_pick(self):
        self.state = State.PICK
        self._smooth_stop()

        target = self.current_target
        if target is None:
            self.get_logger().error('PICK: no target')
            self._enter_scan()
            return

        bin_name = BIN_MAP.get(target.class_name, 'landfill')
        self.get_logger().info(
            f'=== PICK: {target.class_name} -> {bin_name} ===')

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
        self.get_logger().info('PICK: published /pickup_request')

        time.sleep(30.0)
        self.items_collected += 1
        self._enter_scan()

    # ==================================================================
    #  Motion helpers
    # ==================================================================

    def _send_vel(self, linear: float, angular: float):
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.cmd_vel_pub.publish(twist)
        self.current_linear = linear
        self.current_angular = angular
        self.last_cmd_linear = linear
        self.last_cmd_angular = angular

    def _smooth_stop(self, duration: float = 0.3):
        if abs(self.current_linear) < 0.005 and abs(self.current_angular) < 0.005:
            self._send_vel(0.0, 0.0)
            return

        start_v = self.current_linear
        start_w = self.current_angular
        t0 = time.time()

        while time.time() - t0 < duration:
            t = (time.time() - t0) / duration
            ratio = 0.5 * (1.0 + math.cos(math.pi * t))
            self._send_vel(start_v * ratio, start_w * ratio)
            time.sleep(0.02)

        self._send_vel(0.0, 0.0)

    def _ramp_toward(self, current: float, target: float, max_step: float) -> float:
        diff = target - current
        if abs(diff) <= max_step:
            return target
        return current + max_step * (1.0 if diff > 0 else -1.0)

    def _smooth_angular(self, raw_w: float) -> float:
        raw_w = self.angular_alpha * raw_w + (1.0 - self.angular_alpha) * self.filtered_angular_z
        self.filtered_angular_z = raw_w

        if abs(raw_w) < self.angular_deadband:
            scale = (raw_w / self.angular_deadband) ** 2
            raw_w = raw_w * scale

        max_delta = self.angular_ramp_rate * self.tick_dt
        delta = raw_w - self.last_angular_z
        if abs(delta) > max_delta:
            t = max_delta / abs(delta)
            smooth_t = 0.5 * (1.0 - math.cos(math.pi * t))
            raw_w = self.last_angular_z + delta * smooth_t

        self.last_angular_z = raw_w
        return raw_w

    # ==================================================================
    #  Perception helpers
    # ==================================================================

    def _smooth_bbox(self, cx: float, cy: float) -> Tuple[float, float]:
        if self.smooth_cx is None:
            self.smooth_cx = cx
            self.smooth_cy = cy
        else:
            self.smooth_cx = self.bbox_alpha * cx + (1.0 - self.bbox_alpha) * self.smooth_cx
            self.smooth_cy = self.bbox_alpha * cy + (1.0 - self.bbox_alpha) * self.smooth_cy
        return self.smooth_cx, self.smooth_cy

    def _reset_bbox_smooth(self):
        self.smooth_cx = None
        self.smooth_cy = None

    def _feed_forward(self, cx: float) -> float:
        now = time.time()
        if self.prev_raw_cx is not None and self.prev_raw_cx_time is not None:
            dt = now - self.prev_raw_cx_time
            if 0.01 < dt < 0.2:
                velocity = (cx - self.prev_raw_cx) / dt
                predicted = cx + velocity * self.tick_dt * self.ff_gain
                self.prev_raw_cx = cx
                self.prev_raw_cx_time = now
                return predicted

        self.prev_raw_cx = cx
        self.prev_raw_cx_time = now
        return cx

    def _reset_ff(self):
        self.prev_raw_cx = None
        self.prev_raw_cx_time = None

    def _find_target_in_detections(self, detections: List[Detection]) -> Optional[Detection]:
        if not detections or self.current_target is None:
            return None

        ref_cx = self.current_target.cx_px
        ref_cy = self.current_target.cy_px

        match_radius = 150 if self.state == State.PURSUE else 80
        nearby = [d for d in detections
                  if abs(d.cx_px - ref_cx) < match_radius
                  and abs(d.cy_px - ref_cy) < match_radius]
        if nearby:
            nearby.sort(key=lambda d: (d.cx_px - ref_cx)**2 + (d.cy_px - ref_cy)**2)
            return nearby[0]

        target_class = self.current_target.class_name
        candidates = [d for d in detections if d.class_name == target_class]
        if candidates:
            candidates.sort(key=lambda d: (d.cx_px - ref_cx)**2 + (d.cy_px - ref_cy)**2)
            return candidates[0]

        if detections:
            detections_sorted = sorted(detections, key=lambda d:
                            (d.cx_px - ref_cx)**2 + (d.cy_px - ref_cy)**2)
            max_r = 300 if self.state == State.FINAL_APPROACH else 200
            dist_sq = ((detections_sorted[0].cx_px - ref_cx)**2 +
                       (detections_sorted[0].cy_px - ref_cy)**2)
            if dist_sq < max_r**2:
                return detections_sorted[0]

        return None

    # ==================================================================
    #  Diagnostics & logging
    # ==================================================================

    def _init_tuning_log(self):
        try:
            with open(self.tuning_log_path, 'w') as f:
                f.write('time,state,state_dur,target,depth_mm,raw_cx,smooth_cx,'
                        'predicted_cx,offset_px,raw_w,ema_w,final_w,cmd_v,'
                        'det_rate,lost_count,hold_frames,cur_v,cur_w\n')
            param_log = self.tuning_log_path.replace('.csv', '_params.txt')
            with open(param_log, 'w') as f:
                f.write(f'=== V2 SMOOTH PARAMS ({time.strftime("%Y-%m-%d %H:%M:%S")}) ===\n')
                f.write(f'States: IDLE->SCAN->PURSUE->FINAL_APPROACH->PICK\n')
                f.write(f'Kp_pursue={self.kp_pursue} Kp_final={self.kp_final}\n')
                f.write(f'min_cmd={self.angular_min_cmd}\n')
                f.write(f'EMA_alpha={self.angular_alpha}\n')
                f.write(f'ramp_rate={self.angular_ramp_rate}\n')
                f.write(f'deadband={self.angular_deadband}\n')
                f.write(f'bbox_alpha={self.bbox_alpha}\n')
                f.write(f'ff_gain={self.ff_gain}\n')
                f.write(f'speed_angular_limit: {self.angular_limit_at_max_speed}-{self.angular_limit_at_min_speed}\n')
                f.write(f'decel_zone: {self.decel_zone_start}-{self.decel_zone_end}mm\n')
                f.write(f'pursue_v: {self.pursue_min_v}-{self.pursue_max_v}\n')
                f.write(f'pursue_ramp: {self.pursue_ramp_duration}s\n')
                f.write(f'scan_decel: {self.scan_decel_duration}s\n')
                f.write(f'poll_rate={self.poll_rate_hz}Hz tick_dt={self.tick_dt}s\n')
                f.write(f'lost_threshold={self.target_lost_threshold}\n')
                f.write(f'det_hold_max={self.det_hold_max}\n')
                f.write(f'confirm_threshold={self.confirm_threshold} miss_max={self.confirm_miss_max}\n')
                f.write(f'pursue_stop_dist={self.pursue_stop_dist}mm\n')
                f.write(f'fa_px_tol={self.fa_px_tol} fa_speed={self.fa_speed}\n')
        except Exception as e:
            self.get_logger().warn(f'Could not init tuning log: {e}')

    def _write_tuning_log(self, raw_cx=None, raw_w=None):
        now = time.time()
        if now - self.tuning_log_last < self.tuning_log_interval:
            return
        self.tuning_log_last = now

        target = self.current_target
        det_count = sum(1 for t in self.det_rate_window if t > now - 1.0)

        try:
            with open(self.tuning_log_path, 'a') as f:
                predicted = self.prev_raw_cx if self.prev_raw_cx else ''
                f.write(f'{now:.3f},'
                        f'{self.state.name},'
                        f'{now - self.state_enter_time:.2f},'
                        f'{target.class_name if target else ""},'
                        f'{target.cam_z:.0f if target else ""},'
                        f'{raw_cx:.1f if raw_cx is not None else ""},'
                        f'{self.smooth_cx:.1f if self.smooth_cx is not None else ""},'
                        f'{predicted},'
                        f'{target.cx_px - self.image_width // 2 if target else ""},'
                        f'{raw_w:.5f if raw_w is not None else ""},'
                        f'{self.filtered_angular_z:.5f},'
                        f'{self.last_cmd_angular:.5f},'
                        f'{self.last_cmd_linear:.4f},'
                        f'{det_count},'
                        f'{self.target_lost_count},'
                        f'{self.det_hold_frames},'
                        f'{self.current_linear:.4f},'
                        f'{self.current_angular:.5f}\n')
        except Exception:
            pass

    def _print_run_summary(self):
        stats = self.run_stats
        total = stats['total_det_frames'] + stats['total_lost_frames']
        det_pct = (stats['total_det_frames'] / max(1, total)) * 100

        pursue_total = stats['pursue_corrections'] + stats['pursue_zero_corrections']
        smooth_pct = (stats['pursue_zero_corrections'] / max(1, pursue_total)) * 100

        avg_ms = (sum(self.trt_response_times) / max(1, len(self.trt_response_times)))
        err_pct = (self.trt_errors / max(1, self.trt_total_polls)) * 100

        self.get_logger().info(
            f'\n{"=" * 55}\n'
            f'  RUN SUMMARY (V2 SMOOTH)\n'
            f'  Scan: {stats["scan_time"]:.1f}s | Pursue: {stats["pursue_time"]:.1f}s | '
            f'FA: {stats["fa_time"]:.1f}s\n'
            f'  Detection: {det_pct:.0f}% ({stats["total_det_frames"]}/{total} frames)\n'
            f'  Max offset: {stats["max_offset_px"]}px\n'
            f'  Max cmds: v={stats["max_linear_cmd"]:.3f} w={stats["max_angular_cmd"]:.4f}\n'
            f'  Pursue smoothness: {smooth_pct:.0f}% frames zero-correction\n'
            f'  TRT: avg={avg_ms:.0f}ms, errors={err_pct:.1f}%\n'
            f'  Log: {self.tuning_log_path}\n'
            f'{"=" * 55}')

    def _send_diag(self):
        now = time.time()
        if now - self.diag_last_send < self.diag_interval:
            return
        self.diag_last_send = now

        cutoff = now - 1.0
        det_rate = sum(1 for t in self.det_rate_window if t > cutoff)
        avg_trt_ms = (sum(self.trt_response_times) / max(1, len(self.trt_response_times)))

        target = self.current_target
        diag = {
            't': round(now, 2),
            'state': self.state.name,
            'state_dur': round(now - self.state_enter_time, 1),
            'det_rate': det_rate,
            'det_hold': self.det_hold_frames,
            'target': target.class_name if target else None,
            'depth_mm': round(target.cam_z) if target else None,
            'cx_px': target.cx_px if target else None,
            'offset_px': round(target.cx_px - self.image_width / 2) if target else None,
            'smooth_cx': round(self.smooth_cx, 1) if self.smooth_cx else None,
            'cmd_w': round(self.last_cmd_angular, 4),
            'cmd_v': round(self.last_cmd_linear, 3),
            'cur_v': round(self.current_linear, 3),
            'cur_w': round(self.current_angular, 4),
            'lost': self.target_lost_count,
            'confirm': self.confirm_count,
            'yaw': round(math.degrees(self.current_yaw), 1),
            'scan_pct': round(self.scan_accumulated / self.scan_target * 100, 1) if self.state == State.SCAN else None,
            'trt_ms': round(avg_trt_ms, 1),
            'trt_err': self.trt_errors,
        }

        try:
            msg_bytes = json.dumps(diag).encode()
            self.diag_sock.sendto(msg_bytes, (self.diag_ip, self.diag_port))
        except Exception:
            pass

    def _publish_state(self):
        msg = String()
        info = f'{self.state.name}'
        if self.state == State.SCAN:
            progress = min(100, int(self.scan_accumulated / self.scan_target * 100))
            info += f' ({progress}%, {len(self.scan_detections)} found)'
        elif self.state in (State.PURSUE, State.FINAL_APPROACH) and self.current_target:
            info += f' {self.current_target.class_name} @ {self.current_target.cam_z:.0f}mm'
            info += f' v={self.current_linear:.2f} w={self.current_angular:.3f}'
        info += f' | collected: {self.items_collected}'
        msg.data = info
        self.state_pub.publish(msg)

    def destroy_node(self):
        self._send_vel(0.0, 0.0)
        if self.trt_conn:
            try:
                self.trt_conn.close()
            except Exception:
                pass
        self.diag_sock.close()
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
