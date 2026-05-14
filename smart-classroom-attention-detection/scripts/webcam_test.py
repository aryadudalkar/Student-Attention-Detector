"""
Smart Classroom — Live Webcam Pipeline
========================================
HYBRID OPTIMIZED VERSION - Uses your fast webcam wisely
"""

import cv2
import os
import sys
import threading
from collections import deque
import numpy as np
from ultralytics import YOLO

from head_pose import get_head_score
from gaze import get_gaze_score
from pose_estimation import get_pose_features
from object_classifier import classify_hand_object
from attention_logic import calculate_attention, get_attention_label
from score_tracker import ScoreTracker
from tracker import SimpleTracker
from face_detector import FaceDetector
from seat_manager import build_seat_rois, in_any_seat
from api_client import start_session, end_session, log_attention_batch, get_or_create_student

# ------------------------------------------------------------------
# Load models
# ------------------------------------------------------------------
_BASE = os.path.dirname(__file__)

_person_model_path = os.path.join(_BASE, "..", "yolov8n.pt")
person_model = YOLO(_person_model_path if os.path.exists(_person_model_path) else "yolov8n.pt")

_attention_model_path = os.path.join(_BASE, "..", "model", "best.pt")
attention_model = YOLO(_attention_model_path) if os.path.exists(_attention_model_path) else None
face_detector = FaceDetector(conf=0.35)


def _yolo_confidence(model, crop) -> float:
    if model is None or crop.size == 0:
        return 0.3
    results = model(crop, verbose=False)
    if results and len(results[0].boxes) > 0:
        return float(results[0].boxes[0].conf[0])
    return 0.3


