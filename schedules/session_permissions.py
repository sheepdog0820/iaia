from __future__ import annotations

from django.db import transaction

from accounts.models import GroupMembership

from .models import SessionParticipant, SessionParticipantRole, TRPGSession


MANAGEMENT_ROLES = (
    SessionParticipantRole.Role.OWNER.value,
    SessionParticipantRole.Role.MANAGER.value,
    SessionParticipantRole.Role.GM.value,
)

VISIBLE_ASSIGNABLE_ROLES = (
    SessionParticipantRole.Role.GM.value,
    SessionParticipantRole.Role.PLAYER.value,
)


def _is_authenticated(user) -> bool:
    return bool(user and getattr(user, "is_authenticated", False))


def _role_value(role) -> str:
    return role.value if hasattr(role, "value") else str(role)


def _user_participant(user, session: TRPGSession) -> SessionParticipant | None:
    if not _is_authenticated(user):
        return None
    return SessionParticipant.objects.filter(session=session, user=user).first()


def _single_role_for_participant(participant: SessionParticipant) -> str | None:
    if not participant.pk:
        return None
    return participant.participant_roles.values_list("role", flat=True).first()


def get_participant_role_values(participant: SessionParticipant) -> set[str]:
    role = _single_role_for_participant(participant)
    return {role} if role else set()


def normalize_participant_roles(roles) -> set[str]:
    normalized_roles = [_role_value(role) for role in roles if role]
    valid_roles = {choice.value for choice in SessionParticipantRole.Role}
    invalid_roles = set(normalized_roles) - valid_roles
    if invalid_roles:
        raise ValueError(f"Unknown participant roles: {', '.join(sorted(invalid_roles))}")
    if len(set(normalized_roles)) > 1:
        raise ValueError("Session participants accept exactly one role.")
    return set(normalized_roles) or {SessionParticipantRole.Role.PLAYER.value}


def normalize_assignable_participant_roles(roles) -> set[str]:
    normalized = normalize_participant_roles(roles)
    invalid_roles = normalized - set(VISIBLE_ASSIGNABLE_ROLES)
    if invalid_roles:
        raise ValueError("Only GM or PL roles can be assigned from this screen.")
    return normalized


def get_primary_participant_role(participant: SessionParticipant) -> str:
    return _single_role_for_participant(participant) or SessionParticipantRole.Role.PLAYER.value


def has_participant_role(user, session: TRPGSession, role: str) -> bool:
    role = _role_value(role)
    if not _is_authenticated(user):
        return False
    return SessionParticipantRole.objects.filter(
        participant__session=session,
        participant__user=user,
        role=role,
    ).exists()


def is_session_gm(user, session: TRPGSession) -> bool:
    if not _is_authenticated(user):
        return False
    return session.gm_id == user.id or has_participant_role(user, session, SessionParticipantRole.Role.GM.value)


def _effective_participant_role(participant: SessionParticipant, role: str) -> str:
    if participant.user_id and participant.session.created_by_id == participant.user_id:
        return SessionParticipantRole.Role.OWNER.value
    return role


def assign_participant_role(
    participant: SessionParticipant,
    role: str,
    *,
    granted_by=None,
) -> SessionParticipantRole:
    role = _role_value(role)
    normalized_role = _effective_participant_role(participant, next(iter(normalize_participant_roles([role]))))
    participant_role, _ = SessionParticipantRole.objects.update_or_create(
        participant=participant,
        defaults={"role": normalized_role},
    )
    return participant_role


def set_participant_roles(
    participant: SessionParticipant,
    roles,
    *,
    granted_by=None,
) -> set[str]:
    normalized_roles = normalize_participant_roles(roles)
    assign_participant_role(participant, next(iter(normalized_roles)), granted_by=granted_by)
    return normalized_roles


@transaction.atomic
def create_participant(
    *,
    session: TRPGSession,
    roles=None,
    role=None,
    granted_by=None,
    **participant_fields,
) -> SessionParticipant:
    if role is not None:
        if roles is not None:
            raise ValueError("Use either role or roles when creating a participant.")
        roles = [role]
    participant = SessionParticipant.objects.create(session=session, **participant_fields)
    set_participant_roles(
        participant,
        roles or [SessionParticipantRole.Role.PLAYER],
        granted_by=granted_by,
    )
    return participant


