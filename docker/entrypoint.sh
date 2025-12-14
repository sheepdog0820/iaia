#!/usr/bin/env sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Starting gunicorn..."
# DJANGO_WSGI_MODULE は .env で指定（デフォルト: arkham_nexus.wsgi）
exec gunicorn "${DJANGO_WSGI_MODULE:-arkham_nexus.wsgi}:application" \
  --bind 0.0.0.0:8000 \
  --workers ${GUNICORN_WORKERS:-2} \
  --timeout ${GUNICORN_TIMEOUT:-60}
