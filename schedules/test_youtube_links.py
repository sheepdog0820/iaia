"""
セッションYouTubeリンク機能のテスト
"""

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta
from unittest.mock import patch, Mock
from accounts.models import CustomUser, Group
from schedules.models import TRPGSession, SessionParticipant


class SessionYouTubeLinkModelTestCase(TestCase):
    """SessionYouTubeLinkモデルのテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.gm = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            password='password',
            nickname='GMユーザー'
        )
        
        self.player = CustomUser.objects.create_user(
            username='player',
            email='player@example.com',
            password='password',
            nickname='プレイヤー'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='テストグループ',
            created_by=self.gm
        )
        self.group.members.add(self.gm, self.player)
        
        # セッション作成
        self.session = TRPGSession.objects.create(
            title='テストセッション',
            description='YouTubeリンクのテスト',
            date=timezone.now() + timedelta(days=7),
            gm=self.gm,
            group=self.group,
            status='planned'
        )
    
    def test_extract_video_id_from_standard_url(self):
        """標準的なYouTube URLから動画ID抽出"""
        from schedules.models import SessionYouTubeLink
        
        urls = [
            ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtube.com/watch?v=dQw4w9WgXcQ&feature=share', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/embed/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/live/dQw4w9WgXcQ?feature=share', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/shorts/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
        ]
        
        for url, expected_id in urls:
            with self.subTest(url=url):
                video_id = SessionYouTubeLink.extract_video_id(url)
                self.assertEqual(video_id, expected_id)
    
    def test_extract_video_id_invalid_url(self):
        """無効なURLからの動画ID抽出"""
        from schedules.models import SessionYouTubeLink
        
        invalid_urls = [
            'https://www.google.com',
            'not_a_url',
            'https://vimeo.com/123456',
            '',
            None
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                video_id = SessionYouTubeLink.extract_video_id(url)
                self.assertIsNone(video_id)
    
    def test_duration_display_formats(self):
        """再生時間の表示形式テスト"""
        from schedules.models import SessionYouTubeLink
        
        test_cases = [
            (30, '0:30'),      # 30秒
            (90, '1:30'),      # 1分30秒
            (3600, '1:00:00'), # 1時間
            (3661, '1:01:01'), # 1時間1分1秒
            (7322, '2:02:02'), # 2時間2分2秒
        ]
        
        for seconds, expected_display in test_cases:
            with self.subTest(seconds=seconds):
                link = SessionYouTubeLink(
                    session=self.session,
                    youtube_url='https://youtube.com/watch?v=test',
                    video_id='test',
                    title='Test Video',
                    duration_seconds=seconds,
                    added_by=self.gm
                )
                self.assertEqual(link.duration_display, expected_display)
    
    def test_auto_order_assignment(self):
        """自動順序設定のテスト"""
        from schedules.models import SessionYouTubeLink
        
        # 最初のリンク
        link1 = SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=test1',
            video_id='test1',
            title='First Video',
            added_by=self.gm
        )
        self.assertEqual(link1.order, 1)
        
        # 2番目のリンク
        link2 = SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=test2',
            video_id='test2',
            title='Second Video',
            added_by=self.gm
        )
        self.assertEqual(link2.order, 2)
        
        # 3番目のリンク
        link3 = SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=test3',
            video_id='test3',
            title='Third Video',
            added_by=self.player
        )
        self.assertEqual(link3.order, 3)
    
    def test_unique_video_per_session(self):
        """同一セッション内での動画重複防止"""
        from schedules.models import SessionYouTubeLink
        from django.db import IntegrityError
        
        # 最初のリンク作成
        SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=dQw4w9WgXcQ',
            video_id='dQw4w9WgXcQ',
            title='Original Video',
            added_by=self.gm
        )
        
        # 同じ動画IDで作成しようとするとエラー
        with self.assertRaises(IntegrityError):
            SessionYouTubeLink.objects.create(
                session=self.session,
                youtube_url='https://youtu.be/dQw4w9WgXcQ',  # 異なるURL形式
                video_id='dQw4w9WgXcQ',  # 同じ動画ID
                title='Duplicate Video',
                added_by=self.player
            )
    
    def test_description_field(self):
        """備考フィールドのテスト"""
        from schedules.models import SessionYouTubeLink
        
        description = "このセッションのハイライトシーン。\n15:30からの戦闘シーンは必見！"
        link = SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=test',
            video_id='test',
            title='Session Highlight',
            description=description,
            added_by=self.gm
        )
        
        self.assertEqual(link.description, description)


class SessionYouTubeLinkAPITestCase(APITestCase):
    """YouTube動画リンクAPIのテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.gm = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            password='password',
            nickname='GMユーザー'
        )
        
        self.player1 = CustomUser.objects.create_user(
            username='player1',
            email='player1@example.com',
            password='password',
            nickname='プレイヤー1'
        )
        
        self.player2 = CustomUser.objects.create_user(
            username='player2',
            email='player2@example.com',
            password='password',
            nickname='プレイヤー2'
        )
        
        self.other_user = CustomUser.objects.create_user(
            username='other',
            email='other@example.com',
            password='password',
            nickname='その他ユーザー'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='テストグループ',
            created_by=self.gm
        )
        self.group.members.add(self.gm, self.player1, self.player2)
        
        # セッション作成
        self.session = TRPGSession.objects.create(
            title='YouTubeテストセッション',
            description='動画リンクのテスト',
            date=timezone.now() + timedelta(days=7),
            gm=self.gm,
            group=self.group,
            status='planned'
        )
        
        # 参加者追加
        SessionParticipant.objects.create(
            session=self.session,
            user=self.player1,
            role='player'
        )
    
    @patch('schedules.services.YouTubeService.fetch_video_info')
    def test_gm_can_add_youtube_link(self, mock_fetch):
        """GMがYouTube動画を追加できる"""
        self.client.force_authenticate(user=self.gm)
        
        # モックの設定
        mock_fetch.return_value = {
            'title': 'Test Video Title',
            'channel_name': 'Test Channel',
            'thumbnail_url': 'https://i.ytimg.com/vi/test/maxresdefault.jpg',
            'duration': 213
        }
        
        data = {
            'youtube_url': 'https://www.youtube.com/watch?v=test123',
            'description': 'セッションのハイライト',
            'perspective': 'GM視点',
            'part_number': 1,
        }
        
        response = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/youtube-links/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['video_id'], 'test123')
        self.assertEqual(response.data['title'], 'Test Video Title')
        self.assertEqual(response.data['duration_seconds'], 213)
        self.assertEqual(response.data['duration_display'], '3:33')
        self.assertEqual(response.data['description'], 'セッションのハイライト')
        self.assertEqual(response.data['perspective'], 'GM視点')
        self.assertEqual(response.data['part_number'], 1)
        self.assertEqual(response.data['added_by'], self.gm.id)
    
    @patch('schedules.services.YouTubeService.fetch_video_info')
    def test_participant_can_add_youtube_link(self, mock_fetch):
        """参加者がYouTube動画を追加できる"""
        self.client.force_authenticate(user=self.player1)
        
        mock_fetch.return_value = {
            'title': 'Player Video',
            'channel_name': 'Player Channel',
            'thumbnail_url': 'https://i.ytimg.com/vi/player/maxresdefault.jpg',
            'duration': 120
        }
        
        data = {
            'youtube_url': 'https://youtu.be/player123',
            'description': 'プレイヤー視点の動画',
            'perspective': 'PL1視点',
            'part_number': 2,
        }
        
        response = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/youtube-links/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['video_id'], 'player123')
        self.assertEqual(response.data['added_by'], self.player1.id)
        self.assertEqual(response.data['perspective'], 'PL1視点')
        self.assertEqual(response.data['part_number'], 2)

    @patch('schedules.services.YouTubeService.fetch_video_info')
    def test_part_number_validation(self, mock_fetch):
        """パート番号は1以上でなければならない"""
        self.client.force_authenticate(user=self.gm)

        mock_fetch.return_value = {
            'title': 'Test Video Title',
            'channel_name': 'Test Channel',
            'thumbnail_url': 'https://i.ytimg.com/vi/test/maxresdefault.jpg',
            'duration': 213
        }

        response = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/youtube-links/',
            {'youtube_url': 'https://www.youtube.com/watch?v=part0', 'part_number': 0},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('part_number', response.data)
    
    def test_non_participant_cannot_add_youtube_link(self):
        """非参加者はYouTube動画を追加できない"""
        self.client.force_authenticate(user=self.other_user)
        
        data = {
            'youtube_url': 'https://youtube.com/watch?v=forbidden',
            'description': '追加できないはず'
        }
        
        response = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/youtube-links/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_fetch_video_info_endpoint(self):
        """動画情報取得エンドポイントのテスト"""
        self.client.force_authenticate(user=self.gm)
        
        with patch('schedules.services.YouTubeService.fetch_video_info') as mock_fetch:
            mock_fetch.return_value = {
                'title': 'Fetched Video',
                'channel_name': 'Fetched Channel',
                'thumbnail_url': 'https://i.ytimg.com/vi/fetched/maxresdefault.jpg',
                'duration': 3661
            }
            
            data = {
                'youtube_url': 'https://www.youtube.com/watch?v=fetched123'
            }
            
            response = self.client.post(
                '/api/schedules/youtube-links/fetch_info/',
                data,
                format='json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['video_id'], 'fetched123')
            self.assertEqual(response.data['title'], 'Fetched Video')
            self.assertEqual(response.data['duration_seconds'], 3661)
    
    def test_update_youtube_link(self):
        """YouTube動画リンクの更新（備考のみ）"""
        from schedules.models import SessionYouTubeLink
        
        # リンク作成
        link = SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=update_test',
            video_id='update_test',
            title='Original Title',
            description='元の備考',
            added_by=self.player1
        )
        
        # 追加者が更新
        self.client.force_authenticate(user=self.player1)
        
        data = {
            'description': '更新された備考'
        }
        
        response = self.client.patch(
            f'/api/schedules/youtube-links/{link.id}/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], '更新された備考')
        
        # 他のプレイヤーは更新できない
        self.client.force_authenticate(user=self.player2)
        
        response = self.client.patch(
            f'/api/schedules/youtube-links/{link.id}/',
            {'description': '不正な更新'},
            format='json'
        )
        
        # 404が返される（ViewSetのget_queryset制限のため）
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_delete_youtube_link_permissions(self):
        """YouTube動画リンクの削除権限"""
        from schedules.models import SessionYouTubeLink
        
        # プレイヤーがリンク追加
        link = SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=delete_test',
            video_id='delete_test',
            title='To Be Deleted',
            added_by=self.player1
        )
        
        # 追加者は削除できる
        self.client.force_authenticate(user=self.player1)
        response = self.client.delete(f'/api/schedules/youtube-links/{link.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 別のリンクを作成
        link2 = SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=delete_test2',
            video_id='delete_test2',
            title='GM Can Delete',
            added_by=self.player1
        )
        
        # GMも削除できる
        self.client.force_authenticate(user=self.gm)
        response = self.client.delete(f'/api/schedules/youtube-links/{link2.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 別のリンクを作成
        link3 = SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=delete_test3',
            video_id='delete_test3',
            title='Others Cannot Delete',
            added_by=self.player1
        )
        
        # 他のプレイヤーは削除できない
        self.client.force_authenticate(user=self.player2)
        response = self.client.delete(f'/api/schedules/youtube-links/{link3.id}/')
        # 404が返される（ViewSetのget_queryset制限のため）
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_reorder_youtube_links(self):
        """YouTube動画リンクの順序変更（GMのみ）"""
        from schedules.models import SessionYouTubeLink
        
        # 複数のリンクを作成
        link1 = SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=order1',
            video_id='order1',
            title='First',
            added_by=self.gm
        )
        
        link2 = SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=order2',
            video_id='order2',
            title='Second',
            added_by=self.player1
        )
        
        link3 = SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=order3',
            video_id='order3',
            title='Third',
            added_by=self.player1
        )
        
        # GMが順序変更
        self.client.force_authenticate(user=self.gm)
        response = self.client.post(
            f'/api/schedules/youtube-links/{link3.id}/reorder/',
            {'order': 1},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['order'], 1)
        
        # プレイヤーは順序変更できない
        self.client.force_authenticate(user=self.player1)
        response = self.client.post(
            f'/api/schedules/youtube-links/{link2.id}/reorder/',
            {'order': 3},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_list_youtube_links_for_session(self):
        """セッションのYouTube動画リンク一覧取得"""
        from schedules.models import SessionYouTubeLink
        
        # 複数のリンクを作成
        links = []
        for i in range(3):
            link = SessionYouTubeLink.objects.create(
                session=self.session,
                youtube_url=f'https://youtube.com/watch?v=list{i}',
                video_id=f'list{i}',
                title=f'Video {i+1}',
                duration_seconds=(i+1) * 100,
                added_by=self.gm if i == 0 else self.player1
            )
            links.append(link)
        
        self.client.force_authenticate(user=self.gm)
        response = self.client.get(
            f'/api/schedules/sessions/{self.session.id}/youtube-links/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        
        # 順序通りに返されるか確認
        for i, link_data in enumerate(response.data):
            self.assertEqual(link_data['video_id'], f'list{i}')
            self.assertEqual(link_data['order'], i + 1)
    
    def test_session_detail_includes_youtube_links(self):
        """セッション詳細にYouTube動画リンク情報が含まれる"""
        from schedules.models import SessionYouTubeLink
        
        # リンクを2つ追加
        for i in range(2):
            SessionYouTubeLink.objects.create(
                session=self.session,
                youtube_url=f'https://youtube.com/watch?v=detail{i}',
                video_id=f'detail{i}',
                title=f'Session Video {i+1}',
                duration_seconds=300,
                channel_name=f'Channel {i+1}',
                added_by=self.gm
            )
        
        self.client.force_authenticate(user=self.gm)
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('youtube_links_detail', response.data)
        self.assertEqual(len(response.data['youtube_links_detail']), 2)
        
        # リンク情報の確認
        for i, link_data in enumerate(response.data['youtube_links_detail']):
            self.assertEqual(link_data['title'], f'Session Video {i+1}')
            self.assertEqual(link_data['duration_display'], '5:00')


class YouTubeServiceTestCase(TestCase):
    """YouTube APIサービスのテスト"""
    
    @patch('schedules.services.getattr')
    @patch('requests.get')
    def test_fetch_video_info_success(self, mock_get, mock_getattr):
        """動画情報の正常取得"""
        from schedules.services import YouTubeService
        
        # APIキーが設定されているふりをする
        mock_getattr.return_value = 'test_api_key'
        
        # モックレスポンス
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [{
                'snippet': {
                    'title': 'Test Video Title',
                    'channelTitle': 'Test Channel',
                    'thumbnails': {
                        'maxres': {
                            'url': 'https://i.ytimg.com/vi/test/maxresdefault.jpg'
                        }
                    }
                },
                'contentDetails': {
                    'duration': 'PT3M33S'  # 3分33秒
                }
            }]
        }
        mock_get.return_value = mock_response
        
        result = YouTubeService.fetch_video_info('test_video_id')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Test Video Title')
        self.assertEqual(result['channel_name'], 'Test Channel')
        self.assertEqual(result['duration'], 213)  # 3*60 + 33
    
    def test_parse_duration_various_formats(self):
        """ISO 8601期間形式のパース"""
        from schedules.services import YouTubeService
        
        test_cases = [
            ('PT30S', 30),           # 30秒
            ('PT1M30S', 90),         # 1分30秒
            ('PT1H', 3600),          # 1時間
            ('PT1H1M1S', 3661),      # 1時間1分1秒
            ('PT2H30M', 9000),       # 2時間30分
            ('PT10M', 600),          # 10分
        ]
        
        for duration_str, expected_seconds in test_cases:
            with self.subTest(duration=duration_str):
                result = YouTubeService.parse_duration(duration_str)
                self.assertEqual(result, expected_seconds)
    
    @patch('schedules.services.getattr')
    @patch('requests.get')
    def test_fetch_video_info_not_found(self, mock_get, mock_getattr):
        """存在しない動画の情報取得"""
        from schedules.services import YouTubeService
        
        mock_getattr.return_value = 'test_api_key'
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': []  # 動画が見つからない
        }
        mock_get.return_value = mock_response
        
        result = YouTubeService.fetch_video_info('nonexistent_id')
        self.assertIsNone(result)
    
    @patch('schedules.services.getattr') 
    @patch('requests.get')
    def test_fetch_video_info_api_error(self, mock_get, mock_getattr):
        """API エラー時の処理"""
        from schedules.services import YouTubeService
        
        mock_getattr.return_value = 'test_api_key'
        
        mock_response = Mock()
        mock_response.status_code = 403  # API制限等
        mock_get.return_value = mock_response
        
        result = YouTubeService.fetch_video_info('test_id')
        self.assertIsNone(result)


