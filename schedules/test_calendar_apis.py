"""
カレンダー統合API単体テスト（ISSUE-008）
"""

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import datetime, timedelta
from accounts.models import CustomUser, Group
from schedules.models import TRPGSession, SessionParticipant
import json


class MonthlyEventListViewTestCase(APITestCase):
    """月別イベント一覧APIのテストケース"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.gm_user = CustomUser.objects.create_user(
            username='gmuser',
            email='gm@example.com',
            password='testpass123'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='Test Group',
            description='Test group for calendar API',
            created_by=self.gm_user
        )
        self.group.members.add(self.user, self.gm_user)
        
        # 認証
        self.client.force_authenticate(user=self.user)
        
        # セッション作成（今月）
        now = timezone.now()
        self.session1 = TRPGSession.objects.create(
            title='Session 1',
            description='Test session 1',
            date=now.replace(day=10, hour=14, minute=0),
            gm=self.gm_user,
            group=self.group,
            status='planned',
            visibility='group',
            duration_minutes=180
        )
        
        self.session2 = TRPGSession.objects.create(
            title='Session 2',
            description='Test session 2',
            date=now.replace(day=20, hour=19, minute=30),
            gm=self.user,  # userがGM
            group=self.group,
            status='planned',
            visibility='public',
            duration_minutes=240
        )
        
        # 参加者追加
        SessionParticipant.objects.create(
            session=self.session1,
            user=self.user,
            role='player'
        )
        SessionParticipant.objects.create(
            session=self.session2,
            user=self.gm_user,
            role='player'
        )
    
    def test_monthly_events_success(self):
        """月別イベント一覧の正常取得"""
        now = timezone.now()
        url = reverse('monthly_events')
        response = self.client.get(url, {'month': now.strftime('%Y-%m')})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # レスポンス構造の確認
        self.assertIn('month', data)
        self.assertIn('year', data)
        self.assertIn('month_name', data)
        self.assertIn('dates', data)
        self.assertIn('total_sessions', data)
        self.assertIn('summary', data)
        
        # セッション数の確認
        self.assertEqual(data['total_sessions'], 2)
        self.assertEqual(len(data['dates']), 2)  # 2つの異なる日付
        
        # ステータスサマリーの確認
        self.assertEqual(data['summary']['planned'], 2)
        self.assertEqual(data['summary']['ongoing'], 0)
        self.assertEqual(data['summary']['completed'], 0)
        self.assertEqual(data['summary']['cancelled'], 0)
    
    def test_monthly_events_date_grouping(self):
        """日付別グループ化の確認"""
        now = timezone.now()
        url = reverse('monthly_events')
        response = self.client.get(url, {'month': now.strftime('%Y-%m')})
        
        data = response.data
        dates = data['dates']
        
        # 日付順にソートされているか確認
        date_strings = [d['date'] for d in dates]
        self.assertEqual(date_strings, sorted(date_strings))
        
        # 各日付のイベント情報確認
        for date_group in dates:
            self.assertIn('date', date_group)
            self.assertIn('events', date_group)
            
            for event in date_group['events']:
                self.assertIn('id', event)
                self.assertIn('title', event)
                self.assertIn('time', event)
                self.assertIn('duration_minutes', event)
                self.assertIn('is_gm', event)
                self.assertIn('is_participant', event)
    
    def test_monthly_events_invalid_month(self):
        """無効な月指定のエラーハンドリング"""
        url = reverse('monthly_events')
        
        # 不正な形式
        response = self.client.get(url, {'month': '2025-13'})  # 13月
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response = self.client.get(url, {'month': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # パラメータなし
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_monthly_events_authentication_required(self):
        """認証必須の確認"""
        self.client.logout()
        url = reverse('monthly_events')
        response = self.client.get(url, {'month': '2025-06'})
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class SessionAggregationViewTestCase(APITestCase):
    """セッション予定集約APIのテストケース"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # グループ作成
        self.group1 = Group.objects.create(
            name='Group 1',
            created_by=self.user
        )
        self.group2 = Group.objects.create(
            name='Group 2',
            created_by=self.user
        )
        self.group1.members.add(self.user)
        self.group2.members.add(self.user)
        
        # 認証
        self.client.force_authenticate(user=self.user)
        
        # 今後30日間のセッション作成
        now = timezone.now()
        self.sessions = []
        
        # GMとして2セッション
        for i in range(2):
            session = TRPGSession.objects.create(
                title=f'GM Session {i+1}',
                date=now + timedelta(days=i*7),
                gm=self.user,
                group=self.group1,
                status='planned',
                duration_minutes=180
            )
            self.sessions.append(session)
        
        # 参加者として3セッション
        other_gm = CustomUser.objects.create_user(
            username='other_gm',
            email='other@example.com',
            password='pass123'
        )
        
        for i in range(3):
            session = TRPGSession.objects.create(
                title=f'Player Session {i+1}',
                date=now + timedelta(days=i*5+3),
                gm=other_gm,
                group=self.group2,
                status='planned',
                duration_minutes=240
            )
            SessionParticipant.objects.create(
                session=session,
                user=self.user,
                role='player'
            )
            self.sessions.append(session)
    
    def test_session_aggregation_success(self):
        """セッション集約の正常取得"""
        url = reverse('session_aggregation')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # レスポンス構造の確認
        self.assertIn('period', data)
        self.assertIn('total_sessions', data)
        self.assertIn('aggregations', data)
        self.assertIn('upcoming_sessions', data)
        
        # 期間情報の確認
        self.assertEqual(data['period']['days'], 30)
        self.assertIn('start', data['period'])
        self.assertIn('end', data['period'])
        
        # 集約情報の確認
        aggregations = data['aggregations']
        self.assertIn('by_group', aggregations)
        self.assertIn('by_week', aggregations)
        self.assertIn('by_role', aggregations)
        
        # 役割別集約の確認
        # 'planned'と'ongoing'のみが集約対象、かつ期間内のみ
        now = timezone.now()
        end_date = now + timedelta(days=30)
        
        gm_sessions = [
            s for s in self.sessions 
            if s.gm == self.user and s.status in ['planned', 'ongoing'] 
            and s.date >= now and s.date <= end_date
        ]
        player_sessions = [
            s for s in self.sessions 
            if s.gm != self.user and s.status in ['planned', 'ongoing']
            and s.date >= now and s.date <= end_date
        ]
        
        self.assertEqual(len(aggregations['by_role']['as_gm']), len(gm_sessions))
        self.assertEqual(len(aggregations['by_role']['as_player']), len(player_sessions))
    
    def test_session_aggregation_custom_days(self):
        """カスタム期間での集約"""
        url = reverse('session_aggregation')
        response = self.client.get(url, {'days': 7})
        
        data = response.data
        self.assertEqual(data['period']['days'], 7)
        
        # 7日以内のセッションのみ（かつplanned/ongoingのみ）
        now = timezone.now()
        total_in_week = sum(
            1 for s in self.sessions 
            if s.date >= now and s.date <= now + timedelta(days=7) and s.status in ['planned', 'ongoing']
        )
        self.assertEqual(data['total_sessions'], total_in_week)
    
    def test_session_aggregation_group_aggregation(self):
        """グループ別集約の確認"""
        url = reverse('session_aggregation')
        response = self.client.get(url)
        
        by_group = response.data['aggregations']['by_group']
        
        # グループ情報の確認
        for group_id, group_data in by_group.items():
            self.assertIn('group_id', group_data)
            self.assertIn('group_name', group_data)
            self.assertIn('sessions', group_data)
            
            # セッション情報の確認
            for session in group_data['sessions']:
                self.assertIn('id', session)
                self.assertIn('title', session)
                self.assertIn('date', session)


