from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import SessionTemplate
from .serializers import SessionTemplateSerializer


class SessionTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = SessionTemplateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return (
            SessionTemplate.objects.filter(owner=self.request.user)
            .select_related('group', 'scenario')
            .order_by('name', 'id')
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

