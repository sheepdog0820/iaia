# Tableno 未完了ロードマップ

最終更新: 2026-06-17

このファイルは、本番投入前に判断または実装が必要な未完了タスクだけを管理します。完了済みの本番完成化作業は `ISSUES_CLOSED.md`、現行仕様は `docs/CURRENT_WEBAPP_FEATURES.md`、実装済み機能とリリース要件の一覧は `docs/IMPLEMENTED_FEATURES_AND_RELEASE_REQUIREMENTS_2026-06-17.md` を参照してください。

## 優先度定義

- **P0**: 一般公開前に必須。未完了なら本番リリース不可。
- **P1**: リリース前に強く推奨。限定ベータでは許容できるが、一般公開前に潰すべき。
- **Future**: 初回本番リリース後の拡張候補。

## P0: 本番リリース前 Go/No-Go

### ISSUE-070: 本番環境への最終適用承認

**目的**: リポジトリ内で検証済みのAWS構成を、実AWS環境へ適用する前に運用承認する。

**2026-06-18 進捗**
- [x] Secrets実値を含めない本番Go/No-Go記録テンプレートを追加した。
- [x] `aws-pre` / `aws-prod` 差分、DNS、ACM、Secrets、予算、バックアップ、監視通知先、apply担当者、実施時間帯、ロールバック判断基準の記録欄を用意した。

**未完了タスク**
- [ ] `aws-pre` と `aws-prod` の差分意図を運用担当者が実値で確認する。
- [ ] DNS、ACM、Secrets、予算、バックアップ保持期間、監視通知先を実値で承認する。
- [ ] `terraform plan -refresh=false` ではなく、実AWS状態を参照したplanを別工程で確認する。
- [ ] apply担当者、実施時間帯、ロールバック判断基準を決める。
- [ ] メンテナンス告知方針を決める。
- [ ] Go/No-Go記録を残す。

**受け入れ条件**
- 実AWS applyの実施可否が明文化されている。
- Secrets実値をリポジトリへコミットしない運用になっている。
- ロールバック判断者と手順が明確になっている。

**検証コマンド**
- `terraform -chdir=infrastructure/terraform fmt -check -recursive`
- `terraform -chdir=infrastructure/terraform validate`
- `terraform -chdir=infrastructure/terraform plan -input=false -lock=false -var-file=environments/aws-prod.tfvars`

**コミット単位**
- 実値を含まない運用手順・Go/No-Go記録のみ。

### ISSUE-073: 本番環境設定とスモークテスト

**目的**: 本番環境へデプロイしたアプリが、実ドメイン・実OAuth設定・実DBで最低限の主要導線を動作できることを確認する。

**2026-06-18 進捗**
- [x] 本番スモークテスト手順を追加し、ヘルスチェック、ログイン、OAuth callback、キャラクター作成、セッション作成、外部連携設定、CloudWatch確認を記録できるようにした。
- [x] Google、Discord、Xのローカル確認用およびAWS本番用OAuth/APIテンプレートをSecretsなしで追加した。

**未完了タスク**
- [ ] 本番DB、ストレージ、ドメイン、TLS証明書を確定する。
- [ ] Google、Discord、Twitter/Xの本番OAuth callback URLを設定する。
- [ ] 本番用環境変数とSecretsを登録する。
- [ ] 管理者アカウントと初期運用権限を整理する。
- [ ] 本番ドメインでログイン、キャラクター作成、セッション作成、外部連携設定を確認する。
- [ ] 本番環境のヘルスチェックURLを監視対象に登録する。

**受け入れ条件**
- 本番ドメインで主要画面へアクセスできる。
- 本番OAuth callbackが成功する。
- 主要CRUD操作が本番DBに保存される。
- 本番ヘルスチェックが成功する。

**検証コマンド**
- `python manage.py check --deploy`
- 本番URLでの手動スモークテスト

**コミット単位**
- 本番環境向け設定のドキュメント
- スモークテスト手順

### ISSUE-074: 本番運用手順・監視・法務導線の確定

