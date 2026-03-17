"""
Gaze estimation using MediaPipe iris landmarks.

Computes iris-center offset relative to eye corners to estimate whether
the student is looking near the forward direction.
"""

import cv2
import mediapipe as mp
import numpy as np
from _shared_models import get_pose_model

_FACE_MESH = None

_LEFT_OUTER = 33
_LEFT_INNER = 133
_RIGHT_INNER = 362
_RIGHT_OUTER = 263

_LEFT_IRIS = [474, 475, 476, 477]
_RIGHT_IRIS = [469, 470, 471, 472]


def _get_face_mesh():
    global _FACE_MESH
    if mp is None or not hasattr(mp, "solutions"):
        return None
    if _FACE_MESH is None:
        _FACE_MESH = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
    return _FACE_MESH


def _lm_to_xy(lm, idx, w, h):
    return np.array([lm[idx].x * w, lm[idx].y * h], dtype=np.float32)


def get_gaze_score(frame, return_details=False):
    """
    Estimate forward gaze score from a face crop.

    Returns:
        score in [0,1] or (score, details) if return_details=True.
    """
    if frame is None or frame.size == 0:
        if return_details:
            return 0.3, {"gaze_x": 0.0, "gaze_y": 0.0}
        return 0.3

    h, w = frame.shape[:2]
    if h < 20 or w < 20:
        if return_details:
            return 0.3, {"gaze_x": 0.0, "gaze_y": 0.0}
        return 0.3

    mesh = _get_face_mesh()
    if mesh is None:
        return _fallback_gaze_pose(frame, return_details=return_details)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = mesh.process(rgb)
    if not result.multi_face_landmarks:
        if return_details:
            return 0.3, {"gaze_x": 0.0, "gaze_y": 0.0}
        return 0.3

    lm = result.multi_face_landmarks[0].landmark

    left_outer = _lm_to_xy(lm, _LEFT_OUTER, w, h)
    left_inner = _lm_to_xy(lm, _LEFT_INNER, w, h)
    right_inner = _lm_to_xy(lm, _RIGHT_INNER, w, h)
    right_outer = _lm_to_xy(lm, _RIGHT_OUTER, w, h)

    left_iris = np.mean([_lm_to_xy(lm, i, w, h) for i in _LEFT_IRIS], axis=0)
    right_iris = np.mean([_lm_to_xy(lm, i, w, h) for i in _RIGHT_IRIS], axis=0)

    left_width = max(1.0, np.linalg.norm(left_inner - left_outer))
    right_width = max(1.0, np.linalg.norm(right_outer - right_inner))

    left_center = (left_outer + left_inner) * 0.5
    right_center = (right_outer + right_inner) * 0.5

    left_x = (left_iris[0] - left_center[0]) / left_width
    right_x = (right_iris[0] - right_center[0]) / right_width
    gaze_x = float((left_x + right_x) * 0.5)

    left_eye_mid_y = (left_outer[1] + left_inner[1]) * 0.5
    right_eye_mid_y = (right_outer[1] + right_inner[1]) * 0.5
    eye_h_ref = max(1.0, 0.5 * (left_width + right_width) * 0.35)
    gaze_y = float((((left_iris[1] - left_eye_mid_y) + (right_iris[1] - right_eye_mid_y)) * 0.5) / eye_h_ref)

    horizontal_score = max(0.0, 1.0 - min(abs(gaze_x) / 0.22, 1.0))
    vertical_score = max(0.0, 1.0 - min(abs(gaze_y) / 0.35, 1.0))
    score = float(np.clip(0.7 * horizontal_score + 0.3 * vertical_score, 0.0, 1.0))

    if return_details:
        return score, {"gaze_x": gaze_x, "gaze_y": gaze_y}
    return score


def _fallback_gaze_pose(frame, return_details=False):
    """Fallback gaze proxy based on nose centering between eyes."""
    if frame is None or frame.size == 0:
        if return_details:
            return 0.3, {"gaze_x": 0.0, "gaze_y": 0.0}
        return 0.3

    model = get_pose_model()
    results = model(frame, verbose=False)
    if not results or results[0].keypoints is None:
        if return_details:
            return 0.3, {"gaze_x": 0.0, "gaze_y": 0.0}
        return 0.3

    kpts_xy = results[0].keypoints.xy
    if len(kpts_xy) == 0:
        if return_details:
            return 0.3, {"gaze_x": 0.0, "gaze_y": 0.0}
        return 0.3

    kpts = kpts_xy[0].cpu().numpy()
    nose = kpts[0]
    left_eye = kpts[1]
    right_eye = kpts[2]

    eye_mid_x = (left_eye[0] + right_eye[0]) / 2.0
    eye_span = max(abs(right_eye[0] - left_eye[0]), 1.0)
    gaze_x = float((nose[0] - eye_mid_x) / eye_span)
    score = float(np.clip(1.0 - min(abs(gaze_x) / 0.35, 1.0), 0.0, 1.0))

    if return_details:
        return score, {"gaze_x": gaze_x, "gaze_y": 0.0}
    return score