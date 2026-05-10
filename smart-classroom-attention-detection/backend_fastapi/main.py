from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from . import models, schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Classroom API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


# -----------------------------
# Helpers
# -----------------------------

def _score_to_grade(score: float) -> str:
    if score >= 0.85:
        return "A"
    if score >= 0.70:
        return "B"
    if score >= 0.55:
        return "C"
    if score >= 0.40:
        return "D"
    return "F"


def _session_to_dict(session: models.Session) -> Dict[str, Any]:
    return {
        "id": session.id,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "is_active": session.is_active,
        "log_file": session.log_file,
        "label": session.label,
    }


def _summary_to_dict(summary: models.SessionSummary) -> Dict[str, Any]:
    student = summary.student
    return {
        "id": summary.id,
        "session": summary.session_id,
        "student": summary.student_id,
        "student_id": student.student_id if student else None,
        "student_name": student.name if student else None,
        "student_usn": student.usn if student else None,
        "avg_score": summary.avg_score,
        "total_frames": summary.total_frames,
        "attentive_pct": summary.attentive_pct,
        "distracted_pct": summary.distracted_pct,
        "phone_frames": summary.phone_frames,
        "reading_frames": summary.reading_frames,
        "grade": summary.grade,
    }


def _log_to_dict(log: models.AttentionLog) -> Dict[str, Any]:
    return {
        "id": log.id,
        "session": log.session_id,
        "student": log.student_id,
        "timestamp": log.timestamp,
        "attention_score": log.attention_score,
        "label": log.label,
        "object_detected": log.object_detected,
        "yolo_score": log.yolo_score,
        "gaze_score": log.gaze_score,
        "head_score": log.head_score,
        "pitch": log.pitch,
        "yaw": log.yaw,
        "roll": log.roll,
    }


def _auto_generate_summary(db: Session, session: models.Session) -> None:
    logs = db.query(models.AttentionLog).filter(models.AttentionLog.session_id == session.id).all()
    if not logs:
        return

    student_ids = sorted({log.student_id for log in logs})
    for student_pk in student_ids:
        student_logs = [log for log in logs if log.student_id == student_pk]
        total = len(student_logs)
        if total == 0:
            continue

        scores = [log.attention_score for log in student_logs]
        labels = [log.label for log in student_logs]
        avg = sum(scores) / total
        attentive_n = sum(1 for label in labels if "Attentive" in label)
        distracted_n = sum(1 for label in labels if "Distracted" in label)
        phone_n = sum(1 for label in labels if "Phone" in label)
        reading_n = sum(1 for label in labels if "Reading" in label)

        summary = (
            db.query(models.SessionSummary)
            .filter(
                models.SessionSummary.session_id == session.id,
                models.SessionSummary.student_id == student_pk,
            )
            .first()
        )
        if summary is None:
            summary = models.SessionSummary(
                session_id=session.id,
                student_id=student_pk,
                avg_score=round(avg, 3),
                total_frames=total,
                attentive_pct=round(attentive_n / total * 100, 1),
                distracted_pct=round(distracted_n / total * 100, 1),
                phone_frames=phone_n,
                reading_frames=reading_n,
                grade=_score_to_grade(avg),
            )
            db.add(summary)
        else:
            summary.avg_score = round(avg, 3)
            summary.total_frames = total
            summary.attentive_pct = round(attentive_n / total * 100, 1)
            summary.distracted_pct = round(distracted_n / total * 100, 1)
            summary.phone_frames = phone_n
            summary.reading_frames = reading_n
            summary.grade = _score_to_grade(avg)

    db.commit()


# -----------------------------
# Sessions
# -----------------------------

@api.post("/sessions/start/", status_code=status.HTTP_201_CREATED)
def start_session(payload: schemas.SessionStartIn, db: Session = Depends(get_db)):
    session = models.Session(label=payload.label)
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_to_dict(session)


