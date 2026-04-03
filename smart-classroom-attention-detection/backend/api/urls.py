from django.urls import path
from . import views

urlpatterns = [
    # Sessions
    path('sessions/start/', views.start_session),
    path('sessions/<int:session_id>/end/', views.end_session),
    path('sessions/', views.list_sessions),
    path('sessions/<int:session_id>/logs/', views.session_logs),
    path('sessions/<int:session_id>/summary/', views.session_summary),

    # Attention Logs
    path('logs/', views.log_attention),

    # Summaries
    path('summaries/', views.save_summary),

    # Students
    path('students/', views.list_students),
    path('students/<int:student_id>/weekly-report/', views.student_weekly_report),
]