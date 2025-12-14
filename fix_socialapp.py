#!/usr/bin/env python3
"""
SocialApp設定修正スクリプト
"""
import os
import sys
import django
from decouple import config

# Django設定を読み込み
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

# 環境変数から認証情報を取得
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')

def fix_socialapp():
    """SocialAppの設定を修正"""
    print("SocialApp設定の修正を開始します...\n")
    
    # 現在のサイトを取得
    site = Site.objects.get_current()
    print(f"現在のサイト: {site.domain} (ID: {site.id})")
    
    # すべてのサイトを表示
    all_sites = Site.objects.all()
    print(f"\nすべてのサイト:")
    for s in all_sites:
        print(f"  ID: {s.id}, Domain: {s.domain}, Name: {s.name}")
    
    # 既存のGoogle Appを削除
    print("\n既存のGoogle Appを削除します...")
    SocialApp.objects.filter(provider='google').delete()
    
    # 環境変数チェック
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("\n[ERROR] 環境変数が設定されていません")
        print("以下の環境変数を.envファイルに設定してください:")
        print("  - GOOGLE_CLIENT_ID")
        print("  - GOOGLE_CLIENT_SECRET")
        sys.exit(1)

    # 新しいGoogle Appを作成
    print("\n新しいGoogle Appを作成します...")
    google_app = SocialApp.objects.create(
        provider='google',
        name='Google',
        client_id=GOOGLE_CLIENT_ID,
        secret=GOOGLE_CLIENT_SECRET
    )
    
    # 現在のサイトに関連付け
    google_app.sites.add(site)
    print(f"✅ Google Appを作成し、サイト {site.domain} に関連付けました")
    
    # 確認
    print("\n最終確認:")
    final_app = SocialApp.objects.get(provider='google')
    print(f"  Provider: {final_app.provider}")
    print(f"  Name: {final_app.name}")
    print(f"  Client ID: {final_app.client_id}")
    print(f"  Sites: {list(final_app.sites.all())}")

if __name__ == '__main__':
    fix_socialapp()