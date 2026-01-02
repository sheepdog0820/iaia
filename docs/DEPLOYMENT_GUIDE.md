# 📦 タブレノ デプロイメントガイド

## 概要

このガイドでは、タブレノを本番環境にデプロイする手順を説明します。

## 🎯 前提条件

- Ubuntu 20.04 LTS 以上
- Python 3.10+
- PostgreSQL 13+
- Redis 6+
- Nginx
- SSL証明書（Let's Encrypt推奨）

## 📋 デプロイ手順

### 1. サーバーの準備

```bash
# システムパッケージの更新
sudo apt update && sudo apt upgrade -y

# 必要なパッケージのインストール
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib redis-server nginx git

# Node.js（オプション：フロントエンドビルド用）
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
```

### 2. PostgreSQLのセットアップ

```bash
# PostgreSQLにログイン
sudo -u postgres psql

# データベースとユーザーの作成
CREATE DATABASE tableno;
CREATE USER tableno_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE tableno TO tableno_user;
\q
```

### 3. アプリケーションのセットアップ

```bash
# アプリケーション用ディレクトリの作成
sudo mkdir -p /var/www/tableno
sudo chown $USER:$USER /var/www/tableno

# リポジトリのクローン
cd /var/www
git clone https://github.com/yourusername/tableno.git
cd tableno

# 仮想環境の作成と有効化
python3 -m venv venv
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt

# 本番環境用の.envファイルの作成
cp .env.production.example .env.production
# .env.productionを編集して適切な値を設定
```

### 4. 環境変数の設定

`.env.production`ファイルを編集：

```env
SECRET_KEY=your-very-secure-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# データベース
DB_NAME=tableno
DB_USER=tableno_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/1

# メール設定
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
```

### 5. 初期デプロイの実行

```bash
# デプロイスクリプトの実行
chmod +x scripts/deploy.sh
./scripts/deploy.sh

# スーパーユーザーの作成
python manage.py createsuperuser
```

### 6. Gunicornのセットアップ

```bash
# systemdサービスファイルのコピー
sudo cp scripts/tableno.service /etc/systemd/system/

# サービスファイルの編集（パスを適切に設定）
sudo nano /etc/systemd/system/tableno.service

# サービスの有効化と開始
sudo systemctl enable tableno
sudo systemctl start tableno
sudo systemctl status tableno
```

### 7. Nginxの設定

```bash
# Nginx設定ファイルのコピー
sudo cp scripts/nginx.conf /etc/nginx/sites-available/tableno

# 設定ファイルの編集（ドメイン名とパスを設定）
sudo nano /etc/nginx/sites-available/tableno

# シンボリックリンクの作成
sudo ln -s /etc/nginx/sites-available/tableno /etc/nginx/sites-enabled/

# デフォルトサイトの無効化（必要に応じて）
sudo rm /etc/nginx/sites-enabled/default

# Nginx設定のテスト
sudo nginx -t

# Nginxの再起動
sudo systemctl restart nginx
```

### 8. SSL証明書の設定（Let's Encrypt）

```bash
# Certbotのインストール
sudo apt install certbot python3-certbot-nginx

# SSL証明書の取得
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 自動更新の確認
sudo certbot renew --dry-run
```

### 9. ファイアウォールの設定

```bash
# UFWの有効化
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 🔧 メンテナンス

### アプリケーションの更新

```bash
cd /var/www/tableno
git pull origin main
source venv/bin/activate
./scripts/deploy.sh
```

### ログの確認

```bash
# Gunicornログ
tail -f logs/gunicorn_access.log
tail -f logs/gunicorn_error.log

# Djangoログ
tail -f logs/tableno.log
tail -f logs/errors.log

# Nginxログ
tail -f /var/log/nginx/tableno_access.log
tail -f /var/log/nginx/tableno_error.log
```

### バックアップ

```bash
# データベースバックアップ
pg_dump -U tableno_user tableno > backup_$(date +%Y%m%d_%H%M%S).sql

# メディアファイルのバックアップ
tar -czf media_backup_$(date +%Y%m%d_%H%M%S).tar.gz media/
```

## 🚨 トラブルシューティング

### 502 Bad Gateway

1. Gunicornが起動しているか確認
   ```bash
   sudo systemctl status tableno
   ```

2. ソケットファイルの権限確認
   ```bash
   ls -la /var/www/tableno/gunicorn.sock
   ```

### 静的ファイルが表示されない

1. collectstaticが実行されているか確認
   ```bash
   python manage.py collectstatic --noinput
   ```

2. Nginx設定のstaticパスが正しいか確認

### マイグレーションエラー

1. データベース接続を確認
   ```bash
   python manage.py dbshell
   ```

2. マイグレーションの状態確認
   ```bash
   python manage.py showmigrations
   ```

## 📊 パフォーマンスチューニング

### PostgreSQL

`/etc/postgresql/13/main/postgresql.conf`:

```conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

### Redis

`/etc/redis/redis.conf`:

```conf
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### Gunicorn

`gunicorn.conf.py`のワーカー数を調整：

```python
workers = multiprocessing.cpu_count() * 2 + 1
```

## 🔐 セキュリティチェックリスト

- [ ] DEBUG=Falseに設定
- [ ] SECRET_KEYを安全な値に変更
- [ ] ALLOWED_HOSTSを適切に設定
- [ ] SSL証明書を設定
- [ ] ファイアウォールを設定
- [ ] 不要なポートを閉じる
- [ ] 定期的なセキュリティアップデート
- [ ] バックアップの自動化

## 📚 参考リンク

- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)