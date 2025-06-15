# 🌟 Arkham Nexus - TRPGスケジュール管理システム

**Gate of Yog-Sothoth** - 時空を超えるTRPGスケジュール管理サービス

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Django](https://img.shields.io/badge/Django-4.2+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📖 概要

Arkham Nexusは、クトゥルフ神話をテーマにしたTRPGスケジュール管理Webサービスです。TRPGセッションの管理、参加者の管理、プレイ履歴の記録など、TRPGライフを豊かにする機能を提供します。

### 🎭 主要機能

#### 👥 **ユーザー管理**
- カスタムユーザーモデル（ニックネーム、TRPG歴、プロフィール画像）
- フレンド機能
- グループ機能（**Cult Circle**）
- Google/Twitter認証対応

#### 📅 **スケジュール管理**
- TRPGセッション管理（**Chrono Abyss** / **R'lyeh Log**）
- 参加者管理・キャラクターシート共有
- 秘匿ハンドアウト機能
- YouTube配信URL対応
- 年間プレイ時間集計（**Tindalos Metrics**）

#### 📚 **シナリオ管理**
- シナリオ情報管理（**Mythos Archive**）
- プレイ履歴記録
- GMメモ機能（公開・非公開）
- プレイ統計表示

#### 🎨 **UI/UX**
- **クトゥルフ神話テーマ**のダークデザイン
- **Gate of Yog-Sothoth**（ログイン画面）
- エルドリッチフォント & グロウエフェクト
- レスポンシブ対応（スマホ対応）

## 🚀 クイックスタート

### 開発環境セットアップ

1. **リポジトリのクローン**
```bash
git clone https://github.com/your-username/arkham_nexus.git
cd arkham_nexus
```

2. **仮想環境作成・有効化**
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
```

3. **依存関係インストール**
```bash
pip install -r requirements.txt
```

4. **環境変数設定**
```bash
cp .env.example .env
# .envファイルを編集して必要な設定を行う
```

5. **データベースセットアップ**
```bash
python manage.py migrate
```

6. **スーパーユーザー作成**
```bash
python create_admin.py
# Username: admin, Password: arkham_admin_2024
```

7. **サンプルデータ作成**
```bash
python manage.py create_sample_data
```

8. **開発サーバー起動**
```bash
python manage.py runserver
```

アプリケーションは http://localhost:8000 でアクセスできます。

### テストアカウント

- **管理者**: admin / arkham_admin_2024
- **一般ユーザー**: azathoth_gm / arkham2024

## 🐳 Docker を使用した起動

### 開発環境
```bash
docker-compose up -d
```

### 本番環境
```bash
# 環境変数を設定
cp .env.production.example .env.production
# .env.production を編集

# デプロイ実行
./deploy.sh production
```

## 🔧 技術スタック

### Backend
- **Django 4.2+** - Webフレームワーク
- **Django REST Framework** - API構築
- **PostgreSQL** - メインデータベース
- **Redis** - キャッシュ・セッション管理
- **Celery** - バックグラウンドタスク

### Frontend
- **Bootstrap 5** - UIフレームワーク
- **Custom CSS/JS** - クトゥルフテーマ
- **Axios** - API通信

### インフラ・デプロイ
- **Docker & Docker Compose**
- **Nginx** - リバースプロキシ
- **Gunicorn** - WSGIサーバー
- **systemd** - サービス管理

### 認証・セキュリティ
- **django-allauth** - ソーシャル認証
- **CORS対応**
- **レート制限**
- **CSP設定**

## 📁 プロジェクト構造

```
arkham_nexus/
├── arkham_nexus/          # Django設定
├── accounts/              # ユーザー管理
├── schedules/             # スケジュール管理
├── scenarios/             # シナリオ管理
├── templates/             # HTMLテンプレート
├── static/                # 静的ファイル
├── media/                 # アップロードファイル
├── requirements.txt       # Python依存関係
├── docker-compose.yml     # Docker設定
├── deploy.sh             # デプロイスクリプト
└── README.md             # このファイル
```

## 🌐 API エンドポイント

### 認証
- `POST /accounts/login/` - ログイン
- `POST /accounts/signup/` - サインアップ
- `POST /accounts/logout/` - ログアウト

### ユーザー・グループ
- `GET /api/accounts/users/` - ユーザー一覧
- `GET /api/accounts/groups/` - グループ一覧
- `GET /api/accounts/friends/` - フレンド一覧

### セッション管理
- `GET /api/schedules/sessions/` - セッション一覧
- `POST /api/schedules/sessions/` - セッション作成
- `GET /api/schedules/sessions/upcoming/` - 次回セッション
- `GET /api/schedules/sessions/statistics/` - プレイ統計

### シナリオ管理
- `GET /api/scenarios/scenarios/` - シナリオ一覧
- `GET /api/scenarios/archive/` - シナリオアーカイブ
- `GET /api/scenarios/statistics/` - プレイ統計

## 🛠️ 開発・運用

### 管理コマンド

```bash
# サンプルデータ作成
python manage.py create_sample_data [--clear]

# 静的ファイル収集
python manage.py collectstatic

# データベースバックアップ
python manage.py dumpdata > backup.json

# データベース復元
python manage.py loaddata backup.json
```

### ログ確認

```bash
# アプリケーションログ
sudo journalctl -u arkham_nexus -f

# Nginxログ
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Django ログ
tail -f /var/log/arkham_nexus/django.log
```

### パフォーマンス監視

```bash
# システム状態確認
sudo systemctl status arkham_nexus
sudo systemctl status arkham_nexus_celery
sudo systemctl status postgresql
sudo systemctl status redis
sudo systemctl status nginx
```

## 🔒 セキュリティ

### 本番環境での推奨設定

1. **SSL証明書の設定**
```bash
# Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

2. **ファイアウォール設定**
```bash
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

3. **セキュリティヘッダー**
   - CSP (Content Security Policy)
   - HSTS (HTTP Strict Transport Security)
   - X-Frame-Options
   - X-Content-Type-Options

## 🧪 テスト

```bash
# テスト実行
python manage.py test

# カバレッジ付きテスト
coverage run manage.py test
coverage report
coverage html
```

## 📈 デプロイ

### 本番環境デプロイ

1. **サーバー準備**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-venv postgresql redis-server nginx git
```

2. **デプロイ実行**
```bash
chmod +x deploy.sh
./deploy.sh production
```

3. **SSL設定**
```bash
sudo certbot --nginx -d your-domain.com
```

### 環境変数

本番環境では以下の環境変数を設定してください：

```bash
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com
DB_NAME=arkham_nexus_prod
DB_USER=arkham_user
DB_PASSWORD=secure-password
# その他の設定...
```

## 🤝 コントリビューション

1. フォークを作成
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 🙏 謝辞

- **H.P. Lovecraft** - インスピレーションの源
- **Django コミュニティ** - 素晴らしいフレームワーク
- **TRPGコミュニティ** - 継続的なフィードバック

---

*"That is not dead which can eternal lie, And with strange aeons even death may die."*

**🌟 Happy Gaming! 🎲**