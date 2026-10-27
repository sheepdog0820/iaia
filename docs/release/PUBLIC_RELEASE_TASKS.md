# 公開前・運用開始後タスク整理

最終更新: 2026-10-28

## 現在の公開対象と判定

有料プランと外部連携を含む正式公開を目指す。正式公開の必須条件は未完了で、現在の判定はNo-Go。下段の旧β計画にある機能の先送りや過去の成功件数は、現在の公開条件や最新候補の検証結果として使用しない。

- 目標と公開範囲: [正式公開の目標](FORMAL_RELEASE_GOAL.md)
- 条件ごとの実装・証拠・未確認事項: [正式公開の受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)
- 確定した無料・有料の範囲: [料金・機能の判断記録](FORMAL_RELEASE_PLAN_DECISIONS.md)
- 最新の候補と承認対象: [10月28日のリリース候補整理](RELEASE_CANDIDATE_2026-10-28.md)

キャラクター・セッション管理、シナリオの作成・編集、CCFOLIAインポート、作成済みセッションの関連シナリオ変更は無料。所有者・GM・閲覧等の権限は引き続き適用する。キャラクター画像は無料・有料共通で1キャラクター5枚までとし、既存の超過画像は維持する。画像の背景透過のみ有料機能とする。料金は月額480円・年額4,800円。キャラクターの総枚数制限とシナリオ画像のアップロード制限は別に扱う。

## 現在の残タスク

| 領域 | 必要な作業 | 状態と参照先 |
| --- | --- | --- |
| 候補統合・既知不具合 | 最新mainを基点に復旧・作成入口、技能表示/統一、7版の幸運・よみがなを修正・検証 | [候補整理](RELEASE_CANDIDATE_2026-10-28.md)。元の未コミット作業は保持し、後続の大きな変更群は依存関係を整理して継続 |
| Stripe | AWS上の購入・戻り画面・Webhook・権限・解約・メール、残る異常系と本番Priceを最終照合 | 登録保留は解除済み。主要な実サンドボックス検証は[再開タスクの完了記録](STRIPE_CONNECTION_PENDING.md)に保持。有料必須ゲートと実AWSの記録は未完了 |
| 外部連携 | Google・Discord・Xの実認可、Calendar/Sheets、Discord通知、ICS/CCFOLIAを実サービス側で確認 | I01〜I07。Google認可保存は成功済み。共有Sheet予約前の認可・上限、結果不明からの回復、常設配送と実出力は残る。宛先・内容・権限変更は承認範囲を確認 |
| 性能 | 登録100人・同時10人、通常操作p95が3秒以内・予期しないエラー0を実AWSで実証 | 基準は決定済み。[現行相当の画像追加p95は6.957秒](CHARACTER_IMAGE_PERFORMANCE_BB61B0E6_2026-09-19.md)で未達。増強案の隔離成功を実AWSの合格へ拡張しない |
| セキュリティ | Python依存更新、OS監査の適用条件、実S3/CDNの迂回防止・権限失効を確認 | [10月28日の監査](RELEASE_CANDIDATE_2026-10-28.md): CIは10パッケージ68指摘で不合格、通常イメージのOS監査は104指摘。旧指摘数やローカル機能試験の成功を現在の安全性・実配備の保護へ拡張しない |
| 復元・切り戻し | DB/S3整合、アプリ切替、RPO24時間/RTO4時間、後続世代を消さない切り戻しを実証 | [実RDSの限定復元](RDS_RESTORE_RESULT_2026-09-08.md)は成功済み。サービス全体の復旧は未完了。追加の実データ操作や資源作成は別の承認対象 |
| 監視・実行基盤 | worker/beat、監視通知、問い合わせの配送を実証 | 受け入れ条件O01。新規リソース・継続費用・通知送信には対象範囲の承認が必要 |
| 公開に必要な判断 | 保存・削除期間、背景透過の保持条件、開示窓口の受信/返信、税務対応、公開日、費用上限を確認 | O04。料金・無料範囲・画像5枚、個人事業者の請求開示方式と返金条件は決定済み。実情報は非公開で保管する |
| 配備・CI | 最終候補SHA・通常配布物・CIを照合し、共有環境で移行・主要操作・復旧を確認 | 定義55とmainに差分あり。0068の実データ移行、mainマージ、AWS反映は[具体案](RELEASE_CANDIDATE_2026-10-28.md)に基づく承認対象 |

