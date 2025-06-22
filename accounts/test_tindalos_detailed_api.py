"""
Tindalos統計API詳細機能のテストスイート
年度・月別詳細集計、ゲームシステム別統計、期間指定フィルタ機能をテスト
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import datetime, timedelta
from schedules.models import TRPGSession, SessionParticipant
from scenarios.models import Scenario, PlayHistory
from .models import Group

User = get_user_model()


class SimpleTindalosMetricsDetailedTestCase(APITestCase):
    """SimpleTindalosMetricsViewの詳細機能テストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
        
        # テスト用グループ作成
        self.group = Group.objects.create(
            name='Test Group',
            description='Test group for statistics',
            visibility='private',
            created_by=self.user
        )
        self.group.members.add(self.user)
        
        # テスト用シナリオ作成
        self.scenarios = []
        for i in range(3):
            scenario = Scenario.objects.create(
                title=f'Test Scenario {i+1}',
                author='Test Author',
                created_by=self.user,
                game_system='coc' if i % 2 == 0 else 'dnd',
                difficulty='intermediate',
                estimated_time=180,
                summary=f'Test scenario {i+1} description'
            )
            self.scenarios.append(scenario)
    
    def test_simple_metrics_with_detailed_flag(self):
        """detailed=trueパラメータで詳細データが返ることをテスト"""
        # 複数年度のデータを作成
        current_year = timezone.now().year
        
        for year_offset in range(3):
            year = current_year - year_offset
            for month in [3, 6, 9, 12]:
                date = datetime(year, month, 15)
                session = TRPGSession.objects.create(
                    title=f'Session {year}-{month}',
                    group=self.group,
                    gm=self.user,
                    date=date,
                    duration_minutes=240,
                    status='completed'
                )
                session.participants.add(self.user)
                
                # プレイ履歴を追加
                scenario = self.scenarios[year_offset % len(self.scenarios)]
                PlayHistory.objects.create(
                    scenario=scenario,
                    user=self.user,
                    session=session,
                    played_date=date,
                    role='gm'
                )
        
        # 詳細データをリクエスト
        response = self.client.get('/api/accounts/statistics/tindalos/?detailed=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('yearly_trends', response.data)
        self.assertIn('popular_scenarios', response.data)
        self.assertIn('system_trends', response.data)
        
        # 年度トレンドの確認
        yearly_trends = response.data['yearly_trends']
        self.assertEqual(len(yearly_trends), 3)  # 3年分のデータ
        for year_data in yearly_trends:
            self.assertIn('year', year_data)
            self.assertIn('session_count', year_data)
            self.assertIn('total_hours', year_data)
    
    def test_monthly_details_with_year_filter(self):
        """年度指定での月別詳細データ取得テスト"""
        year = timezone.now().year
        
        # 各月にセッションを作成
        for month in range(1, 13):
            date = datetime(year, month, 15)
            session = TRPGSession.objects.create(
                title=f'Monthly Session {month}',
                group=self.group,
                gm=self.user,
                date=date,
                duration_minutes=180,
                status='completed'
            )
            session.participants.add(self.user)
            
            # 月によって異なるシナリオをプレイ
            scenario_idx = (month - 1) % len(self.scenarios)
            PlayHistory.objects.create(
                scenario=self.scenarios[scenario_idx],
                user=self.user,
                session=session,
                played_date=date,
                role='player' if month % 2 == 0 else 'gm'
            )
        
        response = self.client.get(f'/api/accounts/statistics/tindalos/?detailed=true&year={year}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('monthly_details', response.data)
        
        monthly_details = response.data['monthly_details']
        self.assertEqual(len(monthly_details), 12)  # 12ヶ月分
        
        for month_data in monthly_details:
            self.assertIn('month', month_data)
            self.assertIn('session_count', month_data)
            self.assertIn('scenarios', month_data)
    
    def test_popular_scenarios_ranking(self):
        """人気シナリオランキングのテスト"""
        # 同じシナリオを複数回プレイ
        popular_scenario = self.scenarios[0]
        
        for i in range(5):
            date = timezone.now() - timedelta(days=i*7)
            session = TRPGSession.objects.create(
                title=f'Popular Session {i+1}',
                group=self.group,
                gm=self.user,
                date=date,
                duration_minutes=240,
                status='completed'
            )
            session.participants.add(self.user)
            
            PlayHistory.objects.create(
                scenario=popular_scenario,
                user=self.user,
                session=session,
                played_date=date,
                role='gm' if i % 2 == 0 else 'player'
            )
        
        # 他のシナリオも少しプレイ
        for scenario in self.scenarios[1:]:
            session = TRPGSession.objects.create(
                title=f'Other Session {scenario.id}',
                group=self.group,
                gm=self.user,
                date=timezone.now(),
                duration_minutes=180,
                status='completed'
            )
            session.participants.add(self.user)
            
            PlayHistory.objects.create(
                scenario=scenario,
                user=self.user,
                session=session,
                played_date=timezone.now(),
                role='player'
            )
        
        response = self.client.get('/api/accounts/statistics/tindalos/?detailed=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('popular_scenarios', response.data)
        
        popular_scenarios = response.data['popular_scenarios']
        self.assertGreater(len(popular_scenarios), 0)
        
        # 最も人気のシナリオが最初に来ることを確認
        top_scenario = popular_scenarios[0]
        self.assertEqual(top_scenario['scenario__id'], popular_scenario.id)
        self.assertEqual(top_scenario['play_count'], 5)
    
    def test_system_trends_over_years(self):
        """ゲームシステム別の年次推移テスト"""
        current_year = timezone.now().year
        
        # 過去3年のデータを作成
        for year_offset in range(3):
            year = current_year - year_offset
            
            # CoCのセッション
            for i in range(3 + year_offset):  # 年を追うごとに増加
                date = datetime(year, 6, 15)
                session = TRPGSession.objects.create(
                    title=f'CoC Session {year}-{i}',
                    group=self.group,
                    gm=self.user,
                    date=date,
                    duration_minutes=240,
                    status='completed'
                )
                session.participants.add(self.user)
                
                PlayHistory.objects.create(
                    scenario=self.scenarios[0],  # CoC
                    user=self.user,
                    session=session,
                    played_date=date,
                    role='gm'
                )
            
            # D&Dのセッション
            for i in range(5 - year_offset):  # 年を追うごとに減少
                date = datetime(year, 9, 15)
                session = TRPGSession.objects.create(
                    title=f'DnD Session {year}-{i}',
                    group=self.group,
                    gm=self.user,
                    date=date,
                    duration_minutes=240,
                    status='completed'
                )
                session.participants.add(self.user)
                
                PlayHistory.objects.create(
                    scenario=self.scenarios[1],  # D&D
                    user=self.user,
                    session=session,
                    played_date=date,
                    role='player'
                )
        
        response = self.client.get('/api/accounts/statistics/tindalos/?detailed=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('system_trends', response.data)
        
        system_trends = response.data['system_trends']
        self.assertGreater(len(system_trends), 0)
        
        # 各システムのトレンドデータを確認
        for system_data in system_trends:
            self.assertIn('system_code', system_data)
            self.assertIn('system_name', system_data)
            self.assertIn('data', system_data)
            
            # 年次データが含まれることを確認
            yearly_data = system_data['data']
            self.assertGreater(len(yearly_data), 0)
            
            for year_data in yearly_data:
                self.assertIn('year', year_data)
                self.assertIn('count', year_data)


class DetailedTindalosMetricsTestCase(APITestCase):
    """DetailedTindalosMetricsViewのテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
        
        # テスト用データの作成
        self.group = Group.objects.create(
            name='Test Group',
            description='Test group',
            visibility='private',
            created_by=self.user
        )
        self.group.members.add(self.user)
        
        self.scenario = Scenario.objects.create(
            title='Test Scenario',
            author='Test Author',
            created_by=self.user,
            game_system='coc',
            difficulty='intermediate',
            estimated_time=180,
            summary='Test scenario for detailed metrics'
        )
    
    def test_summary_stats_endpoint(self):
        """総合統計サマリーエンドポイントのテスト"""
        # データ作成
        year = timezone.now().year
        session = TRPGSession.objects.create(
            title='Test Session',
            group=self.group,
            gm=self.user,
            date=timezone.now(),
            duration_minutes=240,
            status='completed'
        )
        session.participants.add(self.user)
        
        PlayHistory.objects.create(
            scenario=self.scenario,
            user=self.user,
            session=session,
            played_date=timezone.now(),
            role='gm'
        )
        
        response = self.client.get('/api/accounts/statistics/tindalos/detailed/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('year', response.data)
        self.assertIn('session_count', response.data)
        self.assertIn('game_systems', response.data)
    
    def test_yearly_trends_endpoint(self):
        """年度別推移エンドポイントのテスト"""
        # 複数年のデータを作成
        for year_offset in range(3):
            year = timezone.now().year - year_offset
            date = datetime(year, 6, 15)
            
            session = TRPGSession.objects.create(
                title=f'Session {year}',
                group=self.group,
                gm=self.user,
                date=date,
                duration_minutes=240,
                status='completed'
            )
            session.participants.add(self.user)
            
            PlayHistory.objects.create(
                scenario=self.scenario,
                user=self.user,
                session=session,
                played_date=date,
                role='player'
            )
        
        response = self.client.get('/api/accounts/statistics/tindalos/detailed/?type=yearly_trends')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('period', response.data)
        self.assertIn('years', response.data)
        self.assertEqual(len(response.data['years']), 3)
    
    def test_monthly_details_endpoint(self):
        """月別詳細エンドポイントのテスト"""
        year = timezone.now().year
        
        # 各月にデータを作成
        for month in range(1, 4):  # 1-3月のみ
            date = datetime(year, month, 15)
            session = TRPGSession.objects.create(
                title=f'Session {month}',
                group=self.group,
                gm=self.user,
                date=date,
                duration_minutes=180,
                status='completed'
            )
            session.participants.add(self.user)
            
            PlayHistory.objects.create(
                scenario=self.scenario,
                user=self.user,
                session=session,
                played_date=date,
                role='gm'
            )
        
        response = self.client.get(f'/api/accounts/statistics/tindalos/detailed/?type=monthly_details&year={year}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('year', response.data)
        self.assertIn('months', response.data)
        self.assertEqual(len(response.data['months']), 12)  # 全12ヶ月分返る
        
        # 1-3月にセッションがあることを確認
        for i in range(3):
            month_data = response.data['months'][i]
            self.assertEqual(month_data['month'], i + 1)
            self.assertGreater(month_data['sessions']['total'], 0)
    
    def test_popular_scenarios_endpoint(self):
        """人気シナリオエンドポイントのテスト"""
        # 複数のプレイ履歴を作成
        for i in range(3):
            session = TRPGSession.objects.create(
                title=f'Session {i}',
                group=self.group,
                gm=self.user,
                date=timezone.now() - timedelta(days=i),
                duration_minutes=240,
                status='completed'
            )
            session.participants.add(self.user)
            
            PlayHistory.objects.create(
                scenario=self.scenario,
                user=self.user,
                session=session,
                played_date=timezone.now() - timedelta(days=i),
                role='gm' if i == 0 else 'player'
            )
        
        response = self.client.get('/api/accounts/statistics/tindalos/detailed/?type=popular_scenarios')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('scenarios', response.data)
        self.assertGreater(len(response.data['scenarios']), 0)
        
        # シナリオの詳細情報を確認
        scenario_data = response.data['scenarios'][0]
        self.assertIn('title', scenario_data)
        self.assertIn('system', scenario_data)
        self.assertIn('stats', scenario_data)
        self.assertIn('dates', scenario_data)
    
    def test_system_trends_endpoint(self):
        """ゲームシステム推移エンドポイントのテスト"""
        # 複数システムのデータを作成
        systems = ['coc', 'dnd']
        
        for year_offset in range(2):
            year = timezone.now().year - year_offset
            
            for system in systems:
                scenario = Scenario.objects.create(
                    title=f'{system} Scenario {year}',
                    author='Test Author',
                    created_by=self.user,
                    game_system=system,
                    difficulty='intermediate',
                    estimated_time=180
                )
                
                session = TRPGSession.objects.create(
                    title=f'{system} Session {year}',
                    group=self.group,
                    gm=self.user,
                    date=datetime(year, 6, 15),
                    duration_minutes=240,
                    status='completed'
                )
                session.participants.add(self.user)
                
                PlayHistory.objects.create(
                    scenario=scenario,
                    user=self.user,
                    session=session,
                    played_date=datetime(year, 6, 15),
                    role='gm'
                )
        
        response = self.client.get('/api/accounts/statistics/tindalos/detailed/?type=system_trends')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('period', response.data)
        self.assertIn('systems', response.data)
        
        # 各システムのトレンドデータを確認
        for system_data in response.data['systems']:
            self.assertIn('system_code', system_data)
            self.assertIn('yearly_data', system_data)
            self.assertIn('summary', system_data)
            
            # サマリー情報の確認
            summary = system_data['summary']
            self.assertIn('total_sessions', summary)
            self.assertIn('average_per_year', summary)
            self.assertIn('trend', summary)


class TindalosMetricsFilterTestCase(APITestCase):
    """期間指定フィルタ機能のテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
        
        self.group = Group.objects.create(
            name='Test Group',
            description='Test group',
            visibility='private',
            created_by=self.user
        )
        self.group.members.add(self.user)
    
    def test_year_filter_in_simple_metrics(self):
        """SimpleTindalosMetricsViewの年度フィルタテスト"""
        # 異なる年度のデータを作成
        years = [2022, 2023, 2024]
        
        for year in years:
            session = TRPGSession.objects.create(
                title=f'Session {year}',
                group=self.group,
                gm=self.user,
                date=datetime(year, 6, 15),
                duration_minutes=240,
                status='completed'
            )
            session.participants.add(self.user)
        
        # 特定年度でフィルタ
        response = self.client.get('/api/accounts/statistics/tindalos/?year=2023')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['session_count'], 1)
    
    def test_game_system_filter(self):
        """ゲームシステムフィルタのテスト"""
        # 異なるシステムのシナリオを作成
        systems = ['coc', 'dnd', 'sw']
        scenarios = []
        
        for system in systems:
            scenario = Scenario.objects.create(
                title=f'{system} Scenario',
                author='Test Author',
                created_by=self.user,
                game_system=system,
                difficulty='intermediate',
                estimated_time=180
            )
            scenarios.append(scenario)
            
            session = TRPGSession.objects.create(
                title=f'{system} Session',
                group=self.group,
                gm=self.user,
                date=timezone.now(),
                duration_minutes=240,
                status='completed'
            )
            session.participants.add(self.user)
            
            PlayHistory.objects.create(
                scenario=scenario,
                user=self.user,
                session=session,
                played_date=timezone.now(),
                role='player'
            )
        
        # CoCでフィルタ
        response = self.client.get('/api/accounts/statistics/tindalos/?game_system=coc')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['scenario_count'], 1)
    
    def test_year_range_filter_in_detailed_metrics(self):
        """DetailedTindalosMetricsViewの年度範囲フィルタテスト"""
        # 5年分のデータを作成
        current_year = timezone.now().year
        
        for year_offset in range(5):
            year = current_year - year_offset
            session = TRPGSession.objects.create(
                title=f'Session {year}',
                group=self.group,
                gm=self.user,
                date=datetime(year, 6, 15),
                duration_minutes=240,
                status='completed'
            )
            session.participants.add(self.user)
            
            scenario = Scenario.objects.create(
                title=f'Scenario {year}',
                author='Test Author',
                created_by=self.user,
                game_system='coc',
                difficulty='intermediate',
                estimated_time=180
            )
            
            PlayHistory.objects.create(
                scenario=scenario,
                user=self.user,
                session=session,
                played_date=datetime(year, 6, 15),
                role='gm'
            )
        
        # 特定の年度範囲でフィルタ
        start_year = current_year - 2
        end_year = current_year
        
        response = self.client.get(
            f'/api/accounts/statistics/tindalos/detailed/?type=yearly_trends&start_year={start_year}&end_year={end_year}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_years'], 3)
        self.assertEqual(len(response.data['years']), 3)