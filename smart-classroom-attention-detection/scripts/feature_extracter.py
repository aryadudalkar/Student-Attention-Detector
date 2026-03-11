import numpy as np
from head_pose import get_head_score
from gaze import get_gaze_score
from pose_estimation import get_pose_features
from object_classifier import classify_hand_object


def extract_features(frame, bbox):
    """
    Extract a 10-dimensional feature vector for a detected person.

    Features:
        [0] head_score      — head orientation (0-1)
        [1] gaze_score      — eye gaze direction (0-1)
        [2] spine_align     — body facing forward (0/1)
        [3] writing         — writing/reading gesture (0/1)
        [4] phone_detected  — phone visible in hand region (0/1)
        [5] book_detected   — book visible in hand region (0/1)
        [6-9] norm_bbox     — normalised (x1, y1, x2, y2)

    Returns:
        np.ndarray of shape (10,)
    """
    x1, y1, x2, y2 = bbox
    crop = frame[y1:y2, x1:x2]

    head_score = get_head_score(crop)
    gaze_score = get_gaze_score(crop)
    pose_data  = get_pose_features(frame, bbox)

    spine_align = 0
    writing     = 0
    if pose_data:
        spine_align = 1 if pose_data["body_forward"] else 0
        writing     = 1 if pose_data["writing"]       else 0

    obj = classify_hand_object(frame, bbox)
    phone_detected = 1 if obj == "phone" else 0
    book_detected  = 1 if obj == "book"  else 0

    h, w = frame.shape[:2]
    feature_vector = np.array([
        head_score,
        gaze_score,
        spine_align,
        writing,
        phone_detected,
        book_detected,
        x1 / w,
        y1 / h,
        x2 / w,
        y2 / h,
    ], dtype=np.float32)

    return feature_vector