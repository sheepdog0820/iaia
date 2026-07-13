# Tableno

Tableno is a Django-based TRPG schedule, scenario, and character management application for Call of Cthulhu campaigns.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)
![Django](https://img.shields.io/badge/Django-5.2-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Quick Start

```bash
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env.development
APP_ENV=local ENV_FILE=.env.development python manage.py migrate
APP_ENV=local ENV_FILE=.env.development python scripts/dev/create_admin.py
APP_ENV=local ENV_FILE=.env.development python manage.py create_sample_data
APP_ENV=local ENV_FILE=.env.development python manage.py runserver
```

起動後は `http://127.0.0.1:8000` にアクセスします。Python: 3.11+、Django 5.2系 (`Django>=5.2.0,<5.3`) を前提にしています。

### テストアカウント

固定のテストアカウントやパスワードはREADMEに記載しません。必要なアカウントは `python scripts/dev/create_admin.py` や開発用管理コマンドでローカル環境で作成してください。

## Demo / Screenshots

スクリーンショットは `docs/reports/screenshots/` に配置する想定です。公開前には、PC幅とスマホ幅で以下の画面を撮影してREADMEへ差し込みます。

- セッション一覧・日程調整
- キャラクターシート6版/7版の作成画面
- シナリオ管理・プレイ履歴
- 共有リンク閲覧画面

## Architecture

Tableno is a conventional Django application with a Bootstrap 5 and vanilla JavaScript frontend. The backend exposes HTML views plus Django REST Framework APIs, and the production path supports ASGI, Redis-backed channels, Celery workers, object storage, and Stripe billing gates.

主要な仕様と運用資料:

- 現在のWeb機能一覧: `docs/specifications/CURRENT_WEBAPP_FEATURES.md`
- プロジェクト仕様: `docs/specifications/PROJECT_SPECIFICATION.md`
- キャラクターシート仕様: `docs/character_sheet/`
- 共有リンク仕様: `docs/specifications/SAFE_SHARE_LINKS.md`
- AWS/運用資料: `docs/infrastructure/`, `docs/runbooks/`, `infrastructure/terraform/`
- 公開前チェック: `docs/release/PUBLIC_RELEASE_CHECKLIST.md`

## Directory Structure

- `accounts/`: アカウント、認証、グループ、キャラクターシート
- `schedules/`: セッション、日程調整、参加者、秘匿ハンドアウト
- `scenarios/`: シナリオ、プレイ履歴、GMメモ
- `templates/`: Djangoテンプレート
- `static/`: CSS、JavaScript、画像などの静的資産
- `tests/`: unit / integration / system / ui / e2e テスト
- `docs/`: 仕様、運用、セットアップ、レポート、アーカイブ
- `scripts/`: 開発、保守、テスト補助スクリプト
- `infrastructure/`: Terraform/AWS構成
- `docker/`: コンテナ起動用エントリポイント

## Development Status

現在の中核機能は、ローカルテストで継続確認している範囲です。

- アカウント管理: メールログイン、Google/X/Discord OAuth、プロフィール、フレンド、グループ、招待リンク。
- セッション管理: TRPGセッション、参加者、日程調整、秘匿ハンドアウト、添付、YouTubeリンク、カレンダー表示。
- シナリオ管理: シナリオ情報、プレイ履歴、GMメモ、ハンドアウトテンプレート。
- キャラクター管理: クトゥルフ神話TRPG 6版/7版のキャラクター作成、一覧、詳細、編集、画像、技能、装備、ステータス管理。
- 共有機能: `private` / `group` / `link` / `public` の公開範囲と、推測困難な固定共有URL。
- API/運用補助: Django REST Framework、OpenAPI (`/api/schema/`)、Swagger UI (`/api/docs/`)、ヘルスチェック、Celery/AsyncJob基盤。
- 課金安全ゲート: Stripe Checkout/Customer Portal導入前の設定検証、リリースゲート、監査ログ、法務ページ確認。

外部連携のうち Google Calendar/Sheets、advanced Discord notifications、WebSocket notifications は実装済み基盤がありますが、広範な公開利用前に `docs/release/PUBLIC_RELEASE_CHECKLIST.md` と `docs/release/PUBLIC_RELEASE_TASKS.md` に沿った real external-service verification が必要です。

未対応タスクはGitHub Issuesを正本にします。移行前のローカル課題メモは `docs/archive/issues.md`、完了済み履歴は `docs/archive/issues_closed.md` に保存しています。

## Quality Gate

GitHub Actions (`.github/workflows/django-ci.yml`) は `main` とPull Requestで以下を実行します。

- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py migrate --noinput` と `python manage.py migrate --check`
- `python -m pytest`
- `python -m flake8 .`
- `python -m black --check .`
- `python -m isort --check-only .`
- Docker Compose config check
- production settings の `python manage.py check --deploy`
- `python manage.py billing_release_gate`

2026-07-02時点のローカル確認では、上記相当のチェックとシステムテストが通過しています。

- `python -m pytest --collect-only -q`: `1479 tests collected`
- `python -m pytest tests/system -q -rs`: `16 passed, 1 skipped`

## Development Commands

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
python -m pytest
python -m pytest tests/system -q -rs
python -m flake8 .
python -m black --check .
python -m isort --check-only .
```

E2Eを実行する場合はNode.js 18+とPlaywright依存を準備してください。

```bash
npm install
npm run test:e2e
```

## Docker

開発用Composeは `docker-compose.yml` を使います。

```bash
cp .env.compose.example .env.compose
cp .env.docker.example .env.docker
# 必要に応じて .env.compose の ENV_FILE を調整します
docker compose --env-file .env.compose up --build
```

`.env.compose` はComposeの変数展開用、`.env.docker.example` はDjangoアプリenvのサンプルです。Composeの `env_file` 側で `SECRET_KEY` などに `$` を含める場合は、Composeに展開されないよう `$$` にエスケープしてください。

ステージング/本番相当のMySQL構成は `docker-compose.mysql.yml` を使います。詳細は `docs/setup/DOCKER_SETUP.md` を参照してください。

## Deployment

ステージングは `APP_ENV=aws-pre`、本番は `APP_ENV=aws-prod` を使います。反映時はアプリ起動前に、対象環境でマイグレーションと静的ファイル収集を明示的に実行します。

```bash
# Staging
APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml run --rm web python manage.py migrate --noinput
APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml run --rm web python manage.py collectstatic --noinput
APP_ENV=aws-pre ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml up -d

# Production
APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml run --rm web python manage.py migrate --noinput
APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml run --rm web python manage.py collectstatic --noinput
APP_ENV=aws-prod ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d
```

AWS環境への反映や検証は `docs/runbooks/`、`docs/infrastructure/`、`infrastructure/terraform/` の内容に従います。

## Security Notes

- `.env.*` の実値はコミットしないでください。サンプルは `.env.*.example` を使います。
- `APP_ENV=local` は開発用、`aws-pre` / `aws-prod` は `tableno.settings_production` を使う運用環境用です。
- 開発用ログイン、モックOAuth、サンプルデータはローカル検証専用です。
- Stripe Checkoutは設定が揃い、運用ゲートを通過するまで既定で無効です。
- Google Calendar/Sheets、advanced Discord notifications、WebSocket notifications は実装済みでも、公開運用前に real external-service verification が必要です。
- キャラクターシートはクトゥルフ神話TRPG 6版/7版のみを正式対象にします。

## Roadmap

- Stripe Checkout/Customer Portalの本番導入前検証と外部Stripe test-mode確認。
- AWS staging/production運用手順、Terraform、CloudWatch/Sentry連携の実環境検証。
- Google Calendar/Sheets、advanced Discord notifications、WebSocket notifications の公開運用前検証。
- キャラクター管理コードの分割と保守性改善。
- スマホ利用時の一覧・編集画面UX改善。
- 利用状況ログ、運用ダッシュボード、フィードバック導線。
