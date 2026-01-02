# 📦 タブレノ デプロイメントガイド（Phase1: Lightsail + Docker Compose）

## 0. 前提（DNS）

- `app.tableno.jp` の Aレコード → **prod** Lightsail の固定IP
- `stg.tableno.jp` の Aレコード → **stg** Lightsail の固定IP
- `tableno.jp` / `www.tableno.jp` は後回しでOK（LP用に別で設定）

## 1. サーバー準備（Lightsail / Ubuntu）

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git certbot
sudo usermod -aG docker $USER
```

※ `docker` グループ反映のため、再ログインしてください。

## 2. アプリケーション準備

```bash
git clone https://github.com/yourusername/tableno.git
cd tableno

# 環境ファイルを作成（prod / stg のどちらか）
# prod
cp .env.production.example .env.production

# stg
cp .env.staging.example .env.staging

※ 使う環境のファイルだけ用意してください。
```

### 必須設定（.env.production / .env.staging）

- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS`（prod: `app.tableno.jp`, stg: `stg.tableno.jp`）
- `CSRF_TRUSTED_ORIGINS`（prod: `https://app.tableno.jp`, stg: `https://stg.tableno.jp`）

※ `django.contrib.sites` を使っている場合、DB内の `Site` を環境ごとのドメインに合わせて更新してください。

## 3. Docker Composeで起動（deploy.shは使わない）

### Stg
```bash
ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml up -d --build
```

### Prod
```bash
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d --build
```

### 初期化（MySQLに対して実行）
```bash
# マイグレーション
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml exec web python manage.py migrate

# スーパーユーザー作成
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml exec web python manage.py createsuperuser

※ stg は `.env.staging` に置き換えて実行してください。
```

※ `DJANGO_SETTINGS_MODULE=tableno.settings_production` は compose 側で設定済みです。

## 4. Nginx設定

- `nginx.conf` の `server_name` は **環境ごとに** 修正してください。
  - prod: `app.tableno.jp`
  - stg: `stg.tableno.jp`
- 変更後は `docker compose -f docker-compose.mysql.yml restart nginx` を実行します。
- `docker-compose.mysql.yml` の `web` は 8000 番を外部公開しません。
  - 外部公開は Nginx の 80/443 のみ。

## 5. SSL（Let’s Encrypt / host certbot）

### 5.1 証明書取得

```bash
mkdir -p certbot/www ssl

# Nginx が起動している状態で実行（stg は .env.staging）
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d nginx

sudo certbot certonly \
  --webroot -w "$(pwd)/certbot/www" \
  -d app.tableno.jp \
  --agree-tos --email you@example.com --no-eff-email

# Nginx が参照するパスへコピー
sudo cp /etc/letsencrypt/live/app.tableno.jp/fullchain.pem ./ssl/fullchain.pem
sudo cp /etc/letsencrypt/live/app.tableno.jp/privkey.pem ./ssl/privkey.pem

# Nginx 再起動
docker compose -f docker-compose.mysql.yml restart nginx
```

※ stg は `stg.tableno.jp` に置き換えて実行してください。

### 5.2 自動更新（cron）

```bash
chmod +x scripts/renew_certbot.sh scripts/certbot_deploy_hook.sh

# 手動で更新テスト
sudo ENV_FILE=.env.production ./scripts/renew_certbot.sh

※ stg は `.env.staging` に置き換えて実行してください。
```

cron 例（毎日3:00に更新チェック）:

```bash
sudo crontab -e
# 以下を追加
0 3 * * * ENV_FILE=.env.production /path/to/tableno/scripts/renew_certbot.sh >> /var/log/letsencrypt-renew.log 2>&1
```

`scripts/renew_certbot.sh` は `certbot renew` 後に
`./ssl/fullchain.pem` / `./ssl/privkey.pem` を更新し、Nginx を再起動します。

## 6. 動作確認

- https://app.tableno.jp で警告が出ない
- `docker compose -f docker-compose.mysql.yml ps` ですべて `Up`
- MySQL に対して `migrate/createsuperuser` が実行できている
