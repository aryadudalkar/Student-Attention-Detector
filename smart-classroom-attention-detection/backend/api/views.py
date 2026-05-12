from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from .models import Student, Session, AttentionLog, SessionSummary, TeacherFeedback
from .serializers import (
    StudentSerializer, SessionSerializer, SessionDetailSerializer,
    AttentionLogSerializer, SessionSummarySerializer, TeacherFeedbackSerializer
)
from .pdf_utils import generate_session_pdf
from django.http import FileResponse

# ── SESSIONS ──

@api_view(['POST'])
def start_session(request):
    label = request.data.get('label', None)
    session = Session.objects.create(label=label)
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
    _auto_generate_summary(session)
    _auto_generate_feedback(session)
    return Response(SessionDetailSerializer(session).data)

@api_view(['GET'])
def list_sessions(request):
    sessions = Session.objects.all().order_by('-started_at')
    return Response(SessionSerializer(sessions, many=True).data)

@api_view(['GET'])
def session_detail(request, session_id):
    try:
        session = Session.objects.get(id=session_id)
    except Session.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)
    return Response(SessionDetailSerializer(session).data)

@api_view(['GET'])
def active_session(request):
    session = Session.objects.filter(is_active=True).order_by('-started_at').first()
    if not session:
        return Response({'active': False, 'session': None})
    return Response({'active': True, 'session': SessionSerializer(session).data})

# ── ATTENTION LOGS ──

@api_view(['POST'])
def log_attention(request):
    serializer = AttentionLogSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def log_attention_batch(request):
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
    student_id = request.query_params.get('student_id', None)
    logs = AttentionLog.objects.filter(session_id=session_id).order_by('-timestamp')
    if student_id:
        logs = logs.filter(student__student_id=student_id)
    return Response(AttentionLogSerializer(logs, many=True).data)

# ── SESSION SUMMARY ──

@api_view(['POST'])
def save_summary(request):
    serializer = SessionSummarySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def session_summary(request, session_id):
    summaries = SessionSummary.objects.filter(session_id=session_id).select_related('student').order_by('-avg_score')
    if not summaries.exists():
        session = Session.objects.filter(id=session_id).first()
        if session and session.is_active:
            _auto_generate_summary(session)
            summaries = SessionSummary.objects.filter(session_id=session_id).select_related('student').order_by('-avg_score')
    return Response(SessionSummarySerializer(summaries, many=True).data)

@api_view(['POST'])
def import_json_session(request):
    data = request.data
    session_start = data.get('session_start')
    students_data = data.get('students', {})
    if not session_start:
        return Response({'error': 'session_start is required'}, status=400)
    session = Session.objects.create(label=f"Imported: {session_start}", is_active=False, ended_at=timezone.now())
    created = []
    for sid, stats in students_data.items():
        student, _ = Student.objects.get_or_create(student_id=int(sid))
        grade = _score_to_grade(stats.get('avg_score', 0))
        s = SessionSummary.objects.create(session=session, student=student,
            avg_score=stats.get('avg_score', 0), total_frames=stats.get('total_frames', 0),
            attentive_pct=stats.get('attentive_pct', 0), distracted_pct=stats.get('distracted_pct', 0),
            phone_frames=stats.get('phone_frames', 0), reading_frames=stats.get('reading_frames', 0), grade=grade)
        created.append(s)
    return Response({'session_id': session.id, 'students_imported': len(created)}, status=status.HTTP_201_CREATED)

# ── STUDENTS ──

@api_view(['GET', 'POST'])
def students(request):
    if request.method == 'GET':
        q = request.query_params.get('search', '').strip()
        qs = Student.objects.all()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(usn__icontains=q) | Q(student_id__icontains=q))
        return Response(StudentSerializer(qs.order_by('student_id'), many=True).data)
    serializer = StudentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PATCH'])
def student_detail(request, student_id):
    try:
        student = Student.objects.get(student_id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=404)
    if request.method == 'PATCH':
        name = request.data.get('name')
        usn = request.data.get('usn')
        if name is not None:
            student.name = name
        if usn is not None:
            student.usn = usn
        student.save()
    return Response(StudentSerializer(student).data)

@api_view(['GET'])
def student_sessions(request, student_id):
    summaries = SessionSummary.objects.filter(student__student_id=student_id).select_related('session').order_by('-session__started_at')
    results = []
    for s in summaries:
        results.append({
            'session_id': s.session.id, 'session_label': s.session.label or f'Session #{s.session.id}',
            'started_at': s.session.started_at, 'ended_at': s.session.ended_at, 'is_active': s.session.is_active,
            'avg_score': s.avg_score, 'grade': s.grade, 'attentive_pct': s.attentive_pct,
            'distracted_pct': s.distracted_pct, 'phone_frames': s.phone_frames, 'total_frames': s.total_frames,
        })
    return Response(results)

