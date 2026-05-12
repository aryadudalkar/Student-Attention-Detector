from django.db import models


class Student(models.Model):
    student_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    usn = models.CharField(max_length=20, blank=True, null=True, unique=True)
    photo = models.ImageField(upload_to='student_photos/', blank=True, null=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Student {self.student_id} - {self.name or 'Unknown'}"


class Session(models.Model):
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    log_file = models.CharField(max_length=255, blank=True, null=True)
    label = models.CharField(max_length=100, blank=True, null=True)  # e.g. "Math Class - April 3"

    def __str__(self):
        return f"Session {self.id} ({'Active' if self.is_active else 'Ended'}) - {self.started_at}"


class AttentionLog(models.Model):
    LABEL_CHOICES = [
        ('Attentive', 'Attentive'),
        ('Partially Attentive', 'Partially Attentive'),
        ('Distracted', 'Distracted'),
        ('Distracted (Phone)', 'Distracted (Phone)'),
        ('Attentive (Reading)', 'Attentive (Reading)'),
    ]
    OBJECT_CHOICES = [
        ('none', 'None'),
        ('phone', 'Phone'),
        ('book', 'Book'),
        ('laptop', 'Laptop'),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='logs')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    attention_score = models.FloatField()
    label = models.CharField(max_length=50, choices=LABEL_CHOICES)
    object_detected = models.CharField(max_length=20, choices=OBJECT_CHOICES, default='none')
    yolo_score = models.FloatField(blank=True, null=True)
    gaze_score = models.FloatField(blank=True, null=True)
    head_score = models.FloatField(blank=True, null=True)
    pitch = models.FloatField(blank=True, null=True)
    yaw = models.FloatField(blank=True, null=True)
    roll = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"Student {self.student.student_id} | {self.label} | {self.attention_score}"


class SessionSummary(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='summaries')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='summaries')
    avg_score = models.FloatField()
    total_frames = models.IntegerField()
    attentive_pct = models.FloatField()
    distracted_pct = models.FloatField()
    phone_frames = models.IntegerField(default=0)
    reading_frames = models.IntegerField(default=0)
    grade = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        unique_together = ('session', 'student')

    def __str__(self):
        return f"Summary | Student {self.student.student_id} | Session {self.session.id} | {self.grade}"


class TeacherFeedback(models.Model):
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name='feedback')
    generated_at = models.DateTimeField(auto_now_add=True)
    overall_summary = models.TextField()
    peak_distraction_periods = models.JSONField(default=list)
    recommendations = models.TextField(blank=True)
    avg_attention_score = models.FloatField()
    total_students_tracked = models.IntegerField()
    email_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback | Session {self.session.id} | {self.generated_at}"