課金を含む正式公開の判定には、実証跡と `billing_release_gate --require-paid-checkout --verification-record <検証記録>` を使用する。Checkout無効の通常CI成功を有料正式公開の合格条件に読み替えない。

## 過去のβ計画・検証履歴

以下は2026-08-23時点の計画と過去の証拠を保持した履歴。旧画像上限、βの先送り範囲、Docker未確認・CI未確認等の状態は当時の記録であり、現在の仕様・作業指示ではない。最新状態は上段の受け入れ条件と候補別証跡を参照する。

<details>
<summary>旧β計画と検証履歴を表示（現行の公開条件には使用しない）</summary>


## 公開前に潰すべき課題

| 優先 | 課題 | 状態 | 次の確認 |
| --- | --- | --- | --- |
| S | README認証情報削除 | 対応済み。固定テストパスワードの再混入を `tests.unit.test_release_documentation` で検知 | 公開前にドキュメント検索を再実行 |
| S | Djangoバージョン統一 | Django 5.2.15へ統一済み | 全テスト再実行 |
| S | 権限テスト | キャラシ、HO、GMメモの他人閲覧不可を対象テストで確認済み | 公開前に全権限テストを再実行 |
| A | OAuth設定確認 | ローカルでは設定状態表示のみE2E化済み | Stg/ProdのGoogle、Discord、X callbackを実認可で確認 |
| A | 画像アップロード負荷試験 | 1MB/5MB/上限超過、jpg/png/gifを自動テスト化。ローカルHTTP負荷プローブ実行済み | Stg/Prod相当で `tests/performance/image_upload_load.py` を実行 |
| A | バックアップ手順作成 | `docs/infrastructure/backup.md` 作成済み | 本番AWS値で復旧リハーサル |

### OAuth Stg / Prod確認

実Client ID、Secret、callbackの実値はリポジトリからは確認できません。各Providerの管理画面で次を確認してください。

| Provider | Stg callback | Prod callback | 状態 |
| --- | --- | --- | --- |
| Google | `https://stg.tableno.jp/accounts/google/login/callback/` | `https://tableno.jp/accounts/google/login/callback/` | 未確認 |
| Discord | `https://stg.tableno.jp/accounts/discord/login/callback/` | `https://tableno.jp/accounts/discord/login/callback/` | 未確認 |
| X | `https://stg.tableno.jp/accounts/twitter_oauth2/login/callback/` | `https://tableno.jp/accounts/twitter_oauth2/login/callback/` | 未確認 |

### 画像アップロード負荷試験

実HTTPでの同時アップロード確認は以下を使います。

```bash
python tests/performance/image_upload_load.py \
  --base-url http://127.0.0.1:8000 \
  --dev-login admin \
  --concurrency 4 \
  --requests-per-target 9
```

Stg/Prod相当:

```bash
TABLENO_USERNAME=<operator-user> \
TABLENO_PASSWORD=<secret> \
python tests/performance/image_upload_load.py \
  --base-url https://stg.tableno.jp \
  --concurrency 8 \
  --requests-per-target 9
```

| 対象 | サイズ | 形式 | 期待結果 |
| --- | --- | --- | --- |
| キャラ画像 | 1MB | jpg/png/gif | 成功 |
| キャラ画像 | 5MB | jpg/png/gif | 成功または上限境界の明確なエラー |
| キャラ画像 | 上限超過 | jpg/png/gif | 400系、エラーメッセージ表示 |
| シナリオ画像 | 1MB | jpg/png/gif | 成功 |
| シナリオ画像 | 5MB | jpg/png/gif | 成功または上限境界の明確なエラー |
| シナリオ画像 | 上限超過 | jpg/png/gif | 400系、エラーメッセージ表示 |
| 複数枚登録 | 通常2枚 / プレミアム10枚 | jpg/png/gif混在 | 各上限内で成功、上限超過や不正混入時は明確なエラー |
| 大量アクセス | 同時アップロード | jpg/png/gif混在 | worker、DB、S3、Redisが枯渇しない |

