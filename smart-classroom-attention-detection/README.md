# Smart Classroom Attention Detection

This project detects per-student attention in classroom video/webcam streams.

## Installation

1. Clone repository

```bash
git clone https://github.com/YOUR_USERNAME/smart-classroom-attention.git
cd smart-classroom-attention
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

## Run

Webcam:

```bash
python scripts/webcam_test.py
```

Video file:

```bash
python scripts/video_test.py path/to/video.mp4
```

Press `ESC` to quit.

## Current Pipeline

- Person detection: YOLOv8m (`yolov8m.pt`) with `conf=0.5`
- Seat filtering: polygon ROIs in `scripts/seat_manager.py`
- Tracking: DeepSORT (fallback to centroid if package missing)
- Face detection: YOLO face model (`model/yolov8n-face.pt`) with MediaPipe fallback
- Head pose: MediaPipe FaceMesh + `cv2.solvePnP` (pitch, yaw, roll)
- Gaze: MediaPipe iris landmarks
- Object context: phone/book/laptop from student region only

## Important Calibration

Edit seat polygons in `scripts/seat_manager.py` (`SEAT_ROIS_NORM`) so only actual student seats are inside ROI. This is critical for removing unnecessary person boxes.

For best phone detection accuracy, train and place your custom model at:

`model/phone_book_best.pt`

If this file is not present, fallback COCO detection is used.

