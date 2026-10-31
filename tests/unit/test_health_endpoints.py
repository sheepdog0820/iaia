from unittest import mock

from django.test import TestCase, override_settings


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
