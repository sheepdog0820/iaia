# Arkham Nexus - Docker Configuration
FROM python:3.10-slim

# 作業ディレクトリ設定
WORKDIR /app

# システムパッケージ更新とPostgreSQL関連ライブラリのインストール
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# 静的ファイル用ディレクトリ作成
RUN mkdir -p /app/staticfiles /app/media

# 静的ファイル収集
RUN python manage.py collectstatic --noinput --settings=arkham_nexus.settings_production

# ポート8000を公開
EXPOSE 8000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/admin/ || exit 1

# エントリーポイント
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "arkham_nexus.wsgi:application"]