"""
Gaze estimation using YOLOv8n-pose face keypoints.
No MediaPipe dependency required.

Without iris landmarks we use:
  - Horizontal: nose centering between eyes (yaw proxy)
  - Vertical:   nose sitting below eye line (pitch proxy)
"""

import numpy as np
from _shared_models import get_pose_model

_NOSE      = 0
_LEFT_EYE  = 1
_RIGHT_EYE = 2


def get_gaze_score(frame):
    """
    Estimate forward-gaze likelihood from face keypoints.
    Returns [0, 1] where 1 = looking roughly forward.
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

    kpts = kpts_xy[0].cpu().numpy()
    conf = kpts_cf[0].cpu().numpy() if kpts_cf is not None else None

    if conf is not None and (
        conf[_NOSE] < 0.3 or conf[_LEFT_EYE] < 0.3 or conf[_RIGHT_EYE] < 0.3
    ):
        return 0.3

    nose      = kpts[_NOSE]
    left_eye  = kpts[_LEFT_EYE]
    right_eye = kpts[_RIGHT_EYE]

    eye_mid_x = (left_eye[0] + right_eye[0]) / 2
    eye_mid_y = (left_eye[1] + right_eye[1]) / 2
    eye_span  = max(abs(right_eye[0] - left_eye[0]), 1.0)

    # Horizontal: nose should be centred between eyes
    horiz_offset = abs(nose[0] - eye_mid_x) / eye_span
    horiz_score  = 1.0 - min(horiz_offset, 1.0)

    # Vertical: nose should be below eye centre (positive = normal)
    vert_score = 1.0 if (nose[1] - eye_mid_y) > 5 else 0.5

    score = 0.6 * horiz_score + 0.4 * vert_score
    return float(np.clip(score, 0.0, 1.0))