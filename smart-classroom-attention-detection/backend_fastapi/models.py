from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from .database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)
    usn = Column(String(20), unique=True, nullable=True)
    photo = Column(String(255), nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())

    logs = relationship("AttentionLog", back_populates="student", cascade="all, delete-orphan")
    summaries = relationship("SessionSummary", back_populates="student", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    log_file = Column(String(255), nullable=True)
    label = Column(String(100), nullable=True)

    logs = relationship("AttentionLog", back_populates="session", cascade="all, delete-orphan")
    summaries = relationship("SessionSummary", back_populates="session", cascade="all, delete-orphan")


class AttentionLog(Base):
    __tablename__ = "attention_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    attention_score = Column(Float, nullable=False)
    label = Column(String(50), nullable=False)
    object_detected = Column(String(20), default="none")
    yolo_score = Column(Float, nullable=True)
    gaze_score = Column(Float, nullable=True)
    head_score = Column(Float, nullable=True)
    pitch = Column(Float, nullable=True)
    yaw = Column(Float, nullable=True)
    roll = Column(Float, nullable=True)

    session = relationship("Session", back_populates="logs")
    student = relationship("Student", back_populates="logs")


class SessionSummary(Base):
    __tablename__ = "session_summaries"
    __table_args__ = (UniqueConstraint("session_id", "student_id", name="uq_summary_session_student"),)

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    avg_score = Column(Float, nullable=False)
    total_frames = Column(Integer, nullable=False)
    attentive_pct = Column(Float, nullable=False)
    distracted_pct = Column(Float, nullable=False)
    phone_frames = Column(Integer, default=0)
    reading_frames = Column(Integer, default=0)
    grade = Column(String(20), nullable=True)

    session = relationship("Session", back_populates="summaries")
    student = relationship("Student", back_populates="summaries")
