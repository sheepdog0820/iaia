import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import HandoutNotification


logger = logging.getLogger(__name__)


@receiver(post_save, sender=HandoutNotification)
def broadcast_notification(sender, instance, created, **kwargs):
    if not created:
        return
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    payload = {
        'id': instance.pk,
        'notification_type': instance.notification_type,
        'message': instance.message,
        'created_at': instance.created_at.isoformat(),
        'is_read': instance.is_read,
    }
    unread_count = HandoutNotification.objects.filter(
        recipient=instance.recipient,
        is_read=False,
    ).count()
    try:
        async_to_sync(channel_layer.group_send)(
            f'notifications_user_{instance.recipient_id}',
            {
                'type': 'notification_created',
                'notification': payload,
                'unread_count': unread_count,
            },
        )
    except Exception:
        logger.exception('Unable to broadcast notification over Channels.')
