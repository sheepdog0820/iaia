#!/usr/bin/env bash
set -euo pipefail

PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SSL_DIR="${REPO_DIR}/ssl"
COMPOSE_FILE="${REPO_DIR}/docker-compose.mysql.yml"
ENV_FILE_VALUE="${ENV_FILE:-}"

if [[ -z "${RENEWED_LINEAGE:-}" ]]; then
    echo "RENEWED_LINEAGE is not set" >&2
    exit 1
fi

mkdir -p "${SSL_DIR}"
cp -f "${RENEWED_LINEAGE}/fullchain.pem" "${SSL_DIR}/fullchain.pem"
cp -f "${RENEWED_LINEAGE}/privkey.pem" "${SSL_DIR}/privkey.pem"

if [[ -z "${ENV_FILE_VALUE}" ]]; then
    if [[ -f "${REPO_DIR}/.env.production" && ! -f "${REPO_DIR}/.env.staging" ]]; then
        ENV_FILE_VALUE=".env.production"
    elif [[ -f "${REPO_DIR}/.env.staging" && ! -f "${REPO_DIR}/.env.production" ]]; then
        ENV_FILE_VALUE=".env.staging"
    fi
fi

if [[ -n "${ENV_FILE_VALUE}" ]]; then
    ENV_FILE="${ENV_FILE_VALUE}" docker compose -f "${COMPOSE_FILE}" restart nginx
else
    docker compose -f "${COMPOSE_FILE}" restart nginx
fi
