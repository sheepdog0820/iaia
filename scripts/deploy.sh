#!/bin/bash
# 本番環境デプロイスクリプト

set -e  # エラーが発生したら停止

echo "=== タブレノ デプロイ開始 ==="

# 環境変数のチェック
if [ -z "$DJANGO_ENV" ]; then
    export DJANGO_ENV=production
fi

# 仮想環境のアクティベート（存在する場合）
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# 1. 依存関係のインストール
echo "1. 依存関係をインストール中..."
pip install -r requirements.txt

# 2. 静的ファイルの収集
echo "2. 静的ファイルを収集中..."
python manage.py collectstatic --noinput

# 3. データベースマイグレーション
echo "3. データベースマイグレーションを実行中..."
python manage.py migrate --noinput

# 4. 圧縮ファイルの生成（django-compressor）
echo "4. 静的ファイルを圧縮中..."
python manage.py compress --force

# 5. ログディレクトリの作成
echo "5. ログディレクトリを作成中..."
mkdir -p logs

# 6. 権限の設定
echo "6. ファイル権限を設定中..."
chmod -R 755 staticfiles
chmod -R 755 media
chmod -R 755 logs

# 7. Gunicornの再起動（systemdを使用する場合）
if systemctl is-active --quiet gunicorn; then
    echo "7. Gunicornを再起動中..."
    sudo systemctl restart gunicorn
fi

# 8. Nginxの設定再読み込み（必要な場合）
if systemctl is-active --quiet nginx; then
    echo "8. Nginxを再読み込み中..."
    sudo nginx -t && sudo systemctl reload nginx
fi

echo "=== デプロイ完了 ==="
echo "本番環境URL: https://yourdomain.com"