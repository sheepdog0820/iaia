#!/usr/bin/env sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Starting gunicorn..."
# APP_ENV は tableno.runtime_env により settings module へ解決される。
exec gunicorn "${DJANGO_WSGI_MODULE:-tableno.wsgi}:application" \
  --bind 0.0.0.0:8000 \
  --workers ${GUNICORN_WORKERS:-2} \
  --timeout ${GUNICORN_TIMEOUT:-60}
