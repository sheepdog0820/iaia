# Tableno 本番公開前レビュー結果（2026-06-17、2026-06-18更新）

## 判定

**条件付き Go。** 中核画面と主要APIは到達可能で、限定ベータでは十分運用可能な完成度です。ただし、一般公開前は実AWS本番適用、実OAuth資格情報を使った失敗復旧検証、実機レスポンシブ確認、本番相当データ量での速度確認が必要です。

## 2026-06-17 の修正

- セッション一覧の正規URLを `/api/schedules/sessions/view/` に統一し、旧 `/api/schedules/sessions/web/` は互換リダイレクトとして残しました。
- `GET /api/jobs/` と `POST /api/jobs/<uuid>/retry/` を追加し、ユーザー自身の外部連携ジョブを一覧・再試行できるようにしました。
- 連携設定画面に「連携ジョブ状況」を追加し、Google Calendar / Google Sheets の失敗理由と再試行導線を表示しました。
- Google Sheets export ジョブに `character_ids` を保存し、再試行時に元の出力対象を再現できるようにしました。
- ドキュメントとE2Eの旧セッションURL参照を正規URLへ更新しました。

## 2026-06-18 の修正

- `GET /api/groups/<group_id>/discord-deliveries/` を追加し、グループ作成者または admin メンバーが Discord 配送履歴を確認できるようにしました。
- `POST /api/groups/<group_id>/discord-deliveries/<delivery_id>/retry/` を追加し、失敗した Discord 通知を同一 `DiscordDelivery` レコードのまま再送できるようにしました。
- `/integrations/` に「Discord通知失敗履歴」を追加し、失敗理由、再送ボタン、再送成功/queue不可メッセージを表示しました。
- Discord通知失敗の権限、状態、webhook未設定、通知無効、event_type無効、broker不可の回帰テストを追加しました。
- ViewSet の `queryset`、path parameter 型、SerializerMethodField 型、enum override、schema hook を整理し、OpenAPI生成を警告ゼロ相当にしました。
- `/integrations/` の新規Discord通知失敗UI文言を日本語へ統一し、代表的な文字化け検出テストを追加しました。
- `tests.e2e` を Django test discovery で 0件のPythonテストとして扱えるようにし、`python manage.py test tests` の分割確認を安定化しました。
- 本番Go/No-Go記録、本番スモークテスト、外部連携失敗復旧、レスポンシブ/速度確認のテンプレートを追加しました。
- `/terms/`、`/privacy/`、`/contact/` の公開ページとフッター導線を追加しました。本文は正式レビュー前テンプレートです。
- ローカル確認用およびAWS本番用のOAuth/APIテンプレートをSecretsなしで整理しました。

## 公開前ブロッカー

- **P0: 実AWS適用承認**
  DNS、ACM、Secrets、予算、バックアップ、監視通知先、ロールバック手順の実値承認が必要です。これはコードだけでは完了できません。

- **P1: 外部連携の実運用検証**
  Google系ジョブとDiscord配送失敗の可視化・再試行APIは追加済みです。実Google/Discord資格情報を使った失敗復旧の手動検証は本番前に必要です。

- **P1: 画面品質と性能の実環境確認**
  自動テストは通過していますが、主要画面の実機レスポンシブ確認と本番相当データ量での速度確認は未完了です。

- **P1: 法務文書の正式確定**
  利用規約、プライバシーポリシー、問い合わせページの導線は追加済みです。一般公開前に運営者情報、問い合わせ先、制定日、保存期間、準拠法などの正式レビューが必要です。

## 確認済みコマンド

- `python manage.py check`
- `python manage.py test schedules.test_async_jobs schedules.test_external_integrations`
- `python manage.py test tests.ui.test_ui_navigation tests.unit.test_health_endpoints tests.unit.test_runtime_env`
- `python manage.py test schedules.test_discord_and_release schedules.test_async_jobs schedules.test_external_integrations accounts.test_character_6th_comprehensive tests.unit.test_text_quality tests.unit.test_openapi_schema --noinput`
- `python manage.py test accounts --noinput`
- `python manage.py test schedules --noinput`
- `python manage.py test scenarios --noinput`
- `python manage.py test tests --noinput`
- `python manage.py spectacular --file NUL --validate`
- `node ./node_modules/playwright/cli.js test --project=chromium tests/e2e/flows/integrations.spec.ts`
- `terraform -chdir=infrastructure/terraform fmt -check -recursive`
- `terraform -chdir=infrastructure/terraform validate`
- 一時コピーから `backend.tf` を外した `terraform plan -refresh=false -input=false -lock=false -var-file=environments/aws-prod.tfvars`（56 to add）

## 残リスク

- 実AWS本番環境への `terraform plan/apply`、Secrets登録、DNS、ACM、監視、バックアップ、ロールバック手順の承認が未完了です。
- リポジトリ本体のS3 backendを使う `terraform plan` はAWS資格情報が必要なため、このローカル環境では未完了です。backendを外した一時コピーでのoffline planは成功しています。
- 実Google資格情報を使った refresh token 失効、Google Calendar API障害、Google Sheets大規模入出力の失敗復旧検証が未完了です。
- 実Discord webhook資格情報を使った通知失敗、再送、broker不可時の運用検証が未完了です。
- 主要画面の実機レスポンシブ確認は別途必要です。今回の確認はDjangoテストとPlaywright対象更新が中心です。
- 本番相当データ量での一覧画面・連携画面の速度確認は未完了です。
- 利用規約、プライバシーポリシー、問い合わせ先はテンプレート段階です。一般公開前に正式レビューと運営者実値の確定が必要です。
