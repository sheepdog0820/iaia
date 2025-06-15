from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from . import views
from . import handout_views

router = DefaultRouter()
router.register(r'sessions', views.TRPGSessionViewSet, basename='session')
router.register(r'participants', views.SessionParticipantViewSet, basename='participant')
router.register(r'handouts', views.HandoutInfoViewSet, basename='handout')
router.register(r'gm-handouts', handout_views.HandoutManagementViewSet, basename='gm_handout')

urlpatterns = [
    # API URLs
    path('sessions/view/', views.SessionsListView.as_view(), name='sessions_api_view'),
    path('sessions/upcoming/', views.UpcomingSessionsView.as_view(), name='upcoming_sessions'),
    path('sessions/statistics/', views.SessionStatisticsView.as_view(), name='session_statistics'),
    path('sessions/<int:pk>/detail/', views.SessionDetailView.as_view(), name='session_detail'),
    path('', include(router.urls)),
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('sessions/create/', views.CreateSessionView.as_view(), name='create_session'),
    path('sessions/<int:pk>/join/', views.JoinSessionView.as_view(), name='join_session'),
    
    # GM Handout Management
    path('sessions/<int:session_id>/handouts/manage/', handout_views.GMHandoutManagementView.as_view(), name='gm_handout_management'),
    path('handout-templates/', handout_views.HandoutTemplateView.as_view(), name='handout_templates'),
    
    # Web URLs
    path('calendar/view/', TemplateView.as_view(template_name='schedules/calendar.html'), name='calendar_view'),
    path('sessions/web/', TemplateView.as_view(template_name='schedules/sessions.html'), name='sessions_view'),
]