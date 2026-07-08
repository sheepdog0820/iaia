from . import session_permissions
from .models import HandoutInfo, SessionParticipant, SessionParticipantRole

TEMPLATE_PLACEHOLDER_PREFIX = "[template]"


def build_template_placeholder_name(slot=None, index=None):
    if slot:
        return f"{TEMPLATE_PLACEHOLDER_PREFIX} player-{slot}"
    suffix = index or 1
    return f"{TEMPLATE_PLACEHOLDER_PREFIX} recipient-{suffix}"


def is_template_placeholder_name(name):
    if not isinstance(name, str):
        return False
    if not name.startswith(f"{TEMPLATE_PLACEHOLDER_PREFIX} "):
        return False
    suffix = name[len(TEMPLATE_PLACEHOLDER_PREFIX) + 1 :]
    return suffix.startswith("player-") or suffix.startswith("recipient-")


def clone_scenario_handouts_to_session(scenario, session):
    if scenario is None or session is None:
        return

    slot_placeholders = {}
    anonymous_index = 0

    for handout_template in scenario.handout_templates.order_by("order", "id"):
        assigned_slot = handout_template.assigned_player_slot
        if assigned_slot:
            participant = slot_placeholders.get(assigned_slot)
            if participant is None:
                participant = session_permissions.create_participant(
                    session=session,
                    user=None,
                    guest_name=build_template_placeholder_name(slot=assigned_slot),
                    roles=[SessionParticipantRole.Role.PLAYER],
                    player_slot=None,
                )
                slot_placeholders[assigned_slot] = participant
        else:
            anonymous_index += 1
            participant = session_permissions.create_participant(
                session=session,
                user=None,
                guest_name=build_template_placeholder_name(index=anonymous_index),
                roles=[SessionParticipantRole.Role.PLAYER],
                player_slot=None,
            )

        recommended_skills = handout_template.recommended_skills
        skill_names = [
            skill.name for skill in handout_template.recommended_skill_items.order_by("order", "id") if skill.name
        ]
        if skill_names:
            recommended_skills = ", ".join(skill_names)

        HandoutInfo.objects.create(
            session=session,
            participant=participant,
            code=handout_template.code,
            name=handout_template.name or handout_template.title,
            title=handout_template.name or handout_template.title,
            content=handout_template.content,
            recommended_skills=recommended_skills,
            is_secret=handout_template.is_secret,
            handout_number=handout_template.handout_number,
            assigned_player_slot=assigned_slot,
            order=handout_template.order,
        )


def bind_slot_handouts_to_participant(participant):
    session = getattr(participant, "session", None)
    if session is None:
        return
    _rebind_slot_handouts_for_session(session)


def _rebind_slot_handouts_for_session(session):
    handouts = list(
        HandoutInfo.objects.select_related("participant")
        .filter(
            session=session,
            assigned_player_slot__isnull=False,
        )
        .order_by("assigned_player_slot", "id")
    )
    if not handouts:
        _cleanup_unused_template_placeholders(session)
        return

    slots = sorted({handout.assigned_player_slot for handout in handouts if handout.assigned_player_slot is not None})
    participants_by_slot = {
        participant.player_slot: participant
        for participant in SessionParticipant.objects.filter(
            session=session,
            participant_roles__role=SessionParticipantRole.Role.PLAYER,
            player_slot__in=slots,
        ).order_by("id")
    }
    placeholders_by_name = {
        participant.guest_name: participant
        for participant in SessionParticipant.objects.filter(
            session=session,
            user__isnull=True,
            participant_roles__role=SessionParticipantRole.Role.PLAYER,
            guest_name__startswith=TEMPLATE_PLACEHOLDER_PREFIX,
        )
        if is_template_placeholder_name(participant.guest_name)
    }

    updated_handouts = []
    for handout in handouts:
        assigned_slot = handout.assigned_player_slot
        target_participant = participants_by_slot.get(assigned_slot)
        if target_participant is None:
            placeholder_name = build_template_placeholder_name(slot=assigned_slot)
            target_participant = placeholders_by_name.get(placeholder_name)
            if target_participant is None:
                target_participant = session_permissions.create_participant(
                    session=session,
                    user=None,
                    guest_name=placeholder_name,
                    roles=[SessionParticipantRole.Role.PLAYER],
                    player_slot=None,
                )
                placeholders_by_name[placeholder_name] = target_participant

        if handout.participant_id != target_participant.id:
            handout.participant = target_participant
            updated_handouts.append(handout)

    if updated_handouts:
        HandoutInfo.objects.bulk_update(updated_handouts, ["participant"])

    _cleanup_unused_template_placeholders(session)


def _cleanup_unused_template_placeholders(session):
    stale_placeholders = [
        participant
        for participant in SessionParticipant.objects.filter(
            session=session,
            user__isnull=True,
            participant_roles__role=SessionParticipantRole.Role.PLAYER,
            handouts__isnull=True,
            guest_name__startswith=TEMPLATE_PLACEHOLDER_PREFIX,
        )
        if is_template_placeholder_name(participant.guest_name)
    ]
    for participant in stale_placeholders:
        participant.delete()
