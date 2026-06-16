# Tableno 本番完成ロードマップ

最終監査日: 2026-06-17

このファイルは未完了の正式課題だけを、実装順に管理します。完了項目は `ISSUES_CLOSED.md`、現行機能は `docs/CURRENT_WEBAPP_FEATURES.md`、セッション領域の分類は `SESSION_UNIMPLEMENTED_FEATURES_SPEC.md` を参照してください。

## P0: 7版正式サポート品質ゲート

### ISSUE-060: 7版キャラクターシート正式化

**目的**: 7版を保留扱いから正式サポートへ移行し、6版と同じ運用品質で提供する。

**受け入れ条件**
- 7版仕様書が `docs/character_sheet/CHARACTER_SHEET_7TH_EDITION_SPECIFICATION.md` として存在する。
- 7版作成APIがHP/MP/SAN、ダメージボーナス、ビルド、移動率、回避、幸運、職業/趣味技能ポイントを仕様通り返す。
- 7版の作成、編集、詳細、一覧、セッション連携がJavaScriptエラーなしで動作する。
- 6版の既存API/画面/テスト結果に回帰がない。

**検証コマンド**
- `python manage.py test accounts.test_character_sheet_api`
- `python manage.py test accounts.test_character_sheets_integration`
- `npm run test:e2e -- --project=chromium tests/e2e/flows/scenario-session-character.spec.ts`

**完了定義**
- 7版関連の「開発保留」文言がユーザー向け画面、README、ガイドライン、仕様から除去されている。
- 関連テストが成功し、`ISSUES_CLOSED.md` へ移動できる。

## P1: 完成品感とUI品質

### ISSUE-061: 通常画面のテストデータ露出対策

**目的**: E2E/開発データがトップ画面や管理画面の第一印象を壊さないようにする。

**受け入れ条件**
- トップ画面はE2E由来のグループ名を通常表示しない。
- グループ、連携設定、一覧画面は大量データ時も初期表示が読みやすい。
- 開発/デモ/本番データの生成・表示方針がドキュメント化されている。

**検証コマンド**
- `python manage.py test accounts.test_group_features`
- `npm run test:e2e -- --project=chromium tests/e2e/flows/group-management.spec.ts`

**完了定義**
- 実画面確認でトップ、グループ一覧、連携設定に不要なテストデータが目立たない。

### ISSUE-062: ブラウザ標準ダイアログの置き換え

**目的**: `alert()` / `confirm()` 中心の操作感を、サービス内UIへ置き換える。

**受け入れ条件**
- 主要画面の保存、削除、コピー、インポート、外部連携操作はトースト/確認モーダル/インラインエラーを使う。
- 成功・失敗メッセージが画面内に残り、ユーザーが文脈を失わない。
- JavaScript console errorが発生しない。

**検証コマンド**
- `python manage.py test tests.unit.test_js_errors`
- `npm run test:e2e -- --project=chromium tests/e2e/flows/ui-scripts.spec.ts`

**完了定義**
- `templates/` と `static/` のプロダクトコードから不要な `alert(` / `confirm(` が除去されている。

## P2: AWS/運用品質

### ISSUE-056: AWS実環境への適用とGo/No-Go

**目的**: `aws-pre` / `aws-prod` を安全に適用できる状態にする。

**受け入れ条件**
- Terraformはweb/worker/beatをECS Fargateで定義する。
- `ALLOWED_HOSTS`、`SECURE_SSL_REDIRECT`、RDSバックアップ、Redis TLS、Celery broker/result backendが環境別に明示されている。
- `offline_plan=true` の認証不要planが成功する。
- 実AWS apply、DNS、ACM、Secrets、通知先、予算上限、Go/No-Go承認は別運用工程として明確に残る。

**検証コマンド**
- `terraform -chdir=infrastructure/terraform fmt -check -recursive`
- `terraform -chdir=infrastructure/terraform validate`
- `terraform -chdir=infrastructure/terraform plan -refresh=false -input=false -lock=false -var-file=environments/offline-plan.tfvars.example`

**完了定義**
- AWSプレ環境で総合リリーステストを行い、Go/No-Go記録を残せる。

### ISSUE-057: 外部連携の運用強化

**目的**: Google/Discord/Sheets連携を失効・失敗・大規模処理に耐える運用品質へ引き上げる。

**受け入れ条件**
- Google OAuth refresh tokenの失効復旧UIがある。
- Google Calendar双方向同期と競合解決方針が実装/文書化されている。
- Sheetsの大規模インポート/エクスポートはAsyncJobで進捗確認できる。
- Discord配信失敗を管理画面で確認し、手動再送できる。

**検証コマンド**
- `python manage.py test schedules.test_external_integrations`
- `python manage.py test schedules.test_async_jobs`

**完了定義**
- 外部API障害時にユーザー操作がロールバックされず、失敗状態と再試行導線が残る。

## P3: セッション機能拡張

### ISSUE-046: セッション状態スナップショット

**目的**: セッション開始時と終了時の探索者状態を履歴化する。

**受け入れ条件**
- 開始時HP/MP/SANをスナップショット保存できる。
- セッション中のHP/MP/SAN変動、状態異常、一時効果を履歴化できる。
- 終了時に開始との差分を表示できる。

**検証コマンド**
- `python manage.py test schedules.test_character_session_ho_integration`
- `python manage.py test tests.integration.test_character_session_integration`

**完了定義**
- セッション詳細で状態履歴が確認でき、既存のキャラクター現在値と矛盾しない。

### ISSUE-058: 公開募集ページ

**目的**: ゲスト招待URLを横断募集導線へ拡張する。

**受け入れ条件**
- 空き枠検索、募集締切、承認制、参加表明を備えた公開募集ページがある。
- ログインユーザーとゲストのclaim導線が破綻しない。
- 公開範囲と監査ログが残る。

**検証コマンド**
- `python manage.py test schedules.test_group_links_and_guests`
- `npm run test:e2e -- --project=chromium tests/e2e/flows/secret-handout-flow.spec.ts`

**完了定義**
- 公開募集からセッション参加、キャラクター紐付け、通知まで一通り動く。

## Future

- ネイティブモバイルアプリ
- AI分析・推奨
- セッション掲示板
- クイック投票
- 汎用素材ライブラリ
- VTT連携
