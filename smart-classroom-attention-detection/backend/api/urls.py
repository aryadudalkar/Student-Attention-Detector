from django.urls import path
from . import views

urlpatterns = [
    # Sessions
    path('sessions/', views.list_sessions),
    path('sessions/active/', views.active_session),
    path('sessions/start/', views.start_session),
    path('sessions/<int:session_id>/', views.session_detail),
    path('sessions/<int:session_id>/end/', views.end_session),
    path('sessions/<int:session_id>/logs/', views.session_logs),
    path('sessions/<int:session_id>/summary/', views.session_summary),
    path('sessions/<int:session_id>/overview/', views.class_overview),

    # Attention Logs
    path('logs/', views.log_attention),
    path('logs/batch/', views.log_attention_batch),

    # Summaries
    path('summaries/', views.save_summary),
    path('sessions/import/', views.import_json_session),

    # Students
    path('students/', views.students),
    path('students/<int:student_id>/', views.student_detail),
    path('students/<int:student_id>/weekly-report/', views.student_weekly_report),
]