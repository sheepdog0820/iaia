#!/usr/bin/env python3
"""
グループ管理のデバッグ用スクリプト
"""

import os
import sys
import django
from django.test import Client
from django.contrib.auth import get_user_model

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

def test_groups_page_access():
    """グループページアクセステスト"""
    print("🔍 グループ管理ページアクセステスト開始...")
    
    client = Client()
    User = get_user_model()
    
    # 未ログイン状態でのアクセステスト
    print("\n1. 未ログイン状態でのアクセステスト")
    response = client.get('/accounts/groups/view/')
    print(f"   ステータス: {response.status_code}")
    if response.status_code == 302:
        print(f"   リダイレクト先: {response.url}")
    
    # ログイン状態でのアクセステスト
    print("\n2. ログイン状態でのアクセステスト")
    user = User.objects.filter(username='groupuser1').first()
    if user:
        client.force_login(user)
        response = client.get('/accounts/groups/view/')
        print(f"   ステータス: {response.status_code}")
        print(f"   レスポンス長: {len(response.content)} bytes")
        
        if response.status_code == 200:
            print("   ✅ ページアクセス成功")
        else:
            print(f"   ❌ エラー: {response.status_code}")
    else:
        print("   ❌ テストユーザーが見つかりません")
    
    # API エンドポイントテスト
    print("\n3. グループAPI エンドポイントテスト")
    if user:
        # グループ一覧
        response = client.get('/api/accounts/groups/')
        print(f"   グループ一覧: {response.status_code}")
        if response.status_code == 200:
            groups = response.json()
            print(f"   取得したグループ数: {len(groups)}")
        
        # 公開グループ一覧
        response = client.get('/api/accounts/groups/public/')
        print(f"   公開グループ一覧: {response.status_code}")
        if response.status_code == 200:
            public_groups = response.json()
            print(f"   公開グループ数: {len(public_groups)}")
        
        # フレンド一覧
        response = client.get('/api/accounts/friends/')
        print(f"   フレンド一覧: {response.status_code}")
        if response.status_code == 200:
            friends = response.json()
            print(f"   フレンド数: {len(friends)}")

def check_url_patterns():
    """URL パターンの確認"""
    print("\n🗺️ URL パターン確認...")
    
    from django.urls import reverse, NoReverseMatch
    
    urls_to_check = [
        'groups_view',
        'statistics_view',
        'dashboard',
    ]
    
    for url_name in urls_to_check:
        try:
            url = reverse(url_name)
            print(f"   ✅ {url_name}: {url}")
        except NoReverseMatch:
            print(f"   ❌ {url_name}: URL not found")

def check_template_exists():
    """テンプレートファイルの確認"""
    print("\n📄 テンプレートファイル確認...")
    
    import os
    template_path = 'templates/groups/management.html'
    
    if os.path.exists(template_path):
        print(f"   ✅ {template_path} 存在します")
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"   ファイルサイズ: {len(content)} 文字")
            if 'Cult Circle' in content:
                print("   ✅ 'Cult Circle' が含まれています")
            else:
                print("   ❌ 'Cult Circle' が見つかりません")
    else:
        print(f"   ❌ {template_path} が見つかりません")

def main():
    """メイン実行関数"""
    print("=" * 60)
    print("🦑 タブレノ - グループ管理デバッグツール")
    print("=" * 60)
    
    check_url_patterns()
    check_template_exists()
    test_groups_page_access()
    
    print("\n" + "=" * 60)
    print("🔧 デバッグ完了!")
    print("💡 ブラウザでの確認手順:")
    print("   1. http://127.0.0.1:8000/login/ でログイン")
    print("   2. ユーザー名: groupuser1, パスワード: testpass123")
    print("   3. http://127.0.0.1:8000/accounts/groups/view/ にアクセス")
    print("=" * 60)

if __name__ == '__main__':
    main()