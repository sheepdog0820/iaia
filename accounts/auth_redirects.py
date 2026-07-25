from django.utils.http import url_has_allowed_host_and_scheme

AUTH_NEXT_SESSION_KEY = "auth_safe_next"


def safe_local_redirect(request, value):
    if not value or not value.startswith("/") or value.startswith("//"):
        return None
    if not url_has_allowed_host_and_scheme(
        url=value,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return None
    return value


def remember_auth_next(request, value):
    safe_next = safe_local_redirect(request, value)
    if safe_next:
        request.session[AUTH_NEXT_SESSION_KEY] = safe_next
    return safe_next


def consume_auth_next(request):
    value = request.session.pop(AUTH_NEXT_SESSION_KEY, None)
    return safe_local_redirect(request, value)
