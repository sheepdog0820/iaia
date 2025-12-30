"""
ドキュメント内のlocalhostを127.0.0.1に一括更新するスクリプト
"""
import os
import re
from pathlib import Path

# 更新対象のファイルリスト（OAuth関連ドキュメント）
DOCS_TO_UPDATE = [
    'docs/GOOGLE_OAUTH_STATE_ERROR_FIX.md',
    'docs/API_GOOGLE_AUTH_GUIDE.md',
    'docs/GOOGLE_OAUTH_8000_PORT_SETUP.md',
    'docs/GOOGLE_CLOUD_CONSOLE_CHECK.md',
    'docs/GOOGLE_OAUTH_LOGIN_GUIDE.md',
    'docs/GOOGLE_OAUTH_REDIRECT_URI_FIX.md',
    'docs/OAUTH_REGISTRATION_GUIDE.md',
]

def update_localhost_to_127(file_path):
    """localhostを127.0.0.1に置換"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # localhost:8000 -> 127.0.0.1:8000
        content = content.replace('localhost:8000', '127.0.0.1:8000')

        # http://localhost -> http://127.0.0.1 (ポート番号なし)
        content = re.sub(r'http://localhost(?![:])', 'http://127.0.0.1', content)

        # /auth/google/callback/ -> /accounts/google/login/callback/ (django-allauth形式)
        content = content.replace('/auth/google/callback/', '/accounts/google/login/callback/')
        content = content.replace('/auth/google/login/callback/', '/accounts/google/login/callback/')

        # /auth/twitter/callback/ -> /accounts/twitter_oauth2/login/callback/
        content = content.replace('/auth/twitter/callback/', '/accounts/twitter_oauth2/login/callback/')
        content = content.replace('/auth/twitter/login/callback/', '/accounts/twitter_oauth2/login/callback/')

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[UPDATED] {file_path}")
            return True
        else:
            print(f"[NO CHANGE] {file_path}")
            return False

    except FileNotFoundError:
        print(f"[NOT FOUND] {file_path}")
        return False
    except Exception as e:
        print(f"[ERROR] {file_path}: {e}")
        return False

def main():
    print("=" * 60)
    print("ドキュメント内のlocalhostを127.0.0.1に更新")
    print("=" * 60)
    print()

    updated_count = 0

    for doc_path in DOCS_TO_UPDATE:
        if update_localhost_to_127(doc_path):
            updated_count += 1

    print()
    print("=" * 60)
    print(f"更新完了: {updated_count}/{len(DOCS_TO_UPDATE)} ファイル")
    print("=" * 60)

if __name__ == '__main__':
    main()
