from argparse import Namespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tests.performance import image_upload_load as probe


class ImageUploadLoadTests(SimpleTestCase):
    def test_size_cases_do_not_compete_for_character_slots(self):
        created = []
        uploads = []

        def create(session, base, path, payload, timeout):
            created.append((path, payload))
            return {"id": len(created)}

        def upload(session, base, name, path, data, field, filename, content, content_type, expected, timeout):
            uploads.append((name, path, expected))
            return probe.ProbeResult(name, next(iter(expected)), 1, True, "")

        args = Namespace(base_url="http://localhost", timeout=10, requests_per_target=9, concurrency=3)
        with (
            patch.object(probe, "login", return_value=Mock()),
            patch.object(probe, "post_json", side_effect=create),
            patch.object(probe, "make_image_bytes", return_value=b"fixture"),
            patch.object(probe, "upload_once", side_effect=upload),
            patch("builtins.print"),
        ):
            self.assertEqual(probe.run(args), 0)
        character_uploads = [row for row in uploads if row[0].startswith("character-")]
        self.assertEqual(len(character_uploads), 9)
        self.assertEqual(len({row[1] for row in character_uploads}), 9)
        self.assertEqual(sum(row[2] == {400} for row in character_uploads), 3)
        self.assertEqual(sum(row[2] == {201} for row in character_uploads), 6)
        self.assertEqual(len(uploads), 27)
        for path, payload in created:
            if "create_6th_edition" in path:
                self.assertEqual(payload.get("access_scope"), "private")
            elif path == "/api/scenarios/scenarios/":
                self.assertEqual(payload.get("visibility"), "private")
                self.assertEqual(payload.get("game_system"), "coc6")

    def test_invalid_load_sizes_do_not_login_or_create_data(self):
        for requests, concurrency, timeout in ((0, 1, 10), (1, 0, 10), (1, 1, 0)):
            with self.subTest(requests=requests, concurrency=concurrency, timeout=timeout):
                args = Namespace(
                    base_url="http://localhost",
                    timeout=timeout,
                    requests_per_target=requests,
                    concurrency=concurrency,
                )
                with patch.object(probe, "login") as login:
                    with self.assertRaises(ValueError):
                        probe.run(args)
                    login.assert_not_called()
