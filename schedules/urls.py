from django.urls import path, include
from django.views.generic import RedirectView, TemplateView
from django.contrib.auth.decorators import login_required
from rest_framework.routers import DefaultRouter
from . import views
from . import handout_views
from . import attachment_views
from . import notification_views
from . import template_views
from . import analytics_views
from . import reward_views

router = DefaultRouter()
router.register(r'sessions', views.TRPGSessionViewSet, basename='session')
router.register(r'occurrences', views.SessionOccurrenceViewSet, basename='occurrence')
router.register(r'session-invitations', views.SessionInvitationViewSet, basename='session-invitation')
router.register(r'participants', views.SessionParticipantViewSet, basename='participant')
router.register(r'handouts', views.HandoutInfoViewSet, basename='handout')
router.register(r'session-images', views.SessionImageViewSet, basename='session-image')
router.register(r'rewards', reward_views.SessionRewardViewSet, basename='session-reward')
router.register(r'youtube-links', views.SessionYouTubeLinkViewSet, basename='youtube-link')
router.register(r'gm-handouts', handout_views.HandoutManagementViewSet, basename='gm_handout')
router.register(r'notifications', notification_views.HandoutNotificationViewSet, basename='handoutnotification')
router.register(r'notification-preferences', notification_views.UserNotificationPreferencesViewSet, basename='notificationpreferences')
router.register(r'session-templates', template_views.SessionTemplateViewSet, basename='session-template')
# 高度なスケジューリング機能（ISSUE-017）
router.register(r'session-series', views.SessionSeriesViewSet, basename='session-series')
router.register(r'availability', views.SessionAvailabilityViewSet, basename='availability')
router.register(r'date-polls', views.DatePollViewSet, basename='date-poll')

urlpatterns = [
    # API URLs
    path('sessions/view/', views.SessionsListView.as_view(), name='sessions_api_view'),
    path('sessions/next-context/', views.NextSessionContextView.as_view(), name='next_session_context'),
    path('sessions/participating-scenarios/', views.ParticipatingScenarioChoicesView.as_view(), name='participating_scenarios'),
    path('sessions/upcoming/', views.UpcomingSessionsView.as_view(), name='upcoming_sessions'),
    path('sessions/statistics/', views.SessionStatisticsView.as_view(), name='session_statistics'),
    path('analytics/dashboard/', analytics_views.SessionAnalyticsDashboardView.as_view(), name='session_analytics_dashboard'),
    path('sessions/<int:pk>/detail/', views.SessionDetailView.as_view(), name='session_detail'),
    path('sessions/<int:pk>/date-poll/', views.SessionDatePollView.as_view(), name='session_date_poll'),
    path('handouts/<int:handout_id>/attachments/', attachment_views.HandoutAttachmentListCreateView.as_view(), name='handout_attachments'),
    path('attachments/<int:pk>/', attachment_views.HandoutAttachmentDetailView.as_view(), name='handout_attachment_detail'),
    path(
        'notification-preferences/',
        notification_views.UserNotificationPreferencesViewSet.as_view({'get': 'list', 'patch': 'partial_update'}),
        name='notification_preferences',
    ),

    # Web URLs (routerより先に配置して衝突を回避)
    path('calendar/view/', TemplateView.as_view(template_name='schedules/calendar.html'), name='calendar_view'),
    path(
        'sessions/web/',
        RedirectView.as_view(
            url='/api/schedules/sessions/view/',
            permanent=False,
            query_string=True,
        ),
        name='sessions_view',
    ),
    path(
        'notifications/view/',
        login_required(TemplateView.as_view(template_name='schedules/notifications.html')),
        name='notifications_view',
    ),
    path(
        'analytics/view/',
        login_required(TemplateView.as_view(template_name='schedules/analytics_dashboard.html')),
        name='analytics_view',
    ),
    path(
        'session-templates/view/',
        login_required(TemplateView.as_view(template_name='schedules/session_templates.html')),
        name='session_templates_view',
    ),

    path('', include(router.urls)),
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('calendar/holidays/', views.JapaneseHolidayView.as_view(), name='calendar_holidays'),
    
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

    path('sessions/<int:session_id>/rewards/',
         reward_views.SessionRewardViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='session-rewards'),

    # GM Handout Management
    path('sessions/<int:session_id>/handouts/manage/', handout_views.GMHandoutManagementView.as_view(), name='gm_handout_management'),
    path('handout-templates/', handout_views.HandoutTemplateView.as_view(), name='handout_templates'),
]
