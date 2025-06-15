#!/bin/bash
set -e

# データベースが起動するまで待機
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Database started"

# データベースマイグレーション実行
echo "Running database migrations..."
python manage.py migrate --settings=arkham_nexus.settings_production

# スーパーユーザー作成（環境変数が設定されている場合）
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ] && [ "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "Creating superuser..."
    python manage.py createsuperuser \
        --noinput \
        --username $DJANGO_SUPERUSER_USERNAME \
        --email $DJANGO_SUPERUSER_EMAIL \
        --settings=arkham_nexus.settings_production || true
fi

# 静的ファイル収集
echo "Collecting static files..."
python manage.py collectstatic --noinput --settings=arkham_nexus.settings_production

# サンプルデータ作成（開発環境の場合）
if [ "$CREATE_SAMPLE_DATA" = "true" ]; then
    echo "Creating sample data..."
    python manage.py create_sample_data --settings=arkham_nexus.settings_production
fi

exec "$@"