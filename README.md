# Tableno

タブレノは、クトゥルフ神話TRPG 6版・7版のセッション、日程調整、シナリオ、キャラクターシートを管理するDjangoアプリケーションです。

![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)
![Django](https://img.shields.io/badge/Django-5.2-green.svg)

## 現在の状態（2026-11-26 JST、作業開始時点）

**有料プランと外部連携を含む正式公開は No-Go です。** 残条件と証拠は[正式公開の受け入れ条件](docs/release/FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を参照してください。

| 対象 | 確認結果 |
| --- | --- |
| main | HEADは [`4627cdd04eea48dd9b81c1cb558acb73bd1b47f6`](https://github.com/sheepdog0820/iaia/commit/4627cdd04eea48dd9b81c1cb558acb73bd1b47f6)。2026-11-01に [PR #66](https://github.com/sheepdog0820/iaia/pull/66) をマージ済み。[同じSHAのmain push CI](https://github.com/sheepdog0820/iaia/actions/runs/41304175048)は全6ジョブ成功 |
| オープンPR | [18件すべてDraft](https://github.com/sheepdog0820/iaia/pulls)。main向けは [#67](https://github.com/sheepdog0820/iaia/pull/67) と [#68](https://github.com/sheepdog0820/iaia/pull/68) の2件、作業ブランチ向けは16件 |
| オープンPRのCI | 各headのPR CIを確認。main向けは各全6ジョブ成功（[#67 CI](https://github.com/sheepdog0820/iaia/actions/runs/41309855875)、[#68 CI](https://github.com/sheepdog0820/iaia/actions/runs/41318684906)）。作業ブランチ向けは15件成功、[#31](https://github.com/sheepdog0820/iaia/pull/31) は [lint-securityが失敗](https://github.com/sheepdog0820/iaia/actions/runs/40772601909) |
| 開発AWS | [stg.tableno.jp](https://stg.tableno.jp/) のWebサービスはECSタスク定義59で切替完了、稼働1・待機0・`HEALTHY`。稼働イメージのECRタグは `aws-pre-4e19a16e`。対応する[開発反映ブランチのコミット](https://github.com/sheepdog0820/iaia/commit/4e19a16ea6ac0d4286daf93c6417acc7aa027c6c)の [push CI](https://github.com/sheepdog0820/iaia/actions/runs/45545739625) は全6ジョブ成功。稼働digestと確認範囲は[受け入れ条件の冒頭](docs/release/FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)に記録 |

### 2026年9月の統合・検証履歴

- 2026-09-10に [PR #3](https://github.com/sheepdog0820/iaia/pull/3) を `74a4b506` でmainへマージ。Google配送修正を含む `f97c7809` の [push CI](https://github.com/sheepdog0820/iaia/actions/runs/34455121479) と [PR CI](https://github.com/sheepdog0820/iaia/actions/runs/34455126552) は各全6ジョブ成功。開発AWSは当時Webタスク定義48で、9月10日のログイン・統計表示と9月12日の稼働確認を記録しています。 [Google配送修正のAWS反映記録](docs/release/AWS_PRE_GOOGLE_DELIVERY_2026-09-10.md)
- 2026-09-12の [PR #4の候補 `a1a50b63`](docs/release/RUNTIME_CANDIDATE_A1A50B63_2026-09-12.md) は、通常配布物で関連55テストと506ファイルの一致を確認。push/PR CIは各全6ジョブ成功（単体・統合1,828成功・30スキップ、ブラウザ186成功）。
- 2026-09-13に [PR #4](https://github.com/sheepdog0820/iaia/pull/4) を [`d875d028`](https://github.com/sheepdog0820/iaia/commit/d875d028ede0b3172780d54d4baacdb226a1d3b3) でmainへマージし、[main push CI](https://github.com/sheepdog0820/iaia/actions/runs/34734748547) は全6ジョブ成功。同日の開発AWSでは `aws-pre-d875d028` をWebタスク定義49で確認しています。 [当時のAWS反映記録](https://github.com/sheepdog0820/iaia/blob/d4b1262972a8979cc507a2cf57184eedbb6ee313/docs/release/AWS_PRE_D875D028_2026-09-13.md)

## 無料・有料の範囲

| 項目 | 決定済みの仕様 |
| --- | --- |
| 無料の基本機能 | キャラクター・セッション・シナリオの作成と編集、シナリオアーカイブ、CCFOLIAインポート、作成済みセッションの関連シナリオ変更 |
| キャラクター画像 | 無料・有料とも1キャラクター5枚。既存の超過画像は保持し、5枚未満になるまで新規追加を制限 |
| プレミアム | 画像の背景透過のみ。月額480円・年額4,800円（税込）。実Stripe Priceの照合・販売開始の検証は未完了 |
| プレミアム失効 | 基本機能と既存データを維持し、新しい背景透過の実行を制限 |
| 世代削除 | 後続バージョンを残す |
| 日程確定後 | 確定した投票を履歴として保持し、現在の日程はセッション編集で変更 |

無料機能でも、ログイン・所有権・GM・閲覧権限の制限は維持します。背景透過は実AWSで合成画像の処理に成功していますが、有料利用者による画面操作の全経路は検証が残っています。[公開仕様の決定記録](docs/release/FORMAL_RELEASE_PLAN_DECISIONS.md)も参照してください。

特商法ページと課金前の画面には、税込料金、自動更新、次回更新日前までの解約と期間終了時の効力、返金条件を表示します。[個人事業者・請求開示方式の設定](docs/release/INDIVIDUAL_SELLER_POLICY_2026-09-12.md)に設定方法と開示依頼の運用準備を記録しています。

ハンドアウトは[更新・削除権限](docs/release/HANDOUT_WRITE_AUTHORIZATION_2026-09-12.md)、[一括作成の入力形式](docs/release/HANDOUT_BULK_VALIDATION_2026-09-12.md)、[管理テストの検証漏れ](docs/release/HANDOUT_MANAGEMENT_TEST_COVERAGE_2026-09-12.md)を修正しました。[一覧の隔離測定](docs/release/HANDOUT_LIST_PERFORMANCE_2026-09-12.md)は100要求で許可されたID・本文が一致し、p95は1.694秒でした。実AWS・全操作・長時間負荷の合格は未証明です。

## ローカルで起動する

新しいローカル開発環境をセットアップする手順です。新しいターミナルを使い、既存の環境ファイルは内容を確認してから使ってください。

### macOS / Linux / WSL

```bash
python3.11 -m venv venv
source venv/bin/activate
python -m pip install -r requirements-dev.lock.txt
if [ ! -e .env.development ]; then cp .env.example .env.development; fi
export APP_ENV=local ENV_FILE=.env.development DB_ENGINE=sqlite
export DJANGO_SETTINGS_MODULE=tableno.settings
```

### Windows PowerShell

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.lock.txt
if (-not (Test-Path -LiteralPath .env.development)) {
    Copy-Item .env.example .env.development
}
$env:APP_ENV = 'local'
$env:ENV_FILE = '.env.development'
$env:DB_ENGINE = 'sqlite'
$env:DJANGO_SETTINGS_MODULE = 'tableno.settings'
```

`.env.development` の `SECRET_KEY` を開発用の値へ変更します。`.env.example` にはMySQL用の項目も含まれるため、`DB_ENGINE=sqlite` を明示しています。ローカル設定の接続先はリポジトリ直下の `db.sqlite3` です。このファイルが未作成か、実データから隔離した開発専用DBであることを確認し、環境変数を設定した同じターミナルで実行してください。実データを含む場合は、別のチェックアウトで新しいローカルDBを用意してください。

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

起動後は [http://127.0.0.1:8000](http://127.0.0.1:8000) にアクセスします。Python 3.11以上とDjango 5.2系 (`Django>=5.2.0,<5.3`) を前提とし、通常配布物とCIはPython 3.11を使用します。サンプルが必要な場合は、同じ隔離DBで `python manage.py create_sample_data` を実行できます。外部認証・課金・背景透過には別途設定が必要です。

### テストアカウント

検証用の管理者アカウントは、上記の隔離DBで `python manage.py createsuperuser` を使って作成してください。

## Demo / Screenshots

スクリーンショットは `docs/reports/screenshots/` に配置する想定です。公開前には、PC幅とスマホ幅で以下の画面を撮影してREADMEへ差し込みます。

- セッション一覧・日程調整
- キャラクターシート6版/7版の作成画面
- シナリオ管理・プレイ履歴
- 共有リンク閲覧画面

## Architecture

HTML画面とDjango REST Framework APIを提供し、画面はBootstrap 5とVanilla JavaScriptで構成します。開発AWSはECS Fargate・RDS PostgreSQL・S3・CloudFrontを使用します。ASGI/Channels・Celery・Redis・Stripeの対応コードと、実配備・実サービス検証の状況は別に管理します。

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

正式公開の判定は[受け入れ条件](docs/release/FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)で追跡し、実装作業はGitHub Issues・Pull Requestと対応づけます。過去のローカル課題メモは `docs/archive/issues.md`、完了済み履歴は `docs/archive/issues_closed.md` に保存しています。

## Quality Gate

GitHub Actions ([ワークフロー定義](.github/workflows/django-ci.yml)) は `main`・`codex/**` へのpushとPull Requestで、次の6ジョブを実行します。AWSデプロイを自動実行するワークフローではありません。

| ジョブ | 主な確認 |
| --- | --- |
| Unit / Integration | Django設定・移行、単体/統合テストとカバレッジ、書式、Compose、ビルド対象の隔離、配備設定・課金ゲート |
| system | システムテスト |
| production-database | PostgreSQL 18.3での移行・課金ライフサイクル・権限・並行処理等の対象テスト |
| playwright | Chromium・Firefox・WebKitの画面操作、Node依存関係監査 |
| lint-security | Flake8・Black・isort、Bandit、Python依存関係監査 |
| infrastructure | Terraformの書式・構成・模擬試験。実AWSの変更なし |

主な検査コマンド:

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

作業開始時点のmain、オープンPR、開発AWS向けコミットのCIは冒頭を参照してください。テスト件数と合格範囲は実行ごとの対象SHAに対応します。

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

依存関係の宣言は`requirements.txt`、`requirements-dev.txt`、`requirements-test.txt`で管理し、実際のインストールには固定済みファイルを使います。依存関係を更新した場合はPython 3.11環境で次を実行し、3つのロックファイルを更新してください。

```bash
python -m piptools compile --generate-hashes --allow-unsafe --strip-extras --newline=lf --output-file requirements.lock.txt requirements.txt
python -m piptools compile --generate-hashes --allow-unsafe --strip-extras --newline=lf --output-file requirements-dev.lock.txt requirements-dev.txt
python -m piptools compile --generate-hashes --allow-unsafe --strip-extras --newline=lf --output-file requirements-test.lock.txt requirements-test.txt
```

E2Eを実行する場合はNode.js 20+を使用します。[セットアップ手順](docs/testing/E2E_TEST_SETUP.md)とCI定義を参照し、実データから隔離したDB・試験利用者を準備してください。

```bash
npm ci
npx playwright install chromium firefox webkit
npm run test:e2e
```

## Docker

開発用Composeは `docker-compose.yml` を使います。

```bash
cp .env.compose.example .env.compose
cp .env.docker.example .env.docker
# .env.compose の ENV_FILE を .env.docker に変更し、開発用の設定値を確認
docker compose --env-file .env.compose up --build
```

`.env.compose` はComposeの変数展開用、`.env.docker.example` はDjangoアプリenvのサンプルです。Composeの `env_file` 側で `SECRET_KEY` などに `$` を含める場合は、Composeに展開されないよう `$$` にエスケープしてください。

アプリコンテナは既定でUID/GID `10001`の非rootユーザー`tableno`として動作します。LinuxやNASでホストディレクトリをbind mountする場合は、`staticfiles`、`media`、`logs`へこのユーザーが書き込めるよう所有権または権限を設定してください。必要ならビルド引数`APP_UID`、`APP_GID`でホスト側に合わせられます。

開発用ComposeはPostgreSQL構成です。別途 `docker-compose.mysql.yml` もありますが、現在の開発AWSはECS/RDS PostgreSQLです。初期化・起動オプションは[Dockerセットアップ](docs/setup/DOCKER_SETUP.md)を参照してください。

## Deployment

AWSでは `APP_ENV=aws-pre` / `aws-prod` が `tableno.settings_production` を選択します。対象コミットから通常イメージを作成し、現行タスク定義の設定を保持してイメージを更新します。DB移行・静的ファイル更新は変更内容に応じて個別に判断します。

反映前に対象環境・CI・稼働版・復旧先を確認し、[作業・承認境界](AGENTS.md)に従ってください。開発AWSで確認した項目は[過去の反映例](docs/release/AWS_PRE_GOOGLE_DELIVERY_2026-09-10.md)を参照できます。共有DB・実データ・IAM/Secrets・費用変更、mainマージ、本番反映には該当範囲の承認が必要です。詳細資料は `docs/runbooks/`、`docs/infrastructure/`、`infrastructure/terraform/` にあります。

## Security Notes

- `.env.*` の実値はコミットしないでください。サンプルは `.env.*.example` を使います。
- `APP_ENV=local` は開発用、`aws-pre` / `aws-prod` は `tableno.settings_production` を使う運用環境用です。
- 開発用ログイン、モックOAuth、サンプルデータはローカル検証専用です。
- Stripe Checkoutは設定が揃い、運用ゲートを通過するまで既定で無効です。
- Google Calendar/Sheets、advanced Discord notifications、WebSocket notifications は実装済みでも、公開運用前に real external-service verification が必要です。
- キャラクターシートはクトゥルフ神話TRPG 6版/7版のみを正式対象にします。

## 正式公開までの残タスク

| 分野 | 残条件 |
| --- | --- |
| 本番公開の判断 | 正式公開はNo-Go。受け入れ条件を満たし、対象版と本番反映の可否を判断 |
| 外部連携 | Google実同期・失効/再試行/取消・公開審査、Discord/Xの実認証・通知、CCFOLIA画像/ダイス・ICS受信側確認 |
| 非同期・監視 | 常設worker・待ち行列・定期処理、夜間停止、監視通知・問い合わせ配送の実証 |
| 課金 | 実サンドボックスに月額・年額などの個別検証記録あり。公開対象版と実AWS設定での決済・配送・再送および有料必須ゲートの証跡が必要 |
| 主要機能・画面 | 復旧・退会、所有権引継ぎの範囲、日程/セッション全フロー、キャラクター計算・画像・背景透過、実機・スマートフォンの残経路 |
| 情報保護 | 全共有・添付・秘匿情報の配送経路、最新配布物のOS脆弱性指摘の判定・対処 |
| 性能 | 登録100人・同時10人、通常操作p95が3秒以内・予期しないエラー0件を実AWSと不足操作で確認。背景透過は別枠で測定 |
| 移行・復旧・切戻し | 共有DBの移行状況の確認、本番相当の移行、DBとS3を合わせた整合性、RPO24時間・RTO4時間、アプリ切替・主要操作・ロールバックの実証 |
| 公開条件 | 事業者情報、保存/返金等の方針、法務表示、公開時期・運用費用の確定と最終リリース判断 |

隔離環境での性能試験、一時RDS復元、背景透過の実処理、非公開ファイルのS3/CDN権限試験には成功記録がありますが、公開条件全体の合格を意味しません。詳細は[正式公開の受け入れ条件](docs/release/FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を参照してください。
