from django.conf import settings


def runtime_capabilities(request):
    return {
        'websocket_notifications_enabled': getattr(
            settings,
            'WEBSOCKET_NOTIFICATIONS_ENABLED',
            False,
        ),
    }
