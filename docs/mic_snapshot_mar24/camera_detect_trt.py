#!/usr/bin/env python3.8
"""
TensorRT Camera Detection Server — RECLAIM Project

Runs OAK-D Lite + TensorRT YOLO at ~30 FPS.
Serves MJPEG stream + JSON detection endpoint.
Must run with system Python 3.8 (not conda).

Run on MIC-711:
    python3.8 ~/reclaim_ws/tests/camera_detect_trt.py

View on Mac (via SSH tunnel):
    ssh -f -N -L 8081:127.0.0.1:8081 mic
    http://127.0.0.1:8081

Detection API (for pick_and_place.py):
    http://localhost:8081/detection  → JSON with latest detection

Press Ctrl+C to stop.
"""
import depthai as dai
import cv2
import time
import argparse
import math
import json
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

# Global frame + detection storage
latest_frame = None
frame_lock = threading.Lock()
latest_detection = None
detection_lock = threading.Lock()

DEPTH_MIN_MM = 150
DEPTH_MAX_MM = 600

# Hardcoded TF: camera_optical_frame → base_link (at home/look-down pose)
# From tf2_echo: base_link → camera_optical_frame
# Matrix:
#   0.002 -0.872  0.489  0.147
#  -1.000 -0.001  0.001 -0.012
#   0.000 -0.489 -0.872  0.185
# To go FROM camera_optical TO base_link: p_base = R * p_cam + t
TF_R = np.array([
    [ 0.002, -1.000,  0.000],
    [-0.872, -0.001, -0.489],
    [ 0.489,  0.001, -0.872]
])
TF_T = np.array([0.147, -0.012, 0.185])