## 運用開始後の課題

| 優先 | 課題 | 方針 |
| --- | --- | --- |
| B | 利用ログ収集 | ユーザー数、セッション作成数、キャラシ作成数、離脱率を集計 |
| B | フィードバック導線 | 不具合報告、要望フォームを設置 |
| B | 通知機能改善 | Discord通知とメール通知の運用要件を整理 |

## 将来的な改善

| 優先 | 課題 | 方針 |
| --- | --- | --- |
| C | モデル分割 | 巨大な `CharacterSheet` を core/status/profile などへ段階分割 |
| C | API整備 | ココフォリア、Discord Bot、外部連携向けREST APIを整理 |
| C | 性能改善 | 利用者50人超を目安にRedisキャッシュ、DBインデックス、クエリ最適化 |

## β公開前の重点確認

- Playwright E2E: Chromium / Firefox / WebKit の78ケースで、新規登録、メールログイン、OAuth設定状態表示、セッション作成/編集/削除、HO作成/配布/閲覧制御、キャラシ作成/編集、CCFOLIA JSON出力を自動確認済み。
- 権限: 作成者の `owner` と卓内の `gm` / `player` を分離し、GM/PL兼任を許可。`owner` だけでは秘匿HO、GMメモ、GM向けシナリオ情報を扱えないことを対象テストで確認済み。
- モバイルUI: PlaywrightでiPhone/Android相当のセッション一覧とキャラシ編集を自動確認済み。実機確認は公開前に実施。
- エラーページ: 404、403、500のテンプレートを整備済み。表示と導線は公開前に手動確認。
- 外部依存: OAuth実認可、Stg/Prodでの画像負荷、実機モバイル確認はローカルだけでは完了不可。

## β公開スコープ

β公開では「迷わず使える中核」を優先し、外部連携や高度な自動化は検証済みの範囲だけを表示・運用します。

### β公開で残す中核

| 機能 | β公開での扱い | Go/No-Go確認 |
| --- | --- | --- |
| ログイン | 必須 | 通常ログイン、ログアウト、パスワードリセットメール送信、mandatory email verification、未確認メールへのリセットメール抑止、退会導線と有効なStripe購読中の削除ブロックを `accounts.test_authentication`、Google/Discord OAuth verified email重複時の既存ユーザー再利用を `accounts.test_api_auth_google` / `accounts.test_api_auth_discord`、X API認証を `accounts.test_api_auth_twitter` で確認 |
| グループ | 必須 | グループ外ユーザーが非公開グループ/グループ卓を見られないこと |
| セッション管理 | 必須 | 作成、編集、削除、参加者管理、カレンダー表示、作成者とGM/PLの独立した複数ロールを確認 |
| Character sheets | Required | CoC 6版/7版のみ。private/group/link/public/allowed users の直URLアクセスを確認。`link` は公開ID URLでは404、ShareLinkでのみ閲覧可能。fixed character sharing tests と `accounts.tests.BasicAccountsTestCase.test_access_scope_private_update_closes_fixed_share_view` で確認 |
| 秘匿HO | 必須 | GMは全件、割当PLは自分のHOのみ、公開HOは参加者全員、添付も同じ権限で確認 |
| 画像アップロード | 必須 | キャラシ/セッション/シナリオ画像の保存、表示、キャラシ画像の通常2枚/プレミアム10枚制限、上限超過時の明確なエラー |
| 最低限のプレミアム判定 | 条件付き | Stripe CheckoutはISSUE-077完了まで非表示またはテストモード限定。運営コード/手動付与は監査ログ付きで確認 |

### βでは後回しにする機能

| 機能 | βでの扱い | 理由 |
| --- | --- | --- |
| Google Sheets連携 | 後回し可 | コア体験ではない。失敗復旧と権限境界の実地確認後に拡張 |
| Google Calendar同期 | 後回し可 | 外部OAuth/同期失敗時の運用負荷が高い |
| Discord高度通知 | 後回し可 | Webhook設定、再送、失敗監視の運用確認が必要 |
| WebSocket通知 | 後回し可 | ポーリングフォールバックがあるためβ初期は必須ではない |
| 複雑な自動公開条件 | 後回し可 | 秘匿HOの手動公開と単純条件を優先 |
| 高度な統計/年間プレイ時間集計 | 後回し可 | β初期の価値検証には不要 |

