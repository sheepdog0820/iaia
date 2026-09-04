from schedules import session_permissions
from schedules.models import HandoutInfo, SessionParticipant, TRPGSession


def can_view_handout(handout: HandoutInfo, user, *, participants=None) -> bool:
    if not user or not user.is_authenticated:
        return False
    if participants is not None:
        # The list serializer supplies the complete, prefetched session membership.
        # Other callers retain fresh database permission checks.
        own_participants = [p for p in participants if p.user_id == user.id]
        is_gm = handout.session.gm_id == user.id or any(
            role.role == "gm" for p in own_participants for role in p.participant_roles.all()
        )
    else:
        own_participants = None
        is_gm = session_permissions.can_view_secret_content(user, handout.session)
    if is_gm:
        return True
    if handout.participant and handout.participant.user_id == user.id:
        return True
    if not handout.is_secret:
        if own_participants is not None:
            return bool(own_participants)
        return SessionParticipant.objects.filter(session_id=handout.session_id, user_id=user.id).exists()
    if handout.assigned_player_slot:
        if own_participants is not None:
            return any(p.player_slot == handout.assigned_player_slot for p in own_participants)
        return SessionParticipant.objects.filter(
            session_id=handout.session_id,
            user_id=user.id,
            player_slot=handout.assigned_player_slot,
        ).exists()
    return False
