# Tableno 未完了ロードマップ

最終更新: 2026-06-17

このファイルは、まだ本番投入前に判断または実装が必要な課題だけを管理します。完了済みの本番完成化作業は `ISSUES_CLOSED.md`、現行仕様は `docs/CURRENT_WEBAPP_FEATURES.md` と各仕様書を参照してください。

## P0: 本番リリース前 Go/No-Go

### ISSUE-070: 本番環境への最終適用承認

**目的**: リポジトリ内で検証済みのAWS構成を、実AWS環境へ適用する前に運用承認する。

**受け入れ条件**
- `aws-pre` と `aws-prod` の差分意図が運用担当者に確認されている。
- DNS、ACM、Secrets、予算、バックアップ保持期間、監視通知先が実値で承認されている。
- `terraform plan -refresh=false` ではなく、実AWS状態を参照したplanを別工程で確認している。
- apply担当者、ロールバック手順、メンテナンス告知方針が明文化されている。

**検証コマンド**
- `terraform -chdir=infrastructure/terraform fmt -check -recursive`
- `terraform -chdir=infrastructure/terraform validate`
- `terraform -chdir=infrastructure/terraform plan -input=false -lock=false -var-file=environments/aws-prod.tfvars`

**完了定義**
- Go/No-Go記録が残り、実AWS applyの実施可否が決定している。

**コミット単位**
- 実値を含まない運用手順・Go/No-Go記録のみ。Secrets実値はコミットしない。

## P1: 連携機能の運用観測

### ISSUE-071: 外部連携の失敗観測と再試行運用

**目的**: Google Calendar/Sheets、Discord、ゲスト招待、グループ連携の失敗を運用者が追跡し、ユーザーが復旧できる状態にする。

**受け入れ条件**
- Google OAuth refresh token失効時、連携設定画面から再連携導線に到達できる。
- Discord配信失敗は管理画面またはAPIで確認でき、手動再送できる。
- Sheets大規模インポート/エクスポートはAsyncJobで進捗・失敗理由を確認できる。
- 外部API障害時に、画面操作がロールバックされず失敗状態と再試行導線が残る。

**検証コマンド**
- `python manage.py test schedules.test_external_integrations`
- `python manage.py test schedules.test_async_jobs`
- `npm run test:e2e -- --project=chromium tests/e2e/flows/ui-scripts.spec.ts`

**完了定義**
- 外部連携の失敗、再試行、復旧導線がユーザー向け画面と運用ログで確認できる。

**コミット単位**
- 失敗状態モデル/API
- 連携設定UI
- 再試行タスク
- テスト

## P2: セッション拡張

### ISSUE-072: セッション開始/終了時のキャラクター状態スナップショット

**目的**: セッション中のHP/MP/SANなどの変化を、キャラクターシート本体の現在値と混同せず履歴化する。

**受け入れ条件**
- セッション開始時に参加キャラクターのHP/MP/SANをスナップショット保存できる。
- セッション中のHP/MP/SAN変動、状態異常、一時効果を履歴として保存できる。
- セッション終了時に開始時との差分を表示できる。
- 既存キャラクターシートの現在値と矛盾しない。

**検証コマンド**
- `python manage.py test schedules.test_character_session_ho_integration`
- `python manage.py test tests.integration.test_character_session_integration`

**完了定義**
- セッション詳細で状態履歴を確認でき、保存済みキャラクター現在値を破壊しない。

**コミット単位**
- モデル/API
- セッション詳細UI
- テスト

## Future

- ネイティブモバイルアプリ
- AI分析・推薦
- セッション掲示板
- クイック投票
- 汎用素材ライブラリ
- VTT連携
