from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from . import session_permissions
from .models import (
    SessionParticipant,
    SessionParticipantRole,
    SessionRecruitmentLink,
    SessionRecruitmentLinkUse,
)


class RecruitmentLinkNotFound(Exception):
    pass


class RecruitmentLinkInactive(Exception):
    pass


@dataclass(frozen=True)
class RecruitmentJoinResult:
    recruitment_link: SessionRecruitmentLink
    participant: SessionParticipant
    already_joined: bool


def get_recruitment_link(token):
    return (
        SessionRecruitmentLink.objects.select_related(
            "session",
            "session__gm",
            "created_by",
        )
        .filter(token_digest=SessionRecruitmentLink.digest(token))
        .first()
    )


@transaction.atomic
def join_recruitment_link(*, token, user):
    try:
        recruitment_link = (
            SessionRecruitmentLink.objects.select_for_update()
            .select_related("session", "created_by")
            .get(token_digest=SessionRecruitmentLink.digest(token))
        )
    except SessionRecruitmentLink.DoesNotExist as exc:
        raise RecruitmentLinkNotFound from exc

    existing_participant = SessionParticipant.objects.filter(
        session=recruitment_link.session,
        user=user,
    ).first()
    if existing_participant:
        return RecruitmentJoinResult(
            recruitment_link=recruitment_link,
            participant=existing_participant,
            already_joined=True,
        )

    if not recruitment_link.is_active:
        raise RecruitmentLinkInactive

    try:
        with transaction.atomic():
            participant = session_permissions.create_participant(
                session=recruitment_link.session,
                user=user,
                role=SessionParticipantRole.Role.PLAYER,
                granted_by=recruitment_link.created_by,
            )
    except IntegrityError:
        participant = SessionParticipant.objects.filter(
            session=recruitment_link.session,
            user=user,
        ).first()
        if participant is None:
            raise
        return RecruitmentJoinResult(
            recruitment_link=recruitment_link,
            participant=participant,
            already_joined=True,
        )

    slot_claimed = SessionRecruitmentLink.objects.filter(
        pk=recruitment_link.pk,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
        use_count__lt=F("max_uses"),
    ).update(use_count=F("use_count") + 1)
    if slot_claimed != 1:
        raise RecruitmentLinkInactive
    recruitment_link.use_count += 1
    SessionRecruitmentLinkUse.objects.create(
        recruitment_link=recruitment_link,
        participant=participant,
        joined_by=user,
    )
    return RecruitmentJoinResult(
        recruitment_link=recruitment_link,
        participant=participant,
        already_joined=False,
    )
