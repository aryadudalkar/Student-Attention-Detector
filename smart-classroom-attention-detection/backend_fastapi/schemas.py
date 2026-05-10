from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SessionStartIn(BaseModel):
    label: Optional[str] = None


class SessionRead(BaseModel):
    id: int
    started_at: Optional[str]
    ended_at: Optional[str]
    is_active: bool
    log_file: Optional[str]
    label: Optional[str]


class ActiveSessionResponse(BaseModel):
    active: bool
    session: Optional[SessionRead]


class StudentCreate(BaseModel):
    student_id: int
    name: Optional[str] = None
    usn: Optional[str] = None
    photo: Optional[str] = None


class StudentRead(BaseModel):
    id: int
    student_id: int
    name: Optional[str]
    usn: Optional[str]
    photo: Optional[str]
    registered_at: Optional[str]


class AttentionLogCreate(BaseModel):
    session: int
    student: int
    attention_score: float
    label: str
    object_detected: Optional[str] = "none"
    yolo_score: Optional[float] = None
    gaze_score: Optional[float] = None
    head_score: Optional[float] = None
    pitch: Optional[float] = None
    yaw: Optional[float] = None
    roll: Optional[float] = None


class LogBatchIn(BaseModel):
    logs: List[AttentionLogCreate]


class SessionSummaryCreate(BaseModel):
    session: int
    student: int
    avg_score: float
    total_frames: int
    attentive_pct: float
    distracted_pct: float
    phone_frames: Optional[int] = 0
    reading_frames: Optional[int] = 0
    grade: Optional[str] = None


class ImportSessionIn(BaseModel):
    session_start: str
    students: Dict[str, Dict[str, Any]]
