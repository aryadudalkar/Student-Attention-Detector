"""
Face detector wrapper.

Primary: YOLO face model (yolov8n-face-lindevs.pt) -> Runs on CUDA (RTX 4050)
Fallback: MediaPipe face detection if YOLO face model is unavailable.
"""

import os
import cv2
import torch
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
        
        # Determine the best device (RTX 4050 uses 'cuda')
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"--- [FaceDetector] Initializing on: {self.device} ---")

        # Use the specific filename you downloaded
        model_name = "yolov8n-face-lindevs.pt"
        
        # Check current folder and '../model/' folder
        base = os.path.dirname(__file__)
        possible_paths = [
            model_name, # Current working directory
            os.path.join(base, "..", "model", model_name),
            os.path.join(base, model_name)
        ]

        # 1. Try to find and load the YOLO model
        for path in possible_paths:
            if os.path.exists(path):
                # Safety check: if the file is tiny (like the 9-byte error), skip it
                if os.path.getsize(path) < 1000:
                    print(f"[WARNING] Corrupt model file found at {path} (size too small). Skipping...")
                    continue
                    
                try:
                    print(f"[INFO] Loading model: {path}")
                    self._yolo = YOLO(path)
                    if self.device == "cuda":
                        self._yolo.to(self.device)
                        print(f"[SUCCESS] {model_name} loaded on RTX GPU!")
                    break # Stop looking once successfully loaded
                except Exception as e:
                    print(f"[ERROR] Failed to load YOLO from {path}: {e}")

        # 2. Setup Fallback (MediaPipe) if YOLO failed
        if self._yolo is None:
            if mp is not None and hasattr(mp, "solutions"):
                print("[INFO] YOLO failed. Falling back to MediaPipe Face Detection (CPU)")
                self._mp_detector = mp.solutions.face_detection.FaceDetection(
                    model_selection=0,
                    min_detection_confidence=conf,
                )
            else:
                print("[CRITICAL] No face detection models available!")

    def detect_primary_face(self, person_crop):
        """
        Return best face in crop.
        Returns: (x1, y1, x2, y2, conf) in crop coordinates, or None.
        """
        if person_crop is None or person_crop.size == 0:
            return None

        # --- PRIMARY: YOLO (GPU) ---
        if self._yolo is not None:
            try:
                # Running on RTX 4050
                results = self._yolo(person_crop, verbose=False, conf=self.conf, device=self.device)
                
                best = None
                best_conf = 0.0
                
                for res in results:
                    if res.boxes is None:
                        continue
                    for box in res.boxes:
                        conf = float(box.conf[0])
                        if conf < self.conf:
                            continue
                        
                        # Move result from GPU to CPU to get numbers
                        coords = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = map(int, coords)
                        
                        # Prioritize larger faces
                        area = max(1, (x2 - x1) * (y2 - y1))
                        score = conf + 1e-6 * area
                        
                        if score > best_conf:
                            best_conf = score
                            best = (x1, y1, x2, y2, conf)
                
                if best is not None:
                    return best
            except Exception as e:
                print(f"YOLO Inference error: {e}")

        # --- FALLBACK: MEDIAPIPE (CPU) ---
        if self._mp_detector:
            h, w = person_crop.shape[:2]
            rgb = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
            res = self._mp_detector.process(rgb)
            
            if res.detections:
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
                    
                    if x2 > x1 and y2 > y1 and conf > best_conf:
                        best_conf = conf
                        best = (x1, y1, x2, y2, conf)
                return best
                
        return None