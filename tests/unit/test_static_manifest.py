import io
import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


class StaticManifestTests(SimpleTestCase):
    def test_all_static_assets_can_be_collected_with_manifest_rewriting(self):
        with tempfile.TemporaryDirectory() as target:
            with override_settings(
                STATIC_ROOT=target,
                STORAGES={
                    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
                },
            ):
                call_command("collectstatic", interactive=False, stdout=io.StringIO(), verbosity=0)
            root = Path(target)
            manifest = json.loads((root / "staticfiles.json").read_text())
            for name in (
                "vendor/bootstrap/5.3.0/bootstrap.bundle.min.js",
                "vendor/bootstrap/5.3.0/bootstrap.min.css",
                "vendor/fullcalendar/6.1.9/index.global.min.js",
                "vendor/fontawesome/6.0.0/css/all.min.css",
            ):
                with self.subTest(asset=name):
                    self.assertIn(name, manifest["paths"])
                    self.assertTrue((root / manifest["paths"][name]).is_file())
