#!/usr/bin/env python3
"""
Twitter/X OAuth設定スクリプト
django-allauthのSocialAppを設定します
"""
import os
import sys
import argparse
from pathlib import Path
import django

REPO_ROOT = Path(__file__).resolve().parent


def _ensure_default_env_file():
    """
    Prefer the repo's `.env.development` when ENV_FILE isn't set.

    The Django settings loader only reads an env file when `ENV_FILE` is set.
    """
    if os.environ.get('ENV_FILE'):
        return
    for candidate in ('.env.development', '.env'):
        env_path = REPO_ROOT / candidate
        if env_path.exists():
            os.environ['ENV_FILE'] = str(env_path)
            return


_ensure_default_env_file()

# Django設定を読み込み
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

from django.conf import settings as django_settings
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

# 環境変数から認証情報を取得
TWITTER_CLIENT_ID = getattr(django_settings, 'TWITTER_CLIENT_ID', '')
TWITTER_CLIENT_SECRET = getattr(django_settings, 'TWITTER_CLIENT_SECRET', '')
DEFAULT_SITE_DOMAIN = os.environ.get('SITE_DOMAIN', '127.0.0.1:8000')
DEFAULT_SITE_NAME = os.environ.get('SITE_NAME', 'タブレノ (Local Development)')

def default_scheme(domain: str) -> str:
    if domain.startswith('localhost') or domain.startswith('127.0.0.1'):
        return 'http'
    return 'https'

def parse_args():
    parser = argparse.ArgumentParser(description='X (Twitter) OAuth設定スクリプト')
    parser.add_argument(
        '--domain',
        default=DEFAULT_SITE_DOMAIN,
        help='django.contrib.sites のドメイン (例: 127.0.0.1:8000, your-ngrok-domain.ngrok-free.dev)',
    )
    parser.add_argument(
        '--scheme',
        choices=['http', 'https'],
        default=None,
        help='コールバックURLのスキーム (未指定ならドメインから推測)',
    )
    parser.add_argument(
        '--name',
        default=DEFAULT_SITE_NAME,
        help='Siteの表示名',
    )
    args = parser.parse_args()
    if args.scheme is None:
        args.scheme = default_scheme(args.domain)
    return args


def setup_twitter_oauth(site_domain: str, site_name: str, site_scheme: str):
    """X (Twitter) OAuth2用のSocialAppを設定"""
    print("X (Twitter) OAuth2 設定を開始します...\n")

    # 環境変数チェック
    if TWITTER_CLIENT_ID and TWITTER_CLIENT_SECRET:
        client_id = TWITTER_CLIENT_ID
        client_secret = TWITTER_CLIENT_SECRET
    else:
        print("[ERROR] 環境変数が設定されていません")
        print("以下の環境変数を ENV_FILE で指定した環境ファイルに設定してください:")
        print("  - TWITTER_CLIENT_ID (or X_CLIENT_ID)")
        print("  - TWITTER_CLIENT_SECRET (or X_CLIENT_SECRET)")
        print("ヒント: ENV_FILE 未指定の場合、このスクリプトは .env.development -> .env の順で自動検出します。")
        sys.exit(1)

    # Siteを指定ドメインに統一
    site = Site.objects.get_current()
    print("[1/3] サイト設定を確認中...")
    print(f"  現在のドメイン: {site.domain}")

    if site.domain != site_domain:
        site.domain = site_domain
        site.name = site_name
        site.save()
        print(f"  [OK] ドメインを '{site_domain}' に更新しました")
    else:
        print("  [OK] ドメインは正しく設定されています")

    # 既存のTwitter Appを確認
    print("\n[2/3] X (Twitter) SocialApp設定を確認中...")
    try:
        twitter_app = SocialApp.objects.get(provider='twitter_oauth2')
        print("  X (Twitter) SocialAppが既に存在します")
        print(f"  Client ID: {twitter_app.client_id[:20]}...")
        print("  Secret: ******************** (セキュリティのため非表示)")

        # 設定を更新
        twitter_app.client_id = client_id
        twitter_app.secret = client_secret
        twitter_app.save()
        print("  [OK] 認証情報を更新しました")

        # サイトとの関連付けを確認
        if site not in twitter_app.sites.all():
            twitter_app.sites.add(site)
            print(f"  [OK] サイト '{site.domain}' を追加しました")
        else:
            print("  [OK] サイトは正しく関連付けられています")

    except SocialApp.DoesNotExist:
        print("  X (Twitter) SocialAppが見つかりません。新規作成します...")

        # Twitter Social Appを作成
        twitter_app = SocialApp.objects.create(
            provider='twitter_oauth2',
            name='X',
            client_id=client_id,
            secret=client_secret
        )
        twitter_app.sites.add(site)
        print("  [OK] X (Twitter) SocialAppを作成しました")

    # 最終確認
    print("\n[3/3] 設定の最終確認...")
    print(f"  サイトドメイン: {site.domain}")
    print(f"  SocialApp: X (ID: {twitter_app.id})")
    print(f"  関連付けられたサイト数: {twitter_app.sites.count()}")

    print("\n[OK] セットアップ完了！")

    base_url = f"{site_scheme}://{site_domain}"
    print("\n次のステップ:")
    print("1. 開発サーバーを起動: python manage.py runserver")
    print(f"2. ブラウザで {base_url}/accounts/login/ にアクセス")
    print("3. 'X (Twitter)でログイン' ボタンをクリック")
    print("\n[NOTE] 注意: X Developer PortalのコールバックURLに以下が登録されていることを確認してください:")
    print(f"   {base_url}/accounts/twitter_oauth2/login/callback/")


if __name__ == '__main__':
    args = parse_args()
    setup_twitter_oauth(args.domain, args.name, args.scheme)
