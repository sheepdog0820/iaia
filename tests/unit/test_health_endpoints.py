import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone
from itertools import count
from threading import Barrier, Lock
from unittest import mock
from uuid import uuid4

from django.core.cache.backends.locmem import LocMemCache
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from tableno.health_views import health_ready_view


@override_settings(DEBUG=False)
class HealthEndpointTests(TestCase):
    def test_live_endpoint_returns_200(self):
        response = self.client.get("/health/live/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["check"], "live")

    def test_ready_endpoint_returns_200(self):
        response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["check"], "ready")
        self.assertEqual(payload["checks"]["database"], "ok")
        self.assertEqual(payload["checks"]["cache"], "ok")

    @mock.patch("tableno.health_views._check_database", side_effect=RuntimeError("db unavailable"))
    def test_ready_endpoint_returns_503_when_dependency_fails(self, _mock_db_check):
        response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["status"], "degraded")
        self.assertIn("database", payload["errors"])
        self.assertEqual(payload["checks"]["database"], "error")

    def test_ready_endpoint_keeps_dependency_details_private(self):
        details = {
            "database": "private-db.example.invalid:5432 user=private-user password=synthetic-private-token",
            "cache": "rediss://private-user:synthetic-cache-token@private-cache.example.invalid:6379/1",
        }
        for failed in (("database",), ("cache",), ("database", "cache")):
            with self.subTest(failed=failed):
                with (
                    mock.patch("tableno.health_views._check_database") as database,
                    mock.patch("tableno.health_views._check_cache") as cache,
                ):
                    for name, checker in (("database", database), ("cache", cache)):
                        if name in failed:
                            checker.side_effect = RuntimeError(details[name])
                    response = self.client.get("/health/ready/")

                self.assertEqual(response.status_code, 503)
                payload = response.json()
                self.assertEqual(payload["status"], "degraded")
                self.assertEqual(payload["errors"], list(failed))
                self.assertEqual(
                    payload["checks"],
                    {name: "error" if name in failed else "ok" for name in ("database", "cache")},
                )
                database.assert_called_once_with()
                cache.assert_called_once_with()
                for detail in details.values():
                    self.assertNotContains(response, detail, status_code=503)
                for marker in (
                    "private-db",
                    "private-cache",
                    "private-user",
                    "synthetic-private-token",
                    "synthetic-cache-token",
                ):
                    self.assertNotContains(response, marker, status_code=503)

    def test_ready_endpoint_never_formats_dependency_exceptions(self):
        class UnrenderableError(Exception):
            def __str__(self):
                raise AssertionError("Dependency exception text must not be rendered")

        for path in ("/health/ready", "/health/ready/"):
            with self.subTest(path=path):
                with (
                    mock.patch("tableno.health_views._check_database", side_effect=UnrenderableError()),
                    mock.patch("tableno.health_views._check_cache") as cache,
                ):
                    response = self.client.get(path)

                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["checks"], {"database": "error", "cache": "ok"})
                cache.assert_called_once_with()

    @mock.patch("tableno.health_views.caches")
    def test_ready_endpoint_reports_failed_cache_round_trip(self, caches):
        cache = caches.__getitem__.return_value
        cache.get.return_value = "unexpected-synthetic-cache-value"

        response = self.client.get("/health/ready/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"], {"database": "ok", "cache": "error"})
        self.assertEqual(response.json()["errors"], ["cache"])
        cache.set.assert_called_once()
        cache.get.assert_called_once()


class HealthCacheProbeIsolationTests(SimpleTestCase):
    def setUp(self):
        self.backend = LocMemCache("isolated-health-probe-" + uuid4().hex, {})
        self.addCleanup(self.backend.clear)

    def test_concurrent_readiness_checks_do_not_interfere(self):
        barrier = Barrier(2, timeout=5)
        clock = count()
        clock_lock = Lock()
        written_keys = []
        backend = self.backend
        backend.set("unrelated-fixture-key", "unchanged")

        class CoordinatedCache:
            def set(self, key, value, timeout):
                backend.set(key, value, timeout=timeout)
                written_keys.append(key)
                barrier.wait()

            def get(self, key):
                return backend.get(key)

            def delete(self, key):
                return backend.delete(key)

        def now():
            with clock_lock:
                offset = next(clock)
            return datetime(2026, 10, 31, tzinfo=datetime_timezone.utc) + timedelta(microseconds=offset)

        def request():
            response = health_ready_view(RequestFactory().get("/health/ready/"))
            return response.status_code, json.loads(response.content)["checks"]

        with (
            mock.patch("tableno.health_views.caches", {"default": CoordinatedCache()}),
            mock.patch("tableno.health_views._check_database"),
            mock.patch("tableno.health_views.timezone.now", side_effect=now),
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            futures = [pool.submit(request) for _ in range(2)]
            results = [future.result(timeout=10) for future in futures]

        self.assertEqual(results, [(200, {"database": "ok", "cache": "ok"})] * 2)
        self.assertEqual(len(set(written_keys)), 2)
        self.assertTrue(all(self.backend.get(key) is None for key in written_keys))
        self.assertEqual(self.backend.get("unrelated-fixture-key"), "unchanged")

    def test_failed_round_trip_cleans_only_its_probe_key(self):
        self.backend.set("unrelated-fixture-key", "unchanged")
        cache = mock.Mock(wraps=self.backend)
        cache.get.return_value = "mismatched-fixture-value"
        with (
            mock.patch("tableno.health_views.caches", {"default": cache}),
            mock.patch("tableno.health_views._check_database"),
        ):
            response = health_ready_view(RequestFactory().get("/health/ready/"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(json.loads(response.content)["checks"], {"database": "ok", "cache": "error"})
        key = cache.set.call_args.args[0]
        self.assertIsNone(self.backend.get(key))
        self.assertEqual(self.backend.get("unrelated-fixture-key"), "unchanged")
