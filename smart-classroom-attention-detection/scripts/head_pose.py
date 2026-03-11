"""
Head-pose estimation using YOLOv8n-pose keypoints.
No MediaPipe dependency required.
"""

import numpy as np
from _shared_models import get_pose_model

# COCO pose keypoint indices
_NOSE      = 0
_LEFT_EYE  = 1
_RIGHT_EYE = 2


def get_head_score(frame):
    """
    Estimate head yaw from face keypoints.
    Returns [0, 1] where 1 = facing directly forward.
    """
    if frame is None or frame.size == 0:
        return 0.3

    model   = get_pose_model()
    results = model(frame, verbose=False)

    if not results or results[0].keypoints is None:
        return 0.3

    kpts_xy = results[0].keypoints.xy
    kpts_cf = results[0].keypoints.conf
    if len(kpts_xy) == 0:
        return 0.3

    kpts = kpts_xy[0].cpu().numpy()   # (17, 2)
    conf = kpts_cf[0].cpu().numpy() if kpts_cf is not None else None

    # Reject low-confidence keypoints
    if conf is not None and (
        conf[_NOSE] < 0.3 or conf[_LEFT_EYE] < 0.3 or conf[_RIGHT_EYE] < 0.3
    ):
        return 0.3

    nose      = kpts[_NOSE]
    left_eye  = kpts[_LEFT_EYE]
    right_eye = kpts[_RIGHT_EYE]

    eye_mid_x = (left_eye[0] + right_eye[0]) / 2
    eye_span  = max(abs(right_eye[0] - left_eye[0]), 1.0)

    # Normalise horizontal nose-to-eye-centre offset by eye span
    yaw_ratio = abs(nose[0] - eye_mid_x) / eye_span  # 0 = front, ~0.5 = profile
    score = 1.0 - min(yaw_ratio, 1.0)
    return float(np.clip(score, 0.0, 1.0))