def cam_optical_to_base_link(x_m, y_m, z_m):
    """Transform point from camera_optical_frame to base_link (home pose only)."""
    p_cam = np.array([x_m, y_m, z_m])
    # Inverse transform: p_base = R^T * (p_cam - t_cam_in_base)
    # But we have base→cam, so: p_base = R^T * p_cam + t_base
    # Actually the matrix columns are the cam axes in base frame:
    # col0 = cam_X in base, col1 = cam_Y in base, col2 = cam_Z in base
    # So p_base = M * p_cam + translation
    M = np.array([
        [ 0.002, -0.872,  0.489],
        [-1.000, -0.001,  0.001],
        [ 0.000, -0.489, -0.872]
    ])
    t = np.array([0.147, -0.012, 0.185])
    return M @ p_cam + t


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = '<html><body style="margin:0;background:#111;display:flex;justify-content:center;align-items:center;height:100vh;"><img src="/stream" style="max-width:100%;"></body></html>'
            self.wfile.write(html.encode())
        elif self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    with frame_lock:
                        frame = latest_frame
                    if frame is not None:
                        _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                        self.wfile.write(b'--frame\r\n')
                        self.wfile.write(b'Content-Type: image/jpeg\r\n')
                        self.wfile.write(f'Content-Length: {len(jpeg)}\r\n'.encode())
                        self.wfile.write(b'\r\n')
                        self.wfile.write(jpeg.tobytes())
                        self.wfile.write(b'\r\n')
                    time.sleep(0.03)  # ~30fps
            except (BrokenPipeError, ConnectionResetError):
                pass
        elif self.path == '/detection':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with detection_lock:
                det = latest_detection
            if det:
                self.wfile.write(json.dumps(det).encode())
            else:
                self.wfile.write(b'{"status":"no_detection"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def get_depth_for_bbox(depth_frame, x1, y1, x2, y2):
    """Get median depth in inner region of bbox."""
    h, w = depth_frame.shape[:2]
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    bw = max(1, int((x2 - x1) * 0.2))
    bh = max(1, int((y2 - y1) * 0.2))
    y_lo = max(0, cy - bh)
    y_hi = min(h, cy + bh)
    x_lo = max(0, cx - bw)
    x_hi = min(w, cx + bw)
    roi = depth_frame[y_lo:y_hi, x_lo:x_hi]
    valid = roi[(roi > DEPTH_MIN_MM) & (roi < DEPTH_MAX_MM)]
    if len(valid) == 0:
        return 0
    return int(np.median(valid))


def get_ground_depth(depth_frame, x1, y1, x2, y2):
    """Get 90th percentile depth in full bbox (ground around object)."""
    h, w = depth_frame.shape[:2]
    y_lo = max(0, int(y1))
    y_hi = min(h, int(y2))
    x_lo = max(0, int(x1))
    x_hi = min(w, int(x2))
    roi = depth_frame[y_lo:y_hi, x_lo:x_hi]
    valid = roi[(roi > DEPTH_MIN_MM) & (roi < DEPTH_MAX_MM)]
    if len(valid) == 0:
        return 0
    return int(np.percentile(valid, 90))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str,
                        default='models/waste_yolo11n_v3_best.engine')
    parser.add_argument('--conf', type=float, default=0.35)
    parser.add_argument('--port', type=int, default=8081)
    parser.add_argument('--burst', type=int, default=5)
    args = parser.parse_args()

    global latest_frame, latest_detection

    print("=" * 50)
    print("RECLAIM — TensorRT Detection Server")
    print("=" * 50)
    print(f"  Model: {args.model}")
    print(f"  Confidence: {args.conf}")
    print(f"  Port: {args.port}")
    print(f"  Burst: {args.burst} frames")
    print()

    # Start MJPEG + API server
    server = ThreadingHTTPServer(('0.0.0.0', args.port), Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"Stream: http://127.0.0.1:{args.port}")
    print(f"API:    http://127.0.0.1:{args.port}/detection")
    print()

    # Load TensorRT model
    print(f"Loading model: {args.model}")
    from ultralytics import YOLO
    model = YOLO(args.model)
    print(f"Model loaded. Classes: {model.names}")
    print()

    # Camera pipeline
    with dai.Pipeline() as pipeline:
        cam = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
        rgb_queue = cam.requestOutput((640, 480)).createOutputQueue(
            maxSize=2, blocking=False)

        stereo = pipeline.create(dai.node.StereoDepth).build(autoCreateCameras=True)
        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.DEFAULT)
        stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)
        stereo.setOutputSize(640, 480)
        stereo.setLeftRightCheck(True)
        stereo.setSubpixel(True)
        stereo.setExtendedDisparity(True)
        depth_queue = stereo.depth.createOutputQueue(
            maxSize=2, blocking=False)

        pipeline.start()
        print("Camera started.")

        # Get intrinsics
        calib = pipeline.getDefaultDevice().readCalibration()
        intr = np.array(calib.getCameraIntrinsics(
            dai.CameraBoardSocket.CAM_A, 640, 480))
        fx, fy = intr[0][0], intr[1][1]
        cx_cam, cy_cam = intr[0][2], intr[1][2]
        print(f"Intrinsics: fx={fx:.1f} fy={fy:.1f} cx={cx_cam:.1f} cy={cy_cam:.1f}")
        print()

        # Depth burst buffer
        depth_burst = []
        frame_count = 0
        fps_start = time.time()
        fps_display = 0

        print("Running... Press Ctrl+C to stop.")
        print()

        while pipeline.isRunning():
            rgb_data = rgb_queue.tryGet()
            depth_data = depth_queue.tryGet()

            if rgb_data is None:
                time.sleep(0.001)
                continue

            frame = rgb_data.getCvFrame()
            annotated = frame.copy()

            # Update depth burst buffer
            if depth_data is not None:
                df = depth_data.getCvFrame()
                depth_burst.append(df)
                if len(depth_burst) > 10:
                    depth_burst = depth_burst[-10:]
                depth_frame = df
            elif len(depth_burst) > 0:
                depth_frame = depth_burst[-1]
            else:
                depth_frame = None

            # FPS counter
            frame_count += 1
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                fps_display = frame_count / elapsed
                frame_count = 0
                fps_start = time.time()

            # Run YOLO
            results = model(frame, conf=args.conf, verbose=False)

            num_objects = 0
            best_det = None

            if len(results) > 0 and len(results[0].boxes) > 0:
                boxes = results[0].boxes
                num_objects = len(boxes)

                # Process best detection
                best_idx = boxes.conf.argmax().item()
                box = boxes[best_idx]
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                class_name = model.names[cls_id]
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                cx_box = int((x1 + x2) / 2)
                cy_box = int((y1 + y2) / 2)

                # Get depth
                z_mm = 0
                object_height_mm = 0
                if depth_frame is not None and len(depth_burst) >= args.burst:
                    z_samples = []
                    ground_samples = []
                    h, w = depth_frame.shape[:2]
                    for df in depth_burst[-args.burst:]:
                        if df.shape[:2] != (480, 640):
                            df = cv2.resize(df, (640, 480),
                                            interpolation=cv2.INTER_NEAREST)
                        z_val = get_depth_for_bbox(df, x1, y1, x2, y2)
                        if z_val > 0:
                            z_samples.append(z_val)
                        g_val = get_ground_depth(df, x1, y1, x2, y2)
                        if g_val > 0:
                            ground_samples.append(g_val)

                    if len(z_samples) >= args.burst // 2 + 1:
                        z_mm = int(np.median(z_samples))
                    elif len(z_samples) > 0:
                        z_mm = int(np.median(z_samples))  # use whatever we have
                    ground_z_mm = int(np.median(ground_samples)) if len(ground_samples) >= 2 else z_mm
                    object_height_mm = max(0, ground_z_mm - z_mm)

                # Fallback 1: single frame ROI depth
                if z_mm == 0 and depth_frame is not None:
                    z_mm = get_depth_for_bbox(depth_frame, x1, y1, x2, y2)

                # Fallback 2: raw center pixel depth (most reliable)
                if z_mm == 0 and depth_frame is not None:
                    h_d, w_d = depth_frame.shape[:2]
                    raw_cx = min(int((x1 + x2) / 2), w_d - 1)
                    raw_cy = min(int((y1 + y2) / 2), h_d - 1)
                    raw_z = int(depth_frame[raw_cy, raw_cx])
                    if 100 < raw_z < 10000:
                        z_mm = raw_z

                # DEBUG: comprehensive diagnostics every 30th frame
                if frame_count % 30 == 0:
                    # Test 1: Is depth_data arriving from camera?
                    depth_arriving = depth_data is not None
                    # Test 2: Is depth_frame valid?
                    df_shape = depth_frame.shape if depth_frame is not None else 'NONE'
                    # Test 3: What does single-frame depth give?
                    single_z = 0
                    if depth_frame is not None:
                        single_z = get_depth_for_bbox(depth_frame, x1, y1, x2, y2)
                    # Test 4: Raw depth value at bbox center
                    raw_center_depth = 0
                    if depth_frame is not None:
                        dh, dw = depth_frame.shape[:2]
                        dcx = min(int((x1+x2)/2), dw-1)
                        dcy = min(int((y1+y2)/2), dh-1)
                        raw_center_depth = int(depth_frame[dcy, dcx])
                    # Test 5: Burst buffer stats
                    burst_len = len(depth_burst)
                    z_samp_count = len(z_samples) if 'z_samples' in dir() else -1

                    print(f"[DBG] === FRAME DIAGNOSTICS ===")
                    print(f"  YOLO: {class_name} conf={conf:.2f} bbox=({int(x1)},{int(y1)},{int(x2)},{int(y2)})")
                    print(f"  T1 depth_data arriving: {depth_arriving}")
                    print(f"  T2 depth_frame shape: {df_shape}")
                    print(f"  T3 get_depth_for_bbox: {single_z}mm")
                    print(f"  T4 raw center pixel depth: {raw_center_depth}mm")
                    print(f"  T5 burst buffer: {burst_len} frames, z_samples: {z_samp_count}")
                    print(f"  FINAL z_mm: {z_mm} → {'API OK' if z_mm > 0 else 'API no_detection'}")
                    print()

                # Compute camera-frame XYZ
                x_mm = int((cx_box - cx_cam) * z_mm / fx) if z_mm > 0 else 0
                y_mm = int((cy_box - cy_cam) * z_mm / fy) if z_mm > 0 else 0

                # Draw all bboxes
                for i in range(len(boxes)):
                    bx1, by1, bx2, by2 = boxes[i].xyxy[0].cpu().numpy()
                    c = float(boxes[i].conf[0])
                    cid = int(boxes[i].cls[0])
                    nm = model.names[cid]
                    color = (0, 255, 255) if i == best_idx else (100, 100, 100)
                    cv2.rectangle(annotated, (int(bx1), int(by1)),
                                  (int(bx2), int(by2)), color, 2)
                    cv2.putText(annotated, f"{nm} {c:.2f}",
                                (int(bx1), int(by1) - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # Draw crosshair on best
                cv2.drawMarker(annotated, (cx_box, cy_box),
                               (0, 255, 0), cv2.MARKER_CROSS, 15, 2)

                if z_mm > 0:
                    # Compute base_link coords (hardcoded TF for home pose)
                    base = cam_optical_to_base_link(
                        x_mm / 1000.0, y_mm / 1000.0, z_mm / 1000.0)
                    bx_mm = int(base[0] * 1000)
                    by_mm = int(base[1] * 1000)
                    bz_mm = int(base[2] * 1000)
                    dist_j1 = int(math.sqrt(bx_mm**2 + by_mm**2))

                    ly = int(y2) + 20
                    for txt, clr in [
                        (f"cam: X={x_mm} Y={y_mm} Z={z_mm}mm", (0, 255, 255)),
                        (f"base: X={bx_mm} Y={by_mm} Z={bz_mm}mm", (255, 200, 0)),
                        (f"dist:{dist_j1}mm h={object_height_mm}mm burst:{min(len(depth_burst), args.burst)}/{args.burst}", (0, 200, 255)),
                    ]:
                        cv2.putText(annotated, txt, (int(x1), ly),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
                        cv2.putText(annotated, txt, (int(x1), ly),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, clr, 2)
                        ly += 18

                    # Update detection for API
                    gz = ground_z_mm if 'ground_z_mm' in dir() else z_mm
                    # Compute ground point in base_link
                    ground_x_mm_cam = int((cx_box - cx_cam) * gz / fx)
                    ground_y_mm_cam = int((cy_box - cy_cam) * gz / fy)
                    base_ground = cam_optical_to_base_link(
                        ground_x_mm_cam / 1000.0, ground_y_mm_cam / 1000.0, gz / 1000.0)

                    best_det = {
                        'class': class_name,
                        'confidence': round(conf, 3),
                        'cam_x_mm': x_mm,
                        'cam_y_mm': y_mm,
                        'cam_z_mm': z_mm,
                        'base_x_mm': bx_mm,
                        'base_y_mm': by_mm,
                        'base_z_mm': bz_mm,
                        'base_ground_z_mm': int(base_ground[2] * 1000),
                        'object_height_mm': object_height_mm,
                        'ground_z_mm': gz,
                        'bbox': [int(x1), int(y1), int(x2), int(y2)],
                        'timestamp': time.time(),
                        'status': 'ok'
                    }

            # HUD
            cv2.putText(annotated,
                        f"FPS: {fps_display:.1f} | Objects: {num_objects}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 0), 2)
            cv2.putText(annotated,
                        f"TensorRT | Conf: {args.conf}",
                        (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (0, 255, 0), 1)

            # Update globals
            with frame_lock:
                latest_frame = annotated
            with detection_lock:
                latest_detection = best_det


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