def revoke_participant_role(
    participant: SessionParticipant,
    role: str,
) -> int:
    role = _role_value(role)
    if (
        participant.user_id
        and participant.session.created_by_id == participant.user_id
        and role == SessionParticipantRole.Role.OWNER.value
    ):
        return 0
    deleted, _ = SessionParticipantRole.objects.filter(participant=participant, role=role).delete()
    return deleted


def is_group_admin(user, session: TRPGSession) -> bool:
    if not _is_authenticated(user) or not session.group_id:
        return False
    if session.group.created_by_id == user.id:
        return True
    return GroupMembership.objects.filter(
        group_id=session.group_id,
        user=user,
        role="admin",
    ).exists()


def is_group_member(user, session: TRPGSession) -> bool:
    if not _is_authenticated(user) or not session.group_id:
        return False
    return GroupMembership.objects.filter(group_id=session.group_id, user=user).exists()


@transaction.atomic
def assign_session_gm(
    session: TRPGSession,
    user,
    *,
    granted_by=None,
    sync_legacy_gm: bool = True,
) -> SessionParticipant:
    if not _is_authenticated(user):
        raise ValueError("A session GM must be an authenticated user.")
    participant, _ = SessionParticipant.objects.get_or_create(
        session=session,
        user=user,
    )
    if session.created_by_id == user.id:
        assign_participant_role(participant, SessionParticipantRole.Role.OWNER, granted_by=granted_by)
    else:
        assign_participant_role(participant, SessionParticipantRole.Role.GM, granted_by=granted_by)

    if sync_legacy_gm and session.gm_id != user.id:
        session.gm = user
        session.save(update_fields=["gm", "updated_at"])

    return participant


@transaction.atomic
def initialize_created_session_permissions(
    session: TRPGSession,
    *,
    created_by=None,
    gm=None,
    granted_by=None,
) -> None:
    created_by = created_by or session.created_by
    if created_by:
        participant, _ = SessionParticipant.objects.get_or_create(
            session=session,
            user=created_by,
        )
        assign_participant_role(
            participant,
            SessionParticipantRole.Role.OWNER,
            granted_by=granted_by,
        )

    gm = gm if gm is not None else session.gm
    if gm:
        assign_session_gm(session, gm, granted_by=granted_by or created_by)


@transaction.atomic
def create_session_with_permissions(*, created_by, gm=None, **session_fields) -> TRPGSession:
    if created_by:
        session_fields.setdefault("created_by", created_by)
    if gm is not None:
        session_fields.setdefault("gm", gm)

    session = TRPGSession.objects.create(**session_fields)
    initialize_created_session_permissions(
        session,
        created_by=created_by,
        gm=gm if gm is not None else session.gm,
    )
    return session


def can_view_session_basic(user, session: TRPGSession) -> bool:
    if session.visibility == "public":
        return True
    if not _is_authenticated(user):
        return False
    if SessionParticipant.objects.filter(session=session, user=user).exists():
        return True
    return is_group_member(user, session) or is_group_admin(user, session)


def _has_management_role(user, session: TRPGSession) -> bool:
    if not _is_authenticated(user):
        return False
    return SessionParticipantRole.objects.filter(
        participant__session=session,
        participant__user=user,
        role__in=MANAGEMENT_ROLES,
    ).exists()


def can_edit_session_basic(user, session: TRPGSession) -> bool:
    if not _is_authenticated(user):
        return False
    return _has_management_role(user, session) or is_session_gm(user, session) or is_group_admin(user, session)


def can_manage_participants(user, session: TRPGSession) -> bool:
    return can_edit_session_basic(user, session)


def can_manage_share_links(user, session: TRPGSession) -> bool:
    return can_edit_session_basic(user, session)


def can_manage_permissions(user, session: TRPGSession) -> bool:
    if not _is_authenticated(user):
        return False
    return _has_management_role(user, session) or is_session_gm(user, session) or is_group_admin(user, session)


def can_view_secret_content(user, session: TRPGSession) -> bool:
    return is_session_gm(user, session)


def can_manage_secret_content(user, session: TRPGSession) -> bool:
    return can_view_secret_content(user, session)


def can_link_own_character(user, participant: SessionParticipant) -> bool:
    return _is_authenticated(user) and participant.user_id == user.id
