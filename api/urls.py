"""
API URLパターン
"""

from django.urls import path

from accounts.views.api_auth_views import current_user, discord_auth, google_auth, logout, twitter_auth

urlpatterns = [
    # 認証関連
    path("auth/google/", google_auth, name="api_google_auth"),
    path("auth/twitter/", twitter_auth, name="api_twitter_auth"),
    path("auth/discord/", discord_auth, name="api_discord_auth"),
    path("auth/user/", current_user, name="api_current_user"),
    path("auth/logout/", logout, name="api_logout"),
]
