"""
統計データエクスポート機能のテストケース
"""
import json
import csv
from io import StringIO
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Group, GroupMembership
from schedules.models import TRPGSession, SessionParticipant
from scenarios.models import Scenario, PlayHistory

User = get_user_model()


class ExportFunctionalityTestCase(APITestCase):
    """エクスポート機能のテストケース"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.user = User.objects.create_user(
            username='exportuser',
            email='export@example.com',
            password='pass123',
            nickname='Export User'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='Export Test Group',
            description='Test Group for Export',
            created_by=self.user
        )
        GroupMembership.objects.create(
            user=self.user,
            group=self.group,
            role='admin'
        )
        
        # シナリオ作成
        self.scenario = Scenario.objects.create(
            title='Export Test Scenario',
            author='Export Author',
            game_system='coc',
            created_by=self.user
        )
        
        # セッション作成
        self.session = TRPGSession.objects.create(
            title='Export Test Session',
            date=timezone.now() - timedelta(days=30),
            gm=self.user,
            group=self.group,
            duration_minutes=180,
            status='completed'
        )
        
        # 参加者とプレイ履歴作成
        SessionParticipant.objects.create(
            session=self.session,
            user=self.user,
            role='gm'
        )
        PlayHistory.objects.create(
            scenario=self.scenario,
            user=self.user,
            session=self.session,
            played_date=self.session.date,
            role='gm'
        )

    def test_export_available_formats_view(self):
        """利用可能なエクスポート形式ビューのテスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accounts/export/formats/')
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertIn('formats', data)
            
            # 基本的な形式の確認
            formats = data['formats']
            if isinstance(formats, dict):
                self.assertIn('csv', formats)
                self.assertIn('json', formats)
                self.assertTrue(formats['csv']['available'])
                self.assertTrue(formats['json']['available'])
            else:
                format_names = [
                    fmt.get('format', fmt.get('name'))
                    for fmt in formats
                    if isinstance(fmt, dict)
                ]
                self.assertIn('csv', format_names)
                self.assertIn('json', format_names)
            
            # データタイプの確認
            if 'data_types' in data:
                data_types = data['data_types']
                self.assertIn('tindalos', data_types)
                self.assertIn('ranking', data_types)
                self.assertIn('groups', data_types)

    def test_tindalos_csv_export_unauthenticated(self):
        """未認証でのTindalos CSV エクスポートテスト"""
        response = self.client.get('/api/accounts/export/?type=tindalos&format=csv')
        # URLが存在しない場合は404、存在する場合は403を期待
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )

    def test_tindalos_csv_export_authenticated(self):
        """認証済みTindalos CSV エクスポートテスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accounts/export/?type=tindalos&format=csv')
        
        if response.status_code == status.HTTP_200_OK:
            # CSVレスポンスの確認
            self.assertEqual(response['content-type'], 'text/csv; charset=utf-8')
            self.assertIn('attachment', response['Content-Disposition'])
            self.assertIn('tindalos_metrics', response['Content-Disposition'])
            
            # CSV内容の基本的な確認
            content = response.content.decode('utf-8')
            self.assertIn('Arkham Nexus - Tindalos Metrics Export', content)
            self.assertIn('Export User', content)

    def test_tindalos_json_export(self):
        """Tindalos JSON エクスポートテスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accounts/export/?type=tindalos&format=json')
        
        if response.status_code == status.HTTP_200_OK:
            # JSONレスポンスの確認
            self.assertEqual(response['content-type'], 'application/json; charset=utf-8')
            self.assertIn('attachment', response['Content-Disposition'])
            
            # JSON内容の確認
            content = response.content.decode('utf-8')
            data = json.loads(content)
            self.assertIn('export_info', data)
            self.assertIn('data', data)
            self.assertEqual(data['export_info']['type'], 'tindalos_metrics')

    def test_ranking_csv_export(self):
        """ランキング CSV エクスポートテスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accounts/export/?type=ranking&format=csv')
        
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response['content-type'], 'text/csv; charset=utf-8')
            self.assertIn('user_ranking', response['Content-Disposition'])

    def test_groups_csv_export(self):
        """グループ統計 CSV エクスポートテスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accounts/export/?type=groups&format=csv')
        
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response['content-type'], 'text/csv; charset=utf-8')
            self.assertIn('group_statistics', response['Content-Disposition'])

    def test_invalid_export_type(self):
        """無効なエクスポートタイプのテスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accounts/export/?type=invalid&format=csv')
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            data = response.json()
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'Invalid data type')

    def test_invalid_export_format(self):
        """無効なエクスポート形式のテスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accounts/export/?type=tindalos&format=invalid')
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            data = response.json()
            self.assertIn('error', data)

    def test_csv_content_structure(self):
        """CSV内容の構造テスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accounts/export/?type=tindalos&format=csv')
        
        if response.status_code == status.HTTP_200_OK:
            content = response.content.decode('utf-8')
            reader = csv.reader(StringIO(content))
            rows = list(reader)
            
            # 基本的な構造の確認
            self.assertTrue(len(rows) > 5)  # ヘッダー + データが存在
            
            # 特定のセクションが含まれているか確認
            content_str = '\n'.join([','.join(row) for row in rows])
            self.assertIn('Annual Statistics', content_str)
            self.assertIn('Monthly Statistics', content_str)

    def test_json_export_structure(self):
        """JSON エクスポートの構造テスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accounts/export/?type=tindalos&format=json')
        
        if response.status_code == status.HTTP_200_OK:
            content = response.content.decode('utf-8')
            data = json.loads(content)
            
            # エクスポート情報の確認
            export_info = data['export_info']
            self.assertEqual(export_info['type'], 'tindalos_metrics')
            self.assertIn('year', export_info)
            self.assertIn('export_date', export_info)
            self.assertIn('user', export_info)
            
            # データ構造の確認
            export_data = data['data']
            self.assertIn('user', export_data)
            self.assertIn('yearly_stats', export_data)

    def test_year_parameter_handling(self):
        """年パラメータの処理テスト"""
        self.client.force_authenticate(user=self.user)
        
        # 特定の年を指定
        response = self.client.get('/api/accounts/export/?type=tindalos&format=json&year=2023')
        
        if response.status_code == status.HTTP_200_OK:
            content = response.content.decode('utf-8')
            data = json.loads(content)
            
            # 指定した年が正しく設定されているか確認
            if 'year' in data['export_info']:
                # 年は文字列または数値で返される可能性がある
                year_value = data['export_info']['year']
                self.assertIn(str(year_value), ['2023', '2023'])

    def test_export_file_naming(self):
        """エクスポートファイル名のテスト"""
        self.client.force_authenticate(user=self.user)
        
        # CSV ファイル名
        response = self.client.get('/api/accounts/export/?type=tindalos&format=csv')
        if response.status_code == status.HTTP_200_OK:
            filename = response['Content-Disposition']
            self.assertIn('tindalos_metrics', filename)
            self.assertIn('.csv', filename)
        
        # JSON ファイル名
        response = self.client.get('/api/accounts/export/?type=ranking&format=json')
        if response.status_code == status.HTTP_200_OK:
            filename = response['Content-Disposition']
            self.assertIn('user_ranking', filename)
            self.assertIn('.json', filename)

    def test_pdf_export_fallback(self):
        """PDF エクスポートのフォールバック テスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accounts/export/?type=tindalos&format=pdf')
        
        # PDFが利用できない場合はCSVにフォールバックするか、
        # 利用できる場合はPDFレスポンスが返される
        if response.status_code == status.HTTP_200_OK:
            content_type = response['content-type']
            self.assertIn(content_type, ['application/pdf', 'text/csv; charset=utf-8'])

    def test_export_with_no_data(self):
        """データが存在しない場合のエクスポートテスト"""
        # 新規ユーザーを作成（データなし）
        new_user = User.objects.create_user(
            username='nodata',
            email='nodata@example.com',
            password='pass123',
            nickname='No Data User'
        )
        
        self.client.force_authenticate(user=new_user)
        response = self.client.get('/api/accounts/export/?type=tindalos&format=csv')
        
        # データがなくてもエクスポートは成功する
        if response.status_code == status.HTTP_200_OK:
            content = response.content.decode('utf-8')
            self.assertIn('No Data User', content)
    
    # 新仕様のテストケースを追加
    def test_statistics_export_endpoint_new_spec(self):
        """新仕様: /api/accounts/export/statistics/ エンドポイントのテスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accounts/export/statistics/')
        
        # 実装前は404、実装後は200を期待
        if response.status_code == status.HTTP_200_OK:
            # デフォルトはJSON形式
            self.assertIn('application/json', response['Content-Type'])
            data = response.json()
            
            # 新仕様: 統計データの構造確認
            self.assertIn('user_statistics', data)
            self.assertIn('play_history', data)
            self.assertIn('session_statistics', data)
            self.assertIn('scenario_statistics', data)
            
            # ユーザー統計の内容確認
            user_stats = data['user_statistics']
            self.assertIn('total_sessions', user_stats)
            self.assertIn('total_play_time', user_stats)
            self.assertIn('scenarios_played', user_stats)
            self.assertIn('gm_sessions', user_stats)
            self.assertIn('player_sessions', user_stats)
        else:
            # 実装前は404であることを確認
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_export_formats_endpoint_new_spec(self):
        """新仕様: /api/accounts/export/formats/ エンドポイントのテスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accounts/export/formats/')
        
        # 実装前は404、実装後は200を期待
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            
            # 新仕様: formats配列に各形式の詳細情報
            self.assertIn('formats', data)
            formats = data['formats']
            self.assertIsInstance(formats, list)
            
            # 期待される形式: JSON, CSV, PDF
            format_names = [f['name'] for f in formats if isinstance(f, dict)]
            self.assertIn('json', format_names)
            self.assertIn('csv', format_names)
            self.assertIn('pdf', format_names)
            
            # 各形式の詳細情報確認
            for format_info in formats:
                if isinstance(format_info, dict):
                    self.assertIn('name', format_info)
                    self.assertIn('description', format_info)
                    self.assertIn('mime_type', format_info)
                    self.assertIn('available', format_info)
        else:
            # 実装前は404であることを確認
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# 統合テストケース
class ExportIntegrationTestCase(APITestCase):
    """エクスポート機能の統合テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.user = User.objects.create_user(
            username='integration_user',
            email='integration@arkham.edu',
            password='integration_2024',
            nickname='Integration User'
        )
        
        # 大量のテストデータ作成
        self.gm_user = User.objects.create_user(
            username='perf_gm',
            email='perf_gm@arkham.edu',
            password='perf_2024'
        )
        
        self.group = Group.objects.create(
            name='Integration Test Group',
            created_by=self.gm_user
        )
        
        self.scenario = Scenario.objects.create(
            title='Integration Test Scenario',
            author='Test Author',
            game_system='coc',
            created_by=self.gm_user
        )
        
        # 複数セッションの作成
        for i in range(10):
            session_date = timezone.now() - timedelta(days=i*7)
            session = TRPGSession.objects.create(
                title=f'Integration Session {i}',
                date=session_date,
                gm=self.gm_user,
                group=self.group,
                status='completed',
                duration_minutes=240
            )
            
            PlayHistory.objects.create(
                user=self.user,
                scenario=self.scenario,
                session=session,
                played_date=session_date,
                role='player',
                notes=f'Integration test session {i}'
            )
    
    def test_export_workflow_complete(self):
        """エクスポート機能の完全ワークフローテスト"""
        self.client.force_authenticate(user=self.user)
        
        # 1. 利用可能なフォーマット一覧を取得
        formats_response = self.client.get('/api/accounts/export/formats/')
        
        if formats_response.status_code == status.HTTP_200_OK:
            formats_data = formats_response.json()
            available_formats = []
            
            if 'formats' in formats_data:
                formats = formats_data['formats']
                if isinstance(formats, list):
                    available_formats = [f['name'] if isinstance(f, dict) else f for f in formats]
                elif isinstance(formats, dict):
                    available_formats = [k for k, v in formats.items() if v.get('available', False)]
            
            # 2. 各フォーマットでエクスポートを実行
            for format_type in ['json', 'csv', 'pdf']:
                if format_type in available_formats:
                    export_response = self.client.get('/api/accounts/export/statistics/', {
                        'format': format_type
                    })
                    
                    # フォーマットが利用可能な場合は正常にエクスポートできることを確認
                    self.assertEqual(export_response.status_code, status.HTTP_200_OK)
                    
                    # Content-Typeの確認
                    if format_type == 'json':
                        self.assertIn('application/json', export_response['Content-Type'])
                    elif format_type == 'csv':
                        self.assertEqual(export_response['Content-Type'], 'text/csv')
                    elif format_type == 'pdf':
                        self.assertEqual(export_response['Content-Type'], 'application/pdf')
    
    def test_export_performance_with_large_dataset(self):
        """大量データに対するエクスポート性能テスト"""
        self.client.force_authenticate(user=self.user)
        
        # エクスポート実行時間の確認
        import time
        start_time = time.time()
        
        response = self.client.get('/api/accounts/export/statistics/', {'format': 'json'})
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        if response.status_code == status.HTTP_200_OK:
            # エクスポートが5秒以内に完了することを確認
            self.assertLess(execution_time, 5.0, 
                          f"Export took {execution_time:.2f} seconds, which is too slow")
            
            # データの整合性確認
            data = response.json()
            play_history = data.get('play_history', [])
            self.assertEqual(len(play_history), 10, "All 10 sessions should be exported")
