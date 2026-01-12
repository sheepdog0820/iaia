"""
キャラクター複数画像アップロード機能のテスト
TDDアプローチで実装前にテストを作成
"""
import os
import tempfile
from PIL import Image
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.base import ContentFile
from rest_framework.test import APITestCase
from rest_framework import status
from accounts.models import CharacterSheet, CharacterImage

User = get_user_model()


class CharacterImageModelTestCase(TestCase):
    """CharacterImageモデルのテストケース"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='テストキャラクター',
            edition='6th',
            age=25,
            str_value=50,
            con_value=60,
            pow_value=55,
            dex_value=65,
            app_value=50,
            siz_value=60,
            int_value=70,
            edu_value=75
        )
    
    def create_test_image(self, name='test.png', size=(100, 100)):
        """テスト用画像ファイルを作成"""
        file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        image = Image.new('RGB', size, color='red')
        image.save(file, 'PNG')
        file.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=file.read(),
            content_type='image/png'
        )
    
    def test_create_character_image(self):
        """画像の作成テスト"""
        image_file = self.create_test_image()
        character_image = CharacterImage.objects.create(
            character_sheet=self.character,
            image=image_file,
            is_main=True,
            order=0
        )
        
        self.assertEqual(character_image.character_sheet, self.character)
        self.assertTrue(character_image.is_main)
        self.assertEqual(character_image.order, 0)
        self.assertIsNotNone(character_image.uploaded_at)
    
    def test_unique_main_image_constraint(self):
        """メイン画像の一意性制約テスト"""
        # 最初のメイン画像
        image1 = self.create_test_image('test1.png')
        CharacterImage.objects.create(
            character_sheet=self.character,
            image=image1,
            is_main=True
        )
        
        # 2つ目のメイン画像を作成しようとすると制約違反
        image2 = self.create_test_image('test2.png')
        with self.assertRaises(Exception):
            CharacterImage.objects.create(
                character_sheet=self.character,
                image=image2,
                is_main=True
            )
    
    def test_image_ordering(self):
        """画像の並び順テスト"""
        # 複数の画像を異なる順序で作成
        for i in [2, 0, 1]:
            image = self.create_test_image(f'test{i}.png')
            CharacterImage.objects.create(
                character_sheet=self.character,
                image=image,
                order=i
            )
        
        # orderフィールドで並んでいることを確認
        images = CharacterImage.objects.filter(character_sheet=self.character)
        orders = [img.order for img in images]
        self.assertEqual(orders, [0, 1, 2])
    
    def test_cascade_delete(self):
        """キャラクター削除時の画像削除テスト"""
        # 画像を作成
        image = self.create_test_image()
        CharacterImage.objects.create(
            character_sheet=self.character,
            image=image
        )
        
        # キャラクターを削除
        self.character.delete()
        
        # 画像も削除されていることを確認
        self.assertEqual(CharacterImage.objects.count(), 0)


class CharacterImageAPITestCase(APITestCase):
    """複数画像アップロードAPIのテストケース"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='テストキャラクター',
            edition='6th',
            age=25,
            str_value=50,
            con_value=60,
            pow_value=55,
            dex_value=65,
            app_value=50,
            siz_value=60,
            int_value=70,
            edu_value=75
        )
        self.client.force_authenticate(user=self.user)
    
    def create_test_image(self, name='test.png', size=(100, 100)):
        """テスト用画像ファイルを作成"""
        file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        image = Image.new('RGB', size, color='red')
        image.save(file, 'PNG')
        file.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=file.read(),
            content_type='image/png'
        )
    
    def test_upload_single_image(self):
        """単一画像のアップロードテスト"""
        image = self.create_test_image()
        url = reverse('character-image-list', kwargs={'character_id': self.character.id})
        
        response = self.client.post(url, {
            'image': image,
            'is_main': True
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CharacterImage.objects.count(), 1)
        self.assertTrue(response.data['is_main'])
        self.assertIn('image_url', response.data)
        self.assertIn('thumbnail_url', response.data)
    
    def test_upload_multiple_images(self):
        """複数画像の同時アップロードテスト"""
        images = [self.create_test_image(f'test{i}.png') for i in range(3)]
        url = reverse('character-image-list', kwargs={'character_id': self.character.id})
        
        for i, image in enumerate(images):
            response = self.client.post(url, {
                'image': image,
                'order': i
            }, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.assertEqual(CharacterImage.objects.count(), 3)
    
    def test_image_count_limit(self):
        """画像数制限のテスト（10枚まで）"""
        url = reverse('character-image-list', kwargs={'character_id': self.character.id})
        
        # 10枚まではアップロード可能
        for i in range(10):
            image = self.create_test_image(f'test{i}.png')
            response = self.client.post(url, {
                'image': image
            }, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 11枚目はエラー
        image = self.create_test_image('test11.png')
        response = self.client.post(url, {
            'image': image
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('最大10枚', str(response.data))
    
    def test_file_size_limit(self):
        """ファイルサイズ制限のテスト（5MB）"""
        # 5MB超のファイルを作成
        large_image = self.create_test_image('large.png', size=(3000, 3000))
        url = reverse('character-image-list', kwargs={'character_id': self.character.id})
        
        response = self.client.post(url, {
            'image': large_image
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('5MB', str(response.data))
    
    def test_total_size_limit(self):
        """総容量制限のテスト（30MB）"""
        url = reverse('character-image-list', kwargs={'character_id': self.character.id})
        
        # 4MBの画像を8枚アップロードしようとする（32MB）
        for i in range(8):
            image = self.create_test_image(f'test{i}.png', size=(2000, 2000))
            response = self.client.post(url, {
                'image': image
            }, format='multipart')
            
            if i < 7:  # 7枚目まではOK
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            else:  # 8枚目でエラー
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('30MB', str(response.data))
    
    def test_invalid_file_format(self):
        """無効なファイル形式のテスト"""
        # テキストファイルをアップロード
        invalid_file = SimpleUploadedFile(
            name='test.txt',
            content=b'This is not an image',
            content_type='text/plain'
        )
        url = reverse('character-image-list', kwargs={'character_id': self.character.id})
        
        response = self.client.post(url, {
            'image': invalid_file
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('画像ファイル', str(response.data))
    
    def test_list_character_images(self):
        """画像一覧取得のテスト"""
        # 複数の画像を作成
        for i in range(3):
            image = self.create_test_image(f'test{i}.png')
            CharacterImage.objects.create(
                character_sheet=self.character,
                image=image,
                order=i,
                is_main=(i == 0)
            )
        
        url = reverse('character-image-list', kwargs={'character_id': self.character.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 3)
        self.assertTrue(response.data['results'][0]['is_main'])
    
    def test_update_image_order(self):
        """画像順序更新のテスト"""
        # 3つの画像を作成
        images = []
        for i in range(3):
            image = self.create_test_image(f'test{i}.png')
            img_obj = CharacterImage.objects.create(
                character_sheet=self.character,
                image=image,
                order=i
            )
            images.append(img_obj)
        
        # 順序を逆転
        url = reverse('character-image-reorder', kwargs={'character_id': self.character.id})
        response = self.client.patch(url, {
            'order': [
                {'id': images[2].id, 'order': 0},
                {'id': images[1].id, 'order': 1},
                {'id': images[0].id, 'order': 2}
            ]
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 順序が更新されていることを確認
        images[0].refresh_from_db()
        images[2].refresh_from_db()
        self.assertEqual(images[0].order, 2)
        self.assertEqual(images[2].order, 0)
    
    def test_delete_image(self):
        """画像削除のテスト"""
        image = self.create_test_image()
        img_obj = CharacterImage.objects.create(
            character_sheet=self.character,
            image=image
        )
        
        url = reverse('character-image-detail', kwargs={
            'character_id': self.character.id,
            'pk': img_obj.id
        })
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CharacterImage.objects.count(), 0)
    
    def test_set_main_image(self):
        """メイン画像設定のテスト"""
        # 2つの画像を作成
        img1 = CharacterImage.objects.create(
            character_sheet=self.character,
            image=self.create_test_image('test1.png'),
            is_main=True
        )
        img2 = CharacterImage.objects.create(
            character_sheet=self.character,
            image=self.create_test_image('test2.png'),
            is_main=False
        )
        
        # img2をメイン画像に設定
        url = reverse('character-image-set-main', kwargs={
            'character_id': self.character.id,
            'pk': img2.id
        })
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # メイン画像が切り替わっていることを確認
        img1.refresh_from_db()
        img2.refresh_from_db()
        self.assertFalse(img1.is_main)
        self.assertTrue(img2.is_main)
    
    def test_permission_denied_other_user(self):
        """他ユーザーの画像操作権限エラーテスト"""
        # 他ユーザーとして認証
        self.client.force_authenticate(user=self.other_user)
        
        # アップロード試行
        image = self.create_test_image()
        url = reverse('character-image-list', kwargs={'character_id': self.character.id})
        response = self.client.post(url, {
            'image': image
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_character_not_found(self):
        """存在しないキャラクターへのアップロードテスト"""
        image = self.create_test_image()
        url = reverse('character-image-list', kwargs={'character_id': 99999})
        
        response = self.client.post(url, {
            'image': image
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CharacterImageIntegrationTestCase(TestCase):
    """複数画像機能の統合テスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def create_test_image(self, name='test.png'):
        """テスト用画像ファイルを作成"""
        file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        image = Image.new('RGB', (100, 100), color='red')
        image.save(file, 'PNG')
        file.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=file.read(),
            content_type='image/png'
        )
    
    def test_character_creation_with_multiple_images(self):
        """キャラクター作成時の複数画像アップロードテスト"""
        # キャラクター作成画面を表示
        response = self.client.get(reverse('character_create_6th'))
        self.assertEqual(response.status_code, 200)
        
        # 複数画像付きでキャラクターを作成
        images = [self.create_test_image(f'test{i}.png') for i in range(3)]
        
        form_data = {
            'name': 'テストキャラクター',
            'age': '25',
            'occupation': '探偵',
            'birthplace': '東京',
            'str_value': '10',
            'con_value': '12',
            'pow_value': '14',
            'dex_value': '11',
            'app_value': '13',
            'siz_value': '10',
            'int_value': '15',
            'edu_value': '16',
            'hp': '11',
            'mp': '14',
            'san_value': '70',
            'damage_bonus': '0',
            'images': images  # 複数画像
        }
        
        response = self.client.post(
            reverse('character_create_6th'),
            data=form_data,
            follow=True
        )
        
        # キャラクターが作成されたことを確認
        self.assertEqual(response.status_code, 200)
        character = CharacterSheet.objects.get(name='テストキャラクター')
        
        # 画像が保存されていることを確認
        self.assertEqual(character.images.count(), 3)
    
    def test_character_detail_with_images(self):
        """画像付きキャラクター詳細表示テスト"""
        # キャラクターと画像を作成
        character = CharacterSheet.objects.create(
            user=self.user,
            name='テストキャラクター',
            edition='6th',
            age=25,
            str_value=50,
            con_value=60,
            pow_value=55,
            dex_value=65,
            app_value=50,
            siz_value=60,
            int_value=70,
            edu_value=75
        )
        
        for i in range(3):
            CharacterImage.objects.create(
                character_sheet=character,
                image=self.create_test_image(f'test{i}.png'),
                order=i,
                is_main=(i == 0)
            )
        
        # 詳細画面を表示
        response = self.client.get(
            reverse('character_detail_6th', kwargs={'character_id': character.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test0.png')  # メイン画像
        self.assertContains(response, 'test1.png')
        self.assertContains(response, 'test2.png')
    
    def test_image_preview_on_edit(self):
        """編集画面での画像プレビューテスト"""
        # キャラクターと画像を作成
        character = CharacterSheet.objects.create(
            user=self.user,
            name='テストキャラクター',
            edition='6th',
            age=25,
            str_value=50,
            con_value=60,
            pow_value=55,
            dex_value=65,
            app_value=50,
            siz_value=60,
            int_value=70,
            edu_value=75
        )
        
        CharacterImage.objects.create(
            character_sheet=character,
            image=self.create_test_image(),
            is_main=True
        )
        
        # 編集画面を表示
        response = self.client.get(
            reverse('character_edit', kwargs={'character_id': character.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'image-preview')  # プレビュー要素
    
    def test_drag_and_drop_upload(self):
        """ドラッグ&ドロップアップロードのテスト"""
        character = CharacterSheet.objects.create(
            user=self.user,
            name='テストキャラクター',
            edition='6th',
            age=25,
            str_value=50,
            con_value=60,
            pow_value=55,
            dex_value=65,
            app_value=50,
            siz_value=60,
            int_value=70,
            edu_value=75
        )
        
        # ドラッグ&ドロップエリアの存在確認
        response = self.client.get(
            reverse('character_edit', kwargs={'character_id': character.pk})
        )
        
        self.assertContains(response, 'drop-zone')
        self.assertContains(response, 'dragover')
        self.assertContains(response, 'dragleave')
        self.assertContains(response, 'drop')
