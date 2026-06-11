from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock

from scripts.aws.sync_media import build_plan


class ClientError(Exception):
    def __init__(self, status_code):
        self.response = {"ResponseMetadata": {"HTTPStatusCode": status_code}}


class MediaSyncPlanTest(TestCase):
    def test_build_plan_skips_matching_and_uploads_missing(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "same.txt").write_text("same", encoding="utf-8")
            (root / "new.txt").write_text("new", encoding="utf-8")

            client = Mock()
            client.exceptions.ClientError = ClientError

            def head_object(*, Bucket, Key):
                if Key.endswith("new.txt"):
                    raise ClientError(404)
                return {"ETag": '"51037a4a37730f52c8732586d3aaa316"'}

            client.head_object.side_effect = head_object

            plan = build_plan(root, "bucket", "media", client)

            self.assertEqual(
                [(action, key) for action, _, key in plan],
                [("upload", "media/new.txt"), ("skip", "media/same.txt")],
            )

    def test_build_plan_propagates_non_404_errors(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "file.txt").write_text("value", encoding="utf-8")
            client = Mock()
            client.exceptions.ClientError = ClientError
            client.head_object.side_effect = ClientError(403)

            with self.assertRaises(ClientError):
                build_plan(root, "bucket", "media", client)
