import uuid
from contextlib import ExitStack
from unittest.mock import patch

from django.db import transaction
from django.test import TestCase

from schedules.models import AsyncJob, GoogleCalendarSync
from schedules.test_google_job_start_claim import GoogleJobStartFixtures


class GoogleDispatchIdentityTest(GoogleJobStartFixtures, TestCase):
    def _prepare(self, mode):
        if mode == "calendar":
            self.sync.external_event_id = ""
            self.sync.save(update_fields=["external_event_id"])
        job, args = self._queue(mode)
        return job, args, self._worker(mode)

    def _refuse(self, stack, worker, args, no_queries=False):
        jobs = list(AsyncJob.objects.order_by("pk").values())
        syncs = list(GoogleCalendarSync.objects.order_by("pk").values())
        sends, token = self._sends(stack)
        retry = stack.enter_context(patch.object(worker, "retry"))
        if no_queries:
            with self.assertNumQueries(0):
                self.assertEqual(worker.run(*args), "invalid-job")
        else:
            self.assertEqual(worker.run(*args), "invalid-job")
        token.assert_not_called()
        retry.assert_not_called()
        for send in sends.values():
            send.assert_not_called()
        self.assertEqual(list(AsyncJob.objects.order_by("pk").values()), jobs)
        self.assertEqual(list(GoogleCalendarSync.objects.order_by("pk").values()), syncs)

    def test_malformed_job_identity_is_rejected_before_orm_or_authentication(self):
        invalid = (None, True, False, 1, 1.5, [], {}, (), b"private", "", "private", "1", "x" * 1000, "\ud800")
        for mode in ("sheets", "calendar"):
            for value in invalid:
                with self.subTest(mode=mode, value=repr(value)), transaction.atomic(), ExitStack() as stack:
                    _, args, worker = self._prepare(mode)
                    changed = (value, *args[1:]) if mode == "sheets" else (args[0], value)
                    self._refuse(stack, worker, changed, no_queries=True)

    def test_sheets_owner_must_be_strict_positive_signed_int_not_an_alias(self):
        invalid = (
            None,
            True,
            False,
            0,
            -1,
            2**63,
            2**80,
            [],
            {},
            (),
            "private",
            float("nan"),
            float("inf"),
            str(self.user.pk),
            float(self.user.pk),
        )
        for value in invalid:
            with self.subTest(value=repr(value)), transaction.atomic(), ExitStack() as stack:
                _, args, worker = self._prepare("sheets")
                self._refuse(stack, worker, (args[0], value, *args[2:]), no_queries=True)

    def test_normal_uuid_representations_deliver_real_api_job_with_existing_owner(self):
        for mode in ("sheets", "calendar"):
            for form in ("uuid", "canonical", "upper", "hex", "braces", "urn"):
                with self.subTest(mode=mode, form=form), transaction.atomic(), ExitStack() as stack:
                    job, args, worker = self._prepare(mode)
                    value = {
                        "uuid": job.pk,
                        "canonical": str(job.pk),
                        "upper": str(job.pk).upper(),
                        "hex": job.pk.hex,
                        "braces": "{" + str(job.pk) + "}",
                        "urn": job.pk.urn,
                    }[form]
                    changed = (value, *args[1:]) if mode == "sheets" else (args[0], value)
                    sends, _ = self._sends(stack)
                    self.assertEqual(worker.run(*changed), "exported" if mode == "sheets" else "synced")
                    self.assertEqual(sum(send.call_count for send in sends.values()), 1)
                    job.refresh_from_db()
                    self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)

    def test_missing_valid_uuid_does_not_use_or_change_another_job(self):
        for mode in ("sheets", "calendar"):
            for value in (uuid.UUID(int=0), str(uuid.uuid4()), uuid.UUID(int=2**128 - 1)):
                with self.subTest(mode=mode, value=repr(value)), transaction.atomic(), ExitStack() as stack:
                    _, args, worker = self._prepare(mode)
                    changed = (value, *args[1:]) if mode == "sheets" else (args[0], value)
                    self._refuse(stack, worker, changed)
