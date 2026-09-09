from pathlib import Path

from django.test import RequestFactory, TestCase


class PublicFontTests(TestCase):
    # Response.close() dispatches Django's DB connection cleanup signal even
    # for static responses. Keep that lifecycle inside a managed test DB.
    def test_anonymous_http_route_works_with_external_static_domain(self):
        from django.test import override_settings
        from django.urls import reverse

        with override_settings(STATIC_URL="https://example.invalid/static/"):
            url = reverse("public_font", args=["theme-fonts/fonts.css"])
            self.assertEqual(url, "/fonts/theme-fonts/fonts.css")
            with self.assertNumQueries(0):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response["Content-Type"].startswith("text/css"))
                response.close()

    def test_anonymous_font_delivery_and_conditional_request(self):
        from tableno.public_fonts import public_font

        path = "fontawesome/6.0.0/webfonts/fa-solid-900.woff2"
        response = public_font(RequestFactory().get("/fonts/" + path), path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "font/woff2")
        self.assertIn("public", response["Cache-Control"])
        self.assertEqual(b"".join(response.streaming_content)[:4], b"wOF2")
        response.close()
        cached = public_font(RequestFactory().get("/fonts/" + path, HTTP_IF_NONE_MATCH=response["ETag"]), path)
        self.assertEqual(cached.status_code, 304)

    def test_css_relative_font_urls_are_available(self):
        import re
        from posixpath import normpath

        from tableno.public_fonts import public_font

        for css in ("fontawesome/6.0.0/css/all.min.css", "theme-fonts/fonts.css"):
            response = public_font(RequestFactory().get("/fonts/" + css), css)
            text = b"".join(response.streaming_content).decode("utf-8")
            response.close()
            for url in set(re.findall(r"url\(['\"]?([^)'\"]+)", text)):
                path = normpath(str(Path(css).parent).replace("\\", "/") + "/" + url)
                font = public_font(RequestFactory().head("/fonts/" + path), path)
                self.assertEqual(font.status_code, 200, path)
                font.close()

    def test_unlisted_paths_and_mutations_are_rejected(self):
        from django.http import Http404

        from tableno.public_fonts import public_font

        for path in ("../settings.py", "theme-fonts/../../../../.env", "media/private.txt", "unknown.woff2"):
            with self.assertRaises(Http404):
                public_font(RequestFactory().get("/fonts/" + path), path)
        response = public_font(RequestFactory().post("/fonts/theme-fonts/fonts.css"), "theme-fonts/fonts.css")
        self.assertEqual(response.status_code, 405)

    def test_base_template_loads_font_stylesheets_from_app_origin(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates/base.html").read_text(encoding="utf-8")
        for path in ("fontawesome/6.0.0/css/all.min.css", "theme-fonts/fonts.css"):
            self.assertIn("{% url 'public_font' '" + path + "' %}", template)
        self.assertNotIn("@import", (root / "static/css/arkham_modern.css").read_text(encoding="utf-8"))
