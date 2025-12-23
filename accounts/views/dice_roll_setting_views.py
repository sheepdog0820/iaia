from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..character_models import CharacterDiceRollSetting
from ..serializers import CharacterDiceRollSettingSerializer


class DiceRollSettingViewSet(viewsets.ModelViewSet):
    """Dice roll setting API."""
    serializer_class = CharacterDiceRollSettingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CharacterDiceRollSetting.objects.filter(
            user=self.request.user
        ).order_by('-is_default', 'setting_name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, pk=None):
        setting = self.get_object()
        setting.set_as_default()
        serializer = self.get_serializer(setting)
        return Response(serializer.data)