## 耐震補強チェックリスト

| 項目 | 状態 | 証跡/確認コマンド |
| --- | --- | --- |
| 危険ファイルのGit管理除外 | ローカル対応済み | `cookies.txt`, `node_modules/`, `venv311/` を削除対象化。`.env*.example` 以外の危険パスは `git ls-files` 確認で0件、`tests.unit.test_repository_hygiene` で自動確認 |
| `.gitignore` 再確認 | 対応済み | `.env*` は除外し `.env*.example` のみ追跡可。`node_modules/`, `venv*/`, `cookies.txt`, `media/`, `staticfiles/`, `logs/`, `test-results/`, `playwright-report/` |
| Python/Docker統一 | 対応済み | README/AGENTS/CLAUDE/SPECIFICATION は Python 3.11+、`.python-version` は 3.11、Dockerfile は `python:3.11-slim` |
| CI最低ライン | 対応済み | `.github/workflows/django-ci.yml` で Python 3.11, `manage.py check`, Docker Compose config check, production deploy check, `billing_release_gate`, `manage.py test --noinput` |
| 本番認証設定 | 対応済み | production settings で `ACCOUNT_EMAIL_VERIFICATION=mandatory`, `ACCOUNT_PREVENT_ENUMERATION=True`, `ACCOUNT_FORMS.reset_password=accounts.forms.CustomPasswordResetForm`。独自signup/loginでも未確認メールを拒否し、未確認メールへのパスワードリセット送信も抑止 |
| 公開プロフィール/API情報量 | 対応済み | Web profile は共有グループ必須かつメール非表示。通常 `/api/accounts/users/<id>/` は本人以外404。グループ/招待/フレンド詳細は公開用ユーザー情報のみ |
| 共有リンクの情報量 | 対応済み | `accounts.test_share_links` で ShareLink 発行/失効/期限切れ、`link` と `public` の分離、セッション/キャラクター/シナリオ/統計共有から秘匿HO、GMメモ、所有者/ユーザーID/メール/claim情報が出ないことを確認 |
| デプロイ起動処理分離 | 対応済み | Stg/Prodは `migrate` と `collectstatic` を `up` 前に明示実行。entrypointはlocal/明示指定時のみ実行し、`tests.unit.test_docker_entrypoint` で `exec daphne`、自動migration条件、Compose `ENV_FILE` 分離を確認 |
| 非公開キャラシ直URL | 対応済み | `accounts.tests.BasicAccountsTestCase.test_fixed_character_share_view_requires_shareable_scope` と `accounts.tests.BasicAccountsTestCase.test_access_scope_private_update_closes_fixed_share_view`; group member character API uses `access_scope=public` via `accounts.test_group_features.GroupMemberCharactersAPITestCase.test_member_characters_only_include_public_scope` |
| 秘匿HO/API/添付権限 | 対応済み | `schedules.test_handout_permissions` と `schedules.test_session_visibility` で API/detail/attachment/public share URL/セッション詳細 `handouts_detail` を確認。秘匿HO添付の直URL DELETEは割当外ユーザーへ404で存在秘匿し、閲覧可能だが削除権限がない参加者は403。private/group卓の `share_token` URL は404; stale or misdirected secret handout notifications are omitted from notification API list/detail/mark_read/unread_count/mark_all_read; scenario public API omits secret handout templates and creator private fields via `scenarios.test_scenarios.ScenarioAPITestCase.test_scenario_public_view_mode_is_readable_without_login` |
| Guest invitation management | 対応済み | `schedules.test_group_links_and_guests` で group admin create/revoke、outsider 403、期限切れ/失効済み招待URLが410かつセッション詳細を返さないこと、参加枠claimは `claim_token` 必須であることを `schedules.test_group_links_and_guests.GuestInvitationClaimTestCase.test_guest_claim_requires_invitation_token` で確認 |
| Stripe課金事故防止 | ローカル対応済み | `accounts.test_billing`。`STRIPE_CHECKOUT_ENABLED` は通常settings/production/.env examplesとも既定Falseで、ヘルパー/管理コマンドの設定欠落時フォールバックもFalse。明示True時のみCheckoutを出す。Checkout/Customer PortalのStripe一時障害時は汎用503で例外詳細を返さない。外部Stripe test-mode event ID確認はISSUE-077として未完。有効なStripe購読中のアカウント削除は課金管理ページへ誘導してブロック |
| Docker実ビルド | 要再確認 | `docker compose --env-file .env.compose.example config --quiet` と `docker compose --env-file .env.compose.example -f docker-compose.mysql.yml config --quiet` は成功。過去に `docker compose build --no-cache` 成功、build context約117KB。entrypoint修正後の実ビルドはDocker daemon未起動で未完 |
| 全体テスト完走 | ローカル確認済み | ローカルvenv（Python 3.10.6）で `pytest -q` は1518件成功、失敗・スキップ0件、subtests 179件成功。PlaywrightはChromium / Firefox / WebKitの78ケースを確認。CIはPython 3.11で `manage.py test --noinput` と3ブラウザE2Eを実行 |

