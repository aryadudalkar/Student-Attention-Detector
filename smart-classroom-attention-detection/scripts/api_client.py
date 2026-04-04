"""
API Client for Smart Classroom Attention Detection
====================================================
Used by webcam_test.py and video_test.py to send data
to the Django API in real time.
"""

import requests

BASE_URL = "http://127.0.0.1:8000/api"


def start_session(label=None):
    """Start a new session and return the session ID."""
    try:
        res = requests.post(f"{BASE_URL}/sessions/start/", json={"label": label})
        data = res.json()
        print(f"[API] Session started: ID={data['id']}")
        return data["id"]
    except Exception as e:
        print(f"[API] Failed to start session: {e}")
        return None


def end_session(session_id):
    """End an active session."""
    try:
        res = requests.post(f"{BASE_URL}/sessions/{session_id}/end/")
        print(f"[API] Session {session_id} ended.")
        return res.json()
    except Exception as e:
        print(f"[API] Failed to end session: {e}")
        return None


def log_attention_batch(logs: list):
    """
    Send a batch of attention logs to the API.
    logs: list of dicts with keys:
        session, student, attention_score, label, object_detected,
        yolo_score, gaze_score, head_score, pitch, yaw, roll
    """
    if not logs:
        return
    try:
        res = requests.post(f"{BASE_URL}/logs/batch/", json={"logs": logs})
        if res.status_code != 201:
            print(f"[API] Batch log error: {res.text}")
    except Exception as e:
        print(f"[API] Failed to send logs: {e}")


def get_or_create_student(student_id: int, name=None, usn=None):
    """Get or create a student in the DB and return their DB primary key."""
    try:
        # Try to get existing student
        res = requests.get(f"{BASE_URL}/students/{student_id}/")
        if res.status_code == 200:
            return res.json()["id"]

        # Create new student
        payload = {"student_id": student_id}
        if name:
            payload["name"] = name
        if usn:
            payload["usn"] = usn
        res = requests.post(f"{BASE_URL}/students/", json=payload)
        if res.status_code == 201:
            return res.json()["id"]
    except Exception as e:
        print(f"[API] Failed to get/create student {student_id}: {e}")
    return None