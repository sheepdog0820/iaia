from django.conf import settings


def runtime_capabilities(request):
    return {
        "websocket_notifications_enabled": getattr(
            settings,
            "WEBSOCKET_NOTIFICATIONS_ENABLED",
            False,
        ),
        "contact_email": getattr(settings, "CONTACT_EMAIL", "support@tableno.jp"),
        "support_email": getattr(settings, "SUPPORT_EMAIL", "support@tableno.jp"),
    }
