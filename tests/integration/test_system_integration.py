"""
システム統合テスト - 認証・権限・業務フロー包括テスト
タブレノ TRPGスケジュール管理システム
"""

from django.test import TestCase, TransactionTestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta, datetime
from unittest.mock import patch

from accounts.models import CustomUser, Friend, Group as CustomGroup, GroupMembership, GroupInvitation
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo
from scenarios.models import Scenario, PlayHistory, ScenarioNote

User = get_user_model()


class AuthenticationPermissionIntegrationTestCase(APITestCase):
    """認証とAPI権限の統合テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = APIClient()
        
        # 複数の権限レベルのユーザーを作成
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@arkham.edu',
            password='admin_pass_2024',
            nickname='System Admin',
            is_staff=True,
            is_superuser=True
        )
        
        self.group_admin = User.objects.create_user(
            username='group_admin',
            email='group_admin@arkham.edu',
            password='group_admin_2024',
            nickname='Group Administrator'
        )
        
        self.group_member = User.objects.create_user(
            username='group_member',
            email='member@arkham.edu',
            password='member_2024',
            nickname='Group Member'
        )
        
        self.external_user = User.objects.create_user(
            username='external_user',
            email='external@arkham.edu',
            password='external_2024',
            nickname='External User'
        )
        
        # グループとメンバーシップ設定
        self.private_group = CustomGroup.objects.create(
            name='Secret Society',
            description='Private group for testing',
            visibility='private',
            created_by=self.group_admin
        )
        
        self.public_group = CustomGroup.objects.create(
            name='Public Library',
            description='Public group for testing',
            visibility='public',
            created_by=self.group_admin
        )
        
        # メンバーシップ作成
        GroupMembership.objects.create(user=self.group_admin, group=self.private_group, role='admin')
        GroupMembership.objects.create(user=self.group_admin, group=self.public_group, role='admin')
        GroupMembership.objects.create(user=self.group_member, group=self.private_group, role='member')
        
        # テストシナリオとセッション
        self.scenario = Scenario.objects.create(
            title='Test Authentication Scenario',
            author='Test Author',
            game_system='coc',
            created_by=self.group_admin
        )
        
        self.session = TRPGSession.objects.create(
            title='Test Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.group_admin,
            group=self.private_group
        )
    
    def test_unauthenticated_access_restrictions(self):
        """未認証ユーザーのアクセス制限テスト"""
        # 認証が必要なエンドポイントをテスト
        restricted_endpoints = [
            '/api/accounts/users/',
            '/api/accounts/groups/',
            '/api/accounts/friends/',
            '/api/schedules/sessions/',
            '/api/scenarios/scenarios/',
            '/api/accounts/profile/',
        ]
        
        for endpoint in restricted_endpoints:
            response = self.client.get(endpoint)
            expected_statuses = [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
            if endpoint == '/api/accounts/profile/':
                expected_statuses.append(status.HTTP_302_FOUND)
            self.assertIn(response.status_code, expected_statuses,
                         f"Endpoint {endpoint} should require authentication")
    
    def test_group_visibility_access_control(self):
        """グループ可視性によるアクセス制御テスト"""
        
        # === 外部ユーザーのテスト ===
        self.client.force_authenticate(user=self.external_user)
        
        # プライベートグループは閲覧不可（非メンバーの場合は404）
        response = self.client.get(f'/api/accounts/groups/{self.private_group.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # パブリックグループは閲覧可能
        response = self.client.get(f'/api/accounts/groups/{self.public_group.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # パブリックグループに参加可能
        response = self.client.post(f'/api/accounts/groups/{self.public_group.id}/join/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # プライベートグループには参加不可（404エラー）
        response = self.client.post(f'/api/accounts/groups/{self.private_group.id}/join/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # === グループメンバーのテスト ===
        self.client.force_authenticate(user=self.group_member)
        
        # プライベートグループのメンバーは閲覧可能
        response = self.client.get(f'/api/accounts/groups/{self.private_group.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 管理者権限が必要な操作は不可（メンバーによる編集は権限エラー）
        response = self.client.patch(f'/api/accounts/groups/{self.private_group.id}/', 
                                   {'name': 'Modified Name'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_session_participation_permissions(self):
        """セッション参加権限のテスト"""
        
        # === 外部ユーザー（グループ非参加）===
        self.client.force_authenticate(user=self.external_user)
        
        # プライベートグループのセッションは閲覧不可
        response = self.client.get('/api/schedules/sessions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # APIレスポンスの構造を確認してからフィルタされることをテスト
        sessions_data = response.data
        if isinstance(sessions_data, dict) and 'results' in sessions_data:
            self.assertEqual(len(sessions_data['results']), 0)  # フィルタされて0件
        else:
            self.assertEqual(len(sessions_data), 0)  # リスト形式の場合
        
        # セッション詳細も閲覧不可
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # === グループメンバー ===
        self.client.force_authenticate(user=self.group_member)
        
        # グループメンバーはセッション閲覧可能
        response = self.client.get('/api/schedules/sessions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # セッション詳細も閲覧可能
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # セッション参加申請
        response = self.client.post(f'/api/schedules/sessions/{self.session.id}/join/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_handout_secret_information_access(self):
        """ハンドアウト秘匿情報のアクセス制御テスト"""
        
        # セッション参加者を作成
        participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.group_member,
            role='player',
            character_name='Test Character'
        )
        
        # 秘匿ハンドアウトを作成
        secret_handout = HandoutInfo.objects.create(
            session=self.session,
            participant=participant,
            title='Secret Information',
            content='This is secret information only for this participant',
            is_secret=True
        )
        
        # 公開ハンドアウトを作成
        public_handout = HandoutInfo.objects.create(
            session=self.session,
            participant=participant,
            title='Public Information',
            content='This is public information for all participants',
            is_secret=False
        )
        
        # === 対象参加者（自分のハンドアウト）===
        self.client.force_authenticate(user=self.group_member)
        
        # 自分の秘匿ハンドアウトは閲覧可能
        response = self.client.get(f'/api/schedules/handouts/{secret_handout.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], secret_handout.content)
        
        # === GM（セッション管理者）===
        self.client.force_authenticate(user=self.group_admin)
        
        # GMは全てのハンドアウトを閲覧可能
        response = self.client.get(f'/api/schedules/handouts/{secret_handout.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # === 外部ユーザー ===
        self.client.force_authenticate(user=self.external_user)
        
        # 外部ユーザーはハンドアウト閲覧不可
        response = self.client.get(f'/api/schedules/handouts/{secret_handout.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_scenario_note_privacy_control(self):
        """シナリオメモのプライバシー制御テスト"""
        
        # プライベートメモを作成
        private_note = ScenarioNote.objects.create(
            scenario=self.scenario,
            user=self.group_admin,
            title='Private GM Notes',
            content='Secret strategy and plot points',
            is_private=True
        )
        
        # パブリックメモを作成
        public_note = ScenarioNote.objects.create(
            scenario=self.scenario,
            user=self.group_admin,
            title='Public Session Notes',
            content='General notes for all players',
            is_private=False
        )
        
        # === メモ作成者 ===
        self.client.force_authenticate(user=self.group_admin)
        
        # 作成者は全てのメモを閲覧可能
        response = self.client.get(f'/api/scenarios/notes/{private_note.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.client.get(f'/api/scenarios/notes/{public_note.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # === 他のユーザー ===
        self.client.force_authenticate(user=self.group_member)
        
        # プライベートメモは閲覧不可
        response = self.client.get(f'/api/scenarios/notes/{private_note.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # パブリックメモは閲覧可能
        response = self.client.get(f'/api/scenarios/notes/{public_note.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CompleteWorkflowIntegrationTestCase(TransactionTestCase):
    """完全な業務ワークフロー統合テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = APIClient()
        
        # TRPGサークルの設定
        self.gm = User.objects.create_user(
            username='master_keeper',
            email='keeper@miskatonic.edu',
            password='yog_sothoth_2024',
            nickname='Master Keeper'
        )
        
        self.players = []
        for i in range(1, 5):  # 4人のプレイヤー
            player = User.objects.create_user(
                username=f'investigator_{i}',
                email=f'inv{i}@miskatonic.edu',
                password=f'cthulhu_{i}_2024',
                nickname=f'Investigator {i}'
            )
            self.players.append(player)
    
    def test_complete_trpg_circle_lifecycle(self):
        """TRPGサークル運営の完全ライフサイクルテスト"""
        
        # ===== Phase 1: サークル設立とメンバー募集 =====
        self.client.force_authenticate(user=self.gm)
        
        print("\n=== Phase 1: Circle Establishment ===")
        
        # 1. サークル（グループ）作成
        circle_data = {
            'name': 'Miskatonic University Occult Research Circle',
            'description': 'A research circle dedicated to studying supernatural phenomena through tabletop roleplaying',
            'visibility': 'public'  # 公開サークルとして作成
        }
        response = self.client.post('/api/accounts/groups/', circle_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        circle_id = response.data['id']
        print(f"[OK] Circle created: {response.data['name']}")
        
        # 2. メンバー招待システムのテスト
        invitation_results = []
        for player in self.players:
            # フレンド関係を事前に構築
            Friend.objects.create(user=self.gm, friend=player)
            
            # 招待送信
            invitation_data = {
                'group': circle_id,
                'invitee': player.id,
                'message': f'Welcome to our research circle, {player.nickname}! Join us in exploring the mysteries of the cosmos.'
            }
            response = self.client.post('/api/accounts/invitations/', invitation_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            invitation_results.append(response.data['id'])
        
        print(f"[OK] Sent {len(invitation_results)} invitations")
        
        # 3. 招待受諾プロセス
        accepted_count = 0
        for i, (player, invitation_id) in enumerate(zip(self.players, invitation_results)):
            self.client.force_authenticate(user=player)
            
            # 一部のプレイヤーは招待を受諾、一部は拒否
            if i < 3:  # 最初の3人は受諾
                response = self.client.post(f'/api/accounts/invitations/{invitation_id}/accept/')
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                accepted_count += 1
            else:  # 4人目は拒否
                response = self.client.post(f'/api/accounts/invitations/{invitation_id}/decline/')
                self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        print(f"[OK] {accepted_count} members joined the circle")
        
        # ===== Phase 2: キャンペーン企画とシナリオ準備 =====
        self.client.force_authenticate(user=self.gm)
        
        print("\n=== Phase 2: Campaign Planning ===")
        
        # 4. キャンペーンシナリオ登録
        campaign_data = {
            'title': 'Masks of Nyarlathotep Campaign',
            'author': 'Larry DiTillio & Lynn Willis',
            'game_system': 'coc',
            'difficulty': 'expert',
            'estimated_duration': 'campaign',
            'summary': 'A globe-spanning campaign of cosmic horror and investigation',
            'player_count': 3,
            'estimated_time': 2400  # 40 hours total
        }
        response = self.client.post('/api/scenarios/scenarios/', campaign_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        campaign_id = response.data['id']
        print(f"[OK] Campaign scenario registered: {response.data['title']}")
        
        # 5. GM事前準備メモ
        prep_notes = [
            {
                'title': 'Campaign Overview',
                'content': 'Multi-session campaign spanning 5 countries. Focus on investigation and roleplay.',
                'is_private': True
            },
            {
                'title': 'Player Guidelines',
                'content': 'Character creation guidelines and campaign expectations for players.',
                'is_private': False
            },
            {
                'title': 'Session Planning',
                'content': 'Detailed session breakdown and pacing notes.',
                'is_private': True
            }
        ]
        
        for note_data in prep_notes:
            note_data['scenario'] = campaign_id
            response = self.client.post('/api/scenarios/notes/', note_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        print(f"[OK] Created {len(prep_notes)} preparation notes")
        
        # ===== Phase 3: セッション実行（複数回） =====
        print("\n=== Phase 3: Session Execution ===")
        
        session_schedule = [
            {
                'title': 'Masks of Nyarlathotep - Peru Chapter',
                'description': 'The investigators begin their journey in Lima, Peru',
                'days_offset': 7,
                'location': 'University Gaming Room A'
            },
            {
                'title': 'Masks of Nyarlathotep - New York Chapter', 
                'description': 'Investigation continues in New York City',
                'days_offset': 14,
                'location': 'University Gaming Room B'
            },
            {
                'title': 'Masks of Nyarlathotep - London Chapter',
                'description': 'The trail leads to foggy London',
                'days_offset': 21,
                'location': 'University Gaming Room A'
            }
        ]
        
        session_ids = []
        active_players = self.players[:3]  # 受諾した3人のプレイヤー
        
        for session_info in session_schedule:
            # 6. セッション作成
            session_date = timezone.now() + timedelta(days=session_info['days_offset'])
            session_data = {
                'title': session_info['title'],
                'description': session_info['description'],
                'date': session_date.isoformat(),
                'location': session_info['location'],
                'status': 'planned',
                'visibility': 'group',
                'group': circle_id,
                'duration_minutes': 360  # 6 hours per session
            }
            response = self.client.post('/api/schedules/sessions/', session_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            session_id = response.data['id']
            session_ids.append(session_id)
            
            # 7. 参加者登録とキャラクター設定
            participants = []
            for j, player in enumerate(active_players):
                participant_data = {
                    'session': session_id,
                    'user': player.id,
                    'role': 'player',
                    'character_name': f'Investigator Character {j+1}',
                    'character_sheet_url': f'https://charaeno.sakasin.net/character/{j+1}'
                }
                response = self.client.post('/api/schedules/participants/', participant_data)
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                participants.append(response.data['id'])
            
            # 8. ハンドアウト配布（秘匿情報含む）
            for k, participant_id in enumerate(participants):
                # 個人用秘匿ハンドアウト
                secret_handout_data = {
                    'session': session_id,
                    'participant': participant_id,
                    'title': f'Personal Investigation Lead - Chapter {len(session_ids)}',
                    'content': f'Secret information for Player {k+1}: You have a personal connection to this location...',
                    'is_secret': True
                }
                response = self.client.post('/api/schedules/handouts/', secret_handout_data)
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                
                # 共通情報ハンドアウト（最初の参加者のみ作成）
                if k == 0:
                    public_handout_data = {
                        'session': session_id,
                        'participant': participant_id,
                        'title': f'Chapter {len(session_ids)} - General Information',
                        'content': f'Background information for {session_info["title"]}',
                        'is_secret': False
                    }
                    response = self.client.post('/api/schedules/handouts/', public_handout_data)
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            
            # 9. セッション実行シミュレーション
            # セッション開始
            response = self.client.patch(f'/api/schedules/sessions/{session_id}/', 
                                       {'status': 'ongoing'})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            # セッション完了
            response = self.client.patch(f'/api/schedules/sessions/{session_id}/', 
                                       {'status': 'completed'})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            print(f"[OK] Completed session: {session_info['title']}")
        
        # ===== Phase 4: プレイ履歴とフィードバック記録 =====
        print("\n=== Phase 4: Play History Recording ===")
        
        # 10. 各セッションのプレイ履歴記録
        total_play_histories = 0
        for i, session_id in enumerate(session_ids):
            session_date = timezone.now() + timedelta(days=session_schedule[i]['days_offset'])
            
            # プレイヤーの履歴記録
            for player in active_players:
                self.client.force_authenticate(user=player)
                play_history_data = {
                    'scenario': campaign_id,
                    'session': session_id,
                    'played_date': session_date.isoformat(),
                    'role': 'player',
                    'notes': f'Chapter {i+1} completed. Character development and investigation progress.'
                }
                response = self.client.post('/api/scenarios/history/', play_history_data)
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                total_play_histories += 1
            
            # GMの履歴記録
            self.client.force_authenticate(user=self.gm)
            gm_history_data = {
                'scenario': campaign_id,
                'session': session_id,
                'played_date': session_date.isoformat(),
                'role': 'gm',
                'notes': f'Chapter {i+1} - Great player engagement. Story pacing excellent.'
            }
            response = self.client.post('/api/scenarios/history/', gm_history_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            total_play_histories += 1
            
            # セッション後のGMメモ
            session_note_data = {
                'scenario': campaign_id,
                'title': f'Session {i+1} - Post-Game Notes',
                'content': f'Player feedback and notes for chapter {i+1}. Adjustments for next session.',
                'is_private': True
            }
            response = self.client.post('/api/scenarios/notes/', session_note_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        print(f"[OK] Recorded {total_play_histories} play history entries")
        
        # ===== Phase 5: キャンペーン終了と総評 =====
        print("\n=== Phase 5: Campaign Conclusion ===")
        
        # 11. キャンペーン総評メモ
        final_notes = [
            {
                'title': 'Campaign Conclusion - GM Perspective',
                'content': 'Excellent 3-chapter campaign. Players showed exceptional roleplay and investigation skills.',
                'is_private': True
            },
            {
                'title': 'Public Campaign Review',
                'content': 'Masks of Nyarlathotep campaign successfully completed! Thanks to all participants.',
                'is_private': False
            }
        ]
        
        for note_data in final_notes:
            note_data['scenario'] = campaign_id
            response = self.client.post('/api/scenarios/notes/', note_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # ===== Phase 6: データ整合性とビジネスロジック検証 =====
        print("\n=== Phase 6: Data Validation ===")
        
        # 12. 作成されたデータの整合性確認
        circle = CustomGroup.objects.get(id=circle_id)
        self.assertEqual(circle.members.count(), 4)  # GM + 3 accepted players
        print(f"[OK] Circle has {circle.members.count()} members")
        
        completed_sessions = TRPGSession.objects.filter(
            group=circle, 
            status='completed'
        )
        self.assertEqual(completed_sessions.count(), 3)
        print(f"[OK] {completed_sessions.count()} sessions completed")
        
        total_duration = sum(session.duration_minutes for session in completed_sessions)
        self.assertEqual(total_duration, 1080)  # 3 sessions * 360 minutes
        print(f"[OK] Total play time: {total_duration} minutes ({total_duration/60} hours)")
        
        # プレイ履歴の確認
        campaign_histories = PlayHistory.objects.filter(scenario_id=campaign_id)
        expected_histories = len(session_ids) * (len(active_players) + 1)  # players + GM per session
        self.assertEqual(campaign_histories.count(), expected_histories)
        print(f"[OK] {campaign_histories.count()} play history records created")
        
        # ハンドアウトの確認
        total_handouts = HandoutInfo.objects.filter(session__in=session_ids)
        # 各セッションに秘匿ハンドアウト3個 + 共通ハンドアウト1個 = 4個 * 3セッション = 12個
        self.assertEqual(total_handouts.count(), 12)
        print(f"[OK] {total_handouts.count()} handouts created")
        
        secret_handouts = total_handouts.filter(is_secret=True)
        self.assertEqual(secret_handouts.count(), 9)  # 3 players * 3 sessions
        print(f"[OK] {secret_handouts.count()} secret handouts")
        
        # シナリオメモの確認
        scenario_notes = ScenarioNote.objects.filter(scenario_id=campaign_id)
        self.assertEqual(scenario_notes.count(), 8)  # 3 prep + 3 session + 2 final notes
        print(f"[OK] {scenario_notes.count()} scenario notes created")
        
        private_notes = scenario_notes.filter(is_private=True)
        self.assertEqual(private_notes.count(), 6)  # Private notes
        print(f"[OK] {private_notes.count()} private notes for GM only")
        
        # ===== Phase 7: 統計データ検証（将来実装を想定）=====
        print("\n=== Phase 7: Statistics Validation ===")
        
        # 各プレイヤーの統計確認
        for player in active_players:
            player_histories = PlayHistory.objects.filter(
                user=player,
                scenario_id=campaign_id
            )
            self.assertEqual(player_histories.count(), 3)  # 3 sessions
            
            # 参加セッション時間の計算
            player_sessions = TRPGSession.objects.filter(
                participants=player,
                status='completed'
            )
            total_time = sum(session.duration_minutes for session in player_sessions)
            self.assertEqual(total_time, 1080)  # 18 hours total
        
        # GMの統計確認
        gm_histories = PlayHistory.objects.filter(
            user=self.gm,
            scenario_id=campaign_id,
            role='gm'
        )
        self.assertEqual(gm_histories.count(), 3)  # GMed 3 sessions
        
        print("[OK] Complete TRPG Circle Lifecycle Test Passed Successfully!")
        print("\n=== Final Summary ===")
        print(f"Circle: {circle.name} ({circle.members.count()} members)")
        print(f"Campaign: {campaign_data['title']}")
        print(f"Sessions: {completed_sessions.count()} completed")
        print(f"Total playtime: {total_duration/60:.1f} hours")
        print(f"Play records: {campaign_histories.count()}")
        print(f"Handouts: {total_handouts.count()} ({secret_handouts.count()} secret)")
        print(f"Notes: {scenario_notes.count()} ({private_notes.count()} private)")


@override_settings(DEBUG=True)
class DemoLoginIntegrationTestCase(TestCase):
    """デモログイン機能の統合テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = Client()
    
    def test_demo_login_workflow(self):
        """デモログイン機能のワークフローテスト"""
        
        # 1. デモログインページアクセス
        response = self.client.get('/accounts/demo/')
        self.assertEqual(response.status_code, 200)
        
        # 2. Google疑似ログイン
        response = self.client.get('/accounts/mock-social/google/')
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # 3. ユーザーが作成されていることを確認
        demo_user = User.objects.filter(email='demo.google@example.com').first()
        self.assertIsNotNone(demo_user)
        self.assertEqual(demo_user.nickname, 'Google Demo User')
        
        # 4. ログイン状態の確認
        response = self.client.get('/accounts/dashboard/')
        self.assertEqual(response.status_code, 200)
        
        # 5. 再ログイン（既存ユーザー）
        self.client.logout()
        response = self.client.get('/accounts/mock-social/google/')
        self.assertEqual(response.status_code, 302)
        
        # 同じユーザーでログインされていることを確認
        users_count = User.objects.filter(email='demo.google@example.com').count()
        self.assertEqual(users_count, 1)  # 重複作成されていない
        
        print("[OK] Demo Login Integration Test Passed!")


class APIErrorHandlingIntegrationTestCase(APITestCase):
    """APIエラーハンドリングの統合テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='test_user',
            email='test@arkham.edu',
            password='test_pass_2024',
            nickname='Test User'
        )
    
    def test_api_error_handling_workflow(self):
        """API エラーハンドリングのワークフローテスト"""
        
        self.client.force_authenticate(user=self.user)
        
        # 1. 存在しないリソースへのアクセス
        response = self.client.get('/api/accounts/groups/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # 2. 不正なデータでのリソース作成
        invalid_group_data = {
            'name': '',  # 必須フィールドが空
            'visibility': 'invalid_choice'  # 無効な選択肢
        }
        response = self.client.post('/api/accounts/groups/', invalid_group_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)
        
        # 3. 権限のないリソースへのアクセス
        other_user = User.objects.create_user(
            username='other_user',
            email='other@arkham.edu',
            password='other_pass_2024'
        )
        other_group = CustomGroup.objects.create(
            name='Other Group',
            created_by=other_user,
            visibility='private'
        )
        
        response = self.client.get(f'/api/accounts/groups/{other_group.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # 4. 重複データの作成試行
        group = CustomGroup.objects.create(
            name='Test Group',
            created_by=self.user
        )
        GroupMembership.objects.create(user=self.user, group=group, role='admin')
        
        # 同じユーザーを再度追加試行
        duplicate_membership_data = {
            'user': self.user.id,
            'group': group.id,
            'role': 'member'
        }
        # 実際のAPIエンドポイントが重複チェックを行う場合
        # response = self.client.post('/api/accounts/memberships/', duplicate_membership_data)
        # self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        print("[OK] API Error Handling Integration Test Passed!")


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests([
        'test_system_integration.AuthenticationPermissionIntegrationTestCase',
        'test_system_integration.CompleteWorkflowIntegrationTestCase', 
        'test_system_integration.DemoLoginIntegrationTestCase',
        'test_system_integration.APIErrorHandlingIntegrationTestCase'
    ])