@api_view(['GET'])
def student_weekly_report(request, student_id):
    summaries = SessionSummary.objects.filter(student__student_id=student_id).select_related('session')
    if not summaries.exists():
        return Response({'error': 'No data found for this student'}, status=404)
    total_frames = sum(s.total_frames for s in summaries)
    weighted_avg = sum(s.avg_score * s.total_frames for s in summaries) / total_frames
    return Response({
        'student_id': student_id, 'weekly_avg_score': round(weighted_avg, 3),
        'grade': _score_to_grade(weighted_avg), 'sessions_recorded': summaries.count(),
        'total_frames': total_frames, 'total_phone_frames': sum(s.phone_frames for s in summaries),
        'total_reading_frames': sum(s.reading_frames for s in summaries),
        'avg_attentive_pct': round(sum(s.attentive_pct for s in summaries) / summaries.count(), 1),
        'avg_distracted_pct': round(sum(s.distracted_pct for s in summaries) / summaries.count(), 1),
    })

# ── CLASS OVERVIEW ──

@api_view(['GET'])
def class_overview(request, session_id):
    try:
        session = Session.objects.get(id=session_id)
    except Session.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)

    if session.is_active:
        logs = AttentionLog.objects.filter(session_id=session_id)
        if not logs.exists():
            return Response({'error': 'No data yet'}, status=404)
        student_ids = logs.values_list('student', flat=True).distinct()
        total = student_ids.count()
        attentive = partial = distracted = phone = 0
        scores = []
        for sid in student_ids:
            sl = logs.filter(student_id=sid)
            avg = sum(sl.values_list('attention_score', flat=True)) / sl.count()
            scores.append(avg)
            if avg >= 0.70: attentive += 1
            elif avg >= 0.50: partial += 1
            else: distracted += 1
            if sl.filter(object_detected='phone').exists(): phone += 1
        avg_score = sum(scores) / len(scores) if scores else 0
        return Response({'session_id': session_id, 'total_students': total,
            'class_avg_score': round(avg_score, 3), 'class_grade': _score_to_grade(avg_score),
            'attentive_count': attentive, 'partially_attentive_count': partial,
            'distracted_count': distracted, 'phone_detected_count': phone,
            'attentive_pct': round(attentive / total * 100, 1) if total else 0,
            'distracted_pct': round(distracted / total * 100, 1) if total else 0})

    summaries = SessionSummary.objects.filter(session_id=session_id).select_related('student')
    if not summaries.exists():
        return Response({'error': 'No data for this session'}, status=404)
    total = summaries.count()
    avg_score = sum(s.avg_score for s in summaries) / total
    return Response({'session_id': session_id, 'total_students': total,
        'class_avg_score': round(avg_score, 3), 'class_grade': _score_to_grade(avg_score),
        'attentive_count': summaries.filter(avg_score__gte=0.70).count(),
        'partially_attentive_count': summaries.filter(avg_score__gte=0.50, avg_score__lt=0.70).count(),
        'distracted_count': summaries.filter(avg_score__lt=0.50).count(),
        'phone_detected_count': summaries.filter(phone_frames__gt=0).count(),
        'attentive_pct': round(summaries.filter(avg_score__gte=0.70).count() / total * 100, 1),
        'distracted_pct': round(summaries.filter(avg_score__lt=0.50).count() / total * 100, 1)})

# ── DISTRACTION TIMELINE ──

