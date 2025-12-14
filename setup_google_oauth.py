#!/usr/bin/env python3
"""
Google OAuth設定スクリプト
django-allauthのSocialAppを設定します
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

def setup_google_oauth():
    """Google OAuth用のSocialAppを設定"""
    print("Google OAuth設定を開始します...")

    # 環境変数チェック
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("\n[ERROR] 環境変数が設定されていません")
        print("以下の環境変数を.envファイルに設定してください:")
        print("  - GOOGLE_CLIENT_ID")
        print("  - GOOGLE_CLIENT_SECRET")
        sys.exit(1)

    # 現在のサイトを取得
    site = Site.objects.get_current()
    print(f"現在のサイト: {site.domain}")

    # 既存のGoogle Appを確認
    try:
        google_app = SocialApp.objects.get(provider='google')
        print(f"\nGoogle Appが既に存在します:")
        print(f"  Client ID: {google_app.client_id}")
        print(f"  Secret: {google_app.secret[:20]}...")
        print(f"  Sites: {list(google_app.sites.all())}")

        # 設定を更新
        google_app.client_id = GOOGLE_CLIENT_ID
        google_app.secret = GOOGLE_CLIENT_SECRET
        google_app.save()

        # サイトとの関連付けを確認
        if site not in google_app.sites.all():
            google_app.sites.add(site)
            print(f"  サイト {site.domain} を追加しました")

        print("\nGoogle App設定を更新しました！")

    except SocialApp.DoesNotExist:
        print("\nGoogle Appが見つかりません。新規作成します...")

        # Google Social Appを作成
        google_app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id=GOOGLE_CLIENT_ID,
            secret=GOOGLE_CLIENT_SECRET
        )
        google_app.sites.add(site)

        print("Google Social Appを作成しました！")
    
    # サイトのドメインが正しいか確認
    if site.domain == 'example.com':
        print(f"\n⚠️  警告: サイトドメインが 'example.com' になっています。")
        print("以下のコマンドで修正してください:")
        print("python3 manage.py shell")
        print(">>> from django.contrib.sites.models import Site")
        print(">>> site = Site.objects.get_current()")
        print(">>> site.domain = 'localhost:8000'")
        print(">>> site.name = 'Arkham Nexus'")
        print(">>> site.save()")

if __name__ == '__main__':
    setup_google_oauth()