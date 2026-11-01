"""ZIP byte preservation, compression cost, and private storage failure logging."""

import hashlib
import io
import zipfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.http import Http404
from django.test import SimpleTestCase
from PIL import Image

from accounts.views.character_image_views import build_character_images_zip_response

VIEW = "accounts.views.character_image_views"


class CharacterImageZipEncodingTests(SimpleTestCase):
    def field(self, content, name="private/portrait.jpg"):
        storage = Mock()
        storage.open.return_value = io.BytesIO(content)
        return SimpleNamespace(name=name, storage=storage)

    def response(self, fields):
        sheet = SimpleNamespace(system_data=SimpleNamespace(name="探索者"))
        with patch(VIEW + "._collect_zip_entries", return_value=fields):
            return build_character_images_zip_response(sheet)

    def test_compressed_image_signatures_are_stored_without_recompression(self):
        # These synthetic bytes exercise ZIP routing; upload validation has its own tests.
        for content in (
            b"\xff\xd8\xffsynthetic-jpeg",
            b"\x89PNG\r\n\x1a\nsynthetic-png",
            b"GIF87asynthetic-gif",
            b"GIF89asynthetic-gif",
            b"RIFF\x20\x00\x00\x00WEBPsynthetic-webp",
        ):
            with self.subTest(signature=content[:12]):
                response = self.response([("01_main_", self.field(content, "private/偽装.bmp"))])
                with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                    self.assertEqual(archive.namelist(), ["01_main_偽装.bmp"])
                    self.assertEqual(archive.read(archive.namelist()[0]), content)
                    self.assertEqual(archive.infolist()[0].compress_type, zipfile.ZIP_STORED)

    def test_small_compressed_image_path_never_creates_a_deflater(self):
        content = b"\xff\xd8\xff" + b"synthetic-image" * 10
        with patch("zipfile.zlib.compressobj", wraps=zipfile.zlib.compressobj) as compress:
            response = self.response([("01_main_", self.field(content))])
        compress.assert_not_called()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(archive.read("01_main_portrait.jpg"), content)

    def test_large_low_compression_png_retains_useful_zip_compression(self):
        buffer = io.BytesIO()
        with Image.new("RGB", (512, 512), "blue") as image:
            image.save(buffer, "PNG", compress_level=0)
        content = buffer.getvalue()
        response = self.response([("01_", self.field(content, "private/portrait.png"))])
        self.assertLess(len(response.content), len(content) // 2)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(archive.read("01_portrait.png"), content)

    def test_large_incompressible_image_skips_full_zip_deflation(self):
        content = b"\xff\xd8\xff" + hashlib.shake_256(b"synthetic ZIP entropy").digest(128 * 1024)
        with patch("zipfile.zlib.compressobj", wraps=zipfile.zlib.compressobj) as compress:
            response = self.response([("01_", self.field(content))])
        compress.assert_not_called()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(archive.read("01_portrait.jpg"), content)

    def test_other_or_incomplete_signatures_keep_deflate_and_exact_content(self):
        for content in (b"BM" + b"\0" * 2048, b"RIFF\x20\0\0\0WAVE", b"RIFF", b"\xff\xd8", b"", b"unknown"):
            with self.subTest(signature=content[:12]):
                response = self.response([("01_", self.field(content, "private/looks-like.png"))])
                with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                    self.assertEqual(archive.read("01_looks-like.png"), content)
                    self.assertEqual(archive.infolist()[0].compress_type, zipfile.ZIP_DEFLATED)

    def test_mixed_archive_keeps_order_unique_names_and_response_headers(self):
        png = b"\x89PNG\r\n\x1a\nsynthetic"
        bitmap = b"BM" + b"\0" * 1024
        response = self.response(
            [("01_", self.field(png, "a/portrait.png")), ("01_", self.field(bitmap, "b/portrait.png"))]
        )
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertEqual(int(response["Content-Length"]), len(response.content))
        self.assertIn("attachment", response["Content-Disposition"])
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(archive.namelist(), ["01_portrait.png", "01_portrait_2.png"])
            self.assertEqual([archive.read(name) for name in archive.namelist()], [png, bitmap])

    def test_storage_failure_log_omits_private_path_exception_and_traceback(self):
        failed = self.field(b"", "private/synthetic-owner/portrait.png")
        failed.storage.open.side_effect = OSError("synthetic-private-endpoint?credential=not-real")
        good = self.field(b"\xff\xd8\xffsynthetic")
        with self.assertLogs(VIEW, level="WARNING") as captured:
            response = self.response([("01_", failed), ("02_", good)])
        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.getMessage(), "Failed to add character image to ZIP.")
        self.assertIsNone(record.exc_info)
        self.assertIsNone(record.stack_info)
        self.assertEqual(record.args, ())
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(archive.namelist(), ["02_portrait.jpg"])

    def test_all_failed_reads_keep_not_found_behavior(self):
        failed = self.field(b"")
        failed.storage.open.side_effect = OSError("synthetic failure")
        with self.assertLogs(VIEW, level="WARNING"), self.assertRaises(Http404):
            self.response([("01_", failed)])
