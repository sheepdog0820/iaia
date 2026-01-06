"""
Google OAuth クライアント疎通確認スクリプト
"""
import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
import requests
import json

def test_oauth_configuration():
    """OAuth設定の確認"""
    print("=" * 60)
    print("Google OAuth 設定確認")
    print("=" * 60)

    # データベースから設定取得
    try:
        app = SocialApp.objects.get(provider='google')
        print(f"\n[OK] SocialApp found in database")
        print(f"  Provider: {app.provider}")
        print(f"  Name: {app.name}")
        print(f"  Client ID: {app.client_id}")
        if app.secret:
            masked = "*" * max(len(app.secret) - 6, 0) + app.secret[-6:]
        else:
            masked = "(empty)"
        print(f"  Secret: {masked}")
        print(f"  Sites: {[site.domain for site in app.sites.all()]}")
    except SocialApp.DoesNotExist:
        print("\n[ERROR] Google SocialApp not found in database")
        return False

    return app

def test_token_endpoint_client_auth(app):
    """トークンエンドポイントでクライアント認証が通るかを簡易確認（ダミーcodeで判定）"""
    print("\n" + "=" * 60)
    print("トークンエンドポイント: クライアント認証チェック")
    print("=" * 60)

    # NOTE: code はダミー。クライアント認証が通れば通常は invalid_grant になる。
    redirect_uri = "http://127.0.0.1:8000/accounts/google/login/callback/"
    data = {
        "client_id": app.client_id,
        "client_secret": app.secret,
        "code": "invalid_code_for_client_auth_check",
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    try:
        resp = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=15)
    except Exception as e:
        print(f"  [ERROR] トークンエンドポイントへの接続に失敗: {str(e)}")
        return False

    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}

    print(f"  Status: {resp.status_code}")
    if body.get("error") == "invalid_client":
        print("  [FAILED] クライアント認証に失敗しています (invalid_client)")
        print("          Client ID と Client secret の組み合わせが一致していない可能性が高いです。")
        return False

    if body.get("error") == "invalid_grant":
        print("  [OK] クライアント認証は通っています (invalid_grant はダミーcodeのため想定内)")
        return True

    print(f"  [INFO] 予期しない応答: {body}")
    return False

def test_client_credentials(app):
    """クライアント認証情報のテスト"""
    print("\n" + "=" * 60)
    print("クライアント認証情報の検証")
    print("=" * 60)

    client_id = app.client_id
    client_secret = app.secret

    # 1. クライアントIDの形式チェック
    print("\n1. クライアントID形式チェック:")
    if client_id.endswith('.apps.googleusercontent.com'):
        print("  [OK] クライアントIDの形式が正しい")
    else:
        print("  [ERROR] クライアントIDの形式が不正")
        return False

    # 2. クライアントシークレットの形式チェック
    print("\n2. クライアントシークレット形式チェック:")
    if len(client_secret) > 20:
        print("  [OK] クライアントシークレットの長さが十分")
    else:
        print("  [ERROR] クライアントシークレットが短すぎます")
        return False

    # 3. Google OAuth 2.0エンドポイントへの接続テスト
    print("\n3. Google OAuth 2.0エンドポイント接続テスト:")
    try:
        # Google の well-known 設定エンドポイント
        discovery_url = "https://accounts.google.com/.well-known/openid-configuration"
        response = requests.get(discovery_url, timeout=10)

        if response.status_code == 200:
            print("  [OK] Google OAuth 2.0エンドポイントに接続可能")
            config = response.json()
            print(f"  - 認証エンドポイント: {config.get('authorization_endpoint')}")
            print(f"  - トークンエンドポイント: {config.get('token_endpoint')}")
        else:
            print(f"  [ERROR] 接続失敗 (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"  [ERROR] 接続エラー: {str(e)}")
        return False

    return True

def test_oauth_flow_urls():
    """OAuth フロー URL の確認"""
    print("\n" + "=" * 60)
    print("OAuth フロー URL 確認")
    print("=" * 60)

    site = Site.objects.get_current()
    base_url = f"http://{site.domain}"

    print(f"\n現在のサイト設定: {site.domain}")
    print(f"\nOAuthフローで使用されるURL:")
    print(f"  1. 開始URL: {base_url}/accounts/google/login/")
    print(f"  2. コールバックURL: {base_url}/accounts/google/login/callback/")

    print(f"\nGoogle Cloud Consoleで設定すべきリダイレクトURI:")
    print(f"  - http://127.0.0.1:8000/accounts/google/login/callback/")

    return True

def test_manual_oauth_request(app):
    """手動でOAuth認証URLを生成してテスト"""
    print("\n" + "=" * 60)
    print("OAuth認証URL生成テスト")
    print("=" * 60)

    client_id = app.client_id
    redirect_uri = "http://127.0.0.1:8000/accounts/google/login/callback/"

    # OAuth 2.0 認証URL
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        "response_type=code&"
        "scope=openid%20email%20profile&"
        "access_type=offline"
    )

    print("\n生成された認証URL:")
    print(auth_url)
    print("\n[注意] このURLをブラウザで開いてテストできます")
    print("       Googleログイン画面が表示されれば、クライアントIDは有効です")

    return True

def check_google_cloud_console_settings():
    """Google Cloud Console 設定確認用の情報を表示"""
    print("\n" + "=" * 60)
    print("Google Cloud Console 設定確認チェックリスト")
    print("=" * 60)

    checklist = """
    [ ] 1. OAuth 2.0 クライアントIDが作成されている
    [ ] 2. クライアントタイプが「ウェブアプリケーション」になっている
    [ ] 3. 承認済みのJavaScript生成元に以下が設定されている:
          - http://127.0.0.1:8000
    [ ] 4. 承認済みのリダイレクトURIに以下が設定されている:
          - http://127.0.0.1:8000/accounts/google/login/callback/
    [ ] 5. OAuth同意画面が設定されている
    [ ] 6. テストユーザーが追加されている（テストモードの場合）
    [ ] 7. Google+ APIが有効になっている（People API）
    """

    print(checklist)
    print("\n確認URL: https://console.cloud.google.com/apis/credentials")

    return True

def main():
    """メイン処理"""
    print("\n")
    print("*" * 60)
    print("  Google OAuth クライアント疎通確認ツール")
    print("*" * 60)

    # 1. OAuth設定の確認
    app = test_oauth_configuration()
    if not app:
        print("\n[FAILED] SocialApp configuration test failed")
        sys.exit(1)

    # 2. クライアント認証情報のテスト
    if not test_client_credentials(app):
        print("\n[FAILED] Client credentials test failed")
        sys.exit(1)

    # 2.5. トークンエンドポイントでクライアント認証が通るか確認
    if not test_token_endpoint_client_auth(app):
        print("\n[FAILED] Token endpoint client authentication failed")
        sys.exit(1)

    # 3. OAuth フロー URL の確認
    test_oauth_flow_urls()

    # 4. 手動OAuth認証URLの生成
    test_manual_oauth_request(app)

    # 5. Google Cloud Console 設定確認
    check_google_cloud_console_settings()

    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)
    print("\n[次のステップ]")
    print("1. 上記のチェックリストを確認してください")
    print("2. Google Cloud Consoleの設定を確認してください")
    print("3. 生成された認証URLをブラウザで開いてテストしてください")
    print("\n")

if __name__ == '__main__':
    main()
