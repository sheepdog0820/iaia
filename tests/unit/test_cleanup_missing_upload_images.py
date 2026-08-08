from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import CustomUser
from scenarios.models import Scenario, ScenarioImage


class CleanupMissingUploadImagesCommandTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="missing-image-owner",
            password="password",
        )
        self.scenario = Scenario.objects.create(
            title="リンク切れ画像テスト",
            author="テスト作者",
            summary="テスト",
            game_system="coc",
            difficulty="intermediate",
            estimated_time=270,
            created_by=self.user,
        )
        self.image = ScenarioImage.objects.create(
            scenario=self.scenario,
            image="scenario_images/definitely-missing.png",
            title="リンク切れ",
            uploaded_by=self.user,
        )

    def test_dry_run_reports_but_does_not_delete_missing_record(self):
        stdout = StringIO()

        call_command("cleanup_missing_upload_images", stdout=stdout)

        self.assertTrue(ScenarioImage.objects.filter(pk=self.image.pk).exists())
        self.assertIn("DRY RUN", stdout.getvalue())
        self.assertIn("ScenarioImage", stdout.getvalue())

    def test_delete_option_removes_missing_record(self):
        stdout = StringIO()

        call_command("cleanup_missing_upload_images", "--delete", stdout=stdout)

        self.assertFalse(ScenarioImage.objects.filter(pk=self.image.pk).exists())
        self.assertIn("削除: 1件", stdout.getvalue())
