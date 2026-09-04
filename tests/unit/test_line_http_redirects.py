from email.message import Message
from io import BytesIO
from unittest.mock import patch
from urllib import request
from urllib.error import HTTPError
from urllib.response import addinfourl

from django.test import SimpleTestCase, override_settings

from support.services import fetch_line_content, push_to_line, reply_to_line


@override_settings(LINE_CHANNEL_ACCESS_TOKEN="local-test-token", LINE_API_TIMEOUT_SECONDS=3)
class LineHttpRedirectTests(SimpleTestCase):
    def test_direct_success_preserves_authentication_timeout_and_content(self):
        for operation, method in (
            (lambda: reply_to_line("reply-test", "テスト"), "POST"),
            (lambda: push_to_line("user-test", "テスト"), "POST"),
            (lambda: fetch_line_content("message-test"), "GET"),
        ):
            with self.subTest(method=method), patch.object(request, "build_opener") as factory:
                response = factory.return_value.open.return_value.__enter__.return_value
                response.status = 200
                response.headers.get.return_value = "5"
                response.headers.get_content_type.return_value = "image/jpeg"
                response.read.return_value = b"image"
                result = operation()
                args, kwargs = factory.return_value.open.call_args
                self.assertEqual(kwargs["timeout"], 3)
                self.assertEqual(args[0].get_method(), method)
                self.assertEqual(args[0].get_header("Authorization"), "Bearer local-test-token")
                if method == "GET":
                    self.assertEqual(result, (b"image", "image/jpeg"))
                else:
                    self.assertIsNone(result)

    def test_authenticated_requests_do_not_follow_redirects(self):
        real_build_opener = request.build_opener
        for operation in (
            lambda: reply_to_line("reply-test", "テスト"),
            lambda: push_to_line("user-test", "テスト"),
            lambda: fetch_line_content("message-test"),
        ):
            for status in (301, 302, 303, 307, 308):
                with self.subTest(operation=operation, status=status):
                    seen = []

                    class FakeHTTPS(request.HTTPSHandler):
                        def https_open(self, req):
                            seen.append(req.full_url)
                            headers = Message()
                            headers["Content-Type"] = "image/jpeg"
                            if len(seen) == 1:
                                headers["Location"] = "https://redirect-target.invalid/capture"
                            response = addinfourl(
                                BytesIO(b"image"), headers, req.full_url, status if len(seen) == 1 else 200
                            )
                            response.msg = "test response"
                            return response

                    def fake_opener(*handlers):
                        return real_build_opener(*handlers, FakeHTTPS())

                    # All HTTPS is handled in memory; no external requests are sent.
                    with (
                        patch.object(request, "build_opener", side_effect=fake_opener),
                        patch.object(request, "_opener", None),
                    ):
                        with self.assertRaises(HTTPError):
                            operation()
                    self.assertEqual(len(seen), 1, "認証付きリクエストを転送先へ送らないこと")
