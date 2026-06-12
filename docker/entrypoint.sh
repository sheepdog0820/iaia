#!/usr/bin/env sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Starting ASGI server..."
# APP_ENV は tableno.runtime_env により settings module へ解決される。
exec daphne \
  --bind 0.0.0.0 \
  --port 8000 \
  --application-close-timeout ${DAPHNE_APPLICATION_CLOSE_TIMEOUT:-10} \
  "${DJANGO_ASGI_MODULE:-tableno.asgi}:application"
