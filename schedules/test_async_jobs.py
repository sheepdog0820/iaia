from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Group
from schedules.models import AsyncJob, GoogleCalendarSync, TRPGSession


class AsyncJobApiTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="job-owner",
            email="job-owner@example.com",
            password="testpass123",
        )
        self.other = get_user_model().objects.create_user(
            username="other-owner",
            email="other-owner@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_owner_can_read_job_state(self):
        job = AsyncJob.objects.create(
            owner=self.user,
            job_type="statistics_export",
            expires_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.get(reverse("async-job-detail", kwargs={"pk": job.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], AsyncJob.Status.QUEUED)
        self.assertEqual(response.data["progress"], 0)

    def test_owner_can_list_and_filter_jobs(self):
        AsyncJob.objects.create(
            owner=self.user,
            job_type="google_calendar_sync",
            expires_at=timezone.now() + timedelta(days=1),
        )
        AsyncJob.objects.create(
            owner=self.user,
            job_type="google_sheets_export",
            expires_at=timezone.now() + timedelta(days=1),
        )
        AsyncJob.objects.create(
            owner=self.other,
            job_type="google_calendar_sync",
            expires_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.get(
            reverse("async-job-list"),
            {"job_type": "google_calendar_sync"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["job_type"], "google_calendar_sync")

    def test_other_user_cannot_read_job(self):
        job = AsyncJob.objects.create(
            owner=self.other,
            job_type="statistics_export",
            expires_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.get(reverse("async-job-detail", kwargs={"pk": job.pk}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_job_state_transitions_store_result_and_error(self):
        job = AsyncJob.objects.create(
            owner=self.user,
            job_type="statistics_export",
            expires_at=timezone.now() + timedelta(days=1),
        )

        job.mark_running(progress=10)
        job.mark_succeeded(result={"download_url": "/download/result"})
        job.refresh_from_db()

        self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)
        self.assertEqual(job.progress, 100)
        self.assertEqual(job.result["download_url"], "/download/result")
        self.assertIsNotNone(job.finished_at)

        failed = AsyncJob.objects.create(
            owner=self.user,
            job_type="discord_notification",
            expires_at=timezone.now() + timedelta(days=1),
        )
        failed.mark_failed("timeout")
        failed.refresh_from_db()
        self.assertEqual(failed.status, AsyncJob.Status.FAILED)
        self.assertEqual(failed.error, "timeout")

    def test_retry_rejects_non_failed_job(self):
        job = AsyncJob.objects.create(
            owner=self.user,
            job_type="google_sheets_export",
            expires_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.post(reverse("async-job-retry", kwargs={"pk": job.pk}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("schedules.job_views.queue_google_calendar_sync", return_value=True)
    def test_retry_failed_google_calendar_sync_job(self, queue_sync):
        group = Group.objects.create(name="Retry Group", created_by=self.user)
        session = TRPGSession.objects.create(
            title="Retry Session",
            gm=self.user,
            group=group,
            date=timezone.now() + timedelta(days=1),
        )
        sync = GoogleCalendarSync.objects.create(
            user=self.user,
            session=session,
            status=GoogleCalendarSync.Status.FAILED,
            last_error="timeout",
        )
        job = AsyncJob.objects.create(
            owner=self.user,
            job_type="google_calendar_sync",
            status=AsyncJob.Status.FAILED,
            payload={"sync_id": sync.pk},
            error="timeout",
            expires_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.post(reverse("async-job-retry", kwargs={"pk": job.pk}))

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        retry_job = AsyncJob.objects.get(pk=response.data["job_id"])
        self.assertEqual(retry_job.payload["retry_of"], str(job.pk))
        sync.refresh_from_db()
        self.assertEqual(sync.status, GoogleCalendarSync.Status.PENDING)
        queue_sync.assert_called_once_with(sync.pk, str(retry_job.pk))

    @patch("schedules.job_views.queue_google_sheet_export", return_value=True)
    def test_retry_failed_google_sheets_export_job(self, queue_export):
        job = AsyncJob.objects.create(
            owner=self.user,
            job_type="google_sheets_export",
            status=AsyncJob.Status.FAILED,
            payload={"spreadsheet_id": "sheet-1", "range": "Characters!A1"},
            error="timeout",
            expires_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.post(reverse("async-job-retry", kwargs={"pk": job.pk}))

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        retry_job = AsyncJob.objects.get(pk=response.data["job_id"])
        self.assertEqual(retry_job.payload["retry_of"], str(job.pk))
        queue_export.assert_called_once()


class OpenApiEndpointTestCase(APITestCase):
    def test_schema_and_docs_are_available(self):
        schema = self.client.get("/api/schema/")
        docs = self.client.get("/api/docs/")

        self.assertEqual(schema.status_code, status.HTTP_200_OK)
        self.assertEqual(docs.status_code, status.HTTP_200_OK)
        self.assertIn(b"/api/jobs/", schema.content)
        self.assertIn(b"/api/jobs/{id}/", schema.content)
