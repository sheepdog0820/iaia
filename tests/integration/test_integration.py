"""
統合テストスイート - 複数機能の連携テスト
Arkham Nexus TRPGスケジュール管理システム
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta

from accounts.models import CustomUser, Friend, Group as CustomGroup, GroupMembership, GroupInvitation
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo
from scenarios.models import Scenario, PlayHistory, ScenarioNote

User = get_user_model()


class UserGroupIntegrationTestCase(APITestCase):
    """ユーザー管理とグループ機能の連携テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = APIClient()
        
        # テストユーザー作成
        self.gm_user = User.objects.create_user(
            username='gm_master',
            email='gm@arkham.com',
            password='arkham_gm_2024',
            nickname='Ancient GM'
        )
        
        self.player1 = User.objects.create_user(
            username='investigator1',
            email='player1@arkham.com', 
            password='cthulhu_2024',
            nickname='Brave Investigator'
        )
        
        self.player2 = User.objects.create_user(
            username='investigator2',
            email='player2@arkham.com',
            password='cthulhu_2024', 
            nickname='Wise Scholar'
        )
        
        self.outsider = User.objects.create_user(
            username='outsider',
            email='outsider@arkham.com',
            password='outsider_2024',
            nickname='Curious Outsider'
        )
    
    def test_group_creation_and_member_management_flow(self):
        """グループ作成からメンバー管理までの業務フロー"""
        self.client.force_authenticate(user=self.gm_user)
        
        # 1. グループ作成
        group_data = {
            'name': 'Miskatonic University Circle',
            'description': 'A secret circle studying forbidden knowledge',
            'visibility': 'private'
        }
        response = self.client.post('/api/accounts/groups/', group_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        group_id = response.data['id']
        
        # 2. グループが作成者により管理者権限で作成されていることを確認
        group = CustomGroup.objects.get(id=group_id)
        membership = GroupMembership.objects.get(user=self.gm_user, group=group)
        self.assertEqual(membership.role, 'admin')
        
        # 3. フレンド関係を構築
        Friend.objects.create(user=self.gm_user, friend=self.player1)
        Friend.objects.create(user=self.gm_user, friend=self.player2)
        
        # 4. メンバー招待
        invitation_data = {
            'group': group_id,
            'invitee': self.player1.id,
            'message': 'Join our investigation into the cosmic truth!'
        }
        response = self.client.post('/api/accounts/invitations/', invitation_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invitation_id = response.data['id']
        
        # 5. 招待を受諾（プレイヤー視点）
        self.client.force_authenticate(user=self.player1)
        response = self.client.post(f'/api/accounts/invitations/{invitation_id}/accept/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 6. メンバーシップが作成されていることを確認
        membership_exists = GroupMembership.objects.filter(
            user=self.player1, group=group, role='member'
        ).exists()
        self.assertTrue(membership_exists, f"Membership not found for user {self.player1.id} in group {group.id}")
        
        # 7. グループメンバー一覧の確認
        self.client.force_authenticate(user=self.gm_user)
        response = self.client.get(f'/api/accounts/groups/{group_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # メンバー数は members_detail フィールドで確認
        members_count = len(response.data.get('members_detail', []))
        self.assertEqual(members_count, 2)  # GM + Player1
    
    def test_access_control_by_group_visibility(self):
        """グループ可視性による権限制御テスト"""
        # プライベートグループ作成
        self.client.force_authenticate(user=self.gm_user)
        private_group_data = {
            'name': 'Secret Cult',
            'description': 'Hidden from prying eyes',
            'visibility': 'private'
        }
        response = self.client.post('/api/accounts/groups/', private_group_data)
        private_group_id = response.data['id']
        
        # パブリックグループ作成
        public_group_data = {
            'name': 'Public Library Club', 
            'description': 'Open to all seekers of knowledge',
            'visibility': 'public'
        }
        response = self.client.post('/api/accounts/groups/', public_group_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        public_group_id = response.data['id']
        
        # 外部ユーザーからのアクセステスト
        self.client.force_authenticate(user=self.outsider)
        
        # プライベートグループは閲覧不可（非メンバーの場合は404）
        response = self.client.get(f'/api/accounts/groups/{private_group_id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # パブリックグループは閲覧可能
        response = self.client.get(f'/api/accounts/groups/{public_group_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SessionScenarioIntegrationTestCase(APITestCase):
    """セッション管理とシナリオ機能の連携テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = APIClient()
        
        # ユーザーとグループ作成
        self.gm_user = User.objects.create_user(
            username='keeper',
            email='keeper@arkham.com',
            password='keeper_2024',
            nickname='The Keeper'
        )
        
        self.player = User.objects.create_user(
            username='player',
            email='player@arkham.com', 
            password='player_2024',
            nickname='Investigator'
        )
        
        self.group = CustomGroup.objects.create(
            name='Call of Cthulhu Circle',
            created_by=self.gm_user,
            visibility='private'
        )
        
        # グループメンバーシップ作成
        GroupMembership.objects.create(user=self.gm_user, group=self.group, role='admin')
        GroupMembership.objects.create(user=self.player, group=self.group, role='member')
        
        # シナリオ作成
        self.scenario = Scenario.objects.create(
            title='The Haunted House',
            author='H.P. Lovecraft',
            game_system='coc',
            difficulty='intermediate',
            estimated_duration='medium',
            summary='A classic investigation into supernatural occurrences',
            created_by=self.gm_user,
            player_count=4,
            estimated_time=240
        )
    
    def test_complete_session_lifecycle_with_scenario(self):
        """セッション作成からプレイ履歴記録までの完全フロー"""
        self.client.force_authenticate(user=self.gm_user)
        
        # 1. セッション作成
        session_date = timezone.now() + timedelta(days=7)
        session_data = {
            'title': 'First Investigation Session',
            'description': 'Beginning our journey into the unknown',
            'date': session_date.isoformat(),
            'location': 'Miskatonic University Library',
            'youtube_url': 'https://youtube.com/watch?v=example',
            'status': 'planned',
            'visibility': 'group',
            'group': self.group.id,
            'duration_minutes': 240
        }
        response = self.client.post('/api/schedules/sessions/', session_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session_id = response.data['id']
        
        # 2. 参加者追加
        participant_data = {
            'session': session_id,
            'user': self.player.id,
            'role': 'player',
            'character_name': 'Dr. Margaret Blackwood',
            'character_sheet_url': 'https://example.com/character/margaret'
        }
        response = self.client.post('/api/schedules/participants/', participant_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        participant_id = response.data['id']
        
        # 3. ハンドアウト作成
        handout_data = {
            'session': session_id,
            'participant': participant_id,
            'title': 'Professor\'s Last Letter',
            'content': 'My dear colleague, I fear I have discovered something terrible...',
            'is_secret': True
        }
        response = self.client.post('/api/schedules/handouts/', handout_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 4. セッション開始（ステータス変更）
        response = self.client.patch(f'/api/schedules/sessions/{session_id}/', {'status': 'ongoing'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 5. セッション完了
        response = self.client.patch(f'/api/schedules/sessions/{session_id}/', {'status': 'completed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 6. プレイ履歴記録（シナリオと連携）- プレイヤー視点
        self.client.force_authenticate(user=self.player)
        play_history_data = {
            'scenario': self.scenario.id,
            'session': session_id,
            'played_date': session_date.isoformat(),
            'role': 'player',
            'notes': 'Successfully investigated the haunted house. Sanity slightly decreased.'
        }
        response = self.client.post('/api/scenarios/history/', play_history_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 7. GMのプレイ履歴も記録
        self.client.force_authenticate(user=self.gm_user)
        gm_history_data = {
            'scenario': self.scenario.id,
            'session': session_id,
            'played_date': session_date.isoformat(),
            'role': 'gm',
            'notes': 'Players handled the mysteries well. Great atmosphere throughout.'
        }
        response = self.client.post('/api/scenarios/history/', gm_history_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 8. シナリオメモ追加
        scenario_note_data = {
            'scenario': self.scenario.id,
            'title': 'GM Notes - First Run',
            'content': 'Players were very engaged. Consider adding more investigation clues.',
            'is_private': True
        }
        response = self.client.post('/api/scenarios/notes/', scenario_note_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 9. データの整合性確認
        session = TRPGSession.objects.get(id=session_id)
        self.assertEqual(session.status, 'completed')
        
        play_histories = PlayHistory.objects.filter(session_id=session_id)
        self.assertEqual(play_histories.count(), 2)  # GM + Player
        
        handouts = HandoutInfo.objects.filter(session=session)
        self.assertEqual(handouts.count(), 1)


class AuthenticationAndPermissionIntegrationTestCase(APITestCase):
    """認証とAPI権限の統合テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = APIClient()
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@arkham.com',
            password='admin_2024',
            nickname='System Administrator',
            is_staff=True
        )
        
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@arkham.com',
            password='regular_2024',
            nickname='Regular User'
        )
        
        self.group = CustomGroup.objects.create(
            name='Test Group',
            created_by=self.admin_user
        )
        
        GroupMembership.objects.create(user=self.admin_user, group=self.group, role='admin')
    
    def test_api_authentication_requirements(self):
        """API認証要件のテスト"""
        # 未認証でのアクセスは403または401
        response = self.client.get('/api/accounts/users/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        
        response = self.client.get('/api/schedules/sessions/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        
        response = self.client.get('/api/scenarios/scenarios/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        
        # 認証後はアクセス可能
        self.client.force_authenticate(user=self.regular_user)
        
        response = self.client.get('/api/accounts/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.client.get('/api/schedules/sessions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.client.get('/api/scenarios/scenarios/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_resource_ownership_permissions(self):
        """リソースの所有権限テスト"""
        self.client.force_authenticate(user=self.regular_user)
        
        # 他ユーザーのグループは編集不可（非メンバーは404）
        response = self.client.patch(f'/api/accounts/groups/{self.group.id}/', {'name': 'Modified Name'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # 自分が作成したグループは編集可能
        own_group = CustomGroup.objects.create(
            name='My Group',
            created_by=self.regular_user
        )
        GroupMembership.objects.create(user=self.regular_user, group=own_group, role='admin')
        
        response = self.client.patch(f'/api/accounts/groups/{own_group.id}/', {'name': 'Updated Name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class EndToEndBusinessFlowTestCase(TransactionTestCase):
    """エンドツーエンドの業務フローテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = APIClient()
        
        # 複数ユーザー作成
        self.keeper = User.objects.create_user(
            username='keeper_azathoth',
            email='keeper@miskatonic.edu',
            password='azathoth_2024',
            nickname='Keeper Azathoth'
        )
        
        self.players = []
        for i in range(1, 4):
            player = User.objects.create_user(
                username=f'investigator_{i}',
                email=f'investigator{i}@miskatonic.edu',
                password=f'cthulhu_{i}_2024',
                nickname=f'Investigator {i}'
            )
            self.players.append(player)
    
    def test_complete_trpg_campaign_workflow(self):
        """完全なTRPGキャンペーン運営ワークフロー"""
        # フェーズ1: サークル設立
        self.client.force_authenticate(user=self.keeper)
        
        # 1. グループ作成
        group_data = {
            'name': 'Miskatonic University Occult Society',
            'description': 'Dedicated to investigating supernatural phenomena',
            'visibility': 'private'
        }
        response = self.client.post('/api/accounts/groups/', group_data)
        group_id = response.data['id']
        
        # 2. メンバー招待と受諾
        for player in self.players:
            # フレンド関係構築
            Friend.objects.create(user=self.keeper, friend=player)
            
            # 招待送信
            invitation_data = {
                'group': group_id,
                'invitee': player.id,
                'message': f'Welcome to our investigation team, {player.nickname}!'
            }
            response = self.client.post('/api/accounts/invitations/', invitation_data)
            invitation_id = response.data['id']
            
            # プレイヤーが招待を受諾
            self.client.force_authenticate(user=player)
            self.client.post(f'/api/accounts/invitations/{invitation_id}/accept/')
        
        # フェーズ2: シナリオ準備
        self.client.force_authenticate(user=self.keeper)
        
        # 3. シナリオ登録
        scenario_data = {
            'title': 'The Call of Cthulhu Campaign',
            'author': 'Sandy Petersen',
            'game_system': 'coc',
            'difficulty': 'advanced',
            'estimated_duration': 'campaign',
            'summary': 'A multi-session campaign exploring cosmic horror',
            'player_count': 3,
            'estimated_time': 720  # 12 hours total
        }
        response = self.client.post('/api/scenarios/scenarios/', scenario_data)
        scenario_id = response.data['id']
        
        # 4. GMメモ作成
        gm_note_data = {
            'scenario': scenario_id,
            'title': 'Campaign Planning Notes',
            'content': 'Session 1: Introduction to Arkham\nSession 2: The Dunwich Horror\nSession 3: Final Confrontation',
            'is_private': True
        }
        self.client.post('/api/scenarios/notes/', gm_note_data)
        
        # フェーズ3: セッション実行（複数回）
        session_dates = [
            timezone.now() + timedelta(days=i*7) for i in range(1, 4)
        ]
        
        session_ids = []
        for i, session_date in enumerate(session_dates):
            # 5. セッション作成
            session_data = {
                'title': f'Call of Cthulhu Campaign - Session {i+1}',
                'description': f'Session {i+1} of our ongoing investigation',
                'date': session_date.isoformat(),
                'location': 'Miskatonic University - Room 237',
                'status': 'planned',
                'visibility': 'group',
                'group': group_id,
                'duration_minutes': 240
            }
            response = self.client.post('/api/schedules/sessions/', session_data)
            session_id = response.data['id']
            session_ids.append(session_id)
            
            # 6. 参加者登録
            for j, player in enumerate(self.players):
                participant_data = {
                    'session': session_id,
                    'user': player.id,
                    'role': 'player',
                    'character_name': f'Character {j+1}',
                    'character_sheet_url': f'https://example.com/character/{j+1}'
                }
                response = self.client.post('/api/schedules/participants/', participant_data)
                participant_id = response.data['id']
                
                # 7. ハンドアウト作成（秘匿情報）
                handout_data = {
                    'session': session_id,
                    'participant': participant_id,
                    'title': f'Personal Investigation - Session {i+1}',
                    'content': f'Secret information for {player.nickname} in session {i+1}',
                    'is_secret': True
                }
                self.client.post('/api/schedules/handouts/', handout_data)
            
            # 8. セッション実行（ステータス変更）
            self.client.patch(f'/api/schedules/sessions/{session_id}/', {'status': 'ongoing'})
            self.client.patch(f'/api/schedules/sessions/{session_id}/', {'status': 'completed'})
            
            # 9. プレイ履歴記録
            for player in self.players:
                self.client.force_authenticate(user=player)
                play_history_data = {
                    'scenario': scenario_id,
                    'session': session_id,
                    'played_date': session_date.isoformat(),
                    'role': 'player',
                    'notes': f'Session {i+1} completed. Character development ongoing.'
                }
                self.client.post('/api/scenarios/history/', play_history_data)
            
            # GMの履歴も記録
            self.client.force_authenticate(user=self.keeper)
            gm_history_data = {
                'scenario': scenario_id,
                'session': session_id,
                'played_date': session_date.isoformat(),
                'role': 'gm',
                'notes': f'Session {i+1} - Good player engagement, story progressing well.'
            }
            self.client.post('/api/scenarios/history/', gm_history_data)
        
        # フェーズ4: 統計確認とデータ検証
        # 10. 作成されたデータの整合性確認
        # 検証のためにKeeperで認証を戻す
        self.client.force_authenticate(user=self.keeper)
        group = CustomGroup.objects.get(id=group_id)
        self.assertEqual(group.members.count(), 4)  # Keeper + 3 Players
        
        sessions = TRPGSession.objects.filter(group=group)
        self.assertEqual(sessions.count(), 3)
        
        completed_sessions = sessions.filter(status='completed')
        self.assertEqual(completed_sessions.count(), 3)
        
        total_play_histories = PlayHistory.objects.filter(scenario_id=scenario_id)
        self.assertEqual(total_play_histories.count(), 12)  # 3 sessions × 4 participants
        
        # プレイヤーごとの参加履歴確認
        for player in self.players:
            player_histories = PlayHistory.objects.filter(user=player, scenario_id=scenario_id)
            self.assertEqual(player_histories.count(), 3)  # 各プレイヤーが3セッション参加
        
        # 11. 統計データの確認（未実装機能として想定）
        # このテストは統計機能が実装された際の期待値を示す
        response = self.client.get('/api/accounts/statistics/tindalos/')
        # 実装時は以下のような統計が取得できることを期待
        # - 総プレイ時間: 12時間（3セッション × 4時間）
        # - 参加セッション数: 3
        # - GMセッション数: 3（Keeperの場合）
        
        # フェーズ5: キャンペーン終了後の処理
        # 12. キャンペーン総評メモ
        final_note_data = {
            'scenario': scenario_id,
            'title': 'Campaign Conclusion',
            'content': 'Excellent 3-session campaign. All players showed great roleplay.',
            'is_private': False  # 公開メモとして
        }
        response = self.client.post('/api/scenarios/notes/', final_note_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        print("✅ Complete TRPG Campaign Workflow Test Passed")
        print(f"   - Group created with {group.members.count()} members")
        print(f"   - {sessions.count()} sessions completed")
        print(f"   - {total_play_histories.count()} play history records created")