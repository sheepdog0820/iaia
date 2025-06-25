from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from . import views
from . import handout_views
from . import notification_views

router = DefaultRouter()
router.register(r'sessions', views.TRPGSessionViewSet, basename='session')
router.register(r'participants', views.SessionParticipantViewSet, basename='participant')
router.register(r'handouts', views.HandoutInfoViewSet, basename='handout')
router.register(r'session-images', views.SessionImageViewSet, basename='session-image')
router.register(r'youtube-links', views.SessionYouTubeLinkViewSet, basename='youtube-link')
router.register(r'gm-handouts', handout_views.HandoutManagementViewSet, basename='gm_handout')
router.register(r'notifications', notification_views.HandoutNotificationViewSet, basename='handoutnotification')
router.register(r'notification-preferences', notification_views.UserNotificationPreferencesViewSet, basename='notificationpreferences')

urlpatterns = [
    # API URLs
    path('sessions/view/', views.SessionsListView.as_view(), name='sessions_api_view'),
    path('sessions/upcoming/', views.UpcomingSessionsView.as_view(), name='upcoming_sessions'),
    path('sessions/statistics/', views.SessionStatisticsView.as_view(), name='session_statistics'),
    path('sessions/<int:pk>/detail/', views.SessionDetailView.as_view(), name='session_detail'),
    path('', include(router.urls)),
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    
    # Calendar Integration APIs (ISSUE-008)
    path('calendar/monthly/', views.MonthlyEventListView.as_view(), name='monthly_events'),
    path('calendar/aggregation/', views.SessionAggregationView.as_view(), name='session_aggregation'),
    path('calendar/export/ical/', views.ICalExportView.as_view(), name='ical_export'),
    
    path('sessions/create/', views.CreateSessionView.as_view(), name='create_session'),
    path('sessions/<int:pk>/join/', views.JoinSessionView.as_view(), name='join_session'),
    
    # YouTube Links
    path('sessions/<int:session_id>/youtube-links/', 
         views.SessionYouTubeLinkViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='session-youtube-links'),
    path('sessions/<int:session_id>/youtube-links/statistics/',
         views.SessionYouTubeLinkViewSet.as_view({'get': 'statistics'}),
         name='session-youtube-links-statistics'),
    
    # GM Handout Management
    path('sessions/<int:session_id>/handouts/manage/', handout_views.GMHandoutManagementView.as_view(), name='gm_handout_management'),
    path('handout-templates/', handout_views.HandoutTemplateView.as_view(), name='handout_templates'),
    
    # Web URLs
    path('calendar/view/', TemplateView.as_view(template_name='schedules/calendar.html'), name='calendar_view'),
    path('sessions/web/', TemplateView.as_view(template_name='schedules/sessions.html'), name='sessions_view'),
]