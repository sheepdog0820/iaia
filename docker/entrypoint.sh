#!/usr/bin/env sh
set -e

is_true() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

is_local_env() {
  case "${APP_ENV:-local}" in
    local|development|dev) return 0 ;;
    *) return 1 ;;
  esac
}

if [ -z "${RUN_MIGRATIONS+x}" ] && [ "$#" -eq 0 ] && is_local_env; then
  RUN_MIGRATIONS=true
fi

if [ -z "${RUN_COLLECTSTATIC+x}" ] && [ "$#" -eq 0 ] && is_local_env; then
  RUN_COLLECTSTATIC=true
fi

if [ -z "${COLLECTSTATIC_ALLOW_FAILURE+x}" ] && is_local_env; then
  COLLECTSTATIC_ALLOW_FAILURE=true
fi

if is_true "${RUN_MIGRATIONS:-false}"; then
  echo "Running migrations..."
  python manage.py migrate --noinput
fi

if is_true "${RUN_COLLECTSTATIC:-false}"; then
  echo "Collecting static files..."
  if is_true "${COLLECTSTATIC_ALLOW_FAILURE:-false}"; then
    python manage.py collectstatic --noinput || true
  else
    python manage.py collectstatic --noinput
  fi
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

echo "Starting ASGI server..."
# APP_ENV is resolved to the settings module by tableno.runtime_env.
exec daphne \
  --bind 0.0.0.0 \
  --port 8000 \
  --application-close-timeout ${DAPHNE_APPLICATION_CLOSE_TIMEOUT:-10} \
  "${DJANGO_ASGI_MODULE:-tableno.asgi}:application"
