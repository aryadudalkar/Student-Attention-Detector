"""
Body-pose estimation using YOLOv8n-pose keypoints.
No MediaPipe dependency required.

COCO keypoint indices used:
    0  nose          5  left_shoulder    6  right_shoulder
    9  left_wrist   10  right_wrist
   11  left_hip     12  right_hip
"""

import numpy as np
from _shared_models import get_pose_model

_NOSE           = 0
_LEFT_SHOULDER  = 5
_RIGHT_SHOULDER = 6
_LEFT_WRIST     = 9
_RIGHT_WRIST    = 10
_LEFT_HIP       = 11
_RIGHT_HIP      = 12


class _KptProxy:
    """Mimics mediapipe landmark .x / .y in normalised [0,1] coords."""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


def _safe(kpts, conf, idx, w, h, min_conf=0.3):
    """Return a _KptProxy for keypoint `idx`, defaulting to centre if low confidence."""
    if conf is None or conf[idx] < min_conf:
        return _KptProxy(0.5, 0.5)
    return _KptProxy(kpts[idx][0] / w, kpts[idx][1] / h)


def get_body_features(frame):
    """Legacy compatibility wrapper — calls get_pose_features()."""
    return get_pose_features(frame, None)


def get_pose_features(frame, bbox):
    """
    Returns pose-based behavioural features for a detected person.

    Args:
        frame: Full BGR video frame.
        bbox:  (x1, y1, x2, y2) person bounding box, or None to use first detection.

    Returns:
        dict with keys: body_forward, writing, head_down, left_wrist,
        right_wrist, nose, left_shoulder, right_shoulder — or None if
        no pose was detected.
    """
    if frame is None or frame.size == 0:
        return None

    model   = get_pose_model()
    results = model(frame, verbose=False)

    if not results or results[0].keypoints is None:
        return None

    kpts_xy = results[0].keypoints.xy
    kpts_cf = results[0].keypoints.conf
    if len(kpts_xy) == 0:
        return None

    # Pick the detection whose centroid is closest to the bbox centre
    person_idx = 0
    if bbox is not None and len(kpts_xy) > 1:
        x1, y1, x2, y2 = bbox
        bx, by = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        best_dist = float("inf")
        for i, kp in enumerate(kpts_xy):
            np_kp = kp.cpu().numpy()
            valid = np_kp[np_kp[:, 0] > 0]
            if len(valid) == 0:
                continue
            cx, cy = valid[:, 0].mean(), valid[:, 1].mean()
            dist = (cx - bx) ** 2 + (cy - by) ** 2
            if dist < best_dist:
                best_dist = dist
                person_idx = i

    kpts = kpts_xy[person_idx].cpu().numpy()   # (17, 2) pixel coords
    conf = kpts_cf[person_idx].cpu().numpy() if kpts_cf is not None else None

    h, w = frame.shape[:2]

    nose           = _safe(kpts, conf, _NOSE,           w, h)
    left_shoulder  = _safe(kpts, conf, _LEFT_SHOULDER,  w, h)
    right_shoulder = _safe(kpts, conf, _RIGHT_SHOULDER, w, h)
    left_wrist     = _safe(kpts, conf, _LEFT_WRIST,     w, h)
    right_wrist    = _safe(kpts, conf, _RIGHT_WRIST,    w, h)
    left_hip       = _safe(kpts, conf, _LEFT_HIP,       w, h)
    right_hip      = _safe(kpts, conf, _RIGHT_HIP,      w, h)

    shoulder_mid_y = (left_shoulder.y + right_shoulder.y) / 2.0
    hip_mid_y      = (left_hip.y      + right_hip.y)      / 2.0

    body_forward = (
        abs(left_shoulder.y - right_shoulder.y) < 0.06 and
        abs(left_shoulder.x - right_shoulder.x) > 0.08
    )

    wrist_at_desk = (
        (shoulder_mid_y < left_wrist.y  < hip_mid_y) or
        (shoulder_mid_y < right_wrist.y < hip_mid_y)
    )
    hands_close = abs(left_wrist.x - right_wrist.x) < 0.35
    writing = wrist_at_desk and hands_close

    head_down = nose.y >= (shoulder_mid_y - 0.05)

    return {
        "body_forward":   body_forward,
        "writing":        writing,
        "head_down":      head_down,
        "left_wrist":     left_wrist,
        "right_wrist":    right_wrist,
        "nose":           nose,
        "left_shoulder":  left_shoulder,
        "right_shoulder": right_shoulder,
    }
