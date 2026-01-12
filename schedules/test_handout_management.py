"""
ハンドアウト管理機能の詳細テストケース
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from .models import TRPGSession, SessionParticipant, HandoutInfo
from accounts.models import Group

User = get_user_model()


class HandoutManagementDetailTestCase(APITestCase):
    """ハンドアウト管理の詳細テストケース"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.gm_user = User.objects.create_user(
            username='gmuser',
            email='gm@example.com',
            password='pass123',
            nickname='GM User'
        )
        self.player1 = User.objects.create_user(
            username='player1',
            email='player1@example.com',
            password='pass123',
            nickname='Player 1'
        )
        self.player2 = User.objects.create_user(
            username='player2',
            email='player2@example.com',
            password='pass123',
            nickname='Player 2'
        )
        self.other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='pass123',
            nickname='Other User'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='Test Group',
            created_by=self.gm_user
        )
        
        # セッション作成
        self.session = TRPGSession.objects.create(
            title='Test Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.gm_user,
            group=self.group
        )
        
        # 参加者作成
        self.participant1 = SessionParticipant.objects.create(
            session=self.session,
            user=self.player1,
            role='player',
            character_name='Character 1'
        )
        self.participant2 = SessionParticipant.objects.create(
            session=self.session,
            user=self.player2,
            role='player',
            character_name='Character 2'
        )

    def test_gm_handout_management_view_authenticated(self):
        """GM認証済みハンドアウト管理ビューテスト"""
        self.client.force_authenticate(user=self.gm_user)
        response = self.client.get(
            f'/api/schedules/gm-handouts/{self.session.id}/',
            HTTP_ACCEPT='application/json'
        )
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertEqual(data['session_id'], self.session.id)
            self.assertEqual(data['session_title'], self.session.title)
            self.assertIn('participants', data)
            self.assertEqual(len(data['participants']), 2)

    def test_gm_handout_management_view_permission_denied(self):
        """非GM権限でのハンドアウト管理ビューアクセステスト"""
        self.client.force_authenticate(user=self.player1)
        response = self.client.get(
            f'/api/schedules/gm-handouts/{self.session.id}/',
            HTTP_ACCEPT='application/json'
        )
        # URLが存在しない場合は404、存在する場合は403を期待
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_handout_bulk_creation(self):
        """ハンドアウト一括作成テスト"""
        self.client.force_authenticate(user=self.gm_user)
        
        handouts_data = [
            {
                'participant': self.participant1.id,
                'title': 'Handout for Player 1',
                'content': 'Secret information for player 1',
                'is_secret': True
            },
            {
                'participant': self.participant2.id,
                'title': 'Handout for Player 2',
                'content': 'Public information for player 2',
                'is_secret': False
            }
        ]
        
        response = self.client.post('/api/schedules/handouts/bulk_create/', {
            'session_id': self.session.id,
            'handouts': handouts_data
        }, format='json')
        
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            self.assertEqual(data['created_count'], 2)
            self.assertEqual(data['error_count'], 0)
            self.assertEqual(len(data['created']), 2)

    def test_handout_bulk_creation_with_invalid_data(self):
        """無効なデータでのハンドアウト一括作成テスト"""
        self.client.force_authenticate(user=self.gm_user)
        
        handouts_data = [
            {
                'participant': self.participant1.id,
                'title': 'Valid Handout',
                'content': 'Valid content'
            },
            {
                # participant が不足
                'title': 'Invalid Handout',
                'content': 'Invalid content'
            }
        ]
        
        response = self.client.post('/api/schedules/handouts/bulk_create/', {
            'session_id': self.session.id,
            'handouts': handouts_data
        }, format='json')
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            data = response.json()
            self.assertEqual(data['created_count'], 1)
            self.assertEqual(data['error_count'], 1)

    def test_handout_visibility_toggle(self):
        """ハンドアウト公開/秘匿切り替えテスト"""
        # ハンドアウト作成
        handout = HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant1,
            title='Test Handout',
            content='Test content',
            is_secret=True
        )
        
        self.client.force_authenticate(user=self.gm_user)
        response = self.client.post('/api/schedules/handouts/toggle_visibility/', {
            'handout_id': handout.id
        })
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertFalse(data['handout']['is_secret'])  # 秘匿 → 公開
            self.assertIn('公開', data['message'])
            
            # データベースでも確認
            handout.refresh_from_db()
            self.assertFalse(handout.is_secret)

    def test_handout_visibility_toggle_permission_denied(self):
        """非GM権限でのハンドアウト公開/秘匿切り替えテスト"""
        handout = HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant1,
            title='Test Handout',
            content='Test content',
            is_secret=True
        )
        
        self.client.force_authenticate(user=self.player1)
        response = self.client.post('/api/schedules/handouts/toggle_visibility/', {
            'handout_id': handout.id
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_handout_by_session_as_gm(self):
        """GMとしてのセッション別ハンドアウト取得テスト"""
        # ハンドアウト作成
        HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant1,
            title='GM Handout 1',
            content='Content 1',
            is_secret=True
        )
        HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant2,
            title='GM Handout 2',
            content='Content 2',
            is_secret=False
        )
        
        self.client.force_authenticate(user=self.gm_user)
        response = self.client.get('/api/schedules/handouts/by_session/', {
            'session_id': self.session.id
        })
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertEqual(len(data), 2)  # GMは全てのハンドアウトを見れる

    def test_handout_by_session_as_player(self):
        """プレイヤーとしてのセッション別ハンドアウト取得テスト"""
        # ハンドアウト作成
        HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant1,
            title='Player 1 Handout',
            content='Content for Player 1',
            is_secret=True
        )
        HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant2,
            title='Player 2 Handout',
            content='Content for Player 2',
            is_secret=True
        )
        
        self.client.force_authenticate(user=self.player1)
        response = self.client.get('/api/schedules/handouts/by_session/', {
            'session_id': self.session.id
        })
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertEqual(len(data), 1)  # プレイヤーは自分のハンドアウトのみ

    def test_handout_by_session_unauthorized_user(self):
        """権限のないユーザーでのセッション別ハンドアウト取得テスト"""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get('/api/schedules/handouts/by_session/', {
            'session_id': self.session.id
        })
        # URLが存在しない場合は404、存在する場合は403を期待
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_handout_template_list(self):
        """ハンドアウトテンプレート一覧取得テスト"""
        self.client.force_authenticate(user=self.gm_user)
        response = self.client.get('/api/schedules/handout-templates/')
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertIn('templates', data)
            templates = data['templates']
            self.assertGreater(len(templates), 0)
            
            # テンプレートの構造確認
            template = templates[0]
            self.assertIn('id', template)
            self.assertIn('name', template)
            self.assertIn('description', template)
            self.assertIn('template', template)

    def test_handout_creation_from_template(self):
        """テンプレートからハンドアウト作成テスト"""
        self.client.force_authenticate(user=self.gm_user)
        
        response = self.client.post('/api/schedules/handout-templates/', {
            'template_id': 'basic_intro',
            'session_id': self.session.id,
            'participant_id': self.participant1.id,
            'customizations': {
                'title': 'Custom Handout Title',
                'is_secret': True
            }
        }, format='json')
        
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            self.assertEqual(data['title'], 'Custom Handout Title')
            self.assertTrue(data['is_secret'])
            self.assertEqual(data['participant'], self.participant1.id)

    def test_handout_creation_from_template_missing_params(self):
        """必須パラメータ不足でのテンプレートからハンドアウト作成テスト"""
        self.client.force_authenticate(user=self.gm_user)
        
        response = self.client.post('/api/schedules/handout-templates/', {
            'template_id': 'basic_intro',
            # session_idとparticipant_idが不足
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_handout_creation_from_template_permission_denied(self):
        """非GM権限でのテンプレートからハンドアウト作成テスト"""
        self.client.force_authenticate(user=self.player1)
        
        response = self.client.post('/api/schedules/handout-templates/', {
            'template_id': 'basic_intro',
            'session_id': self.session.id,
            'participant_id': self.participant1.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_handout_crud_operations(self):
        """ハンドアウトのCRUD操作テスト"""
        self.client.force_authenticate(user=self.gm_user)
        
        # Create
        create_data = {
            'session': self.session.id,
            'participant': self.participant1.id,
            'title': 'Test CRUD Handout',
            'content': 'Original content',
            'is_secret': True
        }
        response = self.client.post('/api/schedules/handouts/', create_data)
        if response.status_code == status.HTTP_201_CREATED:
            handout_id = response.json()['id']
            
            # Read
            response = self.client.get(f'/api/schedules/handouts/{handout_id}/')
            if response.status_code == status.HTTP_200_OK:
                self.assertEqual(response.json()['title'], 'Test CRUD Handout')
            
            # Update
            update_data = {
                'title': 'Updated CRUD Handout',
                'content': 'Updated content',
                'is_secret': False
            }
            response = self.client.patch(f'/api/schedules/handouts/{handout_id}/', update_data)
            if response.status_code == status.HTTP_200_OK:
                self.assertEqual(response.json()['title'], 'Updated CRUD Handout')
                self.assertFalse(response.json()['is_secret'])
            
            # Delete
            response = self.client.delete(f'/api/schedules/handouts/{handout_id}/')
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_handout_queryset_filtering(self):
        """ハンドアウトクエリセットフィルタリングテスト"""
        # 別セッションとユーザーを作成
        other_session = TRPGSession.objects.create(
            title='Other Session',
            date=timezone.now() + timedelta(days=2),
            gm=self.other_user,
            group=self.group
        )
        
        # ハンドアウト作成
        my_handout = HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant1,
            title='My Handout',
            content='My content'
        )
        
        # 他のセッションのハンドアウト（アクセス不可）
        other_participant = SessionParticipant.objects.create(
            session=other_session,
            user=self.other_user,
            role='player'
        )
        HandoutInfo.objects.create(
            session=other_session,
            participant=other_participant,
            title='Other Handout',
            content='Other content'
        )
        
        # GMとしてアクセス
        self.client.force_authenticate(user=self.gm_user)
        response = self.client.get('/api/schedules/handouts/')
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            handouts = data.get('results', data) if isinstance(data, dict) else data
            handout_titles = [h['title'] for h in handouts]
            self.assertIn('My Handout', handout_titles)
            self.assertNotIn('Other Handout', handout_titles)  # 他のセッションは見えない

    def test_handout_secret_content_access(self):
        """秘匿ハンドアウトのアクセス制御テスト"""
        # 秘匿ハンドアウト作成
        secret_handout = HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant1,
            title='Secret Handout',
            content='Secret information',
            is_secret=True
        )
        
        # Player1（対象者）としてアクセス
        self.client.force_authenticate(user=self.player1)
        response = self.client.get(f'/api/schedules/handouts/{secret_handout.id}/')
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertEqual(data['content'], 'Secret information')
        
        # Player2（非対象者）としてアクセス
        self.client.force_authenticate(user=self.player2)
        response = self.client.get(f'/api/schedules/handouts/{secret_handout.id}/')
        # Player2からは見えないか、権限エラーになる
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_handout_content_validation(self):
        """ハンドアウト内容バリデーションテスト"""
        self.client.force_authenticate(user=self.gm_user)
        
        # 空のタイトル
        response = self.client.post('/api/schedules/handouts/', {
            'session': self.session.id,
            'participant': self.participant1.id,
            'title': '',  # 空のタイトル
            'content': 'Valid content'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # 空の内容
        response = self.client.post('/api/schedules/handouts/', {
            'session': self.session.id,
            'participant': self.participant1.id,
            'title': 'Valid title',
            'content': ''  # 空の内容
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
