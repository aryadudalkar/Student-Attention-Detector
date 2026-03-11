"""
Smart Classroom — Video File Pipeline
======================================
Runs attention detection on a pre-recorded video.

Usage:
    python video_test.py                        # uses ../sample.mp4
    python video_test.py path/to/video.mp4

Press ESC to quit early.  A JSON session report is saved to ../attention_logs/.
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


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _yolo_confidence(model, crop) -> float:
    """Return the top box confidence from the attention YOLO model, or 0.3."""
    if model is None or crop.size == 0:
        return 0.3
    results = model(crop, verbose=False)
    if results and len(results[0].boxes) > 0:
        return float(results[0].boxes[0].conf[0])
    return 0.3


def _draw_hud(frame, student_id, label, score, object_det, x1, y1, x2, y2, color):
    """Draw bounding box + label overlay for one student."""
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

def run(video_path: str):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        sys.exit(1)

    tracker       = SimpleTracker()
    score_tracker = ScoreTracker()

    print(f"[INFO] Processing: {video_path}")
    print("[INFO] Press ESC to quit early.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # --- Detect persons ---
        person_results = person_model(frame, verbose=False)
        boxes_list = []
        for result in person_results:
            for box in result.boxes:
                if int(box.cls[0]) != 0:   # class 0 = person (COCO)
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                boxes_list.append((x1, y1, x2, y2))

        tracked = tracker.update(boxes_list)

        # --- Per-student analysis ---
        for student_id, center in tracked.items():
            for (x1, y1, x2, y2) in boxes_list:
                bx, by = (x1 + x2) // 2, (y1 + y2) // 2
                if abs(bx - center[0]) > 15 or abs(by - center[1]) > 15:
                    continue  # not this student's box

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
                          object_detected, x1, y1, x2, y2, color)
                break  # matched this student; move to next

        cv2.imshow("Smart Classroom — Video", frame)
        if cv2.waitKey(1) & 0xFF == 27:   # ESC
            break

    cap.release()
    cv2.destroyAllWindows()

    # --- Session report ---
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
    if len(sys.argv) > 1:
        # Join all extra args so unquoted paths with spaces still work
        video_path = " ".join(sys.argv[1:])
    else:
        video_path = os.path.join(_BASE, "..", "sample.mp4")
    run(video_path)