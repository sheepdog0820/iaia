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
- グループ機能（**Cult Circle**）- 可視性制御（公開/非公開）
- グループ招待システム（承認・拒否機能）
- Google/Twitter認証対応（開発環境用モック機能）

#### 📅 **スケジュール管理**
- TRPGセッション管理（**Chrono Abyss** / **R'lyeh Log**）
- 参加者管理・キャラクターシート統合
- 秘匿ハンドアウト機能（GM専用・参加者限定配布）
- YouTube配信URL対応
- 年間プレイ時間集計（**Tindalos Metrics**）
- カレンダー表示・月間表示機能

#### 📚 **シナリオ管理**
- シナリオ情報管理（**Mythos Archive**）
- 高度なフィルタリング（ゲームシステム・難易度・時間・人数）
- プレイ履歴記録・統計表示
- GMメモ機能（公開・非公開）
- マルチゲームシステム対応（CoC、D&D、ソードワールド等）

#### 🎨 **UI/UX**
- **クトゥルフ神話テーマ**のダークデザイン
- **Gate of Yog-Sothoth**（ログイン画面）
- エルドリッチフォント & グロウエフェクト
- レスポンシブ対応（スマホ対応）

## 🚀 クイックスタート

### 開発環境セットアップ

1. **リポジトリのクローン**
```bash
git clone https://github.com/sheepdog0820/iaia.git
cd iaia
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

### 🎲 キャラクターシート機能（クトゥルフ神話TRPG専用）

#### 6版対応
- **能力値範囲**: 3-18（SIZは8-18）
- **副次ステータス**: HP、MP、SAN、アイデア、知識、幸運
- **ダメージボーナス**: STR+SIZに基づく6版ルール
- **スキルシステム**: 基本値+職業技能+趣味技能

#### 7版対応
- **能力値範囲**: 15-90（パーセンテージベース）
- **ビルドシステム**: STR+SIZに基づくビルド値
- **移動力計算**: 年齢・能力値修正
- **半分・1/5値**: スキルの自動計算
- **背景情報**: 思想、重要な人物、宝物等

#### 高度な機能
- **バージョン管理**: キャラクターの成長・変更追跡
- **キャラクター画像**: アップロード機能
- **クロスユーザー可視**: 全ユーザーがキャラクターシート閲覧可能
- **管理インターフェース**: Django Adminでの包括的管理
- **装備・スキル管理**: 武器、防具、アイテムの詳細管理

## 🚀 キー機能ハイライト

### 🎭 クトゥルフ神話TRPG専用機能
- **6版・7版完全対応**: 能力値、スキル、副次ステータスの正確な計算
- **キャラクター成長追跡**: バージョン管理でキャラクターの成長を記録
- **探索者履歴**: プレイしたシナリオと成果を記録

### 👥 グループ管理（Cult Circle）
- **可視性制御**: 公開/非公開グループの管理
- **ロールベースアクセス**: 管理者/メンバーの権限分離
- **招待システム**: 承認・拒否機能付き招待

### 📅 セッション管理（Chrono Abyss）
- **秘匿ハンドアウト**: GMから特定プレイヤーへの情報配布
- **YouTube統合**: セッション配信URL管理
- **統計ダッシュボード**: 年間プレイ時間、ランキング

### 📚 シナリオアーカイブ（Mythos Archive）
- **高度フィルタリング**: ゲームシステム、難易度、時間、人数
- **プレイ統計**: シナリオ別プレイ回数、成功率
- **GMメモ**: 公開/非公開のGM専用メモ

### 🎨 クトゥルフテーマ
Atmospheric dark design with Cthulhu Mythos styling

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
- **SQLite** - 開発用データベース
- **PostgreSQL/MySQL** - 本番環境対応
- **Redis** - キャッシュ・セッション管理（設定済み）

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
iaia/
├── arkham_nexus/          # Django設定
├── accounts/              # ユーザー管理・キャラクターシート
│   ├── models.py          # ユーザー・グループ・キャラクターシートモデル
│   ├── views.py           # REST APIビュー・キャラクター作成
│   ├── statistics_views.py # 統計API
│   └── export_views.py    # エクスポートAPI
├── schedules/             # スケジュール管理
│   ├── models.py          # セッション・参加者・ハンドアウト
│   └── handout_views.py   # ハンドアウト管理API
├── scenarios/             # シナリオ管理
├── templates/             # HTMLテンプレート
│   ├── accounts/          # キャラクターシート・ユーザー管理
│   ├── groups/            # グループ管理
│   ├── scenarios/         # シナリオアーカイブ
│   └── statistics/        # 統計ダッシュボード
├── static/                # 静的ファイル・CSS・クトゥルフテーマ
├── CHARACTER_SHEET_*.md   # キャラクターシート仕様書
├── CLAUDE.md              # 開発ガイドライン
├── test_*.py              # 包括的テストスイート
├── requirements.txt       # Python依存関係
├── docker-compose.yml     # Docker設定
└── deploy.sh             # デプロイスクリプト
```

## 🌐 API エンドポイント

### 認証
- `POST /accounts/login/` - ログイン
- `POST /accounts/signup/` - サインアップ
- `POST /accounts/logout/` - ログアウト

### ユーザー・グループ管理
- `GET/POST /api/accounts/users/` - ユーザー管理
- `GET/POST /api/accounts/groups/` - グループCRUD・可視性制御
- `POST /api/accounts/groups/{id}/join/` - 公開グループ参加
- `POST /api/accounts/groups/{id}/invite/` - メンバー招待
- `GET /api/accounts/friends/` - フレンド管理
- `GET/POST /api/accounts/invitations/` - 招待処理

### キャラクターシート管理（クトゥルフ神話TRPG）
- `GET/POST /api/accounts/character-sheets/` - キャラクターシートCRUD
- `POST /api/accounts/character-sheets/create_6th_edition/` - 6版探索者作成
- `POST /api/accounts/character-sheets/{id}/create_version/` - バージョン管理
- `GET /api/accounts/character-sheets/{id}/versions/` - バージョン履歴
- スキル・装備管理用ネストエンドポイント

### セッション管理
- `GET/POST /api/schedules/sessions/` - セッションCRUD
- `GET /api/schedules/sessions/upcoming/` - 次回セッション
- `GET /api/schedules/sessions/statistics/` - プレイ統計
- `GET /api/schedules/calendar/` - カレンダーAPI
- `POST /api/schedules/sessions/{id}/join/` - セッション参加

### シナリオ管理
- `GET/POST /api/scenarios/scenarios/` - シナリオCRUD・高度フィルタリング
- `GET /api/scenarios/archive/` - シナリオアーカイブ・プレイ統計
- `GET /api/scenarios/statistics/` - ユーザープレイ統計

### 統計・エクスポート
- `GET /api/accounts/statistics/tindalos/` - Tindalos Metricsダッシュボード
- `GET /api/accounts/statistics/ranking/` - ユーザーランキング
- `GET /api/accounts/export/statistics/` - 統計データエクスポート

## 🛠️ 開発・運用

### 管理コマンド

```bash
# サンプルデータ作成
python manage.py create_sample_data [--clear]

# 探索者履歴データ作成・クリア
python manage.py create_investigator_history_data [--clear-history]

# テストデータ作成
python manage.py create_test_data

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