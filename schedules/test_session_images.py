"""
セッション画像機能のテスト
"""

from schedules import session_permissions
import io
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import CustomUser, Group
from schedules.models import SessionImage, SessionParticipant, TRPGSession


class SessionImageTestCase(APITestCase):
    """セッション画像機能のテスト"""

    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.gm = CustomUser.objects.create_user(
            username="gm_user", email="gm@example.com", password="password", nickname="GMユーザー"
        )

        self.player1 = CustomUser.objects.create_user(
            username="player1", email="player1@example.com", password="password", nickname="プレイヤー1"
        )

        self.player2 = CustomUser.objects.create_user(
            username="player2", email="player2@example.com", password="password", nickname="プレイヤー2"
        )

        self.other_user = CustomUser.objects.create_user(
            username="other", email="other@example.com", password="password", nickname="その他ユーザー"
        )

        # グループ作成
        self.group = Group.objects.create(name="テストグループ", created_by=self.gm)
        self.group.members.add(self.gm, self.player1, self.player2)

        # セッション作成
        self.session = TRPGSession.objects.create(
            title="画像テストセッション",
            description="画像アップロードのテスト",
            date=timezone.now() + timedelta(days=7),
            gm=self.gm,
            group=self.group,
            status="planned",
        )

        # 参加者追加
        session_permissions.create_participant(session=self.session, user=self.player1, role="player")

    def create_test_image(self, name="test.png"):
        """テスト用画像ファイルを作成"""
        file = io.BytesIO()
        image = Image.new("RGB", (100, 100), color="red")
        image.save(file, "PNG")
        file.seek(0)
        return SimpleUploadedFile(name=name, content=file.getvalue(), content_type="image/png")

    def create_padded_image(self, name, target_size, image_format="PNG", content_type="image/png"):
        file = io.BytesIO()
        image = Image.new("RGB", (100, 100), color="red")
        image.save(file, image_format)
        content = file.getvalue()
        if len(content) < target_size:
            content += b"\0" * (target_size - len(content))
        return SimpleUploadedFile(
            name=name,
            content=content,
            content_type=content_type,
        )

    def test_gm_can_upload_image(self):
        """GMが画像をアップロードできる"""
        self.client.force_authenticate(user=self.gm)

        image_file = self.create_test_image()
        data = {
            "session": self.session.id,
            "image": image_file,
            "title": "セッションマップ",
            "description": "ダンジョンの地図",
        }

        response = self.client.post(reverse("session-image-list"), data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "セッションマップ")
        self.assertEqual(response.data["uploaded_by"], self.gm.id)
        self.assertIsNotNone(response.data["image_url"])

        # データベースに保存されているか確認
        session_image = SessionImage.objects.get(id=response.data["id"])
        self.assertEqual(session_image.session, self.session)
        self.assertEqual(session_image.uploaded_by, self.gm)

    def test_participant_can_upload_image(self):
        """参加者が画像をアップロードできる"""
        self.client.force_authenticate(user=self.player1)

        image_file = self.create_test_image("player_image.png")
        data = {
            "session": self.session.id,
            "image": image_file,
            "title": "キャラクターイメージ",
            "description": "私のキャラクター",
        }

        response = self.client.post(reverse("session-image-list"), data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["uploaded_by"], self.player1.id)

    def test_non_participant_cannot_upload_image(self):
        """非参加者は画像をアップロードできない"""
        self.client.force_authenticate(user=self.other_user)

        image_file = self.create_test_image()
        data = {"session": self.session.id, "image": image_file, "title": "不正アップロード"}

        response = self.client.post(reverse("session-image-list"), data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bulk_upload_images(self):
        """複数画像の一括アップロード"""
        self.client.force_authenticate(user=self.gm)

        # 3つの画像を準備
        images = [self.create_test_image(f"image{i}.png") for i in range(3)]

        data = {"session_id": self.session.id, "images": images}

        response = self.client.post(reverse("session-image-bulk-upload"), data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 3)

        # 自動的に順序が設定されているか確認
        for i, image_data in enumerate(response.data):
            self.assertEqual(image_data["order"], i + 1)

    def test_upload_accepts_supported_image_formats_and_size_boundary(self):
        """jpg/png/gif と5MB境界の画像を受け付ける"""
        self.client.force_authenticate(user=self.gm)

        cases = [
            ("session.jpg", "JPEG", "image/jpeg"),
            ("session.png", "PNG", "image/png"),
            ("session.gif", "GIF", "image/gif"),
        ]
        for filename, image_format, content_type in cases:
            with self.subTest(filename=filename):
                response = self.client.post(
                    reverse("session-image-list"),
                    {
                        "session": self.session.id,
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
            reverse("session-image-list"),
            {
                "session": self.session.id,
                "image": self.create_padded_image(
                    "session-5mb.png",
                    target_size=5 * 1024 * 1024,
                ),
                "title": "5MB境界",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_upload_rejects_oversized_and_non_image_files(self):
        """上限超過と非画像ファイルを拒否する"""
        self.client.force_authenticate(user=self.gm)

        response = self.client.post(
            reverse("session-image-list"),
            {
                "session": self.session.id,
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
            reverse("session-image-list"),
            {
                "session": self.session.id,
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
        self.client.force_authenticate(user=self.gm)

        response = self.client.post(
            reverse("session-image-bulk-upload"),
            {
                "session_id": self.session.id,
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
        self.assertEqual(SessionImage.objects.count(), 0)

    def test_image_ordering(self):
        """画像の表示順序"""
        self.client.force_authenticate(user=self.gm)

        # 3つの画像を作成（orderは1から始まる）
        for i in range(3):
            SessionImage.objects.create(
                session=self.session,
                image=self.create_test_image(f"order{i}.png"),
                title=f"画像{i}",
                uploaded_by=self.gm,
                order=i + 1,  # 1から始まる
            )

        response = self.client.get(reverse("session-image-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 順序通りに返されるか確認
        for i, image_data in enumerate(response.data):
            self.assertEqual(image_data["order"], i + 1)

    def test_reorder_images(self):
        """画像の順序変更（GMのみ）"""
        # 画像作成
        image = SessionImage.objects.create(
            session=self.session,
            image=self.create_test_image(),
            title="順序変更テスト",
            uploaded_by=self.player1,
            order=1,
        )

        # GMが順序変更
        self.client.force_authenticate(user=self.gm)
        response = self.client.post(
            reverse("session-image-reorder", kwargs={"pk": image.id}), {"order": 5}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["order"], 5)

        # プレイヤーは順序変更できない
        self.client.force_authenticate(user=self.player1)
        response = self.client.post(
            reverse("session-image-reorder", kwargs={"pk": image.id}), {"order": 10}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reorder_images_bulk(self):
        """画像の一括順序変更（GMのみ・トランザクション）"""
        images = [
            SessionImage.objects.create(
                session=self.session,
                image=self.create_test_image(f"bulk{i}.png"),
                title=f"画像{i}",
                uploaded_by=self.player1,
                order=i + 1,
            )
            for i in range(3)
        ]

        self.client.force_authenticate(user=self.gm)
        response = self.client.post(
            reverse("session-image-reorder-bulk"),
            {
                "session_id": self.session.id,
                "ordered_ids": [images[2].id, images[0].id, images[1].id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        images[0].refresh_from_db()
        images[1].refresh_from_db()
        images[2].refresh_from_db()
        self.assertEqual(images[2].order, 1)
        self.assertEqual(images[0].order, 2)
        self.assertEqual(images[1].order, 3)

        # GM以外は実行不可
        self.client.force_authenticate(user=self.player1)
        response = self.client.post(
            reverse("session-image-reorder-bulk"),
            {
                "session_id": self.session.id,
                "ordered_ids": [images[0].id, images[1].id, images[2].id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 不正な順序指定は反映されない
        self.client.force_authenticate(user=self.gm)
        before_orders = {image.id: SessionImage.objects.get(id=image.id).order for image in images}
        response = self.client.post(
            reverse("session-image-reorder-bulk"),
            {
                "session_id": self.session.id,
                "ordered_ids": [images[0].id, images[0].id, images[1].id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        after_orders = {image.id: SessionImage.objects.get(id=image.id).order for image in images}
        self.assertEqual(before_orders, after_orders)

    def test_delete_image_permissions(self):
        """画像削除の権限"""
        # プレイヤーが画像をアップロード
        image = SessionImage.objects.create(
            session=self.session, image=self.create_test_image(), title="削除テスト", uploaded_by=self.player1
        )

        # アップロード者は削除できる
        self.client.force_authenticate(user=self.player1)
        response = self.client.delete(reverse("session-image-detail", kwargs={"pk": image.id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # 別の画像を作成
        image2 = SessionImage.objects.create(
            session=self.session, image=self.create_test_image(), title="削除テスト2", uploaded_by=self.player1
        )

        # GMも削除できる
        self.client.force_authenticate(user=self.gm)
        response = self.client.delete(reverse("session-image-detail", kwargs={"pk": image2.id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # 別の画像を作成
        image3 = SessionImage.objects.create(
            session=self.session, image=self.create_test_image(), title="削除テスト3", uploaded_by=self.player1
        )

        # 他のプレイヤーは削除できない
        self.client.force_authenticate(user=self.player2)
        response = self.client.delete(reverse("session-image-detail", kwargs={"pk": image3.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_session_with_images_response(self):
        """セッション詳細に画像情報が含まれる"""
        # 画像を2つ追加
        for i in range(2):
            SessionImage.objects.create(
                session=self.session,
                image=self.create_test_image(f"session{i}.png"),
                title=f"セッション画像{i+1}",
                uploaded_by=self.gm,
            )

        self.client.force_authenticate(user=self.gm)
        response = self.client.get(reverse("session-detail", kwargs={"pk": self.session.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("images_detail", response.data)
        self.assertEqual(len(response.data["images_detail"]), 2)

        # 画像情報の確認
        for i, image_data in enumerate(response.data["images_detail"]):
            self.assertEqual(image_data["title"], f"セッション画像{i+1}")
            self.assertIsNotNone(image_data["image_url"])


if __name__ == "__main__":
    import django
    from django.conf import settings
    from django.test.utils import get_runner

    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True, keepdb=True)

    failures = test_runner.run_tests(["schedules.test_session_images.SessionImageTestCase"])

    if failures:
        print(f"\n❌ {failures} 件のテストが失敗しました")
    else:
        print("\n✅ すべてのテストが成功しました！")
