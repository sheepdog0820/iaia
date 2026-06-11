def filter_api_endpoints(endpoints):
    """Keep the generated contract focused on the supported public API surface."""
    from rest_framework.generics import GenericAPIView
    from rest_framework.viewsets import ViewSetMixin

    filtered = []
    for endpoint in endpoints:
        path, _, _, callback = endpoint
        if not path.startswith('/api/') or path in {'/api/schema/', '/api/docs/'}:
            continue
        view_class = getattr(callback, 'cls', None)
        if view_class and (
            issubclass(view_class, GenericAPIView)
            or issubclass(view_class, ViewSetMixin)
        ):
            filtered.append(endpoint)
    return filtered