class ICalExportViewTestCase(APITestCase):
    """iCal形式エクスポートAPIのテストケース"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.group = Group.objects.create(
            name='Test Group',
            created_by=self.user
        )
        self.group.members.add(self.user)
        
        self.client.force_authenticate(user=self.user)
        
        # セッション作成
        now = timezone.now()
        self.session = TRPGSession.objects.create(
            title='Test Session for iCal',
            description='Test description',
            date=now + timedelta(days=7),
            location='オンライン',
            gm=self.user,
            group=self.group,
            status='planned',
            duration_minutes=180
        )
    
    def test_ical_export_success(self):
        """iCal形式エクスポートの正常動作"""
        url = reverse('ical_export')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/calendar; charset=utf-8')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('.ics', response['Content-Disposition'])
        
        # iCal形式の確認
        content = response.content.decode('utf-8')
        self.assertIn('BEGIN:VCALENDAR', content)
        self.assertIn('END:VCALENDAR', content)
        self.assertIn('VERSION:2.0', content)
        self.assertIn('PRODID:-//Arkham Nexus//TRPG Session Calendar//JP', content)
        
        # イベント情報の確認
        self.assertIn('BEGIN:VEVENT', content)
        self.assertIn('END:VEVENT', content)
        self.assertIn('[GM] Test Session for iCal', content)
        self.assertIn('LOCATION:オンライン', content)
        
        # アラームの確認（plannedステータスのみ）
        self.assertIn('BEGIN:VALARM', content)
        self.assertIn('END:VALARM', content)
    
    def test_ical_export_custom_days(self):
        """カスタム期間でのエクスポート"""
        # 遠い未来のセッション追加
        far_session = TRPGSession.objects.create(
            title='Far Future Session',
            date=timezone.now() + timedelta(days=100),
            gm=self.user,
            group=self.group,
            status='planned'
        )
        
        url = reverse('ical_export')
        
        # デフォルト90日
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        self.assertIn('Test Session for iCal', content)
        self.assertNotIn('Far Future Session', content)
        
        # 120日指定
        response = self.client.get(url, {'days': 120})
        content = response.content.decode('utf-8')
        self.assertIn('Test Session for iCal', content)
        self.assertIn('Far Future Session', content)
    
    def test_ical_export_status_handling(self):
        """ステータス別の処理確認"""
        # キャンセルされたセッション
        cancelled_session = TRPGSession.objects.create(
            title='Cancelled Session',
            date=timezone.now() + timedelta(days=3),
            gm=self.user,
            group=self.group,
            status='cancelled'
        )
        
        url = reverse('ical_export')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # キャンセルステータスの確認
        self.assertIn('STATUS:CANCELLED', content)
        
        # キャンセルされたセッションにはアラームなし
        events = content.split('BEGIN:VEVENT')
        for event in events:
            if 'Cancelled Session' in event:
                self.assertNotIn('BEGIN:VALARM', event)