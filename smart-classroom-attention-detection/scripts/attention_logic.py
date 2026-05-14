"""
Attention scoring and labelling logic.

Combines YOLO model confidence, head pose angles, gaze, body pose,
and detected objects into a single [0, 1] attention score.
"""

# ── CONFIGURABLE THRESHOLDS (degrees) ── must match head_pose.py ──
ATTENTIVE_MAX_YAW    = 25.0
ATTENTIVE_MAX_PITCH  = 25.0
DISTRACTED_MIN_YAW   = 40.0
DISTRACTED_MIN_PITCH = 40.0
PITCH_OFFSET         = -8.0   # same as head_pose.py
# ────────────────────────────────────────────────────────────────────

_frame_counter = 0


def calculate_attention(yolo_score, head_score, gaze_score, pose_data,
                        object_detected="none"):
    """
    Calculate a [0, 1] attention score with book/phone discrimination.

    Scoring weights (tuned for no-custom-model scenario where yolo ≈ 0.3):
        yolo_score  0.05  — custom model confidence (low weight: often absent)
        head_score  0.45  — head orientation (primary signal)
        gaze_score  0.35  — eye gaze direction
        writing     0.10  — hands in writing position (bonus)
        body_fwd    0.05  — upright, shoulders level (small bonus)

    With good head + gaze (~1.0 each), base score ≈ 0.82 → Attentive.
    With moderate head/gaze (~0.6), base score ≈ 0.55 → Partially Attentive.
    With poor head/gaze (~0.2), base score ≈ 0.25 → Distracted.

    Object overrides (applied after base score):
        phone   → cap score at 0.25  (always distracted)
        book    → floor score at 0.72 when head is down (reading = attentive)
        laptop  → slight neutral penalty (-0.05)

    Head-pose hard override (highest priority after object):
        |yaw| or corrected |pitch| > DISTRACTED_MIN  → cap at 0.30
        |yaw| or corrected |pitch| in (ATTENTIVE_MAX, DISTRACTED_MIN] → cap at 0.55
    """
    global _frame_counter
    _frame_counter += 1

    score = 0.0

    # YOLO custom-model confidence — low weight because model is often absent
    score += yolo_score * 0.05

    # Extract raw angles from head_score dict
    if isinstance(head_score, dict):
        raw_pitch = float(head_score.get("pitch", 0.0))
        yaw = float(head_score.get("yaw", 0.0))
        head_score_val = float(head_score.get("score", 0.5))
    else:
        raw_pitch = 0.0
        yaw = 0.0
        head_score_val = float(head_score) if head_score else 0.5

    # Apply same pitch correction as head_pose.py
    corrected_pitch = raw_pitch - PITCH_OFFSET
    abs_yaw = abs(yaw)
    abs_pitch = abs(corrected_pitch)

    # Head orientation — PRIMARY signal (45% weight)
    score += head_score_val * 0.45

    # Gaze direction — SECONDARY signal (35% weight)
    score += gaze_score * 0.35

    # Body pose bonuses
    head_down = False
    if pose_data:
        head_down = pose_data.get("head_down", False)
        if pose_data.get("writing", False):
            score += 0.10
        if pose_data.get("body_forward", False):
            score += 0.05

    # ── Object-based overrides — highest priority in the pipeline ──
    if object_detected == "phone":
        score = min(score, 0.25)          # phone in hand → always distracted
    elif object_detected == "book" and head_down:
        score = max(score, 0.72)          # looking down at a book → attentive
    elif object_detected == "laptop":
        score = max(0.0, score - 0.05)    # laptop: slight uncertainty

    # ── Head-pose hard override (uses corrected pitch) ──
    if abs_yaw > DISTRACTED_MIN_YAW or abs_pitch > DISTRACTED_MIN_PITCH:
        # Clearly looking far away → hard cap at 0.30 (distracted)
        score = min(score, 0.30)
    elif abs_yaw > ATTENTIVE_MAX_YAW or abs_pitch > ATTENTIVE_MAX_PITCH:
        # Borderline angles → cap at 0.55 (partially attentive at best)
        score = min(score, 0.55)

    final = round(max(0.0, min(1.0, score)), 3)

    # Debug logging (every 30th frame to avoid spam)
    if _frame_counter % 30 == 0:
        label, _ = get_attention_label(final, object_detected)
        print(f"[ATTENTION] yaw={yaw:.1f}° pitch={raw_pitch:.1f}° (corr={corrected_pitch:.1f}°) | "
              f"head={head_score_val:.2f} gaze={gaze_score:.2f} yolo={yolo_score:.2f} | "
              f"obj={object_detected} | score={final:.3f} → {label}")

    return final


def get_attention_label(score, object_detected="none"):
    """
    Map a score + detected object to a human-readable label and BGR color.

    Returns:
        (label: str, color: tuple(B, G, R))
    """
    if object_detected == "phone":
        return "Distracted (Phone)", (0, 0, 220)       # Red
    if object_detected == "book":
        return "Attentive (Reading)", (50, 210, 80)     # Green
    if score >= 0.70:
        return "Attentive", (0, 220, 0)                 # Green
    if score >= 0.50:
        return "Partially Attentive", (0, 165, 255)     # Orange
    return "Distracted", (0, 0, 220)                     # Red