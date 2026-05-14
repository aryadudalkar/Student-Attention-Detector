"""
Head-pose estimation using MediaPipe FaceMesh + solvePnP.

Returns a forward-facing score in [0, 1] and can optionally return
Euler angles (pitch, yaw, roll).
"""

import cv2
import mediapipe as mp
import numpy as np
from _shared_models import get_pose_model

# ── CONFIGURABLE THRESHOLDS (degrees) ──────────────────────────────
# |angle| <= ATTENTIVE_MAX  → considered facing forward (attentive)
# ATTENTIVE_MAX < |angle| <= DISTRACTED_MIN → borderline (partial)
# |angle| > DISTRACTED_MIN  → clearly looking away (distracted)
ATTENTIVE_MAX_YAW    = 25.0   # degrees left/right
ATTENTIVE_MAX_PITCH  = 25.0   # degrees up/down
DISTRACTED_MIN_YAW   = 40.0
DISTRACTED_MIN_PITCH = 40.0

# Natural pitch offset: webcams sit above screen, so looking at screen
# naturally produces a small negative pitch.  This offset is SUBTRACTED
# from the measured pitch before thresholding so that looking at the
# screen registers as ~0°.
PITCH_OFFSET = -8.0   # degrees (negative = looking slightly down is normal)
# ────────────────────────────────────────────────────────────────────

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

_frame_counter = 0


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

    Uses symmetric thresholds for yaw (left/right) and offset-corrected
    pitch (up/down) so that looking at the screen is considered forward.

    Args:
        frame: face crop (preferred) or person crop.
        return_details: whether to also return Euler angles.

    Returns:
        float score in [0,1], or (score, details) when return_details=True.
    """
    global _frame_counter
    _frame_counter += 1

    details = _euler_from_crop(frame)
    if details is None:
        details = _fallback_from_pose(frame)
    if details is None:
        if return_details:
            return 0.60, {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}
        return 0.60

    raw_yaw = details["yaw"]
    raw_pitch = details["pitch"]

    # Apply offset: subtract natural webcam pitch so that "looking at screen" ≈ 0°
    corrected_pitch = raw_pitch - PITCH_OFFSET
    abs_yaw = abs(raw_yaw)
    abs_pitch = abs(corrected_pitch)

    # ── Yaw score: linear ramp from 1.0 (forward) to 0.0 (>= DISTRACTED) ──
    if abs_yaw <= ATTENTIVE_MAX_YAW:
        yaw_score = 1.0
    elif abs_yaw >= DISTRACTED_MIN_YAW:
        yaw_score = 0.0
    else:
        yaw_score = 1.0 - (abs_yaw - ATTENTIVE_MAX_YAW) / (DISTRACTED_MIN_YAW - ATTENTIVE_MAX_YAW)

    # ── Pitch score: same approach, with offset correction ──
    if abs_pitch <= ATTENTIVE_MAX_PITCH:
        pitch_score = 1.0
    elif abs_pitch >= DISTRACTED_MIN_PITCH:
        pitch_score = 0.0
    else:
        pitch_score = 1.0 - (abs_pitch - ATTENTIVE_MAX_PITCH) / (DISTRACTED_MIN_PITCH - ATTENTIVE_MAX_PITCH)

    # Combined: weighted average (yaw more important than pitch for attention)
    score = 0.6 * yaw_score + 0.4 * pitch_score

    # Hard cap ONLY for extreme angles
    if abs_yaw > DISTRACTED_MIN_YAW or abs_pitch > DISTRACTED_MIN_PITCH:
        score = min(score, 0.20)

    score = float(np.clip(score, 0.0, 1.0))

    # Debug logging (every 30th frame to avoid spam)
    if _frame_counter % 30 == 0:
        print(f"[HEAD_POSE] yaw={raw_yaw:.1f}° pitch={raw_pitch:.1f}° (corrected={corrected_pitch:.1f}°) | "
              f"yaw_score={yaw_score:.2f} pitch_score={pitch_score:.2f} | "
              f"final_head_score={score:.2f}")

    if return_details:
        return score, details
    return score