**目的**: 一般公開後に障害、問い合わせ、データ保護の最低限の運用ができる状態にする。

**2026-06-18 進捗**
- [x] バックアップ、リストア、監視通知テスト、ロールバック検証の記録欄を障害対応Runbookへ追加した。
- [x] 障害時の一次対応手順は `docs/runbooks/AWS_INCIDENT_RESPONSE.md` として整備済みであることを確認した。
- [x] `/terms/`、`/privacy/`、`/contact/` の公開導線とフッターリンクを追加した。
- [x] 利用規約、プライバシーポリシー、問い合わせページを正式レビュー前テンプレートとして追加した。

**未完了タスク**
- [ ] 実AWS環境でバックアップ取得手順を確定する。
- [ ] 実AWS環境でリストア手順を検証する。
- [ ] 実AWS環境で監視、アラート、ログ確認手順を確定する。
- [ ] 実AWS環境でロールバック手順を検証する。
- [ ] 利用規約を正式レビューし、運営者名、制定日、準拠法を確定する。
- [ ] プライバシーポリシーを正式レビューし、個人情報管理者、保存期間、問い合わせ先を確定する。
- [ ] 問い合わせ先メールアドレスまたはフォームURLを確定する。

**受け入れ条件**
- DBリストアを手順に沿って再現できる。
- 監視アラートの通知先が実運用先になっている。
- 障害時に確認するログとロールバック手順が明文化されている。
- ユーザーが利用規約、プライバシーポリシー、問い合わせ先を確認できる。

**検証コマンド**
- バックアップ/リストア手順の手動検証
- 監視通知のテスト送信

**コミット単位**
- 運用手順書
- 公開ページまたはフッター導線

## P1: リリース前に強く推奨

### ISSUE-071: 外部連携の失敗観測と再試行運用

**目的**: Google Calendar/Sheets、Discord、ゲスト招待、グループ連携の失敗を運用者が追跡し、ユーザーが復旧できる状態にする。

**2026-06-17 進捗**
- [x] `GET /api/jobs/` と `POST /api/jobs/<uuid>/retry/` を追加し、Google Calendar同期とGoogle Sheets出力の失敗ジョブをユーザーが再試行できるようにした。
- [x] 連携設定画面に「連携ジョブ状況」を追加し、失敗理由と再試行導線を表示した。
- [x] セッション一覧の正規URLを `/api/schedules/sessions/view/` に統一し、旧 `/api/schedules/sessions/web/` は互換リダイレクトにした。

**2026-06-18 進捗**
- [x] Discord通知失敗の一覧API、失敗理由表示、同一 `DiscordDelivery` レコードでの再送APIを追加した。
- [x] 連携設定画面に「Discord通知失敗履歴」を追加し、失敗行の再送導線と broker 利用不可時のメッセージを表示した。
- [x] Discord通知失敗の権限、状態、webhook未設定、通知無効、event_type無効、broker不可の回帰テストを追加した。
- [x] 外部連携失敗復旧Runbookを追加し、Google/Discord/broker不可の確認・再試行・記録方法を整理した。

**未完了タスク**
- [ ] Google OAuth refresh token失効時、連携設定画面から再連携導線に到達できることを確認する。
- [ ] Google Calendar API障害時に、失敗状態と再試行導線が残ることを確認する。
- [ ] Google Sheets大規模インポート/エクスポートで進捗と失敗理由を確認する。
- [ ] 実Google資格情報を使った本番相当の失敗復旧検証を行う。
- [ ] 実Discord資格情報を使った本番相当の失敗復旧検証を行う。
- [ ] 外部API障害時に、画面操作がロールバックされずユーザーに復旧手段が残ることを確認する。

**受け入れ条件**
- 外部連携の失敗、再試行、復旧導線がユーザー向け画面と運用ログで確認できる。
- 実サービスの資格情報を使った失敗復旧検証結果が残っている。

**検証コマンド**
- `python manage.py test schedules.test_external_integrations`
- `python manage.py test schedules.test_async_jobs`
- `npm run test:e2e -- --project=chromium tests/e2e/flows/ui-scripts.spec.ts`

