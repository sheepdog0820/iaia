# syntax=docker/dockerfile:1
# Refresh this digest deliberately with runtime tests and a vulnerability scan.
FROM python:3.11-slim@sha256:bab1b7ef4b450c81002278d035eff85ebe394ae94df904f7a3ba14f7e16e487b

ARG APP_UID=10001
ARG APP_GID=10001

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Refresh PCRE2 security updates even when the base image has an older installed
# version, alongside packages needed by Python, PostgreSQL, and MySQL dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    libpcre2-8-0 \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${APP_GID}" tableno \
    && useradd --uid "${APP_UID}" --gid tableno --create-home --shell /usr/sbin/nologin tableno

# Install Python dependencies first to improve Docker layer caching.
COPY requirements.lock.txt /app/requirements.lock.txt
# Validate installed dependencies before removing packaging tools from runtime.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.lock.txt \
    && pip check \
    && pip uninstall --yes pip setuptools wheel

# Keep native runtime libraries while removing compilers and development headers.
RUN apt-mark manual libmariadb3 libpq5 libgomp1 \
    && apt-get purge -y --auto-remove \
        build-essential default-libmysqlclient-dev libpq-dev pkg-config

# Opt out before native library initialization in any runtime command/worker.
ENV ORT_DISABLE_TELEMETRY=1

# Copy application code.
COPY --chown=tableno:tableno . /app

# Prepare runtime directories for collected static files and uploads.
RUN mkdir -p /app/staticfiles /app/media /var/log/tableno \
    && chown tableno:tableno /app \
    && chown -R tableno:tableno /app/staticfiles /app/media /var/log/tableno

# Install the entrypoint used by Docker Compose and runtime containers.
COPY --chown=tableno:tableno ./docker/entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh

USER tableno

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
