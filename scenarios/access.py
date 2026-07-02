from django.db.models import Q

from accounts.models import GroupMembership


def scenario_visibility_filter(user):
    """Return a Q object for scenarios visible to the user.

    A scenario is visible when it was created by the user or by another user
    who belongs to one of the user's groups.
    """
    if not getattr(user, "is_authenticated", False):
        return Q(pk__in=[])

    group_ids = GroupMembership.objects.filter(user=user).values_list("group_id", flat=True)
    return Q(created_by=user) | Q(created_by__groupmembership__group_id__in=group_ids)


def visible_scenarios(queryset, user):
    return queryset.filter(scenario_visibility_filter(user)).distinct()


def can_view_scenario(user, scenario):
    if scenario is None:
        return True
    if not getattr(user, "is_authenticated", False):
        return False
    if scenario.created_by_id == user.id:
        return True

    user_group_ids = GroupMembership.objects.filter(user=user).values_list("group_id", flat=True)
    return GroupMembership.objects.filter(
        user_id=scenario.created_by_id,
        group_id__in=user_group_ids,
    ).exists()
