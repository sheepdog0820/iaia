from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Group, GroupDiscordSettings, GroupMembership


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
