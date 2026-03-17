"""
Smart Classroom — Live Webcam Pipeline
========================================
Runs real-time attention detection on a webcam feed.

Usage:
    python webcam_test.py           # default camera (index 0)
    python webcam_test.py 1         # camera index 1

Press ESC to quit.  A JSON session report is saved to ../attention_logs/.
"""

import cv2
import os
import sys

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

# ------------------------------------------------------------------
# Load models
# ------------------------------------------------------------------
_BASE = os.path.dirname(__file__)

_person_model_path = os.path.join(_BASE, "..", "yolov8m.pt")
person_model = YOLO(_person_model_path if os.path.exists(_person_model_path) else "yolov8m.pt")

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

    # Display USN last 3 digits if available, else student name, else numeric ID
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
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera index {camera_index}")
        sys.exit(1)

    tracker       = SimpleTracker()
    score_tracker = ScoreTracker()
    seat_rois_px  = None

    print(f"[INFO] Webcam started (camera {camera_index})")
    print("[INFO] Press ESC to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if seat_rois_px is None:
            seat_rois_px = build_seat_rois(frame.shape)

        person_results = person_model(frame, verbose=False, conf=0.50)
        boxes_list = []
        for result in person_results:
            for box in result.boxes:
                if int(box.cls[0]) != 0:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                if not in_any_seat((cx, cy), seat_rois_px):
                    continue
                boxes_list.append((x1, y1, x2, y2, conf))

        tracked = tracker.update(boxes_list, frame=frame)

        for trk in tracked:
            student_id = trk["student_id"]
            student_name = trk.get("name")
            student_usn = trk.get("usn")
            x1, y1, x2, y2 = trk["bbox"]

            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frame.shape[1], x2)
            y2 = min(frame.shape[0], y2)

            person_crop = frame[y1:y2, x1:x2]
            if person_crop.size == 0:
                continue

            face_box_local = face_detector.detect_primary_face(person_crop)
            if face_box_local is not None:
                fx1, fy1, fx2, fy2, _ = face_box_local
                face_crop = person_crop[fy1:fy2, fx1:fx2]
                face_box_global = (x1 + fx1, y1 + fy1, x1 + fx2, y1 + fy2)
            else:
                face_crop = person_crop
                face_box_global = None

            yolo_score = _yolo_confidence(attention_model, person_crop)
            head_score_val, head_details = get_head_score(face_crop, return_details=True)
            gaze_score = get_gaze_score(face_crop)
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