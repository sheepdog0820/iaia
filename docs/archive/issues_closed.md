> Repository cleanup note: GitHub Issues is the intended source of truth going forward. This file is retained as a migration snapshot/archive.

# Tableno 完了済み課題アーカイブ

このファイルは、完了済み・取り下げ済み・将来候補へ移動済みの課題を保存します。現在の未完了課題は `docs/archive/issues.md` を参照してください。

## 2026-06-17 本番完成化ロードマップ反映

### 完了: 7版キャラクターシート正式化

**概要**
- 7版をβ/保留扱いから正式サポートへ移行。
- 7版仕様書を `docs/character_sheet/CHARACTER_SHEET_7TH_EDITION_SPECIFICATION.md` として整備。
- 6版と7版の計算・技能定義・API保存処理を版ごとに明確化。
- 7版作成、編集、詳細、一覧、API、セッション連携、CCFOLIA入出力の回帰確認を追加。

**検証**
- `python manage.py test accounts.test_character_sheet_api`
- `python manage.py test accounts.test_character_sheets_integration`
- `node ./node_modules/playwright/cli.js test --project=chromium tests/e2e/flows/scenario-session-character.spec.ts`

### 完了: ブラウザ標準ダイアログ置換

**概要**
- 主要画面の `alert()` / `confirm()` をARKHAMトースト、確認モーダル、インラインエラーへ置換。
- キャラクター、グループ、セッション、日程調整、ハンドアウト、分析、カレンダー、テンプレート、シナリオアーカイブ、ダイス設定の操作感を統一。
- キャラクター6版/7版のバージョン作成確認文の文字化けを修正。

**検証**
- `rg -n "alert\\(|[^.]\\bconfirm\\(" templates static\\js static\\accounts\\js -g "*.html" -g "*.js"`
- `python manage.py check`
- `node ./node_modules/playwright/cli.js test --project=chromium tests/e2e/flows/ui-scripts.spec.ts`

### 完了: 開発/E2Eデータ露出対策

**概要**
- トップ、キャラクター一覧、セッション一覧、シナリオアーカイブで `E2E` / `Guest E2E` 由来の開発データを通常表示から除外。
- E2E検証時のみ `show_test_data=1` で明示表示できるように変更。
- グループ管理画面でもE2Eグループを通常表示から除外。

**検証**
- `python manage.py check`
- `node ./node_modules/playwright/cli.js test --project=chromium tests/e2e/flows/scenario-management.spec.ts tests/e2e/flows/scenario-session-character.spec.ts tests/e2e/flows/session-management.spec.ts tests/e2e/flows/ui-scripts.spec.ts`
- `git diff --check`

### 完了: AWS/運用仕上げ

**概要**
- Terraform/ECS/Celery/Redis/Google token関連の既存差分をレビューし、本番前の安全設定を整理。
- `aws-pre` と `aws-prod` の差分意図を文書化。
- worker/beat ECS service、health check、Secrets、SITE_ID、S3/CloudFront、Celery broker/result backendを本番設定として検証可能な状態に整理。
- 実AWS applyは別承認工程とし、リポジトリ内ではoffline planまでを完了条件に設定。

**検証**
- `terraform -chdir=infrastructure/terraform fmt -check -recursive`
- `terraform -chdir=infrastructure/terraform validate`
- `terraform -chdir=infrastructure/terraform plan -refresh=false -input=false -lock=false -var-file=environments/offline-plan.tfvars.example`

### 完了: ISSUES再編

**概要**
- `docs/archive/issues.md` を未完了課題だけのロードマップへ再編。
- 完了済みの本番完成化項目を本ファイルへ移動。
- 将来候補をFutureへ分離。

**検証**
- `git diff --check`

## 取り下げ・将来候補

- 汎用TRPGシステム対応: 対象外。クトゥルフ神話TRPG 6版/7版のみ対応。
- 実AWS apply、DNS/ACM/Secrets実値投入、予算承認: リポジトリ外の運用承認工程で実施。
- 決済/自動課金: 現時点では高権限ユーザーの手動設定で運用。
