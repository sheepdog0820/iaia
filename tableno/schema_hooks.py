def filter_api_endpoints(endpoints):
    """Keep the generated contract focused on the supported public API surface."""
    from rest_framework.generics import GenericAPIView
    from rest_framework.viewsets import ViewSetMixin

    excluded_exact_paths = {
        "/api/schedules/notification-preferences/{id}/",
    }
    excluded_path_fragments = {
        "/ccfolia_json/",
        "/growth_records/",
        "/add_skill_growth/",
        "/allocate_skill_points/",
        "/background_summary/",
        "/batch_allocate_skill_points/",
        "/bulk_update_items/",
        "/combat_summary/",
        "/financial_summary/",
        "/growth_summary/",
        "/inventory_summary/",
        "/reset_skill_points/",
        "/skill_points_summary/",
        "/update_background_data/",
        "/update_financial_data/",
    }
    excluded_duplicate_prefixes = ("/api/accounts/character-sheets/{character_id}/images/",)

    filtered = []
    for endpoint in endpoints:
        path, _, _, callback = endpoint
        if not path.startswith("/api/") or path in {"/api/schema/", "/api/docs/"}:
            continue
        if path in excluded_exact_paths:
            continue
        if "/notification-preferences/{id}/" in path or "/notification-preferences/{pk}/" in path:
            continue
        if path.startswith(excluded_duplicate_prefixes):
            continue
        if any(fragment in path for fragment in excluded_path_fragments):
            continue
        view_class = getattr(callback, "cls", None)
        if view_class and (issubclass(view_class, GenericAPIView) or issubclass(view_class, ViewSetMixin)):
            filtered.append(endpoint)
    return filtered
