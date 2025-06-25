"""
APIのデバッグ用テスト
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta

from accounts.models import Group, GroupMembership
from schedules.models import TRPGSession

User = get_user_model()


class APIDebugTest(TestCase):
    """APIデバッグテスト"""
    
    def setUp(self):
        """基本的なテストデータの作成"""
        self.client = APIClient()
        
        # ユーザー作成
        self.gm = User.objects.create_user(
            username='gm',
            password='gmpass123',
            email='gm@test.com'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='テストグループ',
            created_by=self.gm,
            visibility='private'
        )
        
        # グループメンバーシップ追加
        GroupMembership.objects.create(
            user=self.gm,
            group=self.group,
            role='admin'
        )
        
        # 認証
        self.client.force_authenticate(user=self.gm)
    
    def test_session_api_create(self):
        """セッションAPI作成のテスト"""
        # 最小限のデータで作成を試みる
        session_data = {
            'title': 'テストセッション',
            'date': (timezone.now() + timedelta(days=7)).isoformat(),
            'group': self.group.id
        }
        
        print(f"\n送信データ: {session_data}")
        
        response = self.client.post('/api/schedules/sessions/', session_data)
        
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {response.data if hasattr(response, 'data') else response.content}")
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print("必須フィールドのエラー詳細:")
            for field, errors in response.data.items():
                print(f"  {field}: {errors}")
        
        # もし成功したら、作成されたセッションの内容を確認
        if response.status_code == status.HTTP_201_CREATED:
            session = TRPGSession.objects.get(id=response.data['id'])
            print(f"\n作成されたセッション:")
            print(f"  ID: {session.id}")
            print(f"  タイトル: {session.title}")
            print(f"  日時: {session.date}")
            print(f"  GM: {session.gm}")
            print(f"  グループ: {session.group}")
            print(f"  ステータス: {session.status}")
        
        return response