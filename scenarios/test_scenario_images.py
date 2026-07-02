"""
シナリオ画像機能のテスト
"""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import CustomUser
from scenarios.models import Scenario, ScenarioImage


class ScenarioImageTestCase(APITestCase):
    """シナリオ画像機能のテスト"""

    def setUp(self):
        self.creator = CustomUser.objects.create_user(
            username="scenario_creator",
            email="creator@example.com",
            password="password",
            nickname="作成者",
        )
        self.uploader = CustomUser.objects.create_user(
            username="scenario_uploader",
            email="uploader@example.com",
            password="password",
            nickname="投稿者",
        )
        self.other_user = CustomUser.objects.create_user(
            username="scenario_other",
            email="other@example.com",
            password="password",
            nickname="その他",
        )

        self.scenario = Scenario.objects.create(
            title="画像付きシナリオ",
            author="Test Author",
            summary="Test Summary",
            game_system="coc",
            difficulty="intermediate",
            estimated_duration="medium",
            created_by=self.creator,
        )

    def create_test_image(self, name="test.png"):
        file = io.BytesIO()
        image = Image.new("RGB", (100, 100), color="blue")
        image.save(file, "PNG")
        file.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=file.getvalue(),
            content_type="image/png",
        )

    def create_padded_image(self, name, target_size, image_format="PNG", content_type="image/png"):
        file = io.BytesIO()
        image = Image.new("RGB", (100, 100), color="blue")
        image.save(file, image_format)
        content = file.getvalue()
        if len(content) < target_size:
            content += b"\0" * (target_size - len(content))
        return SimpleUploadedFile(
            name=name,
            content=content,
            content_type=content_type,
        )

    def test_user_can_upload_image(self):
        """任意ユーザーが画像をアップロードできる（アップロード者として記録される）"""
        self.client.force_authenticate(user=self.uploader)

        image_file = self.create_test_image()
        data = {
            "scenario": self.scenario.id,
            "image": image_file,
            "title": "表紙",
            "description": "シナリオの表紙画像",
        }

        response = self.client.post(
            reverse("scenario-image-list"),
            data,
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["uploaded_by"], self.uploader.id)
        self.assertIsNotNone(response.data["image_url"])

        created = ScenarioImage.objects.get(id=response.data["id"])
        self.assertEqual(created.scenario, self.scenario)
        self.assertEqual(created.uploaded_by, self.uploader)

    def test_bulk_upload_images(self):
        """複数画像の一括アップロード"""
        self.client.force_authenticate(user=self.creator)

        images = [self.create_test_image(f"image{i}.png") for i in range(3)]
        data = {
            "scenario_id": self.scenario.id,
            "images": images,
        }

        response = self.client.post(
            reverse("scenario-image-bulk-upload"),
            data,
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 3)

        for i, image_data in enumerate(response.data):
            self.assertEqual(image_data["order"], i + 1)

    def test_upload_accepts_supported_image_formats_and_size_boundary(self):
        """jpg/png/gif と5MB境界の画像を受け付ける"""
        self.client.force_authenticate(user=self.uploader)

        cases = [
            ("scenario.jpg", "JPEG", "image/jpeg"),
            ("scenario.png", "PNG", "image/png"),
            ("scenario.gif", "GIF", "image/gif"),
        ]
        for filename, image_format, content_type in cases:
            with self.subTest(filename=filename):
                response = self.client.post(
                    reverse("scenario-image-list"),
                    {
                        "scenario": self.scenario.id,
                        "image": self.create_padded_image(
                            filename,
                            target_size=1024 * 1024,
                            image_format=image_format,
                            content_type=content_type,
                        ),
                        "title": filename,
                    },
                    format="multipart",
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse("scenario-image-list"),
            {
                "scenario": self.scenario.id,
                "image": self.create_padded_image(
                    "scenario-5mb.png",
                    target_size=5 * 1024 * 1024,
                ),
                "title": "5MB境界",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_upload_rejects_oversized_and_non_image_files(self):
        """上限超過と非画像ファイルを拒否する"""
        self.client.force_authenticate(user=self.uploader)

        response = self.client.post(
            reverse("scenario-image-list"),
            {
                "scenario": self.scenario.id,
                "image": self.create_padded_image(
                    "too-large.png",
                    target_size=(5 * 1024 * 1024) + 1,
                ),
                "title": "上限超過",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("5MB", str(response.data))

        response = self.client.post(
            reverse("scenario-image-list"),
            {
                "scenario": self.scenario.id,
                "image": SimpleUploadedFile(
                    "not-image.txt",
                    b"not an image",
                    content_type="text/plain",
                ),
                "title": "非画像",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_upload_rejects_invalid_image(self):
        """複数枚登録でも画像バリデーションを通す"""
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            reverse("scenario-image-bulk-upload"),
            {
                "scenario_id": self.scenario.id,
                "images": [
                    self.create_test_image("valid.png"),
                    self.create_padded_image(
                        "too-large.png",
                        target_size=(5 * 1024 * 1024) + 1,
                    ),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ScenarioImage.objects.count(), 0)

    def test_reorder_images(self):
        """画像の順序変更（シナリオ作成者のみ）"""
        image = ScenarioImage.objects.create(
            scenario=self.scenario,
            image=self.create_test_image(),
            title="順序変更テスト",
            uploaded_by=self.uploader,
            order=1,
        )

        self.client.force_authenticate(user=self.creator)
        response = self.client.post(
            reverse("scenario-image-reorder", kwargs={"pk": image.id}),
            {"order": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["order"], 5)

        self.client.force_authenticate(user=self.uploader)
        response = self.client.post(
            reverse("scenario-image-reorder", kwargs={"pk": image.id}),
            {"order": 10},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reorder_images_bulk(self):
        """画像の一括順序変更（シナリオ作成者のみ・トランザクション）"""
        images = [
            ScenarioImage.objects.create(
                scenario=self.scenario,
                image=self.create_test_image(f"bulk{i}.png"),
                title=f"画像{i}",
                uploaded_by=self.uploader,
                order=i + 1,
            )
            for i in range(3)
        ]

        self.client.force_authenticate(user=self.creator)
        response = self.client.post(
            reverse("scenario-image-reorder-bulk"),
            {
                "scenario_id": self.scenario.id,
                "ordered_ids": [images[1].id, images[2].id, images[0].id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        images[0].refresh_from_db()
        images[1].refresh_from_db()
        images[2].refresh_from_db()
        self.assertEqual(images[1].order, 1)
        self.assertEqual(images[2].order, 2)
        self.assertEqual(images[0].order, 3)

        # 作成者以外は実行不可
        self.client.force_authenticate(user=self.uploader)
        response = self.client.post(
            reverse("scenario-image-reorder-bulk"),
            {
                "scenario_id": self.scenario.id,
                "ordered_ids": [images[0].id, images[1].id, images[2].id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 不正な順序指定は反映されない
        self.client.force_authenticate(user=self.creator)
        before_orders = {image.id: ScenarioImage.objects.get(id=image.id).order for image in images}
        response = self.client.post(
            reverse("scenario-image-reorder-bulk"),
            {
                "scenario_id": self.scenario.id,
                "ordered_ids": [images[0].id, images[0].id, images[1].id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        after_orders = {image.id: ScenarioImage.objects.get(id=image.id).order for image in images}
        self.assertEqual(before_orders, after_orders)

    def test_delete_image_permissions(self):
        """画像削除の権限（作成者/アップロード者のみ）"""
        image = ScenarioImage.objects.create(
            scenario=self.scenario,
            image=self.create_test_image(),
            title="削除テスト",
            uploaded_by=self.uploader,
        )

        self.client.force_authenticate(user=self.uploader)
        response = self.client.delete(
            reverse("scenario-image-detail", kwargs={"pk": image.id}),
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        image2 = ScenarioImage.objects.create(
            scenario=self.scenario,
            image=self.create_test_image(),
            title="削除テスト2",
            uploaded_by=self.uploader,
        )

        self.client.force_authenticate(user=self.creator)
        response = self.client.delete(
            reverse("scenario-image-detail", kwargs={"pk": image2.id}),
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        image3 = ScenarioImage.objects.create(
            scenario=self.scenario,
            image=self.create_test_image(),
            title="削除テスト3",
            uploaded_by=self.uploader,
        )

        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(
            reverse("scenario-image-detail", kwargs={"pk": image3.id}),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
