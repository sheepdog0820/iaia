from datetime import timedelta

from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import CharacterSheet

from .models import AsyncJob, GoogleCalendarSync
from .tasks import queue_google_calendar_sync, queue_google_sheet_export


SHEET_COLUMNS = [
    'id', 'name', 'edition', 'age', 'occupation',
    'STR', 'CON', 'POW', 'DEX', 'APP', 'SIZ', 'INT', 'EDU',
    'HP', 'MP', 'SAN',
]


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


class AsyncJobListView(generics.ListAPIView):
    serializer_class = AsyncJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = AsyncJob.objects.filter(owner=self.request.user)
        job_type = self.request.query_params.get('job_type')
        if job_type:
            queryset = queryset.filter(job_type=job_type)
        job_status = self.request.query_params.get('status')
        if job_status:
            queryset = queryset.filter(status=job_status)
        return queryset[:50]


def _sheet_export_values(user, payload):
    characters = CharacterSheet.objects.filter(user=user)
    character_ids = payload.get('character_ids')
    if character_ids:
        characters = characters.filter(pk__in=character_ids)
    rows = []
    for character in characters.order_by('id'):
        rows.append([
            character.pk, character.name, character.edition, character.age,
            character.occupation, character.str_value, character.con_value,
            character.pow_value, character.dex_value, character.app_value,
            character.siz_value, character.int_value, character.edu_value,
            character.hit_points_current, character.magic_points_current,
            character.sanity_current,
        ])
    return [SHEET_COLUMNS] + rows


class AsyncJobRetryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        job = AsyncJob.objects.filter(owner=request.user, pk=pk).first()
        if not job:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if job.status != AsyncJob.Status.FAILED:
            return Response(
                {'detail': 'Only failed jobs can be retried.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if job.job_type == 'google_calendar_sync':
            return self._retry_google_calendar_sync(request, job)
        if job.job_type == 'google_sheets_export':
            return self._retry_google_sheets_export(request, job)
        return Response(
            {'detail': f'Retry is not supported for {job.job_type}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _retry_google_calendar_sync(self, request, job):
        sync_id = job.payload.get('sync_id')
        sync = GoogleCalendarSync.objects.filter(
            pk=sync_id,
            user=request.user,
        ).first()
        if not sync:
            return Response(
                {'detail': 'The original Google Calendar sync record was not found.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sync.status = GoogleCalendarSync.Status.PENDING
        sync.last_error = ''
        sync.save(update_fields=['status', 'last_error', 'updated_at'])
        retry_job = AsyncJob.objects.create(
            owner=request.user,
            job_type=job.job_type,
            payload={'sync_id': sync.pk, 'retry_of': str(job.pk)},
            expires_at=timezone.now() + timedelta(days=7),
        )
        queued = queue_google_calendar_sync(sync.pk, str(retry_job.pk))
        if not queued:
            retry_job.mark_failed('Background task broker is unavailable.')
            sync.status = GoogleCalendarSync.Status.FAILED
            sync.last_error = 'Background task broker is unavailable.'
            sync.save(update_fields=['status', 'last_error', 'updated_at'])
        return Response(
            {
                'job_id': retry_job.pk,
                'queued': queued,
                'retry_of': job.pk,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    def _retry_google_sheets_export(self, request, job):
        spreadsheet_id = job.payload.get('spreadsheet_id')
        if not spreadsheet_id:
            return Response(
                {'detail': 'The original Google Sheets export is missing spreadsheet_id.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        range_name = job.payload.get('range', 'Characters!A1')
        retry_job = AsyncJob.objects.create(
            owner=request.user,
            job_type=job.job_type,
            payload={
                'spreadsheet_id': spreadsheet_id,
                'range': range_name,
                'character_ids': job.payload.get('character_ids', []),
                'retry_of': str(job.pk),
            },
            expires_at=timezone.now() + timedelta(days=7),
        )
        queued = queue_google_sheet_export(
            str(retry_job.pk),
            request.user.pk,
            spreadsheet_id,
            range_name,
            _sheet_export_values(request.user, retry_job.payload),
        )
        if not queued:
            retry_job.mark_failed('Background task broker is unavailable.')
        return Response(
            {
                'job_id': retry_job.pk,
                'queued': queued,
                'retry_of': job.pk,
            },
            status=status.HTTP_202_ACCEPTED,
        )
