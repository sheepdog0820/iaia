from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import GroupMembership

from . import session_permissions
from .models import ParticipantClaimRequest, ParticipantIdentity, SessionParticipant


class ClaimRequestError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _display_name(user) -> str:
    return user.nickname or user.username


def serialize_claim_request(claim: ParticipantClaimRequest) -> dict:
    participant = claim.participant
    identity = claim.participant_identity or (participant.participant_identity if participant else None)
    session = participant.session if participant else None
    group = identity.group if identity else (session.group if session else None)
    display_name = ""
    if identity:
        display_name = identity.display_name
    elif participant:
        display_name = participant.display_name

    return {
        "id": claim.pk,
        "status": claim.status,
        "message": claim.message,
        "review_comment": claim.review_comment,
        "created_at": claim.created_at,
        "reviewed_at": claim.reviewed_at,
        "requested_by": claim.requested_by_id,
        "requested_by_name": _display_name(claim.requested_by),
        "reviewed_by": claim.reviewed_by_id,
        "reviewed_by_name": _display_name(claim.reviewed_by) if claim.reviewed_by_id else "",
        "participant": claim.participant_id,
        "participant_identity": identity.pk if identity else None,
        "target_type": "participant" if claim.participant_id else "participant_identity",
        "target_display_name": display_name,
        "session": session.pk if session else None,
        "session_title": session.title if session else "",
        "group": group.pk if group else None,
        "group_name": group.name if group else "",
    }


def create_participant_claim_request(
    *,
    participant: SessionParticipant,
    requested_by,
    message: str = "",
) -> tuple[ParticipantClaimRequest, bool]:
    if participant.user_id:
        raise ClaimRequestError("Participant is already linked to a user.", 409)
    if SessionParticipant.objects.filter(session=participant.session, user=requested_by).exclude(pk=participant.pk).exists():
        raise ClaimRequestError("User already participates in this session.", 409)

    existing = ParticipantClaimRequest.objects.filter(
        participant=participant,
        requested_by=requested_by,
        status=ParticipantClaimRequest.Status.PENDING,
    ).first()
    if existing:
        return existing, False

    claim = ParticipantClaimRequest.objects.create(
        participant=participant,
        participant_identity=participant.participant_identity,
        requested_by=requested_by,
        message=(message or "").strip(),
    )
    return claim, True


def create_identity_claim_request(
    *,
    identity: ParticipantIdentity,
    requested_by,
    message: str = "",
) -> tuple[ParticipantClaimRequest, bool]:
    if identity.user_id:
        raise ClaimRequestError("Temporary member is already linked to a user.", 409)
    if not identity.is_active:
        raise ClaimRequestError("Temporary member is inactive.", 400)

    existing = ParticipantClaimRequest.objects.filter(
        participant_identity=identity,
        participant__isnull=True,
        requested_by=requested_by,
        status=ParticipantClaimRequest.Status.PENDING,
    ).first()
    if existing:
        return existing, False

    claim = ParticipantClaimRequest.objects.create(
        participant_identity=identity,
        requested_by=requested_by,
        message=(message or "").strip(),
    )
    return claim, True


def can_review_session_claim(user, session) -> bool:
    return session_permissions.can_manage_participants(user, session)


def can_review_group_claim(user, group) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if group.created_by_id == user.id:
        return True
    return GroupMembership.objects.filter(group=group, user=user, role="admin").exists()


def _claim_target_participants(claim: ParticipantClaimRequest):
    participants = []
    if claim.participant_id:
        participants.append(claim.participant)
    identity = claim.participant_identity or (
        claim.participant.participant_identity if claim.participant_id else None
    )
    if identity:
        linked_participants = list(
            identity.session_participations.select_related("session")
            .select_for_update()
            .filter(user__isnull=True)
        )
        by_id = {participant.pk: participant for participant in participants}
        for participant in linked_participants:
            by_id.setdefault(participant.pk, participant)
        participants = list(by_id.values())
    return participants


