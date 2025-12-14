# syntax=docker/dockerfile:1
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# システムパッケージ更新とPostgreSQL関連ライブラリのインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係を先にインストール（キャッシュ効率化）
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# アプリケーションコードをコピー
COPY . /app

# 静的ファイル用ディレクトリ作成
RUN mkdir -p /app/staticfiles /app/media

# 起動スクリプトをコピーして実行権限を付与
COPY ./docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ポート8000を公開
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]