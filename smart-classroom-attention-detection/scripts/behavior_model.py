import math

def calculate_attention(head_score, gaze_score, body_data):
    if body_data is None:
        return 0.5

    nose = body_data["nose"]
    left_wrist = body_data["left_wrist"]
    right_wrist = body_data["right_wrist"]

    # Writing detection (hands near desk, head slightly down)
    writing = (
        abs(left_wrist.y - nose.y) < 0.25 or
        abs(right_wrist.y - nose.y) < 0.25
    )

    # Phone detection (hands below desk level)
    phone_use = (
        left_wrist.y > 0.8 or
        right_wrist.y > 0.8
    )

    score = 0.4 * head_score + 0.4 * gaze_score

    if writing:
        score += 0.2

    if phone_use:
        score -= 0.4

    return max(0, min(1, score))