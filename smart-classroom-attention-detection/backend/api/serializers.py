from rest_framework import serializers
from .models import Student, Session, AttentionLog, SessionSummary, TeacherFeedback


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'


class SessionSerializer(serializers.ModelSerializer):
    has_feedback = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = '__all__'

    def get_has_feedback(self, obj):
        return hasattr(obj, 'feedback') and obj.feedback is not None


class AttentionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttentionLog
        fields = '__all__'


class SessionSummarySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_usn = serializers.CharField(source='student.usn', read_only=True)

    class Meta:
        model = SessionSummary
        fields = '__all__'


class TeacherFeedbackSerializer(serializers.ModelSerializer):
    session_label = serializers.CharField(source='session.label', read_only=True)
    session_started_at = serializers.DateTimeField(source='session.started_at', read_only=True)
    session_ended_at = serializers.DateTimeField(source='session.ended_at', read_only=True)

    class Meta:
        model = TeacherFeedback
        fields = '__all__'


class SessionDetailSerializer(serializers.ModelSerializer):
    summaries = SessionSummarySerializer(many=True, read_only=True)
    total_students = serializers.SerializerMethodField()
    avg_class_score = serializers.SerializerMethodField()
    has_feedback = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = '__all__'

    def get_total_students(self, obj):
        return obj.summaries.count()

    def get_avg_class_score(self, obj):
        summaries = obj.summaries.all()
        if not summaries:
            return None
        return round(sum(s.avg_score for s in summaries) / summaries.count(), 3)

    def get_has_feedback(self, obj):
        return hasattr(obj, 'feedback') and obj.feedback is not None