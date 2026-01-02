#!/usr/bin/env python3
"""
URL パターンの詳細デバッグ
"""

import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

def test_url_resolution():
    """URL解決テスト"""
    from django.urls import resolve, reverse
    from django.urls.exceptions import Resolver404
    
    print("🔍 URL 解決テスト...")
    
    # テストするURL
    test_urls = [
        '/accounts/groups/view/',
        '/accounts/dashboard/',
        '/accounts/statistics/view/',
        '/api/accounts/groups/',
    ]
    
    for url in test_urls:
        try:
            match = resolve(url)
            print(f"   ✅ {url} -> {match.view_name} ({match.func})")
        except Resolver404 as e:
            print(f"   ❌ {url} -> 404: {e}")
    
    print("\n🗺️ Reverse URL テスト...")
    url_names = ['groups_view', 'dashboard', 'statistics_view']
    
    for name in url_names:
        try:
            url = reverse(name)
            print(f"   ✅ {name} -> {url}")
        except Exception as e:
            print(f"   ❌ {name} -> エラー: {e}")

def check_accounts_urls():
    """accounts app の URL パターンを確認"""
    print("\n📋 accounts app URL パターン確認...")
    
    from accounts import urls
    from django.urls import include
    
    print(f"   accounts.urls モジュール: {urls}")
    print(f"   urlpatterns 長さ: {len(urls.urlpatterns)}")
    
    for i, pattern in enumerate(urls.urlpatterns):
        print(f"   {i+1}. {pattern}")

def test_simple_view():
    """シンプルなビューでテスト"""
    print("\n🧪 シンプルビューテスト...")
    
    from django.test import Client
    from django.contrib.auth import get_user_model
    
    client = Client()
    User = get_user_model()
    
    # ログイン
    user = User.objects.filter(username='groupuser1').first()
    if user:
        client.force_login(user)
        
        # dashboard にアクセス（これは動作するはず）
        response = client.get('/accounts/dashboard/')
        print(f"   ダッシュボード: {response.status_code}")
        
        # グループビューにアクセス
        response = client.get('/accounts/groups/view/')
        print(f"   グループビュー: {response.status_code}")
        if response.status_code != 200:
            print(f"   レスポンス内容: {response.content.decode()[:100]}...")

def main():
    """メイン実行"""
    print("=" * 60)
    print("🔧 URL デバッグツール")
    print("=" * 60)
    
    test_url_resolution()
    check_accounts_urls()
    test_simple_view()
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()