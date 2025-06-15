#!/bin/bash
# Arkham Nexus - Production Deployment Script

set -e

echo "🌟 Starting Arkham Nexus deployment..."

# 設定読み込み
DEPLOY_ENV="${1:-production}"
PROJECT_DIR="/opt/arkham_nexus"
BACKUP_DIR="/opt/backups/arkham_nexus"
LOG_FILE="/var/log/arkham_nexus/deploy.log"

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# エラーハンドリング
handle_error() {
    log "❌ Error occurred during deployment. Rolling back..."
    if [ -d "$BACKUP_DIR/current" ]; then
        log "🔄 Restoring from backup..."
        sudo systemctl stop arkham_nexus
        rm -rf "$PROJECT_DIR"
        mv "$BACKUP_DIR/current" "$PROJECT_DIR"
        sudo systemctl start arkham_nexus
        log "✅ Rollback completed"
    fi
    exit 1
}

trap handle_error ERR

# 1. 環境チェック
log "🔍 Checking environment..."
if [ "$EUID" -eq 0 ]; then
    log "❌ Do not run this script as root"
    exit 1
fi

# 必要なディレクトリ作成
sudo mkdir -p "$BACKUP_DIR" "$PROJECT_DIR" "$(dirname "$LOG_FILE")"
sudo chown -R $USER:$USER "$BACKUP_DIR" "$PROJECT_DIR" "$(dirname "$LOG_FILE")"

# 2. 既存のアプリケーションをバックアップ
if [ -d "$PROJECT_DIR" ]; then
    log "💾 Backing up current application..."
    rm -rf "$BACKUP_DIR/current"
    cp -r "$PROJECT_DIR" "$BACKUP_DIR/current"
fi

# 3. 最新コードを取得
log "📥 Pulling latest code..."
if [ ! -d "$PROJECT_DIR/.git" ]; then
    git clone https://github.com/your-username/arkham_nexus.git "$PROJECT_DIR"
else
    cd "$PROJECT_DIR"
    git fetch origin
    git reset --hard origin/main
fi

cd "$PROJECT_DIR"

# 4. 仮想環境セットアップ
log "🐍 Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. 環境変数設定
log "⚙️ Setting up environment..."
if [ ! -f ".env.production" ]; then
    log "❌ .env.production file not found!"
    exit 1
fi

# 6. データベースマイグレーション
log "🗄️ Running database migrations..."
python manage.py migrate --settings=arkham_nexus.settings_production

# 7. 静的ファイル収集
log "📦 Collecting static files..."
python manage.py collectstatic --noinput --settings=arkham_nexus.settings_production

# 8. 依存サービス起動確認
log "🔧 Checking services..."
sudo systemctl is-active --quiet postgresql || sudo systemctl start postgresql
sudo systemctl is-active --quiet redis || sudo systemctl start redis
sudo systemctl is-active --quiet nginx || sudo systemctl start nginx

# 9. Gunicorn設定
log "🚀 Setting up Gunicorn..."
sudo tee /etc/systemd/system/arkham_nexus.service > /dev/null <<EOF
[Unit]
Description=Arkham Nexus TRPG Management System
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment="DJANGO_SETTINGS_MODULE=arkham_nexus.settings_production"
EnvironmentFile=$PROJECT_DIR/.env.production
ExecStart=$PROJECT_DIR/venv/bin/gunicorn \\
    --bind 127.0.0.1:8000 \\
    --workers 3 \\
    --worker-class sync \\
    --worker-connections 1000 \\
    --max-requests 1000 \\
    --max-requests-jitter 100 \\
    --timeout 30 \\
    --keep-alive 2 \\
    --user $USER \\
    --group $USER \\
    --log-level info \\
    --access-logfile /var/log/arkham_nexus/access.log \\
    --error-logfile /var/log/arkham_nexus/error.log \\
    arkham_nexus.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 10. Celery設定
log "🔄 Setting up Celery..."
sudo tee /etc/systemd/system/arkham_nexus_celery.service > /dev/null <<EOF
[Unit]
Description=Arkham Nexus Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment="DJANGO_SETTINGS_MODULE=arkham_nexus.settings_production"
EnvironmentFile=$PROJECT_DIR/.env.production
ExecStart=$PROJECT_DIR/venv/bin/celery -A arkham_nexus worker --loglevel=info --detach
ExecStop=/bin/kill -s TERM \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 11. systemd設定再読み込み
log "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# 12. サービス起動
log "▶️ Starting services..."
sudo systemctl enable arkham_nexus
sudo systemctl enable arkham_nexus_celery
sudo systemctl restart arkham_nexus
sudo systemctl restart arkham_nexus_celery

# 13. Nginx設定
log "🌐 Configuring Nginx..."
sudo tee /etc/nginx/sites-available/arkham_nexus > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # セキュリティヘッダー
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 静的ファイル
    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 1y;
        add_header Cache-Control "public";
    }

    # アプリケーション
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/arkham_nexus /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 14. ヘルスチェック
log "🏥 Performing health check..."
sleep 5
if curl -f http://localhost:8000/admin/ > /dev/null 2>&1; then
    log "✅ Health check passed"
else
    log "❌ Health check failed"
    handle_error
fi

# 15. 古いバックアップをクリーンアップ
log "🧹 Cleaning up old backups..."
find "$BACKUP_DIR" -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true

# 16. 完了
log "🎉 Deployment completed successfully!"
log "📊 Service status:"
sudo systemctl status arkham_nexus --no-pager -l
sudo systemctl status arkham_nexus_celery --no-pager -l

echo "
🌟 Arkham Nexus deployment completed!

📋 Post-deployment checklist:
1. Update DNS settings if needed
2. Configure SSL certificate (Let's Encrypt recommended)
3. Set up monitoring and alerting
4. Configure backup schedule
5. Update social authentication credentials
6. Test all major functionality

🔗 Access your application:
   - Admin: http://your-domain.com/admin/
   - Main site: http://your-domain.com/

📚 Useful commands:
   - View logs: sudo journalctl -u arkham_nexus -f
   - Restart service: sudo systemctl restart arkham_nexus
   - Check status: sudo systemctl status arkham_nexus
"