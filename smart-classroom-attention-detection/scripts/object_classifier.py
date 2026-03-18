"""
Object classifier for smart classroom attention detection.

Uses YOLOv8 models (Roboflow-trained or COCO-pretrained) to detect whether 
a student is holding a phone (distracted) or a book (attentive/reading) 
in their hand region.

Model Priority:
    1. phone_detector.pt (Roboflow-trained phone detection)
    2. phone_book_best.pt (custom multi-class model)
    3. yolov8n.pt (COCO fallback)

Class ID mappings:
    - Roboflow phone_detector: class 0 = phone
    - COCO model: 67=phone, 73=book, 63=laptop
"""

import os
import json

from ultralytics import YOLO

# COCO class IDs (for fallback model)
_COCO_PHONE  = 67
_COCO_BOOK   = 73
_COCO_LAPTOP = 63

_yolo_model = None
_model_type = None  # 'roboflow_phone', 'custom_multi', or 'coco'


def _get_model():
    """
    Load model with priority:
    1. Roboflow phone_detector.pt
    2. Custom phone_book_best.pt
    3. COCO yolov8n.pt fallback
    """
    global _yolo_model, _model_type
    if _yolo_model is None:
        base = os.path.dirname(__file__)
        
        # Try Roboflow phone detector first
        roboflow_model = os.path.join(base, "..", "model", "phone_detector.pt")
        if os.path.exists(roboflow_model):
            _yolo_model = YOLO(roboflow_model)
            _model_type = 'roboflow_phone'
            print("[INFO] Loaded Roboflow phone_detector.pt model")
            return _yolo_model
        
        # Try custom multi-class model
        custom_model = os.path.join(base, "..", "model", "phone_book_best.pt")
        if os.path.exists(custom_model):
            _yolo_model = YOLO(custom_model)
            _model_type = 'custom_multi'
            print("[INFO] Loaded custom phone_book_best.pt model")
            return _yolo_model
        
        # Fallback to COCO model
        fallback_model = os.path.join(base, "..", "yolov8n.pt")
        _yolo_model = YOLO(fallback_model if os.path.exists(fallback_model) else "yolov8n.pt")
        _model_type = 'coco'
        print("[INFO] Loaded COCO yolov8n.pt model (fallback)")
        return _yolo_model


def classify_hand_object(frame, bbox, conf_threshold=0.35):
    """
    Detect whether a student is holding a phone or reading a book.

    Crops the lower 60% of the person bounding box (where hands and laps
    are typically found) and runs YOLO object detection on that region.

    Handles three model types:
    - Roboflow phone detector (class 0 = phone only)
    - Custom multi-class model (phone, book, laptop classes)
    - COCO model (class IDs 67, 73, 63)

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
    results = model(region, verbose=False, conf=conf_threshold)

    phone_conf  = 0.0
    book_conf   = 0.0
    laptop_conf = 0.0

    for result in results:
        if not hasattr(result, 'boxes') or len(result.boxes) == 0:
            continue
            
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf   = float(box.conf[0])
            
            # Handle Roboflow phone detector (class 0 = phone)
            if _model_type == 'roboflow_phone':
                if cls_id == 0:  # Phone class in Roboflow model
                    phone_conf = max(phone_conf, conf)
            
            # Handle custom multi-class model (infer from class count)
            elif _model_type == 'custom_multi':
                # Assume custom model has: 0=phone, 1=book, 2=laptop
                if cls_id == 0:
                    phone_conf = max(phone_conf, conf)
                elif cls_id == 1:
                    book_conf = max(book_conf, conf)
                elif cls_id == 2:
                    laptop_conf = max(laptop_conf, conf)
            
            # Handle COCO model (class IDs 67, 73, 63)
            else:  # _model_type == 'coco'
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


def get_model_info():
    """
    Returns information about the currently loaded model.
    
    Returns:
        dict: Contains 'type', 'path', and 'description'
    """
    model = _get_model()
    base = os.path.dirname(__file__)
    
    info = {
        'type': _model_type,
        'description': ''
    }
    
    if _model_type == 'roboflow_phone':
        info['path'] = os.path.join(base, "..", "model", "phone_detector.pt")
        info['description'] = "Roboflow-trained phone detector (single class: phone)"
    elif _model_type == 'custom_multi':
        info['path'] = os.path.join(base, "..", "model", "phone_book_best.pt")
        info['description'] = "Custom multi-class model (phone, book, laptop)"
    else:
        info['path'] = os.path.join(base, "..", "yolov8n.pt")
        info['description'] = "COCO-pretrained YOLOv8n model (fallback)"
    
    return info
