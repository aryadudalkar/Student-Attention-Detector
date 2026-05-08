from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import Student, Session, AttentionLog, SessionSummary
from .serializers import (
    StudentSerializer, SessionSerializer, SessionDetailSerializer,
    AttentionLogSerializer, SessionSummarySerializer
)


# ─────────────────────────────────────────
# SESSIONS
# ─────────────────────────────────────────

@api_view(['POST'])
def start_session(request):
    """Start a new monitoring session."""
    label = request.data.get('label', None)
    session = Session.objects.create(label=label)
    return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def end_session(request, session_id):
    """End an active session and auto-save summary from logs."""
    try:
        session = Session.objects.get(id=session_id, is_active=True)
    except Session.DoesNotExist:
        return Response({'error': 'Active session not found'}, status=404)

    session.ended_at = timezone.now()
    session.is_active = False
    session.save()

    # Auto-generate summaries from logs if not already saved
    _auto_generate_summary(session)

    return Response(SessionDetailSerializer(session).data)


@api_view(['GET'])
def list_sessions(request):
    """List all sessions, most recent first."""
    sessions = Session.objects.all().order_by('-started_at')
    return Response(SessionSerializer(sessions, many=True).data)


@api_view(['GET'])
def session_detail(request, session_id):
    """Get full detail of a session including summaries."""
    try:
        session = Session.objects.get(id=session_id)
    except Session.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)
    return Response(SessionDetailSerializer(session).data)


@api_view(['GET'])
def active_session(request):
    """Get the currently active session if any."""
    session = Session.objects.filter(is_active=True).order_by('-started_at').first()
    if not session:
        return Response({'active': False, 'session': None})
    return Response({'active': True, 'session': SessionSerializer(session).data})


# ─────────────────────────────────────────
# ATTENTION LOGS
# ─────────────────────────────────────────

