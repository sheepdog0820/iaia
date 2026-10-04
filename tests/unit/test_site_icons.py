import io
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from PIL import Image


class SiteIconTests(TestCase):
    @override_settings(MIDDLEWARE=[*settings.MIDDLEWARE, "django.contrib.auth.middleware.LoginRequiredMiddleware"])
    def test_anonymous_favicon_is_delivered_from_app_origin(self):
        with override_settings(STATIC_URL="https://example.invalid/static/"):
            with self.assertNumQueries(0):
                response = self.client.get("/favicon.ico")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "image/x-icon")
                self.assertIn("public", response["Cache-Control"])
                data = b"".join(response.streaming_content)
                response.close()
            with Image.open(io.BytesIO(data)) as icon:
                self.assertEqual(icon.format, "ICO")
                self.assertEqual(icon.ico.sizes(), {(16, 16), (32, 32), (48, 48)})

    def test_png_icons_are_valid_and_have_declared_dimensions(self):
        for filename, size in (("favicon-32-v1.png", 32), ("apple-touch-icon-v1.png", 180)):
            with self.subTest(filename=filename):
                response = self.client.get(reverse("public_icon", args=[filename]))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "image/png")
                data = b"".join(response.streaming_content)
                response.close()
                with Image.open(io.BytesIO(data)) as icon:
                    self.assertEqual(icon.size, (size, size))
                    self.assertEqual(icon.format, "PNG")

    def test_head_and_conditional_requests_do_not_send_image_body(self):
        response = self.client.head("/favicon.ico")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(int(response["Content-Length"]), 0)
        self.assertEqual(b"".join(response.streaming_content), b"")
        etag = response["ETag"]
        response.close()
        cached = self.client.get("/favicon.ico", HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(cached.status_code, 304)
        self.assertEqual(b"".join(cached.streaming_content), b"")
        cached.close()

    def test_unknown_files_and_traversal_cannot_expose_other_assets(self):
        from tableno.public_icons import public_icon

        for path in ("../settings.py", "../../.env", "unknown.png", "tableno-icon-source-v1.png", "favicon.ico"):
            with self.subTest(path=path):
                with self.assertRaises(Http404):
                    public_icon(RequestFactory().get("/site-icons/" + path), path)

    def test_mutations_are_rejected(self):
        response = self.client.post("/favicon.ico")
        self.assertEqual(response.status_code, 405)
        response.close()

    def test_common_and_standalone_pages_render_same_icon_links(self):
        expected = (
            ("icon", "image/x-icon", "/site-icons/favicon-v1.ico"),
            ("icon", "image/png", "/site-icons/favicon-32-v1.png"),
            ("apple-touch-icon", "", "/site-icons/apple-touch-icon-v1.png"),
        )
        with override_settings(STATIC_URL="https://example.invalid/static/"):
            for template in ("base.html", "500.html", "admin/base_site.html"):
                with self.subTest(template=template):
                    html = render_to_string(template, {"user": AnonymousUser()})
                    for rel, content_type, href in expected:
                        self.assertIn(f'rel="{rel}"', html)
                        self.assertIn(f'href="{href}"', html)
                        if content_type:
                            self.assertIn(f'type="{content_type}"', html)
                    self.assertIn('sizes="32x32"', html)
                    self.assertIn('sizes="180x180"', html)
                    self.assertNotIn("example.invalid/static/branding/", html)

    def test_master_artwork_is_kept_in_the_repository(self):
        root = Path(__file__).resolve().parents[2]
        with Image.open(root / "static/branding/tableno-icon-source-v1.png") as image:
            self.assertEqual(image.size, (512, 512))
