from django.urls import include, path
from oauth2_provider.views import (
    OAuthProtectedResourceMetadataView,
    OAuthServerMetadataView,
    RevokeTokenView,
    TokenView,
)

from tableno_mcp.oauth import PilotAuthorizationView

issuer_patterns = [
    path("authorize/", PilotAuthorizationView.as_view(), name="authorize"),
    path("token/", TokenView.as_view(), name="token"),
    path("revoke_token/", RevokeTokenView.as_view(), name="revoke-token"),
]

urlpatterns = [
    path(".well-known/oauth-authorization-server", OAuthServerMetadataView.as_view()),
    path(".well-known/oauth-protected-resource/mcp", OAuthProtectedResourceMetadataView.as_view()),
    path("mcp/oauth/", include((issuer_patterns, "oauth2_provider"))),
]
