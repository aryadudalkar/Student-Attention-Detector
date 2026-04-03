from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import Student, Session, AttentionLog, SessionSummary
from .serializers import (
    StudentSerializer, SessionSerializer,
    AttentionLogSerializer, SessionSummarySerializer
)


# --- Sessions ---

@api_view(['POST'])
def start_session(request):
    session = Session.objects.create()
    return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def end_session(request, session_id):
    try:
        session = Session.objects.get(id=session_id, is_active=True)
    except Session.DoesNotExist:
        return Response({'error': 'Active session not found'}, status=404)
    session.ended_at = timezone.now()
    session.is_active = False
    session.save()
    return Response(SessionSerializer(session).data)


@api_view(['GET'])
def list_sessions(request):
    sessions = Session.objects.all().order_by('-started_at')
    return Response(SessionSerializer(sessions, many=True).data)


# --- Attention Logs ---

@api_view(['POST'])
def log_attention(request):
    serializer = AttentionLogSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def session_logs(request, session_id):
    logs = AttentionLog.objects.filter(session_id=session_id).order_by('-timestamp')
    return Response(AttentionLogSerializer(logs, many=True).data)


# --- Session Summary ---

@api_view(['POST'])
def save_summary(request):
    serializer = SessionSummarySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def session_summary(request, session_id):
    summaries = SessionSummary.objects.filter(session_id=session_id)
    return Response(SessionSummarySerializer(summaries, many=True).data)


# --- Students ---

@api_view(['GET'])
def list_students(request):
    students = Student.objects.all()
    return Response(StudentSerializer(students, many=True).data)


@api_view(['GET'])
def student_weekly_report(request, student_id):
    summaries = SessionSummary.objects.filter(student__student_id=student_id)
    if not summaries.exists():
        return Response({'error': 'No data found'}, status=404)
    total_frames = sum(s.total_frames for s in summaries)
    weighted_avg = sum(s.avg_score * s.total_frames for s in summaries) / total_frames
    return Response({
        'student_id': student_id,
        'weekly_avg_score': round(weighted_avg, 3),
        'sessions_recorded': summaries.count(),
        'total_frames': total_frames,
        'total_phone_frames': sum(s.phone_frames for s in summaries),
        'total_reading_frames': sum(s.reading_frames for s in summaries),
    })