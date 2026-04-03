"""
Tracking wrapper for student ID persistence.

Uses DeepSORT when available for robust appearance-aware tracking.
Falls back to centroid matching if deep-sort-realtime is not installed.
Integrates ArcFace registry for cross-session student recognition.
"""

import numpy as np

try:
    from deep_sort_realtime.deepsort_tracker import DeepSort
except ImportError:
    DeepSort = None

try:
    from student_registry import recognize_face
except ImportError:
    recognize_face = None


class SimpleTracker:
    def __init__(self, max_age=25, n_init=2, max_cosine_distance=0.35):
        self.next_id = 0
        self.objects = {}
        self._deepsort = None
        self._use_registry = recognize_face is not None

        if DeepSort is not None:
            self._deepsort = DeepSort(
                max_age=max_age,
                n_init=n_init,
                max_cosine_distance=max_cosine_distance,
                nms_max_overlap=0.7,
            )

    def _fallback_update(self, boxes, frame=None):
        updated_objects = {}
        tracked = []

        for box in boxes:
            x1, y1, x2, y2 = box
            center = ((x1 + x2) // 2, (y1 + y2) // 2)

            assigned_id = None
            for obj_id, prev_center in self.objects.items():
                dist = np.linalg.norm(np.array(center) - np.array(prev_center))
                if dist < 60:
                    assigned_id = obj_id
                    break

            if assigned_id is None:
                assigned_id = self.next_id
                self.next_id += 1

            updated_objects[assigned_id] = center
            
            # Try ArcFace recognition if registry is available
            enrolled_match = None
            if self._use_registry and frame is not None:
                enrolled_match = recognize_face(frame, bbox=box, threshold=0.55)

            # If recognized in registry, use that ID; otherwise use tracker ID
            if enrolled_match:
                final_id = enrolled_match["student_id"]
                usn = enrolled_match.get("usn")
                source = f"Registry:{enrolled_match['name']}"
            else:
                final_id = assigned_id
                usn = None
                source = "Tracked"

            tracked.append({
                "student_id": final_id,
                "bbox": (x1, y1, x2, y2),
                "name": enrolled_match.get("name") if enrolled_match else None,
                "usn": usn,
                "recognition_confidence": enrolled_match.get("confidence") if enrolled_match else None,
                "source": source,
            })

        self.objects = updated_objects
        return tracked

    def update(self, boxes_with_conf, frame=None):
        """
        Args:
            boxes_with_conf: list[(x1, y1, x2, y2, conf)]
            frame: BGR frame used by DeepSORT for appearance features.

        Returns:
            list[dict]: [{"student_id": int, "bbox": (x1,y1,x2,y2), "name": str or None, "usn": str or None}]
        """
        if self._deepsort is None:
            fallback_boxes = [b[:4] for b in boxes_with_conf]
            return self._fallback_update(fallback_boxes, frame=frame)

        detections = []
        for x1, y1, x2, y2, conf in boxes_with_conf:
            w = max(1, x2 - x1)
            h = max(1, y2 - y1)
            detections.append(([x1, y1, w, h], float(conf), "student"))

        tracks = self._deepsort.update_tracks(detections, frame=frame)

        tracked = []
        for trk in tracks:
            if not trk.is_confirmed():
                continue
            l, t, r, b = trk.to_ltrb()
            bbox = (int(l), int(t), int(r), int(b))

            # Try ArcFace recognition if registry is available
            enrolled_match = None
            if self._use_registry and frame is not None:
                enrolled_match = recognize_face(frame, bbox=bbox, threshold=0.55)

            # If recognized in registry, use that ID; otherwise use tracker ID
            if enrolled_match:
                final_id = enrolled_match["student_id"]
                usn = enrolled_match.get("usn")
                source = f"Registry:{enrolled_match['name']}"
            else:
                final_id = int(trk.track_id)
                usn = None
                source = "Tracked"

            tracked.append(
                {
                    "student_id": final_id,
                    "bbox": bbox,
                    "name": enrolled_match.get("name") if enrolled_match else None,
                    "usn": usn,
                    "recognition_confidence": enrolled_match.get("confidence") if enrolled_match else None,
                    "source": source,
                }
            )
        return tracked