class YouTubeLinkStatisticsTestCase(TestCase):
    """YouTube動画リンク統計機能のテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.gm = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            password='password',
            nickname='GMユーザー'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='テストグループ',
            created_by=self.gm
        )
        self.group.members.add(self.gm)
        
        # セッション作成
        self.session = TRPGSession.objects.create(
            title='統計テストセッション',
            description='統計機能のテスト',
            date=timezone.now() + timedelta(days=7),
            gm=self.gm,
            group=self.group,
            status='planned'
        )
        
    def test_get_session_total_duration(self):
        """セッションの動画合計時間取得"""
        from schedules.models import SessionYouTubeLink
        
        # 複数の動画を追加
        SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=test1',
            video_id='test1',
            title='Video 1',
            duration_seconds=300,  # 5分
            channel_name='Channel A',
            added_by=self.gm
        )
        
        SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=test2',
            video_id='test2',
            title='Video 2',
            duration_seconds=600,  # 10分
            channel_name='Channel B',
            added_by=self.gm
        )
        
        SessionYouTubeLink.objects.create(
            session=self.session,
            youtube_url='https://youtube.com/watch?v=test3',
            video_id='test3',
            title='Video 3',
            duration_seconds=900,  # 15分
            channel_name='Channel A',
            added_by=self.gm
        )
        
        # 合計時間の確認
        total = SessionYouTubeLink.get_session_total_duration(self.session)
        self.assertEqual(total, 1800)  # 30分 = 1800秒
        
    def test_get_session_statistics(self):
        """セッションの動画統計情報取得"""
        from schedules.models import SessionYouTubeLink
        
        # 複数の動画を追加
        videos = [
            ('test1', 'Short Video', 180, 'Channel A'),    # 3分
            ('test2', 'Medium Video', 600, 'Channel B'),   # 10分
            ('test3', 'Long Video', 1200, 'Channel A'),    # 20分
            ('test4', 'Another Video', 300, 'Channel A'),  # 5分
            ('test5', 'Last Video', 420, 'Channel B'),     # 7分
        ]
        
        for video_id, title, duration, channel in videos:
            SessionYouTubeLink.objects.create(
                session=self.session,
                youtube_url=f'https://youtube.com/watch?v={video_id}',
                video_id=video_id,
                title=title,
                duration_seconds=duration,
                channel_name=channel,
                added_by=self.gm
            )
        
        # 統計情報の取得
        stats = SessionYouTubeLink.get_session_statistics(self.session)
        
        # 基本統計の確認
        self.assertEqual(stats['video_count'], 5)
        self.assertEqual(stats['total_duration_seconds'], 2700)  # 45分
        self.assertEqual(stats['total_duration_display'], '45:00')
        self.assertEqual(stats['average_duration_seconds'], 540)  # 9分
        self.assertEqual(stats['average_duration_display'], '9:00')
        
        # チャンネル別統計の確認
        channel_breakdown = stats['channel_breakdown']
        self.assertEqual(len(channel_breakdown), 2)
        
        # Channel Aの統計
        channel_a = next(c for c in channel_breakdown if c['channel_name'] == 'Channel A')
        self.assertEqual(channel_a['video_count'], 3)
        self.assertEqual(channel_a['total_duration'], 1680)  # 28分
        
        # Channel Bの統計
        channel_b = next(c for c in channel_breakdown if c['channel_name'] == 'Channel B')
        self.assertEqual(channel_b['video_count'], 2)
        self.assertEqual(channel_b['total_duration'], 1020)  # 17分
        
    def test_format_duration(self):
        """時間フォーマット関数のテスト"""
        from schedules.models import SessionYouTubeLink
        
        test_cases = [
            (0, '0:00'),
            (59, '0:59'),
            (60, '1:00'),
            (3599, '59:59'),
            (3600, '1:00:00'),
            (7200, '2:00:00'),
            (7322, '2:02:02'),
            (86400, '24:00:00'),  # 24時間
        ]
        
        for seconds, expected in test_cases:
            with self.subTest(seconds=seconds):
                result = SessionYouTubeLink.format_duration(seconds)
                self.assertEqual(result, expected)
                
    def test_empty_session_statistics(self):
        """動画がないセッションの統計情報"""
        from schedules.models import SessionYouTubeLink
        
        stats = SessionYouTubeLink.get_session_statistics(self.session)
        
        self.assertEqual(stats['video_count'], 0)
        self.assertEqual(stats['total_duration_seconds'], 0)
        self.assertEqual(stats['total_duration_display'], '0:00')
        self.assertEqual(stats['average_duration_seconds'], 0)
        self.assertEqual(stats['average_duration_display'], '0:00')
        self.assertEqual(len(stats['channel_breakdown']), 0)


class YouTubeLinkStatisticsAPITestCase(APITestCase):
    """YouTube動画統計APIのテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.gm = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            password='password',
            nickname='GMユーザー'
        )
        
        self.player = CustomUser.objects.create_user(
            username='player',
            email='player@example.com',
            password='password',
            nickname='プレイヤー'
        )
        
        self.other_user = CustomUser.objects.create_user(
            username='other',
            email='other@example.com',
            password='password',
            nickname='その他'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='テストグループ',
            created_by=self.gm
        )
        self.group.members.add(self.gm, self.player)
        
        # セッション作成
        self.session = TRPGSession.objects.create(
            title='統計APIテストセッション',
            description='統計APIのテスト',
            date=timezone.now() + timedelta(days=7),
            gm=self.gm,
            group=self.group,
            status='planned'
        )
        
        # 参加者追加
        SessionParticipant.objects.create(
            session=self.session,
            user=self.player,
            role='player'
        )
        
        # テスト動画追加
        from schedules.models import SessionYouTubeLink
        
        videos = [
            ('api1', 'API Test 1', 300, 'Test Channel'),
            ('api2', 'API Test 2', 600, 'Test Channel'),
            ('api3', 'API Test 3', 900, 'Another Channel'),
        ]
        
        for video_id, title, duration, channel in videos:
            SessionYouTubeLink.objects.create(
                session=self.session,
                youtube_url=f'https://youtube.com/watch?v={video_id}',
                video_id=video_id,
                title=title,
                duration_seconds=duration,
                channel_name=channel,
                added_by=self.gm
            )
    
    def test_get_statistics_as_gm(self):
        """GMが統計情報を取得"""
        self.client.force_authenticate(user=self.gm)
        
        response = self.client.get(
            f'/api/schedules/sessions/{self.session.id}/youtube-links/statistics/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['video_count'], 3)
        self.assertEqual(response.data['total_duration_seconds'], 1800)
        self.assertEqual(response.data['total_duration_display'], '30:00')
        
        # チャンネル別統計の確認
        channel_breakdown = response.data['channel_breakdown']
        self.assertEqual(len(channel_breakdown), 2)
        
    def test_get_statistics_as_participant(self):
        """参加者が統計情報を取得"""
        self.client.force_authenticate(user=self.player)
        
        response = self.client.get(
            f'/api/schedules/sessions/{self.session.id}/youtube-links/statistics/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['video_count'], 3)
        
    def test_get_statistics_as_non_participant(self):
        """非参加者は統計情報を取得できない"""
        self.client.force_authenticate(user=self.other_user)
        
        response = self.client.get(
            f'/api/schedules/sessions/{self.session.id}/youtube-links/statistics/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_youtube_links_total_in_session_detail(self):
        """セッション詳細に動画合計時間が含まれる"""
        self.client.force_authenticate(user=self.gm)
        
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('youtube_total_duration', response.data)
        self.assertEqual(response.data['youtube_total_duration'], 1800)
        self.assertIn('youtube_total_duration_display', response.data)
        self.assertEqual(response.data['youtube_total_duration_display'], '30:00')


if __name__ == '__main__':
    import django
    from django.test.utils import get_runner
    from django.conf import settings
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True, keepdb=True)
    
    failures = test_runner.run_tests([
        'schedules.test_youtube_links.SessionYouTubeLinkModelTestCase',
        'schedules.test_youtube_links.SessionYouTubeLinkAPITestCase',
        'schedules.test_youtube_links.YouTubeServiceTestCase',
        'schedules.test_youtube_links.YouTubeLinkStatisticsTestCase',
        'schedules.test_youtube_links.YouTubeLinkStatisticsAPITestCase'
    ])
    
    if failures:
        print(f"\n❌ {failures} 件のテストが失敗しました")
    else:
        print("\n✅ すべてのテストが成功しました！")
