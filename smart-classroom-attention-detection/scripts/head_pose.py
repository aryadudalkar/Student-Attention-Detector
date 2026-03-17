"""
Head-pose estimation using MediaPipe FaceMesh + solvePnP.

Returns a forward-facing score in [0, 1] and can optionally return
Euler angles (pitch, yaw, roll).
"""

import cv2
import mediapipe as mp
import numpy as np
from _shared_models import get_pose_model

_FACE_MESH = None

_IDX_NOSE = 1
_IDX_CHIN = 152
_IDX_LEFT_EYE = 33
_IDX_RIGHT_EYE = 263
_IDX_LEFT_MOUTH = 61
_IDX_RIGHT_MOUTH = 291

_MODEL_POINTS = np.array(
    [
        (0.0, 0.0, 0.0),
        (0.0, -63.6, -12.5),
        (-43.3, 32.7, -26.0),
        (43.3, 32.7, -26.0),
        (-28.9, -28.9, -24.1),
        (28.9, -28.9, -24.1),
    ],
    dtype=np.float64,
)


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


def _euler_from_crop(face_crop):
    if face_crop is None or face_crop.size == 0:
        return None

    h, w = face_crop.shape[:2]
    if h < 20 or w < 20:
        return None

    mesh = _get_face_mesh()
    if mesh is None:
        return None
    rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
    result = mesh.process(rgb)
    if not result.multi_face_landmarks:
        return None

    lm = result.multi_face_landmarks[0].landmark

    image_points = np.array(
        [
            (lm[_IDX_NOSE].x * w, lm[_IDX_NOSE].y * h),
            (lm[_IDX_CHIN].x * w, lm[_IDX_CHIN].y * h),
            (lm[_IDX_LEFT_EYE].x * w, lm[_IDX_LEFT_EYE].y * h),
            (lm[_IDX_RIGHT_EYE].x * w, lm[_IDX_RIGHT_EYE].y * h),
            (lm[_IDX_LEFT_MOUTH].x * w, lm[_IDX_LEFT_MOUTH].y * h),
            (lm[_IDX_RIGHT_MOUTH].x * w, lm[_IDX_RIGHT_MOUTH].y * h),
        ],
        dtype=np.float64,
    )

    focal_length = float(w)
    center = (w / 2.0, h / 2.0)
    camera_matrix = np.array(
        [
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1],
        ],
        dtype=np.float64,
    )
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    ok, rvec, _ = cv2.solvePnP(
        _MODEL_POINTS,
        image_points,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not ok:
        return None

    rot_mtx, _ = cv2.Rodrigues(rvec)
    sy = np.sqrt(rot_mtx[0, 0] ** 2 + rot_mtx[1, 0] ** 2)
    singular = sy < 1e-6

    if not singular:
        pitch = np.degrees(np.arctan2(rot_mtx[2, 1], rot_mtx[2, 2]))
        yaw = np.degrees(np.arctan2(-rot_mtx[2, 0], sy))
        roll = np.degrees(np.arctan2(rot_mtx[1, 0], rot_mtx[0, 0]))
    else:
        pitch = np.degrees(np.arctan2(-rot_mtx[1, 2], rot_mtx[1, 1]))
        yaw = np.degrees(np.arctan2(-rot_mtx[2, 0], sy))
        roll = 0.0

    return {
        "pitch": float(pitch),
        "yaw": float(yaw),
        "roll": float(roll),
    }


def _fallback_from_pose(face_crop):
    """Fallback when mediapipe FaceMesh is unavailable in runtime env."""
    if face_crop is None or face_crop.size == 0:
        return None

    model = get_pose_model()
    results = model(face_crop, verbose=False)
    if not results or results[0].keypoints is None:
        return None

    kpts_xy = results[0].keypoints.xy
    if len(kpts_xy) == 0:
        return None
    kpts = kpts_xy[0].cpu().numpy()

    nose = kpts[0]
    left_eye = kpts[1]
    right_eye = kpts[2]
    eye_mid_x = (left_eye[0] + right_eye[0]) / 2.0
    eye_span = max(abs(right_eye[0] - left_eye[0]), 1.0)

    yaw_proxy = ((nose[0] - eye_mid_x) / eye_span) * 45.0
    pitch_proxy = 0.0
    roll_proxy = 0.0
    return {"pitch": float(pitch_proxy), "yaw": float(yaw_proxy), "roll": float(roll_proxy)}


def get_head_score(frame, return_details=False):
    """
    Estimate head pose score from a face crop.

    Args:
        frame: face crop (preferred) or person crop.
        return_details: whether to also return Euler angles.

    Returns:
        float score in [0,1], or (score, details) when return_details=True.
    """
    details = _euler_from_crop(frame)
    if details is None:
        details = _fallback_from_pose(frame)
    if details is None:
        if return_details:
            return 0.3, {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}
        return 0.3

    yaw = details["yaw"]
    pitch = details["pitch"]

    yaw_score = max(0.0, 1.0 - (abs(yaw) / 45.0))
    pitch_score = max(0.0, 1.0 - (max(0.0, -pitch - 10.0) / 35.0))

    score = 0.65 * yaw_score + 0.35 * pitch_score

    if abs(yaw) > 30.0 or pitch < -20.0:
        score = min(score, 0.35)

    score = float(np.clip(score, 0.0, 1.0))
    if return_details:
        return score, details
    return score