@api_view(['POST'])
def log_attention(request):
    """
    Called by the AI script every frame per student.
    Expects: session, student, attention_score, label, object_detected,
             yolo_score, gaze_score, head_score, pitch, yaw, roll
    """
    serializer = AttentionLogSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def log_attention_batch(request):
    """
    Batch log multiple attention records in one request.
    Expects: { "logs": [ {...}, {...}, ... ] }
    """
    logs = request.data.get('logs', [])
    if not logs:
        return Response({'error': 'No logs provided'}, status=400)

    serializer = AttentionLogSerializer(data=logs, many=True)
    if serializer.is_valid():
        serializer.save()
        return Response({'saved': len(logs)}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def session_logs(request, session_id):
    """Get all attention logs for a session, optionally filtered by student."""
    student_id = request.query_params.get('student_id', None)
    logs = AttentionLog.objects.filter(session_id=session_id).order_by('-timestamp')
    if student_id:
        logs = logs.filter(student__student_id=student_id)
    return Response(AttentionLogSerializer(logs, many=True).data)


# ─────────────────────────────────────────
# SESSION SUMMARY
# ─────────────────────────────────────────

@api_view(['POST'])
def save_summary(request):
    """Manually save a session summary."""
    serializer = SessionSummarySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def session_summary(request, session_id):
    """Get all student summaries for a session."""
    summaries = SessionSummary.objects.filter(
        session_id=session_id
    ).select_related('student').order_by('-avg_score')

    if not summaries.exists():
        session = Session.objects.filter(id=session_id).first()
        if session and session.is_active:
            _auto_generate_summary(session)
            summaries = SessionSummary.objects.filter(
                session_id=session_id
            ).select_related('student').order_by('-avg_score')

    return Response(SessionSummarySerializer(summaries, many=True).data)


@api_view(['POST'])
def import_json_session(request):
    """
    Import a session JSON file (from attention_logs/) into the database.
    Expects the raw JSON content from the AI's saved session file.
    """
    data = request.data
    session_start = data.get('session_start')
    students_data = data.get('students', {})

    if not session_start:
        return Response({'error': 'session_start is required'}, status=400)

    session = Session.objects.create(
        label=f"Imported: {session_start}",
        is_active=False,
        ended_at=timezone.now()
    )

    created_summaries = []
    for sid, stats in students_data.items():
        student, _ = Student.objects.get_or_create(student_id=int(sid))
        grade = _score_to_grade(stats.get('avg_score', 0))
        summary = SessionSummary.objects.create(
            session=session,
            student=student,
            avg_score=stats.get('avg_score', 0),
            total_frames=stats.get('total_frames', 0),
            attentive_pct=stats.get('attentive_pct', 0),
            distracted_pct=stats.get('distracted_pct', 0),
            phone_frames=stats.get('phone_frames', 0),
            reading_frames=stats.get('reading_frames', 0),
            grade=grade,
        )
        created_summaries.append(summary)

    return Response({
        'session_id': session.id,
        'students_imported': len(created_summaries),
    }, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────
# STUDENTS
# ─────────────────────────────────────────

@api_view(['GET', 'POST'])
def students(request):
    """List all students or register a new one."""
    if request.method == 'GET':
        all_students = Student.objects.all().order_by('student_id')
        return Response(StudentSerializer(all_students, many=True).data)

    serializer = StudentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def student_detail(request, student_id):
    """Get a single student's details."""
    try:
        student = Student.objects.get(student_id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=404)
    return Response(StudentSerializer(student).data)


@api_view(['GET'])
def student_weekly_report(request, student_id):
    """Get a weekly aggregated report for a student."""
    summaries = SessionSummary.objects.filter(
        student__student_id=student_id
    ).select_related('session')

    if not summaries.exists():
        return Response({'error': 'No data found for this student'}, status=404)

    total_frames = sum(s.total_frames for s in summaries)
    weighted_avg = sum(s.avg_score * s.total_frames for s in summaries) / total_frames

    return Response({
        'student_id': student_id,
        'weekly_avg_score': round(weighted_avg, 3),
        'grade': _score_to_grade(weighted_avg),
        'sessions_recorded': summaries.count(),
        'total_frames': total_frames,
        'total_phone_frames': sum(s.phone_frames for s in summaries),
        'total_reading_frames': sum(s.reading_frames for s in summaries),
        'avg_attentive_pct': round(sum(s.attentive_pct for s in summaries) / summaries.count(), 1),
        'avg_distracted_pct': round(sum(s.distracted_pct for s in summaries) / summaries.count(), 1),
    })


@api_view(['GET'])
def class_overview(request, session_id):
    try:
        session = Session.objects.get(id=session_id)
    except Session.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)

    # If session is active, read from live AttentionLog records
    if session.is_active:
        logs = AttentionLog.objects.filter(session_id=session_id)
        if not logs.exists():
            return Response({'error': 'No data yet'}, status=404)

        student_ids = logs.values_list('student', flat=True).distinct()
        total = student_ids.count()

        # Get latest label per student
        from django.db.models import Max
        attentive = 0
        partial = 0
        distracted = 0
        phone = 0
        scores = []

        for sid in student_ids:
            student_logs = logs.filter(student_id=sid)
            latest = student_logs.order_by('-timestamp').first()
            avg = sum(student_logs.values_list('attention_score', flat=True)) / student_logs.count()
            scores.append(avg)
            if avg >= 0.70:
                attentive += 1
            elif avg >= 0.50:
                partial += 1
            else:
                distracted += 1
            if student_logs.filter(object_detected='phone').exists():
                phone += 1

        avg_score = sum(scores) / len(scores) if scores else 0

        return Response({
            'session_id': session_id,
            'total_students': total,
            'class_avg_score': round(avg_score, 3),
            'class_grade': _score_to_grade(avg_score),
            'attentive_count': attentive,
            'partially_attentive_count': partial,
            'distracted_count': distracted,
            'phone_detected_count': phone,
            'attentive_pct': round(attentive / total * 100, 1) if total else 0,
            'distracted_pct': round(distracted / total * 100, 1) if total else 0,
        })

    # If session is ended, read from SessionSummary
    summaries = SessionSummary.objects.filter(session_id=session_id).select_related('student')
    if not summaries.exists():
        return Response({'error': 'No data for this session'}, status=404)

    total = summaries.count()
    avg_score = sum(s.avg_score for s in summaries) / total
    attentive = summaries.filter(avg_score__gte=0.70).count()
    partial = summaries.filter(avg_score__gte=0.50, avg_score__lt=0.70).count()
    distracted = summaries.filter(avg_score__lt=0.50).count()
    phone_users = summaries.filter(phone_frames__gt=0).count()

    return Response({
        'session_id': session_id,
        'total_students': total,
        'class_avg_score': round(avg_score, 3),
        'class_grade': _score_to_grade(avg_score),
        'attentive_count': attentive,
        'partially_attentive_count': partial,
        'distracted_count': distracted,
        'phone_detected_count': phone_users,
        'attentive_pct': round(attentive / total * 100, 1),
        'distracted_pct': round(distracted / total * 100, 1),
    })
# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

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


def _auto_generate_summary(session):
    """Auto-generate SessionSummary from AttentionLogs when session ends."""
    logs = AttentionLog.objects.filter(session=session)
    if not logs.exists():
        return

    student_ids = logs.values_list('student', flat=True).distinct()
    for student_pk in student_ids:
        student_logs = logs.filter(student_id=student_pk)
        student = Student.objects.get(pk=student_pk)
        total = student_logs.count()
        scores = list(student_logs.values_list('attention_score', flat=True))
        labels = list(student_logs.values_list('label', flat=True))
        avg = sum(scores) / total
        attentive_n = sum(1 for l in labels if 'Attentive' in l)
        distracted_n = sum(1 for l in labels if 'Distracted' in l)
        phone_n = sum(1 for l in labels if 'Phone' in l)
        reading_n = sum(1 for l in labels if 'Reading' in l)

        SessionSummary.objects.update_or_create(
            session=session,
            student=student,
            defaults={
                'avg_score': round(avg, 3),
                'total_frames': total,
                'attentive_pct': round(attentive_n / total * 100, 1),
                'distracted_pct': round(distracted_n / total * 100, 1),
                'phone_frames': phone_n,
                'reading_frames': reading_n,
                'grade': _score_to_grade(avg),
            }
        )