def approve_claim_request(claim_id: int, *, reviewed_by) -> ParticipantClaimRequest:
    with transaction.atomic():
        claim = (
            ParticipantClaimRequest.objects.select_for_update()
            .select_related(
                "requested_by",
                "reviewed_by",
                "participant",
                "participant__session",
                "participant__session__group",
                "participant__participant_identity",
                "participant_identity",
                "participant_identity__group",
            )
            .get(pk=claim_id)
        )
        if claim.status != ParticipantClaimRequest.Status.PENDING:
            raise ClaimRequestError("Claim request is already reviewed.", 409)
        if claim.requested_by_id == reviewed_by.id:
            raise ClaimRequestError("Requester cannot approve their own claim request.", 403)

        identity = claim.participant_identity or (
            claim.participant.participant_identity if claim.participant_id else None
        )
        if identity and identity.user_id and identity.user_id != claim.requested_by_id:
            raise ClaimRequestError("Temporary member is already linked to another user.", 409)

        participants = _claim_target_participants(claim)
        for participant in participants:
            if participant.user_id and participant.user_id != claim.requested_by_id:
                raise ClaimRequestError("Participant is already linked to another user.", 409)
            conflict_exists = (
                SessionParticipant.objects.filter(session=participant.session, user=claim.requested_by)
                .exclude(pk=participant.pk)
                .exists()
            )
            if conflict_exists:
                raise ClaimRequestError("User already participates in this session.", 409)

        try:
            if identity:
                identity.user = claim.requested_by
                identity.save(update_fields=["user", "updated_at"])
                if identity.group_id:
                    GroupMembership.objects.get_or_create(
                        group=identity.group,
                        user=claim.requested_by,
                        defaults={"role": "member"},
                    )

            for participant in participants:
                participant.user = claim.requested_by
                participant.guest_name = ""
                participant.save(update_fields=["user", "guest_name"])
        except IntegrityError as exc:
            raise ClaimRequestError("Claim approval conflicts with existing participation.", 409) from exc

        now = timezone.now()
        claim.status = ParticipantClaimRequest.Status.APPROVED
        claim.reviewed_by = reviewed_by
        claim.reviewed_at = now
        claim.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

        competing = ParticipantClaimRequest.objects.filter(status=ParticipantClaimRequest.Status.PENDING).exclude(
            pk=claim.pk
        )
        if claim.participant_id:
            competing.filter(participant=claim.participant).update(
                status=ParticipantClaimRequest.Status.REJECTED,
                reviewed_by=reviewed_by,
                reviewed_at=now,
                review_comment="Another claim request was approved.",
            )
        if identity:
            competing.filter(participant_identity=identity).update(
                status=ParticipantClaimRequest.Status.REJECTED,
                reviewed_by=reviewed_by,
                reviewed_at=now,
                review_comment="Another claim request was approved.",
            )
        return claim


def reject_claim_request(
    claim_id: int,
    *,
    reviewed_by,
    review_comment: str = "",
) -> ParticipantClaimRequest:
    with transaction.atomic():
        claim = (
            ParticipantClaimRequest.objects.select_for_update()
            .select_related(
                "requested_by",
                "reviewed_by",
                "participant",
                "participant__session",
                "participant__session__group",
                "participant__participant_identity",
                "participant_identity",
                "participant_identity__group",
            )
            .get(pk=claim_id)
        )
        if claim.status != ParticipantClaimRequest.Status.PENDING:
            raise ClaimRequestError("Claim request is already reviewed.", 409)
        if claim.requested_by_id == reviewed_by.id:
            raise ClaimRequestError("Requester cannot reject their own claim request.", 403)

        claim.status = ParticipantClaimRequest.Status.REJECTED
        claim.reviewed_by = reviewed_by
        claim.reviewed_at = timezone.now()
        claim.review_comment = (review_comment or "").strip()
        claim.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_comment", "updated_at"])
        return claim
