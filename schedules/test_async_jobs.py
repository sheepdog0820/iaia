from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from schedules.models import AsyncJob


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


class OpenApiEndpointTestCase(APITestCase):
    def test_schema_and_docs_are_available(self):
        schema = self.client.get("/api/schema/")
        docs = self.client.get("/api/docs/")

        self.assertEqual(schema.status_code, status.HTTP_200_OK)
        self.assertEqual(docs.status_code, status.HTTP_200_OK)
        self.assertIn(b"/api/jobs/{id}/", schema.content)
