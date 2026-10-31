"""Validate public hosts while keeping exact internal HTTP health probes available."""

from .health_views import health_live_view, health_ready_view

_HEALTH_VIEWS = {
    "/health/live": health_live_view,
    "/health/live/": health_live_view,
    "/health/ready": health_ready_view,
    "/health/ready/": health_ready_view,
}


class ProductionHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        health_view = _HEALTH_VIEWS.get(request.path_info) if request.method in ("GET", "HEAD") else None
        if health_view and not request.is_secure():
            response = health_view(request)
        else:
            request.get_host()
            response = self.get_response(request)

        if health_view:
            response["Cache-Control"] = "no-store"
            response["X-Content-Type-Options"] = "nosniff"
            if request.method == "HEAD":
                response.setdefault("Content-Length", str(len(response.content)))
                response.content = b""
        return response
