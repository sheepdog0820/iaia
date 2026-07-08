from schedules.models import HandoutInfo, SessionParticipant, TRPGSession
from schedules import session_permissions


def can_view_handout(handout: HandoutInfo, user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if session_permissions.can_view_secret_content(user, handout.session):
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
