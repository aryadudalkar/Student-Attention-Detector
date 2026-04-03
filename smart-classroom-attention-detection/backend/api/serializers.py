from rest_framework import serializers
from .models import Student, Session, AttentionLog, SessionSummary


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = '__all__'


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


class SessionDetailSerializer(serializers.ModelSerializer):
    summaries = SessionSummarySerializer(many=True, read_only=True)
    total_students = serializers.SerializerMethodField()
    avg_class_score = serializers.SerializerMethodField()

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