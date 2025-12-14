#!/usr/bin/env python3
"""
Google認証コード取得ヘルパースクリプト

このスクリプトは実際のGoogle認証コードを取得するための手順を案内します。
"""

import webbrowser
from urllib.parse import urlencode
import time

# Google OAuth設定（.env.developmentから）
GOOGLE_CLIENT_ID = "456958275505-lgu362m6pl0seeqb8geuom5jf86c1ucn.apps.googleusercontent.com"
GOOGLE_REDIRECT_URI = "http://localhost:3000/auth/callback"

def get_google_auth_url():
    """Google OAuth認証URLを生成"""
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    return f"{base_url}?{urlencode(params)}"

def main():
    print("=== Google認証コード取得ヘルパー ===\n")
    
    auth_url = get_google_auth_url()
    
    print("📋 手順:")
    print("1. 以下のURLをブラウザで開きます（自動的に開きます）")
    print("2. Googleアカウントでログインします")
    print("3. 'Arkham Nexus Development'へのアクセスを許可します")
    print("4. リダイレクト後のURLから認証コードをコピーします\n")
    
    print(f"🔗 認証URL:\n{auth_url}\n")
    
    # ブラウザで自動的に開く
    print("ブラウザで認証ページを開いています...")
    try:
        webbrowser.open(auth_url)
    except:
        print("❌ ブラウザを自動で開けませんでした。上記のURLを手動でコピーしてブラウザで開いてください。")
    
    print("\n⚠️  重要な注意事項:")
    print("- リダイレクト先のページが表示されない場合でも、URLバーを確認してください")
    print("- URLは次のような形式になります:")
    print("  http://localhost:3000/auth/callback?code=4/0AX4XfWi...&scope=...")
    print("- 'code='の後の値（&より前まで）が認証コードです")
    
    print("\n📝 認証コードを取得したら:")
    print("1. test_google_auth_api.py を実行")
    print("2. オプション1（認証コードでテスト）を選択")
    print("3. 取得した認証コードを貼り付け")
    
    print("\n💡 ヒント:")
    print("- 認証コードは一度しか使えません")
    print("- 有効期限は短い（数分）ので、すぐに使用してください")
    print("- エラーが出た場合は、このスクリプトを再実行して新しいコードを取得してください")

if __name__ == "__main__":
    main()