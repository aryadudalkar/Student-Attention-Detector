"""
Object classifier for smart classroom attention detection.

Uses YOLOv8n (COCO-pretrained) to detect whether a student is holding
a phone (distracted) or a book (attentive/reading) in their hand region.

COCO class IDs used:
    67 - cell phone
    73 - book
    63 - laptop
"""

from ultralytics import YOLO

# COCO class IDs
_COCO_PHONE  = 67
_COCO_BOOK   = 73
_COCO_LAPTOP = 63

_yolo_model = None


def _get_model():
    global _yolo_model
    if _yolo_model is None:
        # Uses yolov8n.pt from the parent directory; YOLO will auto-download
        # from Ultralytics if not found locally.
        import os
        local_path = os.path.join(os.path.dirname(__file__), "..", "yolov8n.pt")
        _yolo_model = YOLO(local_path if os.path.exists(local_path) else "yolov8n.pt")
    return _yolo_model


def classify_hand_object(frame, bbox, conf_threshold=0.35):
    """
    Detect whether a student is holding a phone or reading a book.

    Crops the lower 60% of the person bounding box (where hands and laps
    are typically found) and runs YOLO object detection on that region.

    Args:
        frame:          Full BGR video frame.
        bbox:           (x1, y1, x2, y2) person bounding box in frame pixels.
        conf_threshold: Minimum YOLO confidence to accept a detection.

    Returns:
        str: One of "phone", "book", "laptop", or "none".
             "phone" takes priority if both phone and book are detected.
    """
    x1, y1, x2, y2 = bbox
    h, w = frame.shape[:2]

    # Focus on the lower 60% of the person region — hands / lap area
    hand_y_start = y1 + int((y2 - y1) * 0.40)

    rx1 = max(0, x1 - 10)
    rx2 = min(w, x2 + 10)
    ry1 = max(0, hand_y_start)
    ry2 = min(h, y2 + 15)

    region = frame[ry1:ry2, rx1:rx2]
    if region.size == 0:
        return "none"

    model = _get_model()
    results = model(region, verbose=False)

    phone_conf  = 0.0
    book_conf   = 0.0
    laptop_conf = 0.0

    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf   = float(box.conf[0])
            if cls_id == _COCO_PHONE:
                phone_conf = max(phone_conf, conf)
            elif cls_id == _COCO_BOOK:
                book_conf = max(book_conf, conf)
            elif cls_id == _COCO_LAPTOP:
                laptop_conf = max(laptop_conf, conf)

    # Phone takes highest priority (most distracting)
    if phone_conf >= conf_threshold:
        return "phone"
    if book_conf >= conf_threshold:
        return "book"
    if laptop_conf >= conf_threshold:
        return "laptop"
    return "none"