**コミット単位**
- 連携失敗検証結果
- 運用手順
- 必要に応じた追加テスト

### ISSUE-075: Discord通知失敗の可視化と再送導線

**目的**: Discord通知の配信失敗を、管理者またはユーザーが確認し、必要に応じて再送できる状態にする。

**2026-06-18 進捗**
- [x] `GET /api/groups/<group_id>/discord-deliveries/` を追加し、グループ作成者または admin メンバーが最新50件の配送履歴を確認できるようにした。
- [x] `status` と `event_type` の絞り込み、`payload` と `idempotency_key` を含む配送履歴レスポンスを追加した。
- [x] `POST /api/groups/<group_id>/discord-deliveries/<delivery_id>/retry/` を追加し、`failed` の配送だけを同一レコードのまま `pending` に戻して再送できるようにした。
- [x] webhook未設定、Discord設定無効、対象event_type無効、broker利用不可のレスポンスとテストを追加した。
- [x] `/integrations/` に Discord通知失敗履歴、失敗理由、再送ボタン、再送成功/queue不可メッセージを追加した。
- [x] Discord通知失敗時の運用手順を外部連携失敗復旧Runbookへ統合した。

**未完了タスク**
- [ ] 実Discord webhook資格情報を使い、本番相当の失敗復旧検証結果を残す。

**受け入れ条件**
- [x] Discord配信失敗を画面またはAPIで確認できる。
- [x] 失敗したDiscord通知を手動再送できる。
- [x] 再送できない失敗は理由が表示される。
- [ ] 実Discord資格情報で失敗復旧が検証されている。

**検証コマンド**
- `python manage.py test schedules.test_discord_and_release --noinput`
- `node ./node_modules/playwright/cli.js test --project=chromium tests/e2e/flows/integrations.spec.ts`

**コミット単位**
- 2026-06-18: `24b3ca0 Add Discord delivery retry visibility and clean OpenAPI schema`

### ISSUE-076: 公開APIスキーマ警告と主要画面品質の棚卸し

**目的**: 一般公開前に、公開APIの仕様不整合と主要画面の表示崩れ・性能リスクを潰す。

**2026-06-18 進捗**
- [x] ViewSet の `queryset`、path parameter 型、SerializerMethodField 型、enum override、schema hook を整理し、OpenAPI生成を警告ゼロ相当にした。
- [x] `python manage.py spectacular --file NUL --validate` が終了コード0で通ることを確認した。
- [x] Discord通知失敗APIに request/response serializer と `@extend_schema` を追加し、新規API由来のschema警告を出さないようにした。
- [x] `/integrations/` の Discord通知失敗UI文言を日本語へ統一し、代表的な文字化け検出の回帰テストを追加した。
- [x] `accounts/test_character_6th_comprehensive.py` の不自然な文字化けテストデータを修正した。
- [x] 主要画面のレスポンシブ確認チェックリストと本番相当データ量の速度確認手順を追加した。

**未完了タスク**
- [ ] 主要画面のデスクトップ表示を確認する。
- [ ] 主要画面のモバイル表示を確認する。
- [ ] 本番相当データ量で一覧画面の表示速度を確認する。

**受け入れ条件**
- [x] 公開APIに影響するスキーマ警告が残っていない。
- [ ] 主要画面で致命的な表示崩れがない。
- [ ] 本番相当データ量で実用上問題のない表示速度である。

**検証コマンド**
- `python manage.py spectacular --file NUL --validate`
- `python manage.py test tests.unit.test_openapi_schema tests.unit.test_text_quality --noinput`
- E2Eまたは手動のレスポンシブ表示確認

**コミット単位**
- 2026-06-18: `24b3ca0 Add Discord delivery retry visibility and clean OpenAPI schema`
- 実機レスポンシブ確認結果
- 本番相当データ量の速度確認結果

## Future

- ネイティブモバイルアプリ
- AI分析・推薦
- セッション掲示板
- クイック投票
- 汎用素材ライブラリ
- VTT連携
