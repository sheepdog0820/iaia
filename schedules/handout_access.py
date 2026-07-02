from accounts.models import GroupMembership
from schedules.models import HandoutInfo, SessionParticipant, TRPGSession


def can_manage_session(session: TRPGSession, user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if session.gm_id == user.id:
        return True
    if getattr(session, "created_by_id", None) == user.id:
        return True
    if session.group_id:
        if session.group.created_by_id == user.id:
            return True
        if GroupMembership.objects.filter(group_id=session.group_id, user=user, role="admin").exists():
            return True
    return SessionParticipant.objects.filter(session=session, user=user, role="gm").exists()


def can_view_handout(handout: HandoutInfo, user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if can_manage_session(handout.session, user):
        return True
    if handout.participant and handout.participant.user_id == user.id:
        return True
    if not handout.is_secret:
        return SessionParticipant.objects.filter(session_id=handout.session_id, user_id=user.id).exists()
    if handout.assigned_player_slot:
        return SessionParticipant.objects.filter(
            session_id=handout.session_id,
            user_id=user.id,
            player_slot=handout.assigned_player_slot,
        ).exists()
    return False
