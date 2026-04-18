import os

from django.core.files.base import ContentFile

from .models import HandoutInfo, SessionImage, SessionParticipant


TEMPLATE_PLACEHOLDER_PREFIX = '[template]'


def build_template_placeholder_name(slot=None, index=None):
    if slot:
        return f'{TEMPLATE_PLACEHOLDER_PREFIX} player-{slot}'
    suffix = index or 1
    return f'{TEMPLATE_PLACEHOLDER_PREFIX} recipient-{suffix}'


def is_template_placeholder_name(name):
    if not isinstance(name, str):
        return False
    if not name.startswith(f'{TEMPLATE_PLACEHOLDER_PREFIX} '):
        return False
    suffix = name[len(TEMPLATE_PLACEHOLDER_PREFIX) + 1:]
    return suffix.startswith('player-') or suffix.startswith('recipient-')


def clone_template_to_session(template, session, uploaded_by=None):
    if template is None or session is None:
        return

    _clone_template_images(template, session, uploaded_by=uploaded_by)
    if template.copy_handouts_to_session:
        _clone_template_handouts(template, session)


def bind_slot_handouts_to_participant(participant):
    session = getattr(participant, 'session', None)
    if session is None:
        return
    _rebind_slot_handouts_for_session(session)


def _clone_template_images(template, session, uploaded_by=None):
    template_images = template.image_templates.order_by('order', 'id')
    for template_image in template_images:
        image = SessionImage(
            session=session,
            title=template_image.title,
            description=template_image.description,
            uploaded_by=uploaded_by or session.gm,
            order=template_image.order,
        )
        if template_image.image:
            template_image.image.open('rb')
            try:
                image_bytes = template_image.image.read()
            finally:
                template_image.image.close()
            filename = os.path.basename(template_image.image.name or 'template-image')
            image.image.save(filename, ContentFile(image_bytes), save=False)
        image.save()


def _clone_template_handouts(template, session):
    slot_placeholders = {}
    anonymous_index = 0

    for handout_template in template.handout_templates.order_by('handout_number', 'id'):
        assigned_slot = handout_template.assigned_player_slot
        if assigned_slot:
            participant = slot_placeholders.get(assigned_slot)
            if participant is None:
                participant = SessionParticipant.objects.create(
                    session=session,
                    user=None,
                    guest_name=build_template_placeholder_name(slot=assigned_slot),
                    role='player',
                    player_slot=None,
                )
                slot_placeholders[assigned_slot] = participant
        else:
            anonymous_index += 1
            participant = SessionParticipant.objects.create(
                session=session,
                user=None,
                guest_name=build_template_placeholder_name(index=anonymous_index),
                role='player',
                player_slot=None,
            )

        HandoutInfo.objects.create(
            session=session,
            participant=participant,
            title=handout_template.title,
            content=handout_template.content,
            recommended_skills=handout_template.recommended_skills,
            is_secret=handout_template.is_secret,
            handout_number=handout_template.handout_number,
            assigned_player_slot=assigned_slot,
        )


def _rebind_slot_handouts_for_session(session):
    handouts = list(
        HandoutInfo.objects.select_related('participant').filter(
            session=session,
            assigned_player_slot__isnull=False,
        ).order_by('assigned_player_slot', 'id')
    )
    if not handouts:
        _cleanup_unused_template_placeholders(session)
        return

    slots = sorted({
        handout.assigned_player_slot
        for handout in handouts
        if handout.assigned_player_slot is not None
    })
    participants_by_slot = {
        participant.player_slot: participant
        for participant in SessionParticipant.objects.filter(
            session=session,
            role='player',
            player_slot__in=slots,
        ).order_by('id')
    }
    placeholders_by_name = {
        participant.guest_name: participant
        for participant in SessionParticipant.objects.filter(
            session=session,
            user__isnull=True,
            role='player',
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
                target_participant = SessionParticipant.objects.create(
                    session=session,
                    user=None,
                    guest_name=placeholder_name,
                    role='player',
                    player_slot=None,
                )
                placeholders_by_name[placeholder_name] = target_participant

        if handout.participant_id != target_participant.id:
            handout.participant = target_participant
            updated_handouts.append(handout)

    if updated_handouts:
        HandoutInfo.objects.bulk_update(updated_handouts, ['participant'])

    _cleanup_unused_template_placeholders(session)


def _cleanup_unused_template_placeholders(session):
    stale_placeholders = [
        participant
        for participant in SessionParticipant.objects.filter(
            session=session,
            user__isnull=True,
            role='player',
            handouts__isnull=True,
            guest_name__startswith=TEMPLATE_PLACEHOLDER_PREFIX,
        )
        if is_template_placeholder_name(participant.guest_name)
    ]
    for participant in stale_placeholders:
        participant.delete()
