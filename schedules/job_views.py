from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from .models import AsyncJob


class AsyncJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsyncJob
        fields = [
            'id',
            'job_type',
            'status',
            'progress',
            'result',
            'error',
            'created_at',
            'started_at',
            'finished_at',
            'expires_at',
        ]
        read_only_fields = fields


class AsyncJobDetailView(generics.RetrieveAPIView):
    serializer_class = AsyncJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AsyncJob.objects.filter(owner=self.request.user)
