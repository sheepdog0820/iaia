"""
URL configuration for tableno project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.views import CustomLoginView, CustomSignUpView
from schedules.views import PublicSessionDetailView
from tableno.health_views import health_live_view, health_ready_view
from schedules.job_views import AsyncJobDetailView
from accounts.discord_views import GroupDiscordSettingsView
from accounts.group_link_views import (
    GroupLinkAcceptView,
    GroupLinkDetailView,
    GroupLinkListCreateView,
    GroupLinkShareView,
)
from schedules.integration_views import (
    CalendarSubscriptionRotateView,
    CalendarSubscriptionView,
    GoogleCalendarSyncView,
    GoogleIntegrationView,
    GoogleSheetsExportView,
    GoogleSheetsImportView,
)
from schedules.guest_views import (
    GuestInvitationCreateView,
    GuestInvitationLandingView,
    GuestInvitationRespondView,
    GuestInvitationRevokeView,
    GuestParticipantClaimView,
)

urlpatterns = [
    path('health/live/', health_live_view, name='health_live'),
    path('health/live', health_live_view),
    path('health/ready/', health_ready_view, name='health_ready'),
    path('health/ready', health_ready_view),
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('api/jobs/<uuid:pk>/', AsyncJobDetailView.as_view(), name='async-job-detail'),
    path(
        'api/groups/<int:group_id>/discord-settings/',
        GroupDiscordSettingsView.as_view(),
        name='group-discord-settings',
    ),
    path(
        'api/groups/<int:group_id>/links/',
        GroupLinkListCreateView.as_view(),
        name='group-link-list',
    ),
    path(
        'api/groups/<int:group_id>/links/<int:link_id>/accept/',
        GroupLinkAcceptView.as_view(),
        name='group-link-accept',
    ),
    path(
        'api/groups/<int:group_id>/links/<int:link_id>/',
        GroupLinkDetailView.as_view(),
        name='group-link-detail',
    ),
    path(
        'api/groups/<int:group_id>/links/<int:link_id>/shares/',
        GroupLinkShareView.as_view(),
        name='group-link-share',
    ),
    path(
        'api/calendar/subscription-token/rotate/',
        CalendarSubscriptionRotateView.as_view(),
        name='calendar-subscription-rotate',
    ),
    path(
        'calendar/subscribe/<str:token>.ics',
        CalendarSubscriptionView.as_view(),
        name='calendar-subscription',
    ),
    path(
        'api/google/integration/',
        GoogleIntegrationView.as_view(),
        name='google-integration',
    ),
    path(
        'api/sessions/<int:session_id>/google-calendar/sync/',
        GoogleCalendarSyncView.as_view(),
        name='google-calendar-sync',
    ),
    path(
        'api/character-sheets/google-sheets/import/',
        GoogleSheetsImportView.as_view(),
        name='google-sheets-import',
    ),
    path(
        'api/character-sheets/google-sheets/export/',
        GoogleSheetsExportView.as_view(),
        name='google-sheets-export',
    ),
    path(
        'api/sessions/<int:session_id>/guest-invitations/',
        GuestInvitationCreateView.as_view(),
        name='guest-invitation-create',
    ),
    path(
        'api/sessions/<int:session_id>/guest-invitations/<int:invitation_id>/',
        GuestInvitationRevokeView.as_view(),
        name='guest-invitation-revoke',
    ),
    path(
        'api/guest-invitations/<str:token>/respond/',
        GuestInvitationRespondView.as_view(),
        name='guest-invitation-respond',
    ),
    path(
        'guest-invitations/<str:token>/',
        GuestInvitationLandingView.as_view(),
        name='guest-invitation-landing',
    ),
    path(
        'api/participants/<int:participant_id>/claim/',
        GuestParticipantClaimView.as_view(),
        name='guest-participant-claim',
    ),
    path('admin/', admin.site.urls),
    path(
        'integrations/',
        login_required(TemplateView.as_view(template_name='integrations/settings.html')),
        name='integration-settings',
    ),
    
    # Custom authentication views
    path('login/', CustomLoginView.as_view(), name='account_login'),
    path('signup/', CustomSignUpView.as_view(), name='account_signup'),
    
    # API URLs (8000番ポート統一のため、api/auth/を削除)
    path('api/', include('api.urls')),  # 認証API
    path('api/accounts/', include('accounts.urls')),
    path('api/schedules/', include('schedules.urls')),
    path('api/scenarios/', include('scenarios.urls')),

    # Public share URLs
    path('s/<uuid:share_token>/', PublicSessionDetailView.as_view(), name='public_session_detail'),
    
    # Web URLs
    path('accounts/', include('accounts.urls')),

    # django-allauth URLs（Google OAuth認証用）
    # 注意: accounts.urlsの後に配置することで、カスタムログイン画面を優先
    path('accounts/', include('allauth.urls')),

    # Home page
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
]

# Serve uploaded media in non-production environments (local dev) even if DEBUG is false.
if settings.DEBUG or getattr(settings, 'ENVIRONMENT', 'development') != 'production':
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
