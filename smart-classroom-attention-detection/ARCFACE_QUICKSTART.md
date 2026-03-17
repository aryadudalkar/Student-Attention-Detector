# ArcFace Student Registry - Quick Start Guide

## Overview
The ArcFace Student Registry enables **one-time face enrollment** of students and **cross-session identity tracking**. Once enrolled, students are automatically recognized by name in future sessions instead of getting random IDs.

---

## 1. ENROLLMENT (One-time Setup)

### Option A: Enroll from Webcam (Easiest)
```bash
cd scripts
python enrollment_cli.py capture "John Doe"
```
- Opens webcam
- Press **SPACE** to capture photo
- Face is extracted and stored with name "John Doe"
- Auto-saves to `student_photos/`

### Option B: Enroll from Existing Photo
```bash
python enrollment_cli.py enroll "Jane Smith" path/to/photo.jpg
```
- Uses existing photo file
- Face is extracted and stored
- Database entry created

### List Enrolled Students
```bash
python enrollment_cli.py list
```
Output:
```
============================================================
ENROLLED STUDENTS
============================================================
  ID   1  |  John Doe                      |  2026-03-17
  ID   2  |  Jane Smith                    |  2026-03-17
============================================================
```

### Delete Student
```bash
python enrollment_cli.py delete 1
```

### Clear All Students (WARNING: permanent)
```bash
python enrollment_cli.py clear
```

---

## 2. RUN PIPELINE WITH RECOGNITION

### Start Webcam Detection
```bash
python webcam_test.py
```
- Automatically recognizes enrolled students by face
- Displays name instead of ID
- Example: `John Doe  Attentive  (0.85)`
- Press ESC to stop

### Process Video File
```bash
python video_test.py path/to/video.mp4
```
- Automatically recognizes enrolled students
- Generates session report with student names

---

## 3. DATABASE & FILES

**Student Registry Database:**
```
student_data/
├── students.db          (SQLite database with face embeddings)
└── student_photos/
    ├── John_Doe_0.jpg
    ├── Jane_Smith_0.jpg
    └── ...
```

**Session Reports:**
```
attention_logs/
├── session_20260317_195731.json
└── weekly_summary.json
```

---

## 4. HOW IT WORKS TECHNICALLY

### Enrollment Flow
```
Photo → ArcFace Model → Extract Face Embedding (512-dim vector)
                    ↓
              Store in SQLite {name, embedding, timestamp}
```

### Recognition Flow
```
Frame → Detect Face → Extract Embedding → Compare with all stored embeddings
                                        ↓
                         Find closest match (cosine similarity > 0.55)
                                        ↓
                            Display student name + attention score
```

### Why This Works
- **Face embeddings** are unique to each person's face geometry
- **Cosine similarity** measures likeness: 1.0 = identical, 0.0 = completely different
- **Threshold 0.55** balances recognition accuracy vs false positives

---

## 5. BEST PRACTICES

### Enrollment Tips
- ✅ Use clear, front-facing photos (like ID photos)
- ✅ Good lighting, neutral background
- ✅ Face fills ~30-50% of photo
- ✅ No glasses or face coverings (if possible)
- ❌ Don't use very small faces (face detection fails)
- ❌ Don't use side-profile or heavily angled photos

### Running Pipeline
- ✅ Keep same camera setup (lighting, angle, distance)
- ✅ Minimum 0.5m distance from camera
- ✅ Good natural/office lighting (avoid backlighting)
- ❌ Don't change seat positions drastically between sessions

---

## 6. TROUBLESHOOTING

### Issue: "Could not extract face from image"
- **Cause:** Photo too blurry, face too small, bad angle
- **Fix:** Re-capture with clear front-facing photo, better lighting

### Issue: Student not recognized in live pipeline
- **Cause:** Different pose, lighting, or distance from enrollment
- **Fix:** Re-enroll with similar conditions to actual classroom
- **Alternative:** Increase threshold in `tracker.py` (line ~85) from 0.55 to 0.50

### Issue: Wrong student recognized
- **Cause:** Students look similar, threshold too low
- **Fix:** Lower threshold confidence or ensure unique enrollment photos

### Issue: "module 'mediapipe' has no attribute 'solutions'"
- **Status:** This is expected in Python 3.13. System falls back to YOLO-pose.
- **No action needed** — everything still works.

---

## 7. ADVANCED: DATABASE QUERIES

If you need to manually inspect the database:

```python
import sqlite3
import json

db = sqlite3.connect("student_data/students.db")
cursor = db.cursor()
cursor.execute("SELECT student_id, name, enrollment_date FROM students ORDER BY student_id")

for row in cursor.fetchall():
    print(f"ID {row[0]:3d}  |  {row[1]:30s}  |  {row[2][:10]}")

db.close()
```

---

## 8. WHAT HAPPENS AFTER ENROLLMENT

Once students are enrolled:

1. **Session starts** → Detects faces in frame
2. **Face extracted** → Matched against database
3. **Match found** → Student name used as ID
4. **Attention scored** → Name + grade logged
5. **Session ends** → Report includes student names (not just IDs)

---

## 9. NEXT STEPS (After Testing)

1. **Enroll all students** (5 min per class)
2. **Run webcam_test.py** during a class
3. **Watch real-time display** with student names
4. **Check session report**: `attention_logs/session_TIMESTAMP.json`
5. **Optional:** Build dashboard for visualization

---

## 10. EXAMPLE SESSION

```bash
$ python enrollment_cli.py capture "Alice"
[INFO] Opening webcam for Alice
[INFO] Press SPACE to capture, ESC to cancel
[INFO] Photo saved: student_photos/Alice_0.jpg
[INFO] Enrolled Alice (ID: 1)

$ python enrollment_cli.py capture "Bob"
[INFO] Opening webcam for Bob
[INFO] Press SPACE to capture, ESC to cancel
[INFO] Photo saved: student_photos/Bob_0.jpg
[INFO] Enrolled Bob (ID: 2)

$ python enrollment_cli.py list
============================================================
ENROLLED STUDENTS
============================================================
  ID   1  |  Alice                         |  2026-03-17
  ID   2  |  Bob                           |  2026-03-17
============================================================

$ python webcam_test.py
[INFO] Webcam started (camera 0)
[INFO] Press ESC to quit.

[Live view shows:]
Alice  Attentive  (0.92)
Bob  Distracted  (0.31)
```

---

## Questions?

All code is self-documented. Check:
- `student_registry.py` — Core enrollment/recognition logic
- `enrollment_cli.py` — CLI interface
- `tracker.py` — Integration into tracking pipeline

Enjoy automated cross-session student tracking! 🎓
