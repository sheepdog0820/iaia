#!/usr/bin/env bash
# Self-signed TLS for the disposable GitHub Actions PostgreSQL service only.
set -euo pipefail

if [[ "${GITHUB_ACTIONS:-}" != true || "${GITHUB_JOB:-}" != production-database ||
      "${DB_USER:-}" != tableno_ci || "${DB_NAME:-}" != tableno_ci ]]; then
  echo 'Disposable CI PostgreSQL context required.' >&2
  exit 64
fi
if [[ ! "${PG_SERVICE_CONTAINER:-}" =~ ^[0-9a-f]{64}$ ]]; then
  echo 'Exact CI service container ID required.' >&2
  exit 64
fi
if [[ "$(docker inspect --format '{{.Config.Image}}' "$PG_SERVICE_CONTAINER")" != postgres:18.3 ]]; then
  echo 'Expected disposable PostgreSQL image required.' >&2
  exit 64
fi

docker exec "$PG_SERVICE_CONTAINER" sh -eu -c '
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 -subj /CN=localhost \
    -keyout /tmp/tableno-ci-tls.key -out /tmp/tableno-ci-tls.crt >/dev/null 2>&1
  chown postgres:postgres /tmp/tableno-ci-tls.key /tmp/tableno-ci-tls.crt
  chmod 600 /tmp/tableno-ci-tls.key
  chmod 644 /tmp/tableno-ci-tls.crt
'
for setting in \
  "ssl_cert_file = '/tmp/tableno-ci-tls.crt'" \
  "ssl_key_file = '/tmp/tableno-ci-tls.key'" \
  "ssl = on"; do
  docker exec --user postgres "$PG_SERVICE_CONTAINER" \
    psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "ALTER SYSTEM SET $setting"
done
docker exec --user postgres "$PG_SERVICE_CONTAINER" \
  psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -c 'SELECT pg_reload_conf()'

for attempt in {1..20}; do
  if result="$(PGPASSWORD="$DB_PASSWORD" docker exec -e PGPASSWORD "$PG_SERVICE_CONTAINER" \
      psql "host=127.0.0.1 dbname=$DB_NAME user=$DB_USER sslmode=require connect_timeout=2" \
      -v ON_ERROR_STOP=1 -At -c 'SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()' 2>/dev/null)" && [[ "$result" == t ]]; then
    echo 'Disposable PostgreSQL TLS connection verified.'
    exit 0
  fi
  sleep 0.25
done
echo 'Disposable PostgreSQL TLS connection could not be verified.' >&2
exit 1
