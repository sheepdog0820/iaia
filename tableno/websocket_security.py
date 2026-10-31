"""Validate private WebSocket origins independently of HTTP host allowances."""

from channels.security.websocket import OriginValidator
from django.conf import settings


class ConfiguredOriginValidator:
    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        origins = [
            origin.replace("://*.", "://.")
            for origin in [
                *settings.CSRF_TRUSTED_ORIGINS,
                getattr(settings, "PUBLIC_SITE_URL", ""),
            ]
            if origin and origin != "*"
        ]
        await OriginValidator(self.application, origins)(scope, receive, send)
