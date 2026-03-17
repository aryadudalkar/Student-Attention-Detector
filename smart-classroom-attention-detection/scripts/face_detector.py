"""
Face detector wrapper.

Primary: YOLO face model (yolov8n-face.pt)
Fallback: MediaPipe face detection if YOLO face model is unavailable.
"""

import os

import cv2
from ultralytics import YOLO

try:
    import mediapipe as mp
except ImportError:
    mp = None


class FaceDetector:
    def __init__(self, conf=0.35):
        self.conf = conf
        self._yolo = None
        self._mp_detector = None

        base = os.path.dirname(__file__)
        local_face = os.path.join(base, "..", "model", "yolov8n-face.pt")
        if os.path.exists(local_face):
            self._yolo = YOLO(local_face)
        else:
            # Works when model is downloadable/available in env cache.
            try:
                self._yolo = YOLO("yolov8n-face.pt")
            except Exception:
                self._yolo = None

        if self._yolo is None and mp is not None and hasattr(mp, "solutions"):
            self._mp_detector = mp.solutions.face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=conf,
            )

    def detect_primary_face(self, person_crop):
        """
        Return best face in crop.

        Returns:
            (x1, y1, x2, y2, conf) in crop coordinates, or None.
        """
        if person_crop is None or person_crop.size == 0:
            return None

        if self._yolo is not None:
            results = self._yolo(person_crop, verbose=False, conf=self.conf)
            best = None
            best_conf = 0.0
            for res in results:
                for box in res.boxes:
                    conf = float(box.conf[0])
                    if conf < self.conf:
                        continue
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    area = max(1, (x2 - x1) * (y2 - y1))
                    score = conf + 1e-6 * area
                    if score > best_conf:
                        best_conf = score
                        best = (x1, y1, x2, y2, conf)
            if best is not None:
                return best

        if self._mp_detector is None:
            return None

        h, w = person_crop.shape[:2]
        rgb = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
        res = self._mp_detector.process(rgb)
        if not res.detections:
            return None

        best = None
        best_conf = 0.0
        for det in res.detections:
            conf = float(det.score[0]) if det.score else 0.0
            if conf < self.conf:
                continue
            box = det.location_data.relative_bounding_box
            x1 = int(max(0, box.xmin * w))
            y1 = int(max(0, box.ymin * h))
            x2 = int(min(w, (box.xmin + box.width) * w))
            y2 = int(min(h, (box.ymin + box.height) * h))
            if x2 <= x1 or y2 <= y1:
                continue
            if conf > best_conf:
                best_conf = conf
                best = (x1, y1, x2, y2, conf)
        return best