@api_view(['GET'])
def session_timeline(request, session_id):
    """Time-bucketed attention data. Uses frame-index bucketing when time span is short."""
    try:
        session = Session.objects.get(id=session_id)
    except Session.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)
    logs = AttentionLog.objects.filter(session_id=session_id).order_by('timestamp')
    if not logs.exists():
        return Response([])
    all_logs = list(logs.values('attention_score', 'label', 'student_id', 'timestamp'))
    total = len(all_logs)
    first_ts = all_logs[0]['timestamp']
    last_ts = all_logs[-1]['timestamp']
    time_span = (last_ts - first_ts).total_seconds()
    # Use frame-index bucketing: split into ~12 equal segments
    num_buckets = min(12, max(3, total // 5))
    bucket_size = max(1, total // num_buckets)
    timeline = []
    for i in range(0, total, bucket_size):
        chunk = all_logs[i:i + bucket_size]
        if not chunk:
            continue
        scores = [c['attention_score'] for c in chunk]
        labels = [c['label'] for c in chunk]
        student_ids = set(c['student_id'] for c in chunk)
        avg_s = sum(scores) / len(scores)
        dist_n = sum(1 for l in labels if l and 'Distracted' in l)
        phone_n = sum(1 for l in labels if l and 'Phone' in l)
        # Label: use time if spread, else use segment number
        seg_idx = i // bucket_size + 1
        if time_span > 120:
            time_label = chunk[0]['timestamp'].strftime('%H:%M')
        else:
            elapsed_pct = round(i / total * 100)
            time_label = f'{elapsed_pct}%'
        timeline.append({
            'time': time_label,
            'segment': seg_idx,
            'time_iso': chunk[0]['timestamp'].isoformat(),
            'avg_score': round(avg_s, 3),
            'attention_pct': round(avg_s * 100, 1),
            'distraction_pct': round(dist_n / len(labels) * 100, 1) if labels else 0,
            'phone_count': phone_n,
            'student_count': len(student_ids),
            'total_observations': len(scores),
        })
    return Response(timeline)

# ── TEACHER FEEDBACK ──

@api_view(['GET'])
def get_teacher_feedback(request, session_id):
    try:
        fb = TeacherFeedback.objects.select_related('session').get(session_id=session_id)
    except TeacherFeedback.DoesNotExist:
        return Response({'error': 'No feedback generated'}, status=404)
    return Response(TeacherFeedbackSerializer(fb).data)

@api_view(['POST'])
def generate_teacher_feedback(request, session_id):
    try:
        session = Session.objects.get(id=session_id)
    except Session.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)
    fb = _auto_generate_feedback(session)
    if fb is None:
        return Response({'error': 'No attention data available'}, status=400)
    send_email = request.data.get('send_email', False)
    email_to = request.data.get('email', '')
    if send_email and email_to:
        success, err = _send_feedback_email(fb, email_to)
        if not success:
            return Response({'error': f'Feedback generated, but email failed: {err}'}, status=400)
    return Response(TeacherFeedbackSerializer(fb).data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def list_feedbacks(request):
    fbs = TeacherFeedback.objects.select_related('session').order_by('-generated_at')
    return Response(TeacherFeedbackSerializer(fbs, many=True).data)

@api_view(['POST'])
def send_feedback_email_view(request, session_id):
    """Send existing feedback to an email address."""
    try:
        fb = TeacherFeedback.objects.select_related('session').get(session_id=session_id)
    except TeacherFeedback.DoesNotExist:
        return Response({'error': 'No feedback for this session'}, status=404)
    email = request.data.get('email', '').strip()
    if not email:
        return Response({'error': 'Email is required'}, status=400)
    success, error_msg = _send_feedback_email(fb, email)
    if not success:
        return Response({'error': f'Failed to send email: {error_msg}'}, status=400)
    return Response({'success': True, 'email_sent_to': email})

@api_view(['GET'])
def download_session_pdf(request, session_id):
    """Generate and return a PDF report for the session."""
    try:
        session = Session.objects.get(id=session_id)
        fb = TeacherFeedback.objects.filter(session=session).first()
    except Session.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)
    
    pdf_buffer = generate_session_pdf(session, fb)
    return FileResponse(pdf_buffer, as_attachment=True, filename=f"Session_Report_{session.id}.pdf")

# ── HELPERS ──

def _score_to_grade(score):
    if score >= 0.85: return "A"
    if score >= 0.70: return "B"
    if score >= 0.55: return "C"
    if score >= 0.40: return "D"
    return "F"

def _auto_generate_summary(session):
    logs = AttentionLog.objects.filter(session=session)
    if not logs.exists(): return
    for student_pk in logs.values_list('student', flat=True).distinct():
        sl = logs.filter(student_id=student_pk)
        student = Student.objects.get(pk=student_pk)
        total = sl.count()
        scores = list(sl.values_list('attention_score', flat=True))
        labels = list(sl.values_list('label', flat=True))
        avg = sum(scores) / total
        SessionSummary.objects.update_or_create(session=session, student=student, defaults={
            'avg_score': round(avg, 3), 'total_frames': total,
            'attentive_pct': round(sum(1 for l in labels if 'Attentive' in l) / total * 100, 1),
            'distracted_pct': round(sum(1 for l in labels if 'Distracted' in l) / total * 100, 1),
            'phone_frames': sum(1 for l in labels if 'Phone' in l),
            'reading_frames': sum(1 for l in labels if 'Reading' in l),
            'grade': _score_to_grade(avg)})

def _auto_generate_feedback(session):
    logs = AttentionLog.objects.filter(session=session).order_by('timestamp')
    summaries = SessionSummary.objects.filter(session=session).select_related('student')
    if not logs.exists() and not summaries.exists(): return None
    label = session.label or f'Session #{session.id}'
    started = session.started_at.strftime('%I:%M %p') if session.started_at else 'N/A'
    ended = session.ended_at.strftime('%I:%M %p') if session.ended_at else 'N/A'
    if summaries.exists():
        total_students = summaries.count()
        avg_score = sum(s.avg_score for s in summaries) / total_students
        total_phone = sum(s.phone_frames for s in summaries)
        distracted_students = summaries.filter(avg_score__lt=0.50).count()
        attentive_students = summaries.filter(avg_score__gte=0.70).count()
    else:
        sids = logs.values_list('student', flat=True).distinct()
        total_students = sids.count()
        sc = list(logs.values_list('attention_score', flat=True))
        avg_score = sum(sc) / len(sc) if sc else 0
        total_phone = logs.filter(object_detected='phone').count()
        distracted_students = attentive_students = 0
    grade = _score_to_grade(avg_score)
    # Peak distraction periods
    peaks = []
    if logs.exists():
        bd = timedelta(minutes=2)
        cur = logs.first().timestamp
        last = logs.last().timestamp
        while cur <= last + bd:
            be = cur + bd
            bl = logs.filter(timestamp__gte=cur, timestamp__lt=be)
            if bl.exists():
                lbls = list(bl.values_list('label', flat=True))
                dist_n = sum(1 for l in lbls if 'Distracted' in l)
                phone_n = sum(1 for l in lbls if 'Phone' in l)
                dpct = round(dist_n / len(lbls) * 100, 1) if lbls else 0
                if dpct >= 40:
                    peaks.append({'start': cur.strftime('%I:%M %p'), 'end': be.strftime('%I:%M %p'),
                        'distraction_pct': dpct, 'phone_count': phone_n,
                        'student_count': bl.values_list('student', flat=True).distinct().count()})
            cur = be
    spct = round(avg_score * 100, 1)
    parts = [f'Session: "{label}"', f'Time: {started} — {ended}', '',
        f'Overall attention: {spct}% (Grade: {grade})', f'Students tracked: {total_students}']
    if summaries.exists():
        parts += [f'Attentive: {attentive_students}/{total_students}',
                  f'Distracted: {distracted_students}/{total_students}']
    if total_phone > 0: parts.append(f'Phone detections: {total_phone}')
    if peaks:
        parts += ['', '⚠️ PEAK DISTRACTION PERIODS:']
        for p in peaks:
            parts.append(f"  • {p['start']}–{p['end']}: {p['distraction_pct']}% distraction ({p['phone_count']} phones)")
    recs = []
    if peaks: recs.append('Add interactive activities during peak distraction windows to re-engage students.')
    if total_phone > 5: recs.append('Significant phone usage detected. Consider a phone-free policy.')
    if avg_score < 0.50: recs.append('Overall attention was low. Try shorter segments with frequent check-ins.')
    elif avg_score < 0.70: recs.append('Moderate attention. Mix lectures with discussions or polls.')
    else: recs.append('Great engagement! Continue your current approach.')
    fb, _ = TeacherFeedback.objects.update_or_create(session=session, defaults={
        'overall_summary': '\n'.join(parts), 'peak_distraction_periods': peaks,
        'recommendations': '\n'.join(f'• {r}' for r in recs),
        'avg_attention_score': round(avg_score, 3), 'total_students_tracked': total_students})
    return fb

def _send_feedback_email(feedback, to_email):
    from django.core.mail import EmailMessage
    from django.conf import settings
    subject = f"SmartClass AI — Report: {feedback.session.label or f'Session #{feedback.session.id}'}"
    body = f"{feedback.overall_summary}\n\nRECOMMENDATIONS:\n{feedback.recommendations}\n\nPlease find the detailed session report attached as a PDF."
    try:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email]
        )
        
        # Generate PDF and attach it
        pdf_buffer = generate_session_pdf(feedback.session, feedback)
        email.attach(f"Session_Report_{feedback.session.id}.pdf", pdf_buffer.getvalue(), 'application/pdf')
        
        email.send(fail_silently=False)
        feedback.email_sent = True
        feedback.save()
        return True, ""
    except Exception as e:
        print(f"[EMAIL] Failed: {e}")
        return False, str(e)