#!/usr/bin/env python3
"""
Google OAuth設定スクリプト
django-allauthのSocialAppを設定します
"""

import argparse
import os
import sys
from pathlib import Path

import django

REPO_ROOT = Path(__file__).resolve().parent


def _ensure_default_env_file():
    """
    Prefer the repo's `.env.development` when ENV_FILE isn't set.

    The Django settings loader only reads an env file when `ENV_FILE` is set.
    """
    if os.environ.get("ENV_FILE"):
        return
    for candidate in (".env.development", ".env"):
        env_path = REPO_ROOT / candidate
        if env_path.exists():
            os.environ["ENV_FILE"] = str(env_path)
            return


_ensure_default_env_file()

# Django設定を読み込み
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tableno.settings")
django.setup()

from allauth.socialaccount.models import SocialApp
from django.conf import settings as django_settings
from django.contrib.sites.models import Site

# 環境変数から認証情報を取得
GOOGLE_CLIENT_ID = getattr(django_settings, "GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = getattr(django_settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
DEFAULT_SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "127.0.0.1:8000")
DEFAULT_SITE_NAME = os.environ.get("SITE_NAME", "タブレノ (Local Development)")


def default_scheme(domain: str) -> str:
    if domain.startswith("localhost") or domain.startswith("127.0.0.1"):
        return "http"
    return "https"


def parse_args():
    parser = argparse.ArgumentParser(description="Google OAuth設定スクリプト")
    parser.add_argument(
        "--domain",
        default=DEFAULT_SITE_DOMAIN,
        help="django.contrib.sites のドメイン (例: 127.0.0.1:8000, your-ngrok-domain.ngrok-free.dev)",
    )
    parser.add_argument(
        "--scheme",
        choices=["http", "https"],
        default=None,
        help="コールバックURLのスキーム (未指定ならドメインから推測)",
    )
    parser.add_argument(
        "--name",
        default=DEFAULT_SITE_NAME,
        help="Siteの表示名",
    )
    args = parser.parse_args()
    if args.scheme is None:
        args.scheme = default_scheme(args.domain)
    return args


def setup_google_oauth(site_domain: str, site_name: str, site_scheme: str):
    """Google OAuth用のSocialAppを設定"""
    print("Google OAuth設定を開始します...\n")

    # 環境変数チェック
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("[ERROR] 環境変数が設定されていません")
        print("以下の環境変数を ENV_FILE で指定した環境ファイルに設定してください:")
        print("  - GOOGLE_CLIENT_ID")
        print("  - GOOGLE_CLIENT_SECRET")
        print("ヒント: ENV_FILE 未指定の場合、このスクリプトは .env.development -> .env の順で自動検出します。")
        sys.exit(1)

    # Siteを指定ドメインに統一
    site = Site.objects.get_current()
    print(f"[1/3] サイト設定を確認中...")
    print(f"  現在のドメイン: {site.domain}")

    if site.domain != site_domain:
        site.domain = site_domain
        site.name = site_name
        site.save()
        print(f"  [OK] ドメインを '{site_domain}' に更新しました")
    else:
        print(f"  [OK] ドメインは正しく設定されています")

    # 既存のGoogle Appを確認
    print(f"\n[2/3] Google SocialApp設定を確認中...")
    try:
        google_app = SocialApp.objects.get(provider="google")
        print(f"  Google SocialAppが既に存在します")
        print(f"  Client ID: {google_app.client_id[:20]}...")
        print(f"  Secret: {'*' * 20}... (セキュリティのため非表示)")

        # 設定を更新
        google_app.client_id = GOOGLE_CLIENT_ID
        google_app.secret = GOOGLE_CLIENT_SECRET
        google_app.save()
        print(f"  [OK] 認証情報を更新しました")

        # サイトとの関連付けを確認
        if site not in google_app.sites.all():
            google_app.sites.add(site)
            print(f"  [OK] サイト '{site.domain}' を追加しました")
        else:
            print(f"  [OK] サイトは正しく関連付けられています")

    except SocialApp.DoesNotExist:
        print(f"  Google SocialAppが見つかりません。新規作成します...")

        # Google Social Appを作成
        google_app = SocialApp.objects.create(
            provider="google", name="Google", client_id=GOOGLE_CLIENT_ID, secret=GOOGLE_CLIENT_SECRET
        )
        google_app.sites.add(site)
        print(f"  [OK] Google SocialAppを作成しました")

    # 最終確認
    print(f"\n[3/3] 設定の最終確認...")
    print(f"  サイトドメイン: {site.domain}")
    print(f"  SocialApp: Google (ID: {google_app.id})")
    print(f"  関連付けられたサイト数: {google_app.sites.count()}")

    print(f"\n[OK] セットアップ完了！")

    base_url = f"{site_scheme}://{site_domain}"
    print(f"\n次のステップ:")
    print(f"1. 開発サーバーを起動: python manage.py runserver")
    print(f"2. ブラウザで {base_url}/accounts/login/ にアクセス")
    print(f"3. 'Googleでログイン' ボタンをクリック")
    print(f"\n[NOTE] 注意: Google Cloud ConsoleのリダイレクトURIに以下が登録されていることを確認してください:")
    print(f"   {base_url}/accounts/google/login/callback/")


if __name__ == "__main__":
    args = parse_args()
    setup_google_oauth(args.domain, args.name, args.scheme)
