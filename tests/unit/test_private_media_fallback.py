from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings


class PrivateMediaFallbackTests(SimpleTestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        self.root = Path(media.name)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)

    def write_file(self, name):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"private-media-fixture")

    def test_private_work_files_never_use_static_fallback(self):
        for name in (
            "background_removal/input/source.png",
            "background_removal/output/result.png",
            "session_template_images/42/residual.png",
        ):
            self.write_file(name)
            for debug in (True, False):
                for prefix in ("/media/", "/media/other/../"):
                    with self.subTest(name=name, debug=debug, prefix=prefix), override_settings(DEBUG=debug):
                        response = self.client.get(prefix + name)
                        if response.streaming:
                            content = b"".join(response.streaming_content)
                        else:
                            content = response.content
                        self.assertEqual(response.status_code, 404)
                        self.assertNotIn(b"private-media-fixture", content)

    def test_unrelated_local_media_remains_available_in_debug(self):
        name = "character_images/public.png"
        self.write_file(name)
        with override_settings(DEBUG=True):
            response = self.client.get("/media/" + name)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"private-media-fixture")
