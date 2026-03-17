"""
Seat ROI utilities.

Define classroom seat polygons in normalized coordinates [0,1] so they
scale automatically with any resolution.
"""

import cv2
import numpy as np

# Edit these polygons to match your classroom camera view.
# Each seat ROI is a polygon listed in clockwise order as (x_norm, y_norm).
SEAT_ROIS_NORM = [
    [(0.02, 0.20), (0.33, 0.20), (0.33, 0.95), (0.02, 0.95)],
    [(0.34, 0.20), (0.66, 0.20), (0.66, 0.95), (0.34, 0.95)],
    [(0.67, 0.20), (0.98, 0.20), (0.98, 0.95), (0.67, 0.95)],
]


def build_seat_rois(frame_shape, rois_norm=None):
    """Convert normalized seat polygons to pixel polygons."""
    h, w = frame_shape[:2]
    source = rois_norm if rois_norm is not None else SEAT_ROIS_NORM

    rois_px = []
    for poly in source:
        pts = []
        for xn, yn in poly:
            x = int(np.clip(xn, 0.0, 1.0) * w)
            y = int(np.clip(yn, 0.0, 1.0) * h)
            pts.append((x, y))
        rois_px.append(np.array(pts, dtype=np.int32))
    return rois_px


def in_any_seat(point, seat_rois_px):
    """Return True when a (x,y) center point lies inside at least one seat ROI."""
    if not seat_rois_px:
        return True

    x, y = point
    for poly in seat_rois_px:
        if cv2.pointPolygonTest(poly, (float(x), float(y)), False) >= 0:
            return True
    return False


def draw_seat_rois(frame, seat_rois_px, color=(255, 180, 0)):
    """Optional visual debugging helper to overlay seat polygons."""
    for i, poly in enumerate(seat_rois_px, start=1):
        cv2.polylines(frame, [poly], True, color, 1)
        cx = int(poly[:, 0].mean())
        cy = int(poly[:, 1].mean())
        cv2.putText(
            frame,
            f"Seat-{i}",
            (cx - 24, cy),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
        )
