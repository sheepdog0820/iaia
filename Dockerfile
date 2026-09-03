# syntax=docker/dockerfile:1
FROM python:3.11-slim

ARG APP_UID=10001
ARG APP_GID=10001

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system packages required by Python, PostgreSQL, and MySQL dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    libpq-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${APP_GID}" tableno \
    && useradd --uid "${APP_UID}" --gid tableno --create-home --shell /usr/sbin/nologin tableno

# Install Python dependencies first to improve Docker layer caching.
COPY requirements.lock.txt /app/requirements.lock.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.lock.txt

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
