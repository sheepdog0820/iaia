from __future__ import annotations

from django.db import transaction

from accounts.models import GroupMembership

from .models import SessionParticipant, SessionParticipantRole, SessionPermission, TRPGSession


BASIC_MANAGEMENT_PERMISSION_ROLES = (
    SessionPermission.Role.OWNER,
    SessionPermission.Role.MANAGER,
)


def _is_authenticated(user) -> bool:
    return bool(user and getattr(user, "is_authenticated", False))


def get_session_permission_roles(user, session: TRPGSession) -> set[str]:
    if not _is_authenticated(user):
        return set()
    return set(
        SessionPermission.objects.filter(session=session, user=user).values_list(
            "role",
            flat=True,
        )
    )


def has_session_permission(user, session: TRPGSession, *roles: str) -> bool:
    if not roles or not _is_authenticated(user):
        return False
    return SessionPermission.objects.filter(session=session, user=user, role__in=roles).exists()


def grant_session_permission(
    session: TRPGSession,
    user,
    role: str,
    *,
    granted_by=None,
) -> SessionPermission:
    if not _is_authenticated(user):
        raise ValueError("Session permissions require an authenticated user.")
    permission, _ = SessionPermission.objects.get_or_create(
        session=session,
        user=user,
        role=role,
        defaults={"granted_by": granted_by},
    )
    return permission


def revoke_session_permission(session: TRPGSession, user, role: str) -> int:
    if not _is_authenticated(user):
        return 0
    deleted, _ = SessionPermission.objects.filter(session=session, user=user, role=role).delete()
    return deleted


def get_participant_role_values(participant: SessionParticipant) -> set[str]:
    if not participant.pk:
        return set()
    return set(participant.participant_roles.values_list("role", flat=True))


def normalize_participant_roles(roles) -> set[str]:
    normalized_roles = {role.value if hasattr(role, "value") else str(role) for role in roles if role}
    valid_roles = {choice.value for choice in SessionParticipantRole.Role}
    invalid_roles = normalized_roles - valid_roles
    if invalid_roles:
        raise ValueError(f"Unknown participant roles: {', '.join(sorted(invalid_roles))}")
    return normalized_roles or {SessionParticipantRole.Role.PLAYER.value}


def get_primary_participant_role(participant: SessionParticipant) -> str:
    roles = get_participant_role_values(participant)
    if SessionParticipantRole.Role.GM.value in roles:
        return SessionParticipantRole.Role.GM.value
    if SessionParticipantRole.Role.PLAYER.value in roles:
        return SessionParticipantRole.Role.PLAYER.value
    if SessionParticipantRole.Role.OBSERVER.value in roles:
        return SessionParticipantRole.Role.OBSERVER.value
    return SessionParticipantRole.Role.PLAYER.value


def has_participant_role(user, session: TRPGSession, role: str) -> bool:
    if not _is_authenticated(user):
        return False
    return SessionParticipantRole.objects.filter(
        participant__session=session,
        participant__user=user,
        role=role,
    ).exists()


def is_session_gm(user, session: TRPGSession) -> bool:
    return has_participant_role(user, session, SessionParticipantRole.Role.GM.value)


def assign_participant_role(
    participant: SessionParticipant,
    role: str,
    *,
    granted_by=None,
) -> SessionParticipantRole:
    role = role.value if hasattr(role, "value") else str(role)
    participant_role, _ = SessionParticipantRole.objects.get_or_create(
        participant=participant,
        role=role,
    )
    if role == SessionParticipantRole.Role.GM.value and participant.user_id:
        grant_session_permission(
            participant.session,
            participant.user,
            SessionPermission.Role.SECRET_KEEPER,
            granted_by=granted_by,
        )
    return participant_role


def set_participant_roles(
    participant: SessionParticipant,
    roles,
    *,
    granted_by=None,
    revoke_removed_gm_secret_keeper: bool = True,
) -> set[str]:
    normalized_roles = normalize_participant_roles(roles)

    existing_roles = get_participant_role_values(participant)
    for role in normalized_roles - existing_roles:
        assign_participant_role(participant, role, granted_by=granted_by)

    roles_to_remove = existing_roles - normalized_roles
    if roles_to_remove:
        SessionParticipantRole.objects.filter(participant=participant, role__in=roles_to_remove).delete()
        if (
            SessionParticipantRole.Role.GM.value in roles_to_remove
            and revoke_removed_gm_secret_keeper
            and participant.user_id
        ):
            revoke_session_permission(
                participant.session,
                participant.user,
                SessionPermission.Role.SECRET_KEEPER,
            )

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
    *,
    revoke_auto_secret_keeper: bool = False,
) -> int:
    role = role.value if hasattr(role, "value") else str(role)
    deleted, _ = SessionParticipantRole.objects.filter(participant=participant, role=role).delete()
    if role == SessionParticipantRole.Role.GM.value and revoke_auto_secret_keeper and participant.user_id:
        revoke_session_permission(
            participant.session,
            participant.user,
            SessionPermission.Role.SECRET_KEEPER,
        )
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
        grant_session_permission(
            session,
            created_by,
            SessionPermission.Role.OWNER,
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
    if SessionPermission.objects.filter(session=session, user=user).exists():
        return True
    if SessionParticipant.objects.filter(session=session, user=user).exists():
        return True
    return is_group_member(user, session) or is_group_admin(user, session)


def can_edit_session_basic(user, session: TRPGSession) -> bool:
    if not _is_authenticated(user):
        return False
    if has_session_permission(user, session, *BASIC_MANAGEMENT_PERMISSION_ROLES):
        return True
    return is_session_gm(user, session) or is_group_admin(user, session)


def can_manage_participants(user, session: TRPGSession) -> bool:
    return can_edit_session_basic(user, session)


def can_manage_share_links(user, session: TRPGSession) -> bool:
    return can_edit_session_basic(user, session)


def can_manage_permissions(user, session: TRPGSession) -> bool:
    if not _is_authenticated(user):
        return False
    return has_session_permission(user, session, SessionPermission.Role.OWNER) or is_group_admin(user, session)


def can_view_secret_content(user, session: TRPGSession) -> bool:
    return has_session_permission(user, session, SessionPermission.Role.SECRET_KEEPER)


def can_manage_secret_content(user, session: TRPGSession) -> bool:
    return can_view_secret_content(user, session)


def can_link_own_character(user, participant: SessionParticipant) -> bool:
    return _is_authenticated(user) and participant.user_id == user.id
