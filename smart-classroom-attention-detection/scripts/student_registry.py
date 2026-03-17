"""
Student Registry with ArcFace Face Recognition.

Enrolls student faces once, stores embeddings in SQLite database.
At runtime, recognizes returning students automatically across sessions.
"""

import os
import sqlite3
import json
import cv2
import numpy as np
from datetime import datetime

try:
    import insightface
    _INSIGHTFACE_AVAILABLE = True
except ImportError:
    insightface = None
    _INSIGHTFACE_AVAILABLE = False

_REGISTRY_DB = None
_FACE_MODEL = None


def _get_db_path():
    """Get path to student registry database."""
    base = os.path.dirname(__file__)
    db_dir = os.path.join(base, "..", "student_data")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "students.db")


def _init_db():
    """Initialize database schema if not present."""
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            usn TEXT,
            enrollment_date TEXT NOT NULL,
            face_embedding TEXT NOT NULL,
            photo_path TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def _get_face_model():
    """Load ArcFace model for face embeddings."""
    global _FACE_MODEL
    if _FACE_MODEL is None:
        if not _INSIGHTFACE_AVAILABLE:
            print("[WARNING] insightface not available. Using MediaPipe fallback.")
            return None
        try:
            _FACE_MODEL = insightface.app.FaceAnalysis(
                providers=["CPUProvider"],
                allowed_modules=["detection", "recognition"],
            )
            _FACE_MODEL.prepare(ctx_id=-1, det_size=(640, 480))
        except Exception as e:
            print(f"[WARNING] Failed to load ArcFace: {e}. Using fallback.")
            _FACE_MODEL = None
    return _FACE_MODEL


def _image_hash_embedding(image):
    """Fallback: create embedding from image histogram."""
    try:
        h, w = image.shape[:2]
        # Resize to small size and flatten as simple feature vector
        small = cv2.resize(image, (32, 32))
        hist = cv2.calcHist([small], [0, 1, 2], None, [8, 8, 8], 
                            [0, 256, 0, 256, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        # Pad to 512 dims to match ArcFace size
        padded = np.zeros(512)
        padded[:len(hist)] = hist[:512]
        return padded.tolist()
    except Exception:
        return None


def _face_to_embedding(image, bbox=None):
    """Extract face embedding from image (full image or from bbox)."""
    model = _get_face_model()
    if model is None:
        return _image_hash_embedding(image)

    try:
        faces = model.get(image)
        if not faces:
            return _image_hash_embedding(image)
        # Use largest/best face
        best_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        return best_face.embedding.tolist()
    except Exception:
        return _image_hash_embedding(image)


def enroll_student(name: str, image_path_or_array, usn: str = "") -> bool:
    """
    Enroll a student by name with a face photo.

    Args:
        name: Student name (unique identifier)
        image_path_or_array: path to image file OR numpy BGR array
        usn: University Serial Number (optional)

    Returns:
        True if successful, False otherwise
    """
    if isinstance(image_path_or_array, str):
        if not os.path.exists(image_path_or_array):
            print(f"[ERROR] Image file not found: {image_path_or_array}")
            return False
        image = cv2.imread(image_path_or_array)
        if image is None:
            print(f"[ERROR] Could not read image: {image_path_or_array}")
            return False
        image_path = image_path_or_array
    else:
        image = image_path_or_array
        image_path = None

    embedding = _face_to_embedding(image)
    if embedding is None:
        print(f"[ERROR] Could not process image for {name}")
        return False

    _init_db()
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO students (name, usn, enrollment_date, face_embedding, photo_path)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                name,
                usn if usn else None,
                datetime.now().isoformat(),
                json.dumps(embedding),
                image_path,
            ),
        )
        conn.commit()
        student_id = cursor.lastrowid
        usn_display = f" (USN: {usn})" if usn else ""
        print(f"[INFO] Enrolled {name}{usn_display} (ID: {student_id})")
        return True
    except sqlite3.IntegrityError:
        print(f"[ERROR] Student name '{name}' already enrolled")
        return False
    finally:
        conn.close()


def recognize_face(image, bbox=None, threshold=0.6) -> dict:
    """
    Recognize a face in image.

    Args:
        image: BGR image (full or person crop)
        bbox: optional (x1, y1, x2, y2) to crop before embedding
        threshold: cosine similarity threshold [0-1]

    Returns:
        dict: {"student_id": int, "name": str, "confidence": float}
        or {} if no match found
    """
    if bbox is not None:
        x1, y1, x2, y2 = bbox
        image = image[y1:y2, x1:x2]

    embedding = _face_to_embedding(image)
    if embedding is None:
        return {}

    embedding = np.array(embedding)
    _init_db()
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT student_id, name, usn, face_embedding FROM students")
    rows = cursor.fetchall()
    conn.close()

    best_match = None
    best_score = threshold

    for student_id, name, usn, stored_embedding_json in rows:
        stored_embedding = np.array(json.loads(stored_embedding_json))
        # Cosine similarity
        similarity = np.dot(embedding, stored_embedding) / (
            np.linalg.norm(embedding) * np.linalg.norm(stored_embedding) + 1e-6
        )

        if similarity > best_score:
            best_score = similarity
            best_match = {"student_id": student_id, "name": name, "usn": usn, "confidence": float(similarity)}

    return best_match if best_match else {}


def list_students() -> list:
    """List all enrolled students."""
    _init_db()
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT student_id, name, usn, enrollment_date FROM students ORDER BY student_id")
    rows = cursor.fetchall()
    conn.close()

    return [
        {"student_id": row[0], "name": row[1], "usn": row[2], "enrollment_date": row[3]} for row in rows
    ]


def delete_student(student_id: int) -> bool:
    """Delete enrolled student by ID."""
    _init_db()
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()

    if deleted:
        print(f"[INFO] Deleted student ID {student_id}")
    return deleted


def clear_all_students() -> bool:
    """Clear all enrolled students (WARNING: irreversible)."""
    _init_db()
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM students")
    conn.commit()
    conn.close()
    print("[WARNING] All students cleared")
    return True
