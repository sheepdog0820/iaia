from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from schedules.tasks import _broker_available, send_discord_webhook

from .models import DiscordDelivery, Group, GroupDiscordSettings, GroupMembership


class GroupDiscordSettingsSerializer(serializers.ModelSerializer):
    webhook_url = serializers.URLField(write_only=True, required=False, allow_blank=True)
    configured = serializers.BooleanField(source='is_configured', read_only=True)

    class Meta:
        model = GroupDiscordSettings
        fields = ['enabled', 'event_types', 'webhook_url', 'configured', 'disabled_at']
        read_only_fields = ['configured', 'disabled_at']

    def validate_event_types(self, value):
        allowed = {
            'session_created',
            'session_updated',
            'session_cancelled',
            'handout_released',
        }
        unknown = set(value) - allowed
        if unknown:
            raise serializers.ValidationError(f'Unknown event types: {sorted(unknown)}')
        return value

    def update(self, instance, validated_data):
        webhook_url = validated_data.pop('webhook_url', None)
        if webhook_url is not None:
            instance.set_webhook_url(webhook_url)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if instance.enabled and not instance.is_configured:
            raise serializers.ValidationError({'enabled': 'A webhook URL is required.'})
        instance.failure_count = 0
        instance.disabled_at = None
        instance.save()
        return instance


class GroupDiscordSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_settings(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id)
        is_admin = (
            group.created_by_id == request.user.id
            or GroupMembership.objects.filter(
                group=group, user=request.user, role='admin'
            ).exists()
        )
        if not is_admin:
            self.permission_denied(request)
        return GroupDiscordSettings.objects.get_or_create(group=group)[0]

    def get(self, request, group_id):
        settings_obj = self._get_settings(request, group_id)
        return Response(GroupDiscordSettingsSerializer(settings_obj).data)

    def put(self, request, group_id):
        settings_obj = self._get_settings(request, group_id)
        serializer = GroupDiscordSettingsSerializer(settings_obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class DiscordDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscordDelivery
        fields = [
            'id',
            'event_type',
            'status',
            'attempts',
            'last_error',
            'created_at',
            'sent_at',
            'payload',
            'idempotency_key',
        ]
        read_only_fields = fields


class DiscordDeliveryRetryResponseSerializer(serializers.Serializer):
    delivery_id = serializers.IntegerField(read_only=True)
    queued = serializers.BooleanField(read_only=True)


def _is_group_admin(user, group):
    return (
        group.created_by_id == user.id
        or GroupMembership.objects.filter(
            group=group, user=user, role='admin'
        ).exists()
    )


def _get_admin_group(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    if not _is_group_admin(request.user, group):
        raise PermissionError
    return group


class GroupDiscordDeliveryListView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_group(self, request, group_id):
        try:
            return _get_admin_group(request, group_id)
        except PermissionError:
            self.permission_denied(request)

    @extend_schema(
        responses=DiscordDeliverySerializer(many=True),
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter('event_type', OpenApiTypes.STR, OpenApiParameter.QUERY),
        ],
    )
    def get(self, request, group_id):
        group = self._get_group(request, group_id)
        settings_obj = GroupDiscordSettings.objects.filter(group=group).first()
        if not settings_obj:
            return Response([])
        queryset = DiscordDelivery.objects.filter(settings=settings_obj)
        delivery_status = request.query_params.get('status')
        if delivery_status:
            queryset = queryset.filter(status=delivery_status)
        event_type = request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        deliveries = queryset.order_by('-created_at')[:50]
        return Response(DiscordDeliverySerializer(deliveries, many=True).data)


class GroupDiscordDeliveryRetryView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_delivery(self, request, group_id, delivery_id):
        group = get_object_or_404(Group, pk=group_id)
        if not _is_group_admin(request.user, group):
            self.permission_denied(request)
        settings_obj = GroupDiscordSettings.objects.filter(group=group).first()
        return get_object_or_404(
            DiscordDelivery.objects.select_related('settings', 'settings__group'),
            pk=delivery_id,
            settings=settings_obj,
        )

    @extend_schema(responses={202: DiscordDeliveryRetryResponseSerializer})
    def post(self, request, group_id, delivery_id):
        delivery = self._get_delivery(request, group_id, delivery_id)
        settings_obj = delivery.settings
        if delivery.status != DiscordDelivery.Status.FAILED:
            return Response(
                {'detail': 'Only failed Discord deliveries can be retried.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not settings_obj.enabled:
            return Response(
                {'detail': 'Discord notifications are disabled for this group.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not settings_obj.is_configured:
            return Response(
                {'detail': 'A Discord webhook URL is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if delivery.event_type not in settings_obj.event_types:
            return Response(
                {'detail': 'This Discord event type is disabled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not _broker_available():
            delivery.last_error = 'Background task broker is unavailable.'
            delivery.save(update_fields=['last_error'])
            return Response(
                {'delivery_id': delivery.pk, 'queued': False},
                status=status.HTTP_202_ACCEPTED,
            )

        delivery.status = DiscordDelivery.Status.PENDING
        delivery.last_error = ''
        delivery.save(update_fields=['status', 'last_error'])
        send_discord_webhook.delay(
            group_id,
            delivery.event_type,
            delivery.payload,
            delivery.idempotency_key,
        )
        return Response(
            {'delivery_id': delivery.pk, 'queued': True},
            status=status.HTTP_202_ACCEPTED,
        )