@api.get("/sessions/")
def list_sessions(db: Session = Depends(get_db)):
    sessions = db.query(models.Session).order_by(models.Session.started_at.desc()).all()
    return [_session_to_dict(session) for session in sessions]


@api.get("/sessions/active/")
def active_session(db: Session = Depends(get_db)):
    session = (
        db.query(models.Session)
        .filter(models.Session.is_active.is_(True))
        .order_by(models.Session.started_at.desc())
        .first()
    )
    if session is None:
        return {"active": False, "session": None}
    return {"active": True, "session": _session_to_dict(session)}


@api.post("/sessions/import/", status_code=status.HTTP_201_CREATED)
def import_json_session(payload: schemas.ImportSessionIn, db: Session = Depends(get_db)):
    if not payload.session_start:
        raise HTTPException(status_code=400, detail="session_start is required")

    session = models.Session(
        label=f"Imported: {payload.session_start}",
        is_active=False,
        ended_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    created = 0
    for sid, stats in payload.students.items():
        try:
            student_id_value = int(sid)
        except ValueError:
            continue

        student = db.query(models.Student).filter(models.Student.student_id == student_id_value).first()
        if student is None:
            student = models.Student(student_id=student_id_value)
            db.add(student)
            db.commit()
            db.refresh(student)

        avg_score = stats.get("avg_score", 0)
        summary = models.SessionSummary(
            session_id=session.id,
            student_id=student.id,
            avg_score=avg_score,
            total_frames=stats.get("total_frames", 0),
            attentive_pct=stats.get("attentive_pct", 0),
            distracted_pct=stats.get("distracted_pct", 0),
            phone_frames=stats.get("phone_frames", 0),
            reading_frames=stats.get("reading_frames", 0),
            grade=_score_to_grade(avg_score),
        )
        db.add(summary)
        created += 1

    db.commit()
    return {"session_id": session.id, "students_imported": created}


@api.post("/sessions/{session_id}/end/")
def end_session(session_id: int, db: Session = Depends(get_db)):
    session = (
        db.query(models.Session)
        .filter(models.Session.id == session_id, models.Session.is_active.is_(True))
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Active session not found")

    session.ended_at = datetime.now(timezone.utc)
    session.is_active = False
    db.commit()
    db.refresh(session)

    _auto_generate_summary(db, session)
    return session_detail(session_id=session_id, db=db)


@api.get("/sessions/{session_id}/")
def session_detail(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    summaries = (
        db.query(models.SessionSummary)
        .filter(models.SessionSummary.session_id == session_id)
        .order_by(models.SessionSummary.avg_score.desc())
        .all()
    )
    summary_dicts = [_summary_to_dict(summary) for summary in summaries]
    total_students = len(summary_dicts)
    if total_students > 0:
        avg_class_score = round(sum(s["avg_score"] for s in summary_dicts) / total_students, 3)
    else:
        avg_class_score = None

    return {
        **_session_to_dict(session),
        "summaries": summary_dicts,
        "total_students": total_students,
        "avg_class_score": avg_class_score,
    }


@api.get("/sessions/{session_id}/logs/")
def session_logs(session_id: int, student_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.AttentionLog).filter(models.AttentionLog.session_id == session_id)
    if student_id is not None:
        student = db.query(models.Student).filter(models.Student.student_id == student_id).first()
        if student is None:
            return []
        query = query.filter(models.AttentionLog.student_id == student.id)

    logs = query.order_by(models.AttentionLog.timestamp.desc()).all()
    return [_log_to_dict(log) for log in logs]


@api.get("/sessions/{session_id}/summary/")
def session_summary(session_id: int, db: Session = Depends(get_db)):
    summaries = (
        db.query(models.SessionSummary)
        .filter(models.SessionSummary.session_id == session_id)
        .order_by(models.SessionSummary.avg_score.desc())
        .all()
    )
    if not summaries:
        session = db.query(models.Session).filter(models.Session.id == session_id).first()
        if session and session.is_active:
            _auto_generate_summary(db, session)
            summaries = (
                db.query(models.SessionSummary)
                .filter(models.SessionSummary.session_id == session_id)
                .order_by(models.SessionSummary.avg_score.desc())
                .all()
            )
    return [_summary_to_dict(summary) for summary in summaries]


@api.get("/sessions/{session_id}/overview/")
def class_overview(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_active:
        logs = db.query(models.AttentionLog).filter(models.AttentionLog.session_id == session_id).all()
        if not logs:
            raise HTTPException(status_code=404, detail="No data yet")

        student_ids = sorted({log.student_id for log in logs})
        total = len(student_ids)
        attentive = 0
        partial = 0
        distracted = 0
        phone = 0
        scores = []

        for student_pk in student_ids:
            student_logs = [log for log in logs if log.student_id == student_pk]
            avg = sum(log.attention_score for log in student_logs) / len(student_logs)
            scores.append(avg)
            if avg >= 0.70:
                attentive += 1
            elif avg >= 0.50:
                partial += 1
            else:
                distracted += 1
            if any(log.object_detected == "phone" for log in student_logs):
                phone += 1

        avg_score = sum(scores) / len(scores) if scores else 0

        return {
            "session_id": session_id,
            "total_students": total,
            "class_avg_score": round(avg_score, 3),
            "class_grade": _score_to_grade(avg_score),
            "attentive_count": attentive,
            "partially_attentive_count": partial,
            "distracted_count": distracted,
            "phone_detected_count": phone,
            "attentive_pct": round(attentive / total * 100, 1) if total else 0,
            "distracted_pct": round(distracted / total * 100, 1) if total else 0,
        }

    summaries = (
        db.query(models.SessionSummary)
        .filter(models.SessionSummary.session_id == session_id)
        .all()
    )
    if not summaries:
        raise HTTPException(status_code=404, detail="No data for this session")

    total = len(summaries)
    avg_score = sum(summary.avg_score for summary in summaries) / total
    attentive = len([summary for summary in summaries if summary.avg_score >= 0.70])
    partial = len([summary for summary in summaries if 0.50 <= summary.avg_score < 0.70])
    distracted = len([summary for summary in summaries if summary.avg_score < 0.50])
    phone_users = len([summary for summary in summaries if summary.phone_frames > 0])

    return {
        "session_id": session_id,
        "total_students": total,
        "class_avg_score": round(avg_score, 3),
        "class_grade": _score_to_grade(avg_score),
        "attentive_count": attentive,
        "partially_attentive_count": partial,
        "distracted_count": distracted,
        "phone_detected_count": phone_users,
        "attentive_pct": round(attentive / total * 100, 1),
        "distracted_pct": round(distracted / total * 100, 1),
    }


# -----------------------------
# Attention logs
# -----------------------------

@api.post("/logs/", status_code=status.HTTP_201_CREATED)
def log_attention(payload: schemas.AttentionLogCreate, db: Session = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == payload.session).first()
    student = db.query(models.Student).filter(models.Student.id == payload.student).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    log = models.AttentionLog(
        session_id=payload.session,
        student_id=payload.student,
        attention_score=payload.attention_score,
        label=payload.label,
        object_detected=payload.object_detected or "none",
        yolo_score=payload.yolo_score,
        gaze_score=payload.gaze_score,
        head_score=payload.head_score,
        pitch=payload.pitch,
        yaw=payload.yaw,
        roll=payload.roll,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return _log_to_dict(log)


@api.post("/logs/batch/", status_code=status.HTTP_201_CREATED)
def log_attention_batch(payload: schemas.LogBatchIn, db: Session = Depends(get_db)):
    if not payload.logs:
        raise HTTPException(status_code=400, detail="No logs provided")

    logs_to_add: List[models.AttentionLog] = []
    for item in payload.logs:
        session = db.query(models.Session).filter(models.Session.id == item.session).first()
        student = db.query(models.Student).filter(models.Student.id == item.student).first()
        if session is None or student is None:
            raise HTTPException(status_code=400, detail="Invalid session or student in batch")

        logs_to_add.append(
            models.AttentionLog(
                session_id=item.session,
                student_id=item.student,
                attention_score=item.attention_score,
                label=item.label,
                object_detected=item.object_detected or "none",
                yolo_score=item.yolo_score,
                gaze_score=item.gaze_score,
                head_score=item.head_score,
                pitch=item.pitch,
                yaw=item.yaw,
                roll=item.roll,
            )
        )

    db.add_all(logs_to_add)
    db.commit()
    return {"saved": len(logs_to_add)}


# -----------------------------
# Summaries
# -----------------------------

@api.post("/summaries/", status_code=status.HTTP_201_CREATED)
def save_summary(payload: schemas.SessionSummaryCreate, db: Session = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == payload.session).first()
    student = db.query(models.Student).filter(models.Student.id == payload.student).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    summary = models.SessionSummary(
        session_id=payload.session,
        student_id=payload.student,
        avg_score=payload.avg_score,
        total_frames=payload.total_frames,
        attentive_pct=payload.attentive_pct,
        distracted_pct=payload.distracted_pct,
        phone_frames=payload.phone_frames or 0,
        reading_frames=payload.reading_frames or 0,
        grade=payload.grade or _score_to_grade(payload.avg_score),
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return _summary_to_dict(summary)


# -----------------------------
# Students
# -----------------------------

@api.get("/students/")
def students(db: Session = Depends(get_db)):
    all_students = db.query(models.Student).order_by(models.Student.student_id).all()
    return [
        {
            "id": student.id,
            "student_id": student.student_id,
            "name": student.name,
            "usn": student.usn,
            "photo": student.photo,
            "registered_at": student.registered_at,
        }
        for student in all_students
    ]


@api.post("/students/", status_code=status.HTTP_201_CREATED)
def create_student(payload: schemas.StudentCreate, db: Session = Depends(get_db)):
    if db.query(models.Student).filter(models.Student.student_id == payload.student_id).first():
        raise HTTPException(status_code=400, detail="student_id already exists")

    if payload.usn:
        existing_usn = db.query(models.Student).filter(models.Student.usn == payload.usn).first()
        if existing_usn:
            raise HTTPException(status_code=400, detail="usn already exists")

    student = models.Student(
        student_id=payload.student_id,
        name=payload.name,
        usn=payload.usn,
        photo=payload.photo,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return {
        "id": student.id,
        "student_id": student.student_id,
        "name": student.name,
        "usn": student.usn,
        "photo": student.photo,
        "registered_at": student.registered_at,
    }


@api.get("/students/{student_id}/")
def student_detail(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.student_id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    return {
        "id": student.id,
        "student_id": student.student_id,
        "name": student.name,
        "usn": student.usn,
        "photo": student.photo,
        "registered_at": student.registered_at,
    }


@api.get("/students/{student_id}/weekly-report/")
def student_weekly_report(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.student_id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    summaries = (
        db.query(models.SessionSummary)
        .filter(models.SessionSummary.student_id == student.id)
        .all()
    )
    if not summaries:
        raise HTTPException(status_code=404, detail="No data found for this student")

    total_frames = sum(summary.total_frames for summary in summaries)
    if total_frames == 0:
        weighted_avg = 0
    else:
        weighted_avg = sum(summary.avg_score * summary.total_frames for summary in summaries) / total_frames

    return {
        "student_id": student_id,
        "weekly_avg_score": round(weighted_avg, 3),
        "grade": _score_to_grade(weighted_avg),
        "sessions_recorded": len(summaries),
        "total_frames": total_frames,
        "total_phone_frames": sum(summary.phone_frames for summary in summaries),
        "total_reading_frames": sum(summary.reading_frames for summary in summaries),
        "avg_attentive_pct": round(sum(summary.attentive_pct for summary in summaries) / len(summaries), 1),
        "avg_distracted_pct": round(sum(summary.distracted_pct for summary in summaries) / len(summaries), 1),
    }


app.include_router(api)
