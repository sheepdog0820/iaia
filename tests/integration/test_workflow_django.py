"""
Django Test Case形式の動線テスト
Arkham Nexus TRPGスケジュール管理システム
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
from django.utils import timezone

from accounts.models import CustomUser, Group as CustomGroup
from schedules.models import TRPGSession
from scenarios.models import Scenario

User = get_user_model()


class WorkflowIntegrationTestCase(TestCase):
    """動線統合テストケース"""
    
    def setUp(self):
        """テストデータセットアップ"""
        self.client = APIClient()
        
        # テストユーザー作成
        self.user = User.objects.create_user(
            username='workflow_test',
            email='test@workflow.com',
            password='test123',
            nickname='ワークフローテスター'
        )
        
        self.gm_user = User.objects.create_user(
            username='gm_test',
            email='gm@workflow.com',
            password='test123',
            nickname='テストGM'
        )
        
    def test_complete_user_workflow(self):
        """ユーザーの完全な動線テスト"""
        print("\\n🎭 ユーザー動線統合テスト開始")
        
        # 1. ログイン
        self.client.force_authenticate(user=self.user)
        print("1️⃣ ユーザーログイン完了")
        
        # 2. ホーム画面データ取得
        print("\\n2️⃣ ホーム画面データ取得")
        
        response = self.client.get('/api/schedules/sessions/upcoming/')
        self.assertEqual(response.status_code, 200)
        print(f"   ✅ 次回セッション取得: {len(response.data)}件")
        
        response = self.client.get('/api/schedules/sessions/statistics/')
        self.assertEqual(response.status_code, 200)
        print(f"   ✅ セッション統計取得: {response.data}")
        
        # 3. グループ作成・参加
        print("\\n3️⃣ グループ機能")
        
        group_data = {
            'name': 'テストTRPGサークル',
            'description': 'ワークフローテスト用グループ',
            'visibility': 'public'
        }
        response = self.client.post('/api/accounts/groups/', group_data)
        self.assertEqual(response.status_code, 201)
        group_id = response.data['id']
        print(f"   ✅ グループ作成: {response.data['name']}")
        
        # グループ一覧確認
        response = self.client.get('/api/accounts/groups/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(g['id'] == group_id for g in response.data))
        print(f"   ✅ グループ一覧確認: {len(response.data)}件")
        
        # 4. セッション作成
        print("\\n4️⃣ セッション作成")
        
        session_data = {
            'title': 'クトゥルフの呼び声テストセッション',
            'description': 'ワークフロー確認用のテストセッション',
            'date': (timezone.now() + timedelta(days=3)).isoformat(),
            'duration_minutes': 240,
            'location': 'オンライン（Discord）',
            'group': group_id,
            'visibility': 'group',
            'status': 'planned'
        }
        response = self.client.post('/api/schedules/sessions/', session_data)
        self.assertEqual(response.status_code, 201)
        session_id = response.data['id']
        print(f"   ✅ セッション作成: {response.data['title']}")
        
        # 5. カレンダー機能確認
        print("\\n5️⃣ カレンダー機能")
        
        start_date = timezone.now().date()
        end_date = (timezone.now() + timedelta(days=7)).date()
        
        response = self.client.get('/api/schedules/calendar/', {
            'start': f'{start_date}T00:00:00+09:00',
            'end': f'{end_date}T23:59:59+09:00'
        })
        self.assertEqual(response.status_code, 200)
        
        events = response.data
        session_events = [e for e in events if e['id'] == session_id]
        self.assertTrue(len(session_events) > 0)
        
        session_event = session_events[0]
        print(f"   ✅ カレンダーイベント確認: {session_event['title']}")
        print(f"   📅 イベントタイプ: {session_event.get('type', 'unknown')}")
        print(f"   🏷️ GM権限: {session_event.get('is_gm', False)}")
        
        # 6. シナリオ機能
        print("\\n6️⃣ シナリオ機能")
        
        scenario_data = {
            'title': 'インスマウスの影',
            'description': 'H.P.ラヴクラフトの代表作',
            'system': 'cthulhu',
            'difficulty': 'hard',
            'estimated_duration': 360,
            'min_players': 3,
            'max_players': 6
        }
        response = self.client.post('/api/scenarios/scenarios/', scenario_data)
        self.assertEqual(response.status_code, 201)
        scenario_id = response.data['id']
        print(f"   ✅ シナリオ作成: {response.data['title']}")
        
        # シナリオ一覧確認
        response = self.client.get('/api/scenarios/scenarios/')
        self.assertEqual(response.status_code, 200)
        print(f"   ✅ シナリオ一覧: {len(response.data)}件")
        
        # 7. 統計・エクスポート機能
        print("\\n7️⃣ 統計・エクスポート機能")
        
        # 基本統計取得
        response = self.client.get('/api/accounts/statistics/simple/')
        self.assertEqual(response.status_code, 200)
        stats = response.data
        print(f"   ✅ 基本統計: セッション{stats.get('session_count', 0)}回")
        
        # JSON エクスポート
        response = self.client.get('/api/accounts/export/formats/?format=json')
        self.assertEqual(response.status_code, 200)
        export_data = response.json()
        self.assertEqual(export_data['user_info']['id'], self.user.id)
        print(f"   ✅ JSONエクスポート: {export_data['user_info']['username']}")
        
        # 8. ハンドアウト機能
        print("\\n8️⃣ ハンドアウト機能")
        
        # セッション詳細取得（参加者情報が必要）
        response = self.client.get(f'/api/schedules/sessions/{session_id}/')
        self.assertEqual(response.status_code, 200)
        session_detail = response.data
        participants = session_detail.get('participants_detail', [])
        
        if participants:
            participant = participants[0]  # GM（自分）
            handout_data = {
                'session': session_id,
                'participant': participant['id'],
                'title': 'GM用シナリオ概要',
                'content': 'プレイヤーには秘匿の重要情報...',
                'is_secret': True
            }
            response = self.client.post('/api/schedules/handouts/', handout_data)
            self.assertEqual(response.status_code, 201)
            print(f"   ✅ ハンドアウト作成: {response.data['title']}")
        
        print("\\n🎉 ユーザー動線テスト完了!")
        
    def test_calendar_filter_functionality(self):
        """カレンダーフィルター機能テスト"""
        print("\\n📅 カレンダーフィルター機能テスト開始")
        
        self.client.force_authenticate(user=self.user)
        
        # 1. テストデータ準備
        print("\\n1️⃣ テストデータ準備")
        
        # ユーザーのグループ
        group_data = {
            'name': 'フィルターテストグループ',
            'description': 'カレンダーフィルター機能テスト用',
            'visibility': 'public'
        }
        response = self.client.post('/api/accounts/groups/', group_data)
        user_group_id = response.data['id']
        
        # GMのグループ
        self.client.force_authenticate(user=self.gm_user)
        gm_group_data = {
            'name': 'GM用グループ',
            'description': 'GM専用グループ',
            'visibility': 'public'
        }
        response = self.client.post('/api/accounts/groups/', gm_group_data)
        gm_group_id = response.data['id']
        
        # ユーザーがGMグループに参加
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/accounts/groups/{gm_group_id}/join/')
        self.assertEqual(response.status_code, 201)
        print("   ✅ テストグループ準備完了")
        
        # 2. 異なるタイプのセッション作成
        print("\\n2️⃣ 異なるタイプのセッション作成")
        
        # 自分がGMのセッション
        gm_session_data = {
            'title': '自分がGMのセッション',
            'date': (timezone.now() + timedelta(days=1)).isoformat(),
            'duration_minutes': 180,
            'group': user_group_id,
            'visibility': 'group',
            'status': 'planned'
        }
        response = self.client.post('/api/schedules/sessions/', gm_session_data)
        self.assertEqual(response.status_code, 201)
        gm_session_id = response.data['id']
        print(f"   ✅ GMセッション作成: {response.data['title']}")
        
        # 参加するセッション（他のGM）
        self.client.force_authenticate(user=self.gm_user)
        participant_session_data = {
            'title': '参加するセッション',
            'date': (timezone.now() + timedelta(days=2)).isoformat(),
            'duration_minutes': 240,
            'group': gm_group_id,
            'visibility': 'group',
            'status': 'planned'
        }
        response = self.client.post('/api/schedules/sessions/', participant_session_data)
        self.assertEqual(response.status_code, 201)
        participant_session_id = response.data['id']
        
        # ユーザーがセッションに参加
        self.client.force_authenticate(user=self.user)
        join_data = {'character_name': 'テストキャラクター'}
        response = self.client.post(f'/api/schedules/sessions/{participant_session_id}/join/', join_data)
        self.assertEqual(response.status_code, 201)
        print(f"   ✅ 参加セッション作成: {participant_session_data['title']}")
        
        # 3. カレンダーフィルター確認
        print("\\n3️⃣ カレンダーフィルター確認")
        
        start_date = timezone.now().date()
        end_date = (timezone.now() + timedelta(days=7)).date()
        
        response = self.client.get('/api/schedules/calendar/', {
            'start': f'{start_date}T00:00:00+09:00',
            'end': f'{end_date}T23:59:59+09:00'
        })
        self.assertEqual(response.status_code, 200)
        
        events = response.data
        print(f"   📊 総イベント数: {len(events)}")
        
        # セッションタイプ別分類
        gm_events = [e for e in events if e.get('is_gm', False)]
        participant_events = [e for e in events if e.get('is_participant', False)]
        
        print(f"   🎩 GMセッション: {len(gm_events)}件")
        print(f"   👥 参加セッション: {len(participant_events)}件")
        
        # 各イベントの詳細確認
        for event in events:
            event_type = event.get('type', 'unknown')
            is_gm = event.get('is_gm', False)
            is_participant = event.get('is_participant', False)
            print(f"   📅 {event['title']}: type={event_type}, GM={is_gm}, participant={is_participant}")
        
        # GMセッションが正しく識別されているか確認
        gm_session_event = next((e for e in events if e['id'] == gm_session_id), None)
        if gm_session_event:
            self.assertTrue(gm_session_event.get('is_gm', False))
            self.assertEqual(gm_session_event.get('type'), 'gm')
            print("   ✅ GMセッション分類正常")
        
        # 参加セッションが正しく識別されているか確認
        participant_session_event = next((e for e in events if e['id'] == participant_session_id), None)
        if participant_session_event:
            self.assertTrue(participant_session_event.get('is_participant', False))
            self.assertEqual(participant_session_event.get('type'), 'participant')
            print("   ✅ 参加セッション分類正常")
        
        print("\\n📅 カレンダーフィルター機能テスト完了!")
        
    def test_export_statistics_workflow(self):
        """エクスポート・統計機能の動線テスト"""
        print("\\n📊 エクスポート・統計動線テスト開始")
        
        self.client.force_authenticate(user=self.user)
        
        # 1. データ作成
        print("\\n1️⃣ テストデータ作成")
        
        # グループ作成
        group_data = {'name': '統計テストグループ', 'visibility': 'public'}
        response = self.client.post('/api/accounts/groups/', group_data)
        group_id = response.data['id']
        
        # セッション作成
        session_data = {
            'title': '統計用テストセッション',
            'date': (timezone.now() - timedelta(days=30)).isoformat(),
            'duration_minutes': 240,
            'group': group_id,
            'visibility': 'group',
            'status': 'completed'
        }
        response = self.client.post('/api/schedules/sessions/', session_data)
        session_id = response.data['id']
        
        # シナリオ作成
        scenario_data = {
            'title': '統計用シナリオ',
            'system': 'cthulhu',
            'difficulty': 'medium',
            'estimated_duration': 240
        }
        response = self.client.post('/api/scenarios/scenarios/', scenario_data)
        if response.status_code != 201:
            print(f"Scenario creation failed: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, 201)
        scenario_id = response.data['id']
        
        # プレイ履歴作成
        history_data = {
            'user': self.user.id,
            'scenario': scenario_id,
            'session_date': (timezone.now() - timedelta(days=25)).isoformat(),
            'role': 'gm',
            'notes': '統計テスト用履歴'
        }
        response = self.client.post('/api/scenarios/history/', history_data)
        self.assertEqual(response.status_code, 201)
        print("   ✅ テストデータ作成完了")
        
        # 2. 統計機能確認
        print("\\n2️⃣ 統計機能確認")
        
        # 基本統計
        response = self.client.get('/api/accounts/statistics/simple/')
        self.assertEqual(response.status_code, 200)
        stats = response.data
        print(f"   📊 セッション数: {stats.get('session_count', 0)}")
        print(f"   📊 GM回数: {stats.get('gm_session_count', 0)}")
        print(f"   📊 プレイヤー回数: {stats.get('player_session_count', 0)}")
        print(f"   📊 総プレイ時間: {stats.get('total_play_time', 0)}時間")
        
        # セッション統計
        response = self.client.get('/api/schedules/sessions/statistics/')
        self.assertEqual(response.status_code, 200)
        session_stats = response.data
        print(f"   📊 年間セッション数: {session_stats.get('session_count', 0)}")
        print(f"   📊 年間プレイ時間: {session_stats.get('total_hours', 0)}時間")
        
        # 3. エクスポート機能確認
        print("\\n3️⃣ エクスポート機能確認")
        
        # JSON エクスポート
        response = self.client.get('/api/accounts/export/formats/?format=json')
        self.assertEqual(response.status_code, 200)
        export_data = response.json()
        
        # エクスポートデータの構造確認
        self.assertIn('user_info', export_data)
        self.assertIn('statistics', export_data)
        self.assertEqual(export_data['user_info']['id'], self.user.id)
        print(f"   ✅ JSONエクスポート成功: {export_data['user_info']['username']}")
        
        # エクスポート形式一覧
        response = self.client.get('/api/accounts/export/formats/')
        self.assertEqual(response.status_code, 200)
        print("   ✅ エクスポート形式一覧取得成功")
        
        print("\\n📊 エクスポート・統計動線テスト完了!")
        
        print("\\n🎉 全ての動線テストが正常に完了しました!")
        print("✨ Arkham Nexus システムの機能が期待通りに動作しています")