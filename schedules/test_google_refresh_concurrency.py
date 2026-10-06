import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock
from unittest import skipUnless
from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount, SocialToken
from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase, override_settings

from schedules.google_tokens import get_google_access_token
from schedules.test_google_refresh_integrity import GoogleRefreshFixtures


# Isolated settings and credentials; never production secrets.
@override_settings(GOOGLE_OAUTH_CLIENT_ID="isolated-client", GOOGLE_OAUTH_CLIENT_SECRET="isolated-secret")  # nosec B106
@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用の競合検証")
class GoogleRefreshConcurrencyTests(GoogleRefreshFixtures, TransactionTestCase):
    def _refresh_result(self, backend_ids=None):
        close_old_connections()
        try:
            if backend_ids is not None:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    backend_ids.append(cursor.fetchone()[0])
            try:
                return {"token": get_google_access_token(self.user)}
            except ValueError as exc:
                return {"error": str(exc)}
        finally:
            close_old_connections()

    def _wait_for_update_locks(self, backend_ids, timeout=5):
        deadline = time.monotonic() + timeout
        while True:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_stat_clear_snapshot()")
                cursor.execute(
                    "SELECT count(*) FROM pg_stat_activity WHERE pid = ANY(%s) "
                    "AND wait_event_type = 'Lock' AND query LIKE 'UPDATE %%socialaccount_socialtoken%%'",
                    [backend_ids],
                )
                count = cursor.fetchone()[0]
            if count == 2 or time.monotonic() >= deadline:
                return count
            time.sleep(0.01)

    def test_lock_observation_has_a_bounded_timeout(self):
        self.assertEqual(self._wait_for_update_locks([], timeout=0.03), 0)

    def test_competing_refreshes_preserve_one_winner(self):
        barrier = Barrier(2)
        guard = Lock()
        candidates = []

        def credentials(**kwargs):
            with guard:
                candidate = self.credentials()
                index = len(candidates)
                candidate.token = f"competing-access-fixture-{index}"
                candidate.refresh_token = f"competing-secret-fixture-{index}"
                candidates.append(candidate)
            candidate.refresh.side_effect = lambda request: barrier.wait(timeout=10)
            return candidate

        with patch("schedules.google_tokens.Credentials", side_effect=credentials):
            with ThreadPoolExecutor(max_workers=2) as executor:
                backend_ids = []
                with transaction.atomic():
                    SocialToken.objects.select_for_update().get(pk=self.token.pk)
                    futures = [executor.submit(self._refresh_result, backend_ids) for _ in range(2)]
                    self.assertEqual(self._wait_for_update_locks(backend_ids), 2)
                results = [future.result(timeout=20) for future in futures]
        succeeded = [result["token"] for result in results if "token" in result]
        failed = [result["error"] for result in results if "error" in result]
        self.assertEqual(len(succeeded), 1)
        self.assertEqual(failed, [self.changed_message])
        self.token.refresh_from_db()
        winner = next(candidate for candidate in candidates if candidate.token == succeeded[0])
        self.assertEqual(self.token.token, winner.token)
        self.assertEqual(self.token.token_secret, winner.refresh_token)
        self.assertEqual(self.token.expires_at, winner.expiry)

    def test_completed_reconnect_or_disconnect_wins_over_inflight_refresh(self):
        replacement = SocialAccount.objects.create(
            user=self.user, provider="google", uid="concurrent-replacement-fixture"
        )
        for mode in ("same-account", "different-account", "disconnect"):
            with self.subTest(mode=mode):
                self.reset_token()
                entered = Event()
                released = Event()
                credentials = self.credentials()

                def pause(request):
                    entered.set()
                    self.assertTrue(released.wait(timeout=10), "isolated refresh fixture was not released")

                credentials.refresh.side_effect = pause
                with patch("schedules.google_tokens.Credentials", return_value=credentials):
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(self._refresh_result)
                        try:
                            self.assertTrue(entered.wait(timeout=10))
                            if mode == "disconnect":
                                SocialToken.objects.filter(pk=self.token.pk).delete()
                                expected = None
                            else:
                                expected = self.grant(self.account if mode == "same-account" else replacement)
                        finally:
                            released.set()
                        result = future.result(timeout=20)
                self.assertEqual(result, {"error": self.changed_message})
                if expected is None:
                    self.assertFalse(SocialToken.objects.filter(account__user=self.user).exists())
                else:
                    selected = SocialToken.objects.get(account__user=self.user)
                    self.assertEqual(selected.pk, expected.pk)
                    self.assertEqual(selected.token, expected.token)
                    self.assertEqual(selected.token_secret, expected.token_secret)
                    self.assertEqual(selected.expires_at, expected.expires_at)
