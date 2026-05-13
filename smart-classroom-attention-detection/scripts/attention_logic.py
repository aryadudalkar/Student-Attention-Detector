def calculate_attention(yolo_score, head_score, gaze_score, pose_data,
                        object_detected="none"):
    """
    Calculate a [0, 1] attention score with book/phone discrimination.

    Scoring weights:
        yolo_score  0.20  — custom attention model confidence
        head_score  0.30  — head orientation (facing front)
        gaze_score  0.30  — eye gaze direction
        writing     0.20  — hands in writing position (bonus)
        body_fwd    0.05  — upright, shoulders level (small bonus)

    Object overrides (applied after base score):
        phone   → cap score at 0.30  (always distracted)
        book    → floor score at 0.72 when head is down (reading = attentive)
        laptop  → slight neutral penalty (-0.05)
    """
    score = 0.0
    score += yolo_score * 0.20
    if isinstance(head_score, dict):
        pitch = float(head_score.get("pitch", 0.0))
        yaw = float(head_score.get("yaw", 0.0))
    else:
        pitch = 0.0
        yaw = 0.0

    orientation_score = 1.0 - min(abs(yaw) / 45.0, 1.0)
    score += orientation_score * 0.30
    score += gaze_score * 0.30

    head_down = False
    if pose_data:
        head_down = pose_data.get("head_down", False)
        if pose_data.get("writing", False):
            score += 0.20
        if pose_data.get("body_forward", False):
            score += 0.05

    # Object-based overrides — highest priority in the pipeline
    if object_detected == "phone":
        score = min(score, 0.30)          # phone in hand → always distracted
    elif object_detected == "book" and head_down:
        score = max(score, 0.72)          # looking down at a book → attentive
    elif object_detected == "laptop":
        score = max(0.0, score - 0.05)    # laptop: slight uncertainty

    # Hard pose rule requested for strong distraction cues.
    if abs(yaw) > 25.0 or pitch < -15.0:
        score = min(score, 0.35)

    return round(max(0.0, min(1.0, score)), 3)


def get_attention_label(score, object_detected="none"):
    """
    Map a score + detected object to a human-readable label and BGR color.

    Returns:
        (label: str, color: tuple(B, G, R))
    """
    if object_detected == "phone":
        return "Distracted (Phone)", (0, 0, 220)
    if object_detected == "book":
        return "Attentive (Reading)", (50, 210, 80)
    if score >= 0.70:
        return "Attentive", (0, 220, 0)
    if score >= 0.50:
        return "Partially Attentive", (0, 165, 255)
    return "Distracted", (0, 0, 220)