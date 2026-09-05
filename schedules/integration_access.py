"""Session visibility shared by export requests and their background workers."""

from django.db.models import Q

from accounts.models import GroupMembership

from .models import TRPGSession


def visible_user_sessions(user):
    admin_group_ids = GroupMembership.objects.filter(user=user, role="admin").values_list("group_id", flat=True)
    return TRPGSession.objects.filter(
        Q(created_by=user)
        | Q(group__created_by=user)
        | Q(group_id__in=admin_group_ids)
        | Q(sessionparticipant__user=user)
    ).distinct()
