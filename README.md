# 🌟 タブレノ - TRPGスケジュール管理システム

**Gate of Yog-Sothoth** - 時空を超えるTRPGスケジュール管理サービス

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Django](https://img.shields.io/badge/Django-4.2+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Web運用機能（2026-06-12）

- OpenAPI: `/api/schema/`、Swagger UI: `/api/docs/`
- 非同期処理: Celery worker/beat、`AsyncJob`、`GET /api/jobs/{id}/`
- リアルタイム通知: `/ws/notifications/`。接続不能時は30秒ポーリングへフォールバック
- Discord: グループ単位Webhook、暗号化URL保存、冪等送信
- カレンダー: iCalファイル出力、再発行可能なICS購読URL、Google Calendar片方向同期
- Google Sheets: 固定列キャラクターシートのプレビュー、取込、出力
- グループ間連携: 相互承認と明示リソース共有。メンバー資格・管理権限は共有しない
- ゲスト: 期限付き招待URL、参加表明、ログインユーザーによるclaim、監査ログ
- ハンドアウト: 条件ツリーによる自動公開と手動公開
- 運用設定画面: `/integrations/`
- AWS: `infrastructure/terraform/` と `docs/runbooks/`。実AWS適用は別のGo/No-Go工程
- 開発・検証フロー: `docs/WEB_FEATURE_COMPLETION_WORKFLOW.md`

## 🧰 環境要件

- Python 3.11+
- ローカル開発のDBはSQLiteがデフォルト
- Dockerでの起動は `DOCKER_SETUP.md` を参照

## 🌐 環境構成（Dev / Stg / Prod）

| 環境 | 役割 | 例URL | 特徴 |
| --- | --- | --- | --- |
| 開発（Dev） | 作りながら動かす | `http://127.0.0.1:8000` | DEBUG=True / ローカル |
| ステージング（Stg） | 本番リハーサル | `https://stg.tableno.jp` | 本番と同構成 |
| 本番（Prod） | 実ユーザー向け | `https://tableno.jp` | 安定・安全重視 |

補足:
- `APP_ENV` で環境切替できます（`local` / `aws-pre` / `aws-prod`）。
- `APP_ENV=aws-pre/aws-prod` の場合、`tableno.settings_production` を自動選択します。
- `.env.*` は `ENV_FILE` で明示指定できます（未指定時は `APP_ENV` に応じた既定値）。

## 📖 概要

タブレノは、クトゥルフ神話をテーマにしたTRPGスケジュール管理Webサービスです。TRPGセッションの管理、参加者の管理、プレイ履歴の記録など、TRPGライフを豊かにする機能を提供します。

### 🎭 主要機能

#### 👥 **ユーザー管理**
- カスタムユーザーモデル（ニックネーム、TRPG歴、プロフィール画像）
- フレンド機能
- グループ機能（**Cult Circle**）- 可視性制御（公開/非公開）
- グループ招待システム（承認・拒否機能）
- Google/X（Twitter）OAuth認証対応（API経由）

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

または conda を使う場合：

```bash
conda create -n iaia python=3.11
conda activate iaia
```

3. **依存関係インストール**
```bash
pip install -r requirements.txt
# 開発・テスト用
pip install -r requirements-dev.txt
```

4. **環境変数設定**
```bash
# 開発環境用の設定ファイルをコピー
cp .env.example .env.development
# .env.developmentファイルを編集して必要な設定を行う
# 実行時に明示指定（未指定時は APP_ENV に応じた既定値を使用）
export ENV_FILE=.env.development
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
APP_ENV=local ENV_FILE=.env.development python manage.py runserver
```

アプリケーションは http://localhost:8000 でアクセスできます。

### Docker で起動する場合

Docker での起動手順は `DOCKER_SETUP.md` を参照してください。

### ステージング/本番環境の準備

1. Stg: `.env.staging.example` → `.env.staging` を作成  
2. Prod: `.env.production.example` → `.env.production` を作成  
3. Stg/Prod は `APP_ENV=aws-pre` / `APP_ENV=aws-prod` で切替
4. `ALLOWED_HOSTS` と `CSRF_TRUSTED_ORIGINS` を必ず設定  
5. Docker Compose で環境を切り替える場合:

```bash
# Stg
APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml up -d

# Prod
APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d
```

### 依存関係の注意

- `mysqlclient` のビルドに失敗する場合は conda を推奨
- `allauth` の Google プロバイダーを使う場合は `cryptography` が必要

### テストアカウント

- **管理者**: admin / arkham_admin_2024
- **一般ユーザー**: azathoth_gm / arkham2024

### 🎲 キャラクターシート機能（クトゥルフ神話TRPG）

> **注意**: キャラクターシート機能はクトゥルフ神話TRPG専用です。6版は正式対応済みです。7版は作成画面・API・基本保存・派生値計算まで実装されていますが、正式な機能完成は保留中です。

#### 🌟 完成機能（6版）

##### 📋 キャラクター管理
- **一覧表示**: カード形式でキャラクターを一覧表示
- **フィルタリング**: 版別・キャラクター名での検索
- **ステータス管理**: 生存/死亡/発狂/重傷/行方不明/引退
- **バージョン管理**: キャラクターの成長履歴を保存

##### 🎯 キャラクター作成（タブ形式）
1. **基本情報タブ**
   - 探索者名、プレイヤー名、年齢（15-90歳）
   - 性別、職業、出身地、居住地

2. **能力値タブ**
   - **8つの基本能力値**: STR、CON、POW、DEX、APP、SIZ、INT、EDU
   - **ダイスロール機能**:
     - グローバル設定: 3D6（標準）、2D6+6（ヒロイック）
     - 個別設定: 能力値ごとのカスタム式
     - 一括ロール・個別ロール対応
   - **副次ステータス自動計算**:
     - HP: (CON + SIZ) ÷ 2
     - MP: POW
     - SAN: POW × 5
     - アイデア: INT × 5
     - 幸運: POW × 5
     - 知識: EDU × 5
     - ダメージボーナス: STR+SIZから自動判定

3. **技能タブ**
   - **技能ポイント配分**:
     - 職業技能: EDU × 20
     - 趣味技能: INT × 10
     - リアルタイム残りポイント表示
   - **技能管理**:
     - 基本値 + 職業P + 趣味P = 合計値（最大90%）
     - カテゴリ別フィルター（戦闘/探索/知識/対人/技術/行動/言語/特殊）
     - 検索機能
     - ポイント割り振り済み技能の表示

4. **プロフィールタブ**
   - 精神的な障害
   - キャラクターメモ
   - バックストーリー

5. **CCFOLIA連携タブ**
   - ワンクリックでCCFOLIA形式にエクスポート
   - カスタムパラメータ設定
   - JSONダウンロード

##### 🖼️ 画像管理システム（新機能）
- **複数画像対応**: メイン画像 + 追加画像（最大10枚）
- **画像ギャラリー**: サムネイル表示・モーダル拡大
- **自動リサイズ**: アップロード時に最適化
- **対応形式**: JPEG/PNG/GIF（最大5MB）

##### 📊 詳細表示画面
- 基本情報・能力値・技能の見やすい表示
- 画像ギャラリー
- 編集・複製ボタン
- バージョン履歴

#### 🚧 未実装・部分実装

- **7版キャラクターシート**: 基本作成・保存・派生値計算は実装済み。正式な完成作業は保留
- **セッション単位の状態管理**: HP/MP/SANの開始時スナップショット、変動履歴、終了時差分は未実装
- **キャラクターシート出力**: CCFOLIA JSON出力は実装済み。汎用PDF出力は未実装
- **外部共有**: セッション公開共有は実装済み。キャラクターシート単体の公開共有は未実装
- **将来候補**: ダイスロール履歴、モバイルアプリ、リアルタイム機能、AI支援

装備品・所持品管理と成長記録は実装済みです。全体の状態は `docs/CURRENT_WEBAPP_FEATURES.md`、正式な課題は `ISSUES.md` を参照してください。


## 🚀 キー機能ハイライト

### 🎭 クトゥルフ神話TRPG専用機能
- **6版完全対応**: 能力値、スキル、副次ステータスの正確な計算
- **キャラクター成長追跡**: バージョン管理でキャラクターの成長を記録
- **探索者履歴**: プレイしたシナリオと成果を記録
- **CCFOLIA連携**: ワンクリックでオンラインセッション対応

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
docker compose up -d
```

### ステージング/本番環境
```bash
# Stg
ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml up -d

# Prod
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d
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
- **Daphne** - HTTP/WebSocket対応ASGIサーバー

### 認証・セキュリティ
- **django-allauth** - Google/X（Twitter）OAuth認証
- **Django REST Framework Token認証** - API経由でのアクセス
- **CORS対応** - 認証ヘッダー許可
- **レート制限**
- **CSP設定**

## 📁 プロジェクト構造

```
iaia/
├── tableno/          # Django設定
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
└── deploy.sh             # 旧デプロイスクリプト（Phase1では未使用）
```

## 🌐 API エンドポイント

### 認証
- `POST /api/auth/google/` - Google OAuth認証（API経由）
- `POST /api/auth/discord/` - Discord OAuth認証（API経由）
- `POST /api/auth/twitter/` - X（Twitter）OAuth認証（API経由）
- `POST /api/auth/logout/` - APIログアウト（トークン無効化）
- `GET /api/auth/user/` - 現在のユーザー情報取得
- `POST /api/auth/token/refresh/` - トークン更新

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
- `GET /api/accounts/character-sheets/{id}/skill_points_summary/` - スキルポイントサマリー
- `POST /api/accounts/character-sheets/{id}/allocate_skill_points/` - スキルポイント配分
- `GET /api/accounts/character-sheets/{id}/combat_summary/` - 戦闘データサマリー
- `GET /api/accounts/character-sheets/{id}/financial_summary/` - 財産サマリー
- `GET /api/accounts/character-sheets/{id}/inventory_summary/` - インベントリサマリー
- `GET /api/accounts/character-sheets/{id}/background_summary/` - 背景情報サマリー
- `GET /api/accounts/character-sheets/{id}/growth_records/` - 成長記録
- `GET /api/accounts/character-sheets/{id}/ccfolia_json/` - CCFOLIA形式エクスポート

### セッション管理
- `GET/POST /api/schedules/sessions/` - セッションCRUD
- `GET /api/schedules/sessions/upcoming/` - 次回セッション
- `GET /api/schedules/sessions/statistics/` - プレイ統計
- `GET /api/schedules/calendar/` - カレンダーAPI
- `POST /api/schedules/sessions/{id}/join/` - セッション参加

### 運用・外部連携
- `GET /api/schema/` / `GET /api/docs/` - OpenAPIスキーマ / Swagger UI
- `GET /api/jobs/{id}/` - 非同期ジョブ状態
- `POST /api/calendar/subscription-token/rotate/` - ICS購読トークン再発行
- `GET /calendar/subscribe/{token}.ics` - 個人用ICS購読フィード
- `POST /api/groups/{id}/links/` - グループ連携申請
- `POST /api/groups/{id}/links/{link_id}/accept/` - グループ連携承認
- `DELETE /api/groups/{id}/links/{link_id}/` - グループ連携解除
- `GET/PUT /api/groups/{id}/discord-settings/` - Discord通知設定
- `POST /api/sessions/{id}/google-calendar/sync/` - Google Calendar同期
- `POST /api/character-sheets/google-sheets/import/` - Google Sheets取込
- `POST /api/character-sheets/google-sheets/export/` - Google Sheets出力
- `POST /api/sessions/{id}/guest-invitations/` - ゲスト招待発行
- `POST /api/guest-invitations/{token}/respond/` - ゲスト参加表明
- `POST /api/participants/{id}/claim/` - ゲスト枠claim
- `/ws/notifications/` - 認証済みユーザー通知WebSocket

ハンドアウトAPIは `release_conditions`、`release_status`、`next_evaluation_at` を返します。

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
# アプリケーション/プロキシログ
docker compose -f docker-compose.mysql.yml logs -f web
docker compose -f docker-compose.mysql.yml logs -f nginx
```

### パフォーマンス監視

```bash
# コンテナ状態確認
docker compose -f docker-compose.mysql.yml ps
docker compose -f docker-compose.mysql.yml top
```

## 🌐 環境設定管理

### 環境別設定ファイル

本プロジェクトでは環境に応じて異なる設定ファイルを使用します：

- **開発環境**: `.env.development`
- **ステージング環境**: `.env.staging`
- **本番環境**: `.env.production`
- **テンプレート**: `.env.example`

### 環境の切り替え方法

```bash
# 開発環境
APP_ENV=local ENV_FILE=.env.development python manage.py runserver

# AWSプレ環境
APP_ENV=aws-pre ENV_FILE=.env.staging python manage.py migrate

# AWS本番環境
APP_ENV=aws-prod ENV_FILE=.env.production python manage.py migrate

# Dockerを使用する場合（例: 本番）
APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d
```

### 設定ファイルの準備

```bash
# 開発環境用
cp .env.example .env.development

# ステージング環境用
cp .env.staging.example .env.staging

# 本番環境用
cp .env.production.example .env.production
```

`APP_ENV` 未指定時は `local` として扱われます。
`ENV_FILE` 未指定時は `APP_ENV` に応じて以下を既定利用します。
- `local` -> `.env.development`
- `aws-pre` -> `.env.staging`
- `aws-prod` -> `.env.production`
※ 実際に使う環境のファイルだけ用意すればOKです。

## 🔒 セキュリティ

### 本番環境での推奨設定

1. **SSL証明書の設定**
```bash
# Let's Encrypt (webroot)
sudo apt install certbot
sudo certbot certonly --webroot -w /path/to/repo/certbot/www -d tableno.jp -d www.tableno.jp
sudo cp /etc/letsencrypt/live/tableno.jp/fullchain.pem ./ssl/fullchain.pem
sudo cp /etc/letsencrypt/live/tableno.jp/privkey.pem ./ssl/privkey.pem
docker compose -f docker-compose.mysql.yml restart nginx
```
詳細は `docs/DEPLOYMENT_GUIDE.md` を参照してください。

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
ENV_FILE=.env.development python manage.py test

# カバレッジ付きテスト
ENV_FILE=.env.development coverage run manage.py test
coverage report
coverage html
```

## 👨‍💻 開発者向け情報

### キャラクターシート開発

#### データ構造
```python
# 6版キャラクターの能力値は3-18で保存
character = CharacterSheet.objects.create(
    edition='6th',
    str_value=13,  # 3-18の値
    con_value=14,
    # ...
)

# 副次ステータスは自動計算
character.hit_points_max  # (CON + SIZ) ÷ 2
character.magic_points_max  # POW
character.sanity_max  # POW × 5
```

#### 画像管理
```python
# 新しいCharacterImageモデルを使用
from accounts.models import CharacterImage

# メイン画像を設定
main_image = CharacterImage.objects.create(
    character_sheet=character,
    image=image_file,
    is_main=True,
    order=0
)
```

#### テストデータ作成
```bash
# キャラクターのテストデータ作成
python manage.py create_test_characters --username testuser --count 3

# 既存データの移行
python migrate_character_images.py
```

### API開発

#### エンドポイント
- `/api/accounts/character-sheets/` - キャラクター一覧・作成
- `/api/accounts/character-sheets/{id}/` - 詳細・更新・削除
- `/api/accounts/character-sheets/{id}/images/` - 画像管理
- `/api/accounts/character-sheets/{id}/ccfolia_json/` - CCFOLIA連携

#### 認証
全APIエンドポイントは認証が必要です：
```python
permission_classes = [IsAuthenticated]
```

## 📈 デプロイ

正規のAWS構成はECS/Fargate + ALB/ACM + RDS + ElastiCache + S3/CloudFrontです。詳細は `docs/AWS_ECS_SETUP_GUIDE.md` を参照してください。

### 互換デプロイ（Lightsail / Docker Compose）

以下はローカル本番相当検証または既存Lightsail運用向けです。

1. **サーバー準備**
   - Lightsail（Ubuntu）に Docker / Docker Compose / certbot を導入

2. **環境変数の準備**
   - `.env.staging` / `.env.production` を作成して必要値を設定
   - `ALLOWED_HOSTS` と `CSRF_TRUSTED_ORIGINS` は必須

3. **起動**
```bash
# Stg
APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml up -d

# Prod
APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d
```

4. **SSL設定**
   - `docs/DEPLOYMENT_GUIDE.md` の手順に従って証明書取得と自動更新を設定

## 🤝 コントリビューション

1. フォークを作成
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📝 ライセンス

ライセンス条件はリポジトリ管理者へ確認してください。現在、リポジトリにはライセンスファイルが含まれていません。

## 🙏 謝辞

- **H.P. Lovecraft** - インスピレーションの源
- **Django コミュニティ** - 素晴らしいフレームワーク
- **TRPGコミュニティ** - 継続的なフィードバック

---

*"That is not dead which can eternal lie, And with strange aeons even death may die."*

**🌟 Happy Gaming! 🎲**
