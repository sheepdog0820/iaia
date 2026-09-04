from unittest.mock import patch

import requests
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient

from schedules.services import YouTubeService


class GoogleUserInfoResilienceTests(SimpleTestCase):
    @patch("accounts.views.api_auth_views.requests.get")
    def test_userinfo_has_finite_timeout(self, get):
        get.return_value.status_code = 401

        response = APIClient().post("/api/auth/google/", {"access_token": "test-token"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(get.call_args.kwargs["timeout"], 10)

    @patch("accounts.views.api_auth_views.requests.get")
    def test_userinfo_timeout_is_retryable_without_exposing_exception(self, get):
        get.side_effect = requests.Timeout("sensitive-provider-detail")

        with self.assertLogs("accounts.views.api_auth_views", level="WARNING") as logs:
            response = APIClient().post("/api/auth/google/", {"access_token": "test-token"}, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "Googleとの通信に失敗しました。時間をおいて再度お試しください。"})
        self.assertNotIn("sensitive-provider-detail", "\n".join(logs.output))


@override_settings(YOUTUBE_API_KEY="test-youtube-key", YOUTUBE_API_BASE_URL="https://www.googleapis.com/youtube/v3")
class YouTubeResilienceTests(SimpleTestCase):
    @patch("schedules.services.requests.get")
    def test_video_lookup_has_finite_timeout(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = {"items": []}

        self.assertIsNone(YouTubeService.fetch_video_info("test-video"))
        self.assertEqual(get.call_args.kwargs["timeout"], 10)

    @patch("schedules.services.requests.get")
    def test_timeout_does_not_log_api_key_in_request_url(self, get):
        get.side_effect = requests.Timeout("https://www.googleapis.com/youtube/v3/videos?key=test-youtube-key")

        with self.assertLogs("schedules.services", level="WARNING") as logs:
            self.assertIsNone(YouTubeService.fetch_video_info("test-video"))

        self.assertNotIn("test-youtube-key", "\n".join(logs.output))
