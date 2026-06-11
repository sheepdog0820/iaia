from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import HandoutInfo, HandoutView


LEAF_TYPES = {
    'datetime_reached',
    'session_status',
    'handout_viewed',
    'participant_role',
    'player_slot',
}


def walk_conditions(node):
    if not node:
        return
    operator = node.get('operator')
    if operator:
        conditions = node.get('conditions')
        if operator not in {'all', 'any'} or not isinstance(conditions, list) or not conditions:
            raise ValidationError(
                'Condition groups require all/any and a non-empty conditions list.'
            )
        for child in conditions:
            if not isinstance(child, dict):
                raise ValidationError('Each release condition must be an object.')
            yield from walk_conditions(child)
        return
    if node.get('type') not in LEAF_TYPES or 'value' not in node:
        raise ValidationError('Invalid release condition.')
    yield node


def validate_release_conditions(conditions, session, handout=None):
    if not conditions:
        return
    dependencies = []
    for leaf in walk_conditions(conditions):
        condition_type = leaf['type']
        value = leaf['value']
        if condition_type == 'datetime_reached' and parse_datetime(str(value)) is None:
            raise ValidationError('datetime_reached requires an ISO-8601 datetime.')
        if condition_type == 'session_status' and value not in dict(session.STATUS_CHOICES):
            raise ValidationError('Unknown session status.')
        if condition_type == 'participant_role' and value not in {'gm', 'player'}:
            raise ValidationError('Unknown participant role.')
        if condition_type == 'player_slot':
            try:
                slot = int(value)
            except (TypeError, ValueError) as exc:
                raise ValidationError('Player slot must be between 1 and 4.') from exc
            if slot not in {1, 2, 3, 4}:
                raise ValidationError('Player slot must be between 1 and 4.')
        if condition_type == 'handout_viewed':
            try:
                dependency = HandoutInfo.objects.get(pk=value, session=session)
            except HandoutInfo.DoesNotExist as exc:
                raise ValidationError(
                    'Referenced handout does not exist in this session.'
                ) from exc
            if handout and dependency.pk == handout.pk:
                raise ValidationError('A handout cannot depend on itself.')
            dependencies.append(dependency)

    if not handout:
        return
    pending = list(dependencies)
    visited = set()
    while pending:
        dependency = pending.pop()
        if dependency.pk in visited:
            continue
        visited.add(dependency.pk)
        if dependency.pk == handout.pk:
            raise ValidationError('Circular handout dependency.')
        for leaf in walk_conditions(dependency.release_conditions):
            if leaf['type'] == 'handout_viewed':
                pending.extend(
                    HandoutInfo.objects.filter(pk=leaf['value'], session=session)
                )


def get_next_evaluation_at(conditions):
    values = []
    for leaf in walk_conditions(conditions):
        if leaf['type'] != 'datetime_reached':
            continue
        value = parse_datetime(str(leaf['value']))
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        if value > timezone.now():
            values.append(value)
    return min(values) if values else None


def evaluate_release_conditions(handout, now=None):
    now = now or timezone.now()

    def evaluate(node):
        if node.get('operator'):
            results = [evaluate(child) for child in node['conditions']]
            return all(results) if node['operator'] == 'all' else any(results)
        condition_type = node['type']
        value = node['value']
        if condition_type == 'datetime_reached':
            target = parse_datetime(str(value))
            if timezone.is_naive(target):
                target = timezone.make_aware(target, timezone.get_current_timezone())
            return now >= target
        if condition_type == 'session_status':
            return handout.session.status == value
        if condition_type == 'participant_role':
            return handout.participant.role == value
        if condition_type == 'player_slot':
            return handout.participant.player_slot == int(value)
        if condition_type == 'handout_viewed':
            return bool(handout.participant.user_id) and HandoutView.objects.filter(
                handout_id=value,
                user_id=handout.participant.user_id,
            ).exists()
        return False

    return bool(handout.release_conditions) and evaluate(handout.release_conditions)


def publish_handout(handout):
    if handout.release_status == HandoutInfo.ReleaseStatus.RELEASED:
        return False
    handout.is_secret = False
    handout.release_status = HandoutInfo.ReleaseStatus.RELEASED
    handout.released_at = timezone.now()
    handout.next_evaluation_at = None
    handout.save(update_fields=[
        'is_secret',
        'release_status',
        'released_at',
        'next_evaluation_at',
        'updated_at',
    ])
    from .notifications import HandoutNotificationService
    HandoutNotificationService().send_handout_published_notification(handout)
    if handout.session.group_id:
        from .tasks import queue_discord_event
        queue_discord_event(
            handout.session.group_id,
            'handout_released',
            {'content': f'Handout released: {handout.title}'},
            f'handout-released:{handout.pk}:{handout.released_at.isoformat()}',
        )
    return True
