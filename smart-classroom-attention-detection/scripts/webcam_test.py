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

# ------------------------------------------------------------------
# Load models
# ------------------------------------------------------------------
_BASE = os.path.dirname(__file__)

person_model = YOLO(os.path.join(_BASE, "..", "yolov8n.pt"))

_attention_model_path = os.path.join(_BASE, "..", "model", "best.pt")
attention_model = YOLO(_attention_model_path) if os.path.exists(_attention_model_path) else None


def _yolo_confidence(model, crop) -> float:
    if model is None or crop.size == 0:
        return 0.3
    results = model(crop, verbose=False)
    if results and len(results[0].boxes) > 0:
        return float(results[0].boxes[0].conf[0])
    return 0.3


def _draw_hud(frame, student_id, label, score, x1, y1, x2, y2, color):
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    tag = f"ID:{student_id}  {label}  ({score:.2f})"
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

    print(f"[INFO] Webcam started (camera {camera_index})")
    print("[INFO] Press ESC to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        person_results = person_model(frame, verbose=False)
        boxes_list = []
        for result in person_results:
            for box in result.boxes:
                if int(box.cls[0]) != 0:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                boxes_list.append((x1, y1, x2, y2))

        tracked = tracker.update(boxes_list)

        for student_id, center in tracked.items():
            for (x1, y1, x2, y2) in boxes_list:
                bx, by = (x1 + x2) // 2, (y1 + y2) // 2
                if abs(bx - center[0]) > 15 or abs(by - center[1]) > 15:
                    continue

                person_crop = frame[y1:y2, x1:x2]
                if person_crop.size == 0:
                    break

                yolo_score      = _yolo_confidence(attention_model, person_crop)
                head_score      = get_head_score(person_crop)
                gaze_score      = get_gaze_score(person_crop)
                pose_data       = get_pose_features(frame, (x1, y1, x2, y2))
                object_detected = classify_hand_object(frame, (x1, y1, x2, y2))

                final_score = calculate_attention(
                    yolo_score, head_score, gaze_score,
                    pose_data, object_detected
                )
                label, color = get_attention_label(final_score, object_detected)

                score_tracker.update(student_id, final_score, label)
                _draw_hud(frame, student_id, label, final_score,
                          x1, y1, x2, y2, color)
                break

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