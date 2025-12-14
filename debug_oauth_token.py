"""
Google OAuthトークン交換のデバッグスクリプト
"""
import requests
import json
from decouple import config

# 環境変数から設定を読み込み
CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')
REDIRECT_URI = 'http://127.0.0.1:8000/accounts/google/login/callback/'

# ダミーのauthorization_code（実際のテストでは本物のcodeを使用）
# これはテスト用なので失敗しますが、エラーメッセージから問題を特定できます
DUMMY_CODE = 'test_code_12345'

print("=" * 60)
print("Google OAuth Token Exchange Debug")
print("=" * 60)

# 環境変数のチェック
if not CLIENT_ID or not CLIENT_SECRET:
    print("\n[ERROR] 環境変数が設定されていません")
    print("以下の環境変数を.envファイルに設定してください:")
    print("  - GOOGLE_CLIENT_ID")
    print("  - GOOGLE_CLIENT_SECRET")
    exit(1)

# トークンエンドポイント
token_url = 'https://oauth2.googleapis.com/token'

# リクエストデータ
data = {
    'code': DUMMY_CODE,
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'redirect_uri': REDIRECT_URI,
    'grant_type': 'authorization_code'
}

print("\nリクエスト情報:")
print(f"Token URL: {token_url}")
print(f"Client ID: {CLIENT_ID}")
print(f"Client Secret: {CLIENT_SECRET[:20]}..." if len(CLIENT_SECRET) > 20 else "Client Secret: ***")
print(f"Redirect URI: {REDIRECT_URI}")

print("\nトークン交換リクエストを送信中...")

try:
    response = requests.post(token_url, data=data)

    print(f"\nレスポンスステータス: {response.status_code}")
    print(f"レスポンスヘッダー: {dict(response.headers)}")

    try:
        response_json = response.json()
        print(f"\nレスポンスボディ:")
        print(json.dumps(response_json, indent=2, ensure_ascii=False))

        if 'error' in response_json:
            error_code = response_json.get('error')
            error_desc = response_json.get('error_description', '')

            print("\n" + "=" * 60)
            print("エラー分析")
            print("=" * 60)

            if error_code == 'invalid_client':
                print("\n[ERROR] invalid_client")
                print("考えられる原因:")
                print("1. クライアントIDが間違っている")
                print("2. クライアントシークレットが間違っている")
                print("3. クライアントが削除されているか無効化されている")
                print("4. プロジェクトが違う")
                print("\n対処方法:")
                print("- Google Cloud Consoleでクライアント情報を再確認")
                print("- 新しいOAuth 2.0クライアントを作成")

            elif error_code == 'invalid_grant':
                print("\n[INFO] invalid_grant (expected)")
                print("これは正常です。ダミーのcodeを使用したため。")
                print("実際の認証フローでは正しいcodeが使用されます。")

    except json.JSONDecodeError:
        print(f"\nレスポンステキスト: {response.text}")

except requests.exceptions.RequestException as e:
    print(f"\n[ERROR] リクエスト失敗: {str(e)}")

print("\n" + "=" * 60)
print("デバッグ完了")
print("=" * 60)
