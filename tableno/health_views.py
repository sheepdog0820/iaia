from uuid import uuid4

from django.core.cache import caches
from django.db import connections
from django.http import JsonResponse
from django.utils import timezone


def _check_database():
    connection = connections["default"]
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def _check_cache():
    cache = caches["default"]
    probe_key = f"healthcheck:probe:{uuid4().hex}"
    probe_value = timezone.now().isoformat()
    cache.set(probe_key, probe_value, timeout=10)
    try:
        if cache.get(probe_key) != probe_value:
            raise RuntimeError("cache round-trip check failed")
    finally:
        cache.delete(probe_key)


def health_live_view(request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "tableno",
            "check": "live",
            "timestamp": timezone.now().isoformat(),
        }
    )


def health_ready_view(request):
    checks = {}
    errors = []
    checkers = (
        ("database", _check_database),
        ("cache", _check_cache),
    )

    for name, checker in checkers:
        try:
            checker()
            checks[name] = "ok"
        except Exception:  # noqa: BLE001
            checks[name] = "error"
            errors.append(name)

    is_ready = not errors
    return JsonResponse(
        {
            "status": "ok" if is_ready else "degraded",
            "service": "tableno",
            "check": "ready",
            "checks": checks,
            "errors": errors,
            "timestamp": timezone.now().isoformat(),
        },
        status=200 if is_ready else 503,
    )
