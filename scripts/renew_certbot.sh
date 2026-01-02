#!/usr/bin/env bash
set -euo pipefail

PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v certbot >/dev/null 2>&1; then
    echo "certbot is required (install with apt)" >&2
    exit 1
fi

certbot renew --deploy-hook "${REPO_DIR}/scripts/certbot_deploy_hook.sh"