## β公開 Go/No-Go

| 判定項目 | Go条件 | 現状 |
| --- | --- | --- |
| README通りにローカル起動 | 新規環境で `migrate`, `runserver`, ログインまで成功 | 既存ローカル環境で Python 3.11.1、`manage.py check`、`migrate --check`、`runserver --noreload`、`/health/live/`, `/health/ready/`, `/accounts/login/` 200 を再確認済み。新規環境での再現確認は未完 |
| Docker起動 | `docker compose build --no-cache` と `docker compose up` が成功 | 過去に `/health/live/` と `/health/ready/` 200を確認。entrypoint修正後の再確認はDocker daemon未起動で未完 |
| CI | GitHub Actionsがmain/PRで成功 | ワークフロー追加済み、ローカル同等コマンドは確認済み。リモート実行は未確認。CI billing_release_gate runs with STRIPE_CHECKOUT_ENABLED=False |
| production deploy check | production settingsで `check --deploy` 成功 | ローカル確認済み。`tests.unit.test_production_settings` で CI 相当 env の `manage.py check --deploy` を自動確認 |
| 秘匿HO漏れなし | 直URL/API/添付で割当外ユーザーが見られない | 対象テスト済み |
| 非公開キャラシ漏れなし | API detail/public URL/画面URLでprivateが見えない | 対象テスト済み |
| グループ外卓漏れなし | group/private卓を外部ユーザーが見られない | `pytest -q` の全1518件と権限対象テストで再確認済み |
| Stripe状態ずれなし | Checkout/Webhook/返金/異議/手動/プロモコードが監査ログ付きで確認済み | ローカルテスト済み。外部Stripe確認は未完 |
| エラー監視 | Sentry/CloudWatch等の通知先が設定済み | `SENTRY_DSN` 対応、CloudWatch/SNS Runbook と Terraform はあり。実SNS購読/通知試験は未完 |
| DBバックアップ | バックアップ/復旧手順が実環境で確認済み | `docs/infrastructure/backup.md`, `docs/runbooks/AWS_DATABASE_MIGRATION.md`, RDS backup retention設定あり。実RDS復旧リハーサルは未完 |
| 法務/問い合わせ | 利用規約、プライバシーポリシー、特商法表示、問い合わせ先が本番実値かつ正式レビュー済み | `/terms/`, `/privacy/`, `/contact/`, `/commercial-disclosure/` と `tests.unit.test_public_legal_pages`, `tests.unit.test_billing_legal_pages`, `billing_preflight --strict` はローカル確認済み。正式法務レビュー、運営者実値、問い合わせ先実配送確認は未完 |
| 管理者確認 | ユーザー/課金状態/監査ログを管理画面で確認可能 | `accounts.test_billing` の `BillingAdminTestCase` でユーザー/課金状態/監査ログの表示・フィルタ・操作をローカル確認済み。実aws-pre目視確認は未完 |

</details>
