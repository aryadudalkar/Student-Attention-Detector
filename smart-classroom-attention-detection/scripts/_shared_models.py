"""
Singleton wrappers so YOLOv8n-pose is loaded once and shared across
head_pose.py, gaze.py, and pose_estimation.py.
"""

import os
from ultralytics import YOLO

_BASE = os.path.dirname(__file__)

_pose_model = None


def get_pose_model() -> YOLO:
    """Return a cached YOLOv8n-pose model (auto-downloads on first call)."""
    global _pose_model
    if _pose_model is None:
        local_path = os.path.join(_BASE, "..", "yolov8n-pose.pt")
        _pose_model = YOLO(
            local_path if os.path.exists(local_path) else "yolov8n-pose.pt"
        )
    return _pose_model