def _draw_hud(frame, student_id, student_name, label, score, x1, y1, x2, y2, color, usn=None, face_bbox=None):
    """Draw bounding box + label overlay for one student."""
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    if face_bbox is not None:
        fx1, fy1, fx2, fy2 = face_bbox
        cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), (255, 220, 0), 2)

    if usn:
        name_str = f"#{usn[-3:]}"
    elif student_name:
        name_str = f"{student_name}"
    else:
        name_str = f"ID:{student_id}"
    
    tag = f"{name_str}  {label}  ({score:.2f})"
    (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    bg_y1 = max(0, y1 - th - 8)
    cv2.rectangle(frame, (x1, bg_y1), (x1 + tw + 4, y1), color, -1)
    cv2.putText(frame, tag, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)


# ------------------------------------------------------------------
# Main pipeline
# ------------------------------------------------------------------

def run(camera_index: int = 0):
    # Good resolution since webcam is fast
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera index {camera_index}")
        sys.exit(1)
    
    # Use good resolution but limit FPS to save processing
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)  # Cap at 30 FPS
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    tracker       = SimpleTracker()
    score_tracker = ScoreTracker()
    seat_rois_px  = None

    # API session setup
    session_id = start_session(label="Webcam Session")
    batch_logs = []
    batch_counter = 0
    BATCH_SIZE = 5  # Send to API every N observations (lower = faster dashboard updates)

    print(f"[INFO] Webcam started (camera {camera_index}) - HYBRID MODE")
    print(f"[INFO] Batch size: {BATCH_SIZE} (data sent to dashboard every {BATCH_SIZE} frames)")
    print("[INFO] Press ESC to quit.\n")

    # SMART FRAME SKIPPING: Process detection at different rates
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # --- Detect persons ---
        if seat_rois_px is None:
            seat_rois_px = build_seat_rois(frame.shape)

        person_results = person_model(frame, verbose=False, conf=0.50)
        boxes_list = []
        for result in person_results:
            for box in result.boxes:
                if int(box.cls[0]) != 0:   # class 0 = person (COCO)
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                if not in_any_seat((cx, cy), seat_rois_px):
                    continue
                boxes_list.append((x1, y1, x2, y2, conf))

        # Early skip if no detections
        if not boxes_list:
            cv2.imshow("Smart Classroom — Webcam", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
            continue

        tracked = tracker.update(boxes_list, frame=frame)

        # STAGE 2: Process each student with tiered processing
        max_students = 3
        for trk in tracked[:max_students]:
            student_id = trk["student_id"]
            student_name = trk.get("name")
            student_usn = trk.get("usn")
            x1, y1, x2, y2 = trk["bbox"]

            # Ensure valid coordinates
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frame.shape[1], x2)
            y2 = min(frame.shape[0], y2)

            person_crop = frame[y1:y2, x1:x2]
            if person_crop.size == 0:
                continue

            # Face detection (always run - it's fast)
            face_box_local = face_detector.detect_primary_face(person_crop)
            if face_box_local is not None:
                fx1, fy1, fx2, fy2, _ = face_box_local
                face_crop = person_crop[fy1:fy2, fx1:fx2]
                face_box_global = (x1 + fx1, y1 + fy1, x1 + fx2, y1 + fy2)
                has_face = True
            else:
                face_crop = None
                face_box_global = None
                has_face = False

            yolo_score = _yolo_confidence(attention_model, person_crop)
            
            if has_face and face_crop is not None and face_crop.size > 0:
                head_score_val, head_details = get_head_score(face_crop, return_details=True)
                gaze_score = get_gaze_score(face_crop)
            else:
                head_score_val, head_details = 0.3, {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}
                gaze_score = 0.5
            
            pose_data = get_pose_features(frame, (x1, y1, x2, y2))
            object_detected = classify_hand_object(frame, (x1, y1, x2, y2))

            final_score = calculate_attention(
                yolo_score,
                {
                    "score": head_score_val,
                    "pitch": head_details["pitch"],
                    "yaw": head_details["yaw"],
                    "roll": head_details["roll"],
                },
                gaze_score,
                pose_data,
                object_detected,
            )
            label, color = get_attention_label(final_score, object_detected)

            score_tracker.update(student_id, final_score, label)

            # Send to API
            db_student_id = get_or_create_student(student_id, name=student_name, usn=student_usn)
            if db_student_id and session_id:
                batch_logs.append({
                    "session": session_id,
                    "student": db_student_id,
                    "attention_score": final_score,
                    "label": label,
                    "object_detected": object_detected,
                    "yolo_score": yolo_score,
                    "gaze_score": gaze_score,
                    "head_score": head_score_val,
                    "pitch": head_details.get("pitch"),
                    "yaw": head_details.get("yaw"),
                    "roll": head_details.get("roll"),
                })

            # Send batch every BATCH_SIZE observations
            batch_counter += 1
            if batch_counter >= BATCH_SIZE:
                print(f"[BATCH] Sending {len(batch_logs)} logs to API (session={session_id})")
                log_attention_batch(batch_logs)
                batch_logs = []
                batch_counter = 0

            _draw_hud(
                frame,
                student_id,
                student_name,
                label,
                final_score,
                x1,
                y1,
                x2,
                y2,
                color,
                usn=student_usn,
                face_bbox=face_box_global,
            )

        cv2.imshow("Smart Classroom — Webcam", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

    # Flush remaining logs and end session
    if batch_logs:
        log_attention_batch(batch_logs)
    if session_id:
        end_session(session_id)

    saved_path = score_tracker.save()
    print(f"\n[INFO] Session report saved: {saved_path}")
    summary = score_tracker.get_session_summary()
    print("\n--- Session Summary ---")
    for sid, data in summary.items():
        print(
            f"  Student {sid}: avg={data['avg_score']:.3f}  "
            f"attentive={data['attentive_pct']}%  "
            f"distracted={data['distracted_pct']}%  "
            f"phone_frames={data['phone_frames']}  "
            f"reading_frames={data['reading_frames']}"
        )

    score_tracker.print_weekly_report()


if __name__ == "__main__":
    cam = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    run(cam)