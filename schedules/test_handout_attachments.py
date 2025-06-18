"""
TRPGセッション管理システム - ハンドアウト添付ファイル機能のテスト

TDD原則に従って、ハンドアウト添付ファイル機能のテストを作成します。
この機能により、GMはハンドアウトに画像、PDF、音声、動画ファイルを添付できます。
"""

import os
import tempfile
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.utils import timezone
from PIL import Image
import io
from accounts.models import CustomUser, Group
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo
import unittest


class HandoutAttachmentModelTest(TestCase):
    """ハンドアウト添付ファイルモデルのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        # ユーザー作成
        self.gm_user = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            nickname='テストGM'
        )
        self.player1 = CustomUser.objects.create_user(
            username='player1',
            email='player1@example.com',
            nickname='プレイヤー1'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='テストグループ',
            description='テスト用のグループ',
            created_by=self.gm_user,
            visibility='private'
        )
        self.group.members.add(self.gm_user, self.player1)
        
        # セッション作成
        self.session = TRPGSession.objects.create(
            title='テストセッション',
            description='テスト用のセッション',
            date=timezone.now() + timezone.timedelta(days=1),
            gm=self.gm_user,
            group=self.group
        )
        
        # 参加者作成
        self.participant1 = SessionParticipant.objects.create(
            session=self.session,
            user=self.player1,
            role='player',
            character_name='探索者1'
        )
        
        # ハンドアウト作成
        self.handout = HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant1,
            title='テストハンドアウト',
            content='これはテスト用のハンドアウトです。',
            is_secret=True
        )
    
    def test_handout_attachment_model_creation(self):
        """HandoutAttachmentモデルの作成テスト"""
        # このテストは失敗するはず（モデルがまだ存在しない）
        from schedules.models import HandoutAttachment
        
        # テスト用画像ファイルの作成
        image = Image.new('RGB', (100, 100), color='red')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        test_file = SimpleUploadedFile(
            "test_image.jpg",
            image_io.getvalue(),
            content_type="image/jpeg"
        )
        
        attachment = HandoutAttachment.objects.create(
            handout=self.handout,
            file=test_file,
            original_filename='test_image.jpg',
            file_type='image',
            file_size=len(image_io.getvalue()),
            content_type='image/jpeg',
            uploaded_by=self.gm_user
        )
        
        self.assertEqual(attachment.handout, self.handout)
        self.assertEqual(attachment.original_filename, 'test_image.jpg')
        self.assertEqual(attachment.file_type, 'image')
        self.assertEqual(attachment.uploaded_by, self.gm_user)
    
    def test_file_type_validation(self):
        """ファイルタイプのバリデーションテスト"""
        from schedules.models import HandoutAttachment
        
        # 無効なファイルタイプでのテスト
        with self.assertRaises(ValidationError):
            attachment = HandoutAttachment(
                handout=self.handout,
                file_type='invalid_type',
                uploaded_by=self.gm_user
            )
            attachment.full_clean()
    
    def test_file_size_validation(self):
        """ファイルサイズのバリデーションテスト"""
        from schedules.models import HandoutAttachment
        
        # 最大サイズを超過した場合
        with self.assertRaises(ValidationError):
            attachment = HandoutAttachment(
                handout=self.handout,
                file_size=50 * 1024 * 1024,  # 50MB（制限を超過）
                file_type='image',
                uploaded_by=self.gm_user
            )
            attachment.full_clean()
    
    def test_supported_file_formats(self):
        """サポートされるファイル形式のテスト"""
        from schedules.models import HandoutAttachment
        
        # サポートされる形式のテスト
        supported_formats = [
            ('image/jpeg', 'image'),
            ('image/png', 'image'),
            ('image/gif', 'image'),
            ('application/pdf', 'pdf'),
            ('audio/mpeg', 'audio'),
            ('audio/wav', 'audio'),
            ('video/mp4', 'video'),
            ('video/webm', 'video'),
        ]
        
        for content_type, file_type in supported_formats:
            # この部分は実装後に有効になる
            pass
    
    def test_file_upload_path(self):
        """ファイルアップロードパスのテスト"""
        from schedules.models import HandoutAttachment
        
        # アップロードパスが正しく生成されることを確認
        attachment = HandoutAttachment(
            handout=self.handout,
            original_filename='test_file.jpg',
            file_type='image',
            uploaded_by=self.gm_user
        )
        
        # パスの形式: handouts/{session_id}/{handout_id}/{timestamp}_{original_filename}
        expected_path_pattern = f"handouts/{self.session.id}/{self.handout.id}/"
        # 実際のテストは実装後に追加


class HandoutAttachmentServiceTest(TestCase):
    """ハンドアウト添付ファイルサービスのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.gm_user = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            nickname='テストGM'
        )
        self.player1 = CustomUser.objects.create_user(
            username='player1',
            email='player1@example.com',
            nickname='プレイヤー1'
        )
        
        self.group = Group.objects.create(
            name='テストグループ',
            created_by=self.gm_user,
            visibility='private'
        )
        
        self.session = TRPGSession.objects.create(
            title='テストセッション',
            date=timezone.now() + timezone.timedelta(days=1),
            gm=self.gm_user,
            group=self.group
        )
        
        self.participant1 = SessionParticipant.objects.create(
            session=self.session,
            user=self.player1,
            role='player'
        )
        
        self.handout = HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant1,
            title='テストハンドアウト',
            content='テスト内容',
            is_secret=True
        )
    
    def create_test_image(self):
        """テスト用画像ファイルの作成"""
        image = Image.new('RGB', (100, 100), color='blue')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        return SimpleUploadedFile(
            "test_image.jpg",
            image_io.getvalue(),
            content_type="image/jpeg"
        )
    
    def create_test_pdf(self):
        """テスト用PDFファイルの作成（簡易版）"""
        pdf_content = b"%PDF-1.4\n%Test PDF content"
        return SimpleUploadedFile(
            "test_document.pdf",
            pdf_content,
            content_type="application/pdf"
        )
    
    def test_attachment_service_exists(self):
        """添付ファイルサービスクラスの存在テスト"""
        # このテストは失敗するはず（サービスクラスがまだ存在しない）
        from schedules.attachment_service import HandoutAttachmentService
        
        service = HandoutAttachmentService()
        self.assertIsNotNone(service)
    
    def test_upload_image_attachment(self):
        """画像添付ファイルのアップロードテスト"""
        from schedules.attachment_service import HandoutAttachmentService
        
        service = HandoutAttachmentService()
        test_file = self.create_test_image()
        
        attachment = service.upload_attachment(
            handout=self.handout,
            file=test_file,
            uploaded_by=self.gm_user
        )
        
        self.assertIsNotNone(attachment)
        self.assertEqual(attachment.file_type, 'image')
        self.assertEqual(attachment.original_filename, 'test_image.jpg')
        self.assertTrue(os.path.exists(attachment.file.path))
    
    def test_upload_pdf_attachment(self):
        """PDF添付ファイルのアップロードテスト"""
        from schedules.attachment_service import HandoutAttachmentService
        
        service = HandoutAttachmentService()
        test_file = self.create_test_pdf()
        
        attachment = service.upload_attachment(
            handout=self.handout,
            file=test_file,
            uploaded_by=self.gm_user
        )
        
        self.assertIsNotNone(attachment)
        self.assertEqual(attachment.file_type, 'pdf')
        self.assertEqual(attachment.original_filename, 'test_document.pdf')
    
    def test_file_size_limit_validation(self):
        """ファイルサイズ制限のバリデーションテスト"""
        from schedules.attachment_service import HandoutAttachmentService
        
        service = HandoutAttachmentService()
        
        # 大きすぎるファイルのシミュレーション
        large_file = SimpleUploadedFile(
            "large_file.jpg",
            b"x" * (20 * 1024 * 1024),  # 20MB
            content_type="image/jpeg"
        )
        
        with self.assertRaises(ValidationError):
            service.upload_attachment(
                handout=self.handout,
                file=large_file,
                uploaded_by=self.gm_user
            )
    
    def test_unsupported_file_type_validation(self):
        """サポートされていないファイルタイプのバリデーションテスト"""
        from schedules.attachment_service import HandoutAttachmentService
        
        service = HandoutAttachmentService()
        
        # サポートされていないファイル形式
        unsupported_file = SimpleUploadedFile(
            "test.exe",
            b"fake executable content",
            content_type="application/x-msdownload"
        )
        
        with self.assertRaises(ValidationError):
            service.upload_attachment(
                handout=self.handout,
                file=unsupported_file,
                uploaded_by=self.gm_user
            )
    
    def test_delete_attachment(self):
        """添付ファイルの削除テスト"""
        from schedules.attachment_service import HandoutAttachmentService
        
        service = HandoutAttachmentService()
        test_file = self.create_test_image()
        
        # アップロード
        attachment = service.upload_attachment(
            handout=self.handout,
            file=test_file,
            uploaded_by=self.gm_user
        )
        
        file_path = attachment.file.path
        attachment_id = attachment.id
        
        # 削除
        result = service.delete_attachment(attachment_id, self.gm_user)
        
        self.assertTrue(result)
        self.assertFalse(os.path.exists(file_path))
        
        # データベースからも削除されているか確認
        from schedules.models import HandoutAttachment
        with self.assertRaises(HandoutAttachment.DoesNotExist):
            HandoutAttachment.objects.get(id=attachment_id)
    
    def test_get_attachment_url(self):
        """添付ファイルURL取得テスト"""
        from schedules.attachment_service import HandoutAttachmentService
        
        service = HandoutAttachmentService()
        test_file = self.create_test_image()
        
        attachment = service.upload_attachment(
            handout=self.handout,
            file=test_file,
            uploaded_by=self.gm_user
        )
        
        url = service.get_attachment_url(attachment, self.player1)
        
        # 権限のあるユーザーはURLを取得できる
        self.assertIsNotNone(url)
        self.assertIn('handouts', url)
    
    def test_attachment_permission_check(self):
        """添付ファイルの権限チェックテスト"""
        from schedules.attachment_service import HandoutAttachmentService
        
        # 権限のないユーザー
        other_user = CustomUser.objects.create_user(
            username='other_user',
            email='other@example.com'
        )
        
        service = HandoutAttachmentService()
        test_file = self.create_test_image()
        
        attachment = service.upload_attachment(
            handout=self.handout,
            file=test_file,
            uploaded_by=self.gm_user
        )
        
        # 権限のないユーザーはアクセスできない
        with self.assertRaises(PermissionError):
            service.get_attachment_url(attachment, other_user)


class HandoutAttachmentAPITest(TestCase):
    """ハンドアウト添付ファイルAPIのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.gm_user = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            nickname='テストGM'
        )
        self.player1 = CustomUser.objects.create_user(
            username='player1',
            email='player1@example.com',
            nickname='プレイヤー1'
        )
        
        self.group = Group.objects.create(
            name='テストグループ',
            created_by=self.gm_user,
            visibility='private'
        )
        
        self.session = TRPGSession.objects.create(
            title='テストセッション',
            date=timezone.now() + timezone.timedelta(days=1),
            gm=self.gm_user,
            group=self.group
        )
        
        self.handout = HandoutInfo.objects.create(
            session=self.session,
            participant=SessionParticipant.objects.create(
                session=self.session,
                user=self.player1,
                role='player'
            ),
            title='テストハンドアウト',
            content='テスト内容',
            is_secret=True
        )
    
    def create_test_image(self):
        """テスト用画像ファイルの作成"""
        image = Image.new('RGB', (100, 100), color='green')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        return SimpleUploadedFile(
            "api_test_image.jpg",
            image_io.getvalue(),
            content_type="image/jpeg"
        )
    
    def test_attachment_upload_api(self):
        """添付ファイルアップロードAPIのテスト"""
        # このテストは失敗するはず（APIエンドポイントがまだ存在しない）
        from django.test import Client
        
        client = Client()
        client.force_login(self.gm_user)
        
        test_file = self.create_test_image()
        
        response = client.post(
            f'/api/schedules/handouts/{self.handout.id}/attachments/',
            {
                'file': test_file,
                'description': 'テスト用画像ファイル'
            }
        )
        
        self.assertEqual(response.status_code, 201)
        
        data = response.json()
        self.assertIn('id', data)
        self.assertIn('file_url', data)
        self.assertEqual(data['original_filename'], 'api_test_image.jpg')
        self.assertEqual(data['file_type'], 'image')
    
    def test_attachment_list_api(self):
        """添付ファイル一覧APIのテスト"""
        from django.test import Client
        
        client = Client()
        client.force_login(self.player1)
        
        response = client.get(f'/api/schedules/handouts/{self.handout.id}/attachments/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsInstance(data, list)
    
    def test_attachment_delete_api(self):
        """添付ファイル削除APIのテスト"""
        from django.test import Client
        
        client = Client()
        client.force_login(self.gm_user)
        
        # 存在しない添付ファイルIDでのテスト（まだAPIが存在しないので404になるはず）
        response = client.delete('/api/schedules/attachments/1/')
        self.assertEqual(response.status_code, 404)
    
    def test_attachment_permission_api(self):
        """添付ファイル権限チェックAPIのテスト"""
        from django.test import Client
        
        # 権限のないユーザー
        other_user = CustomUser.objects.create_user(
            username='other_user',
            email='other@example.com'
        )
        
        client = Client()
        client.force_login(other_user)
        
        response = client.get(f'/api/schedules/handouts/{self.handout.id}/attachments/')
        # 権限がない場合は403または404が返される
        self.assertIn(response.status_code, [403, 404])


@unittest.skip("Integration test - will be implemented after basic functionality")
class HandoutAttachmentIntegrationTest(TestCase):
    """ハンドアウト添付ファイル機能の統合テスト"""
    
    def test_end_to_end_attachment_flow(self):
        """エンドツーエンドの添付ファイルフロー"""
        # この統合テストは基本機能実装後に実装する
        pass