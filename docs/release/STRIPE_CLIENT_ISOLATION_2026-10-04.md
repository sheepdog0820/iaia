# Stripeクライアント設定の分離（2026-10-04）

## 対象と変更

先行検証記録 `3804dbc55a2ccf42e0e232f7da5b8c4402073fbf` から専用ブランチ `codex/stripe-client-isolation-20261004` で修正した。Stripeモジュールの `api_key` / `api_version` を要求ごとに書き換える構成を、設定を保持する `StripeClient` に移行する。現行SDK 15.5.1・既定API版 `2026-02-25.clover` を維持し、SDK/API版・ロックファイル・DBスキーマ・料金・税設定は変更しない。最新SDK/APIへの更新やRAKへの切替は別の検証・承認対象である。

[Stripe公式SDK README](https://github.com/stripe/stripe-python)と[公式StripeClient移行ガイド](https://github.com/stripe/stripe-python/wiki/Migration-guide-for-v8-(StripeClient))、インストール済み15.5.1の実装で、`client.v1`、`params` / `options`、`products.update`、`client.construct_event` の署名を照合した。既存Stripe CLI 1.42.14は現行のドキュメント取得機能に足りないため、CLI更新・認証変更はせず公式SDK一次資料を使用した。

- `accounts/billing.py`: 未設定キーの拒否を維持してクライアントを生成。顧客/購入/Portal/契約/Invoice/Charge/Disputeをクライアントのサービスへ移行。保存済みintentのパラメーターは `params`、冪等キーは `options` に分離し、23時間の再作成防止・元プロフィール/キー/所有者照合・共有行ロックを維持する。
- `accounts/billing_deletion.py`: Checkoutの一覧/失効と最新契約照合を移行。退会拒否条件・行ロック・所有者検証は変更しない。
- `accounts/views/billing_views.py`: クライアントの署名検証と契約取得を使用。Webhook署名拒否・再試行/重複扱い・レスポンス仕様は維持する。
- 管理コマンド3件: 読み取りチェック、開発Price作成、オフラインWebhookスモーク内のmockを新しいサービス構造へ移行。開発Priceコマンドのtest-key/live-response拒否・月480円/年4800円は維持し、実Stripeでコマンドを実行していない。remote-checkファイルの既存BOMはUTF-8検査基準に合わせて除去した。
- 既存テスト17ファイル: SDK境界のmockと引数参照だけを更新。期待値・拒否条件・監査数・繰り返し回数・競合試験を維持した。
- 新規2モジュール14テスト: 実SDKをメモリー内transportへ接続してシリアライズとアプリ経路を確認。CIの既存PostgreSQLジョブにも必須対象として追加し、時間予算・合格基準・デプロイ設定は変更しない。

利用者向け画面/文言・APIルートの変更はない。共有設定を書き換えず、同時要求も各クライアント固有の資格情報/API版で送ることを目的とする。外部サービスの成功や実決済を、このローカル検証から保証しない。

## テストファーストと最終結果

実装前の新規7テストは1失敗・5エラー・1成功、終了1（0.021秒）。旧モジュール返却、`.v1` / `construct_event` 不在、設定分離不足を再現した。実装後の同7件は成功、終了0。最初の広域288件はスモークコマンド内の旧mockが原因で1エラー・6省略、終了1となった。mock2箇所を修正し、後続で並行要求とアプリSDK試験を追加した。初回失敗を成功件数に加算しない。REDの独立ログは保存していない。

| 最終確認 | 結果 |
| --- | --- |
| PostgreSQL 18.3・関連458件 | 全成功・省略0、65.679秒、終了0 |
| SQLite・先行広域458件 | 成功419・行ロック等39省略、75.354秒、終了0 |
| 最新テストを含むSQLiteカバレッジ295件 | 成功289・行ロック6省略、47.033秒、終了0 |
| 新規実SDKテスト2モジュール | 文228/分岐8すべて実行、100% |
| `get_stripe` / `execute_stripe_creation` | 文7/分岐4すべて実行、100% |
| 本体6ファイルの追加/置換された実行可能行 | 33行すべて実行、未実行0 |
| 既存23 Pythonファイルの構造照合 | 意図したfactory変更を除き、SDK名前空間/引数境界を逆変換したASTが変更前と一致 |
| Black / isort / flake8 | 変更25 Pythonファイルで成功 |
| Bandit・本体6ファイルと新規テスト2ファイル | 指摘0・終了0 |
| Bandit・変更25ファイル全体 | 既存テストの合成資格情報にLOW B106が6件・終了1、全体合格とはしない |
| 隔離SQLiteのDjango check / makemigrations dry-run | 問題0 / 変更なし、終了0 |

広域SQLite結果は最後のテスト専用強化（patcher単位のcleanup、401後の回復再試行）の前であり、最新の確認はPostgreSQL458件とSQLite295件である。本体コードは広域成功から変更していない。上記カバレッジは実行対象を限定した計測で、本体全体の既存未通過分岐は除外していない。対象8モジュール全体は文1275中52未実行・分岐414、合計表示93%。今回の33行実行や新規テスト100%を、全体100%や全既存経路の成功へ拡張しない。

全体Banditの6件は既存の `test_paid_feature_lifecycle` とDispute/Event/Invoiceのテストfixtureで、SDK境界変更前からある値を維持している。既存nosecへの警告も出力された。新規fixtureにだけ理由付きnosecを付け、実資格情報ではなくtransportのメモリー応答/HMACに閉じていることを確認した。本体の指摘を抑制していない。

## 実SDKで確認した範囲

API呼び出しそのものをMockにせず、15.5.1の実HTTPClientインターフェースに外部I/O不能なメモリーtransportを接続した。応答の使い切りは失敗する。以下を新規14件内で確認した。

- 2クライアントを生成した後/同時実行時のAuthorization・Stripe-Version分離、モジュール設定の不変、キー未設定時の生成/HTTP拒否。
- 作成要求の冪等ヘッダーと元intent不変、12種類のサービス操作のHTTP method/path、5種類の一覧サービスの2ページ取得とカーソル/設定保持。
- 実HMAC署名の受理・誤署名拒否、Webhook検証でHTTP0。
- アプリの年払い購入/顧客作成と2回目の既存Checkout再利用、新規POST増加なし。SDKの401後は503かつintent保持、再試行は同じキー・元メール・元bodyを再利用する。
- Portalの顧客/configuration、退会前のCheckout失効/契約照合、読み取り管理コマンドのGETのみ、開発Priceコマンドの月/年の送信パラメーター。

既存の有料ライフサイクル試験は実署名Webhookの解析を維持し、遠隔契約取得だけをmockする。アプリの管理画面/所有者/コード/課金/退会の関連回帰もPostgreSQLで省略せず成功した。異常系で期待される400/401/403/500/503やtracebackはログに残り、「ログに警告・エラー0」という意味ではない。

## 隔離環境・反映境界・復旧

Windows Python 3.11.1/Django 5.2.17と、既存固定image `tableno:billing-runtime-f4ea34ca` に変更ソースをread-only overlayしたLinux環境で検証した。後者は通常の新しい配布イメージではない。今回候補の通常配布物再構築・全OS監査・CI全体は未確認である。

PostgreSQLは専用コンテナ `aded962091c460a05ecf79f59f468522323a74d19c8f00e2efc1bc9b2a17fbc0`、固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、network none・公開ポートなし・512 MiB・tmpfsの合成DB。SQLiteもメモリー内の使い捨てDB、メール/cacheはlocmem。全テスト終了後に完全ID/image/networkを照合してPGコンテナと合成データを削除した。fixtureから再作成可能で、保存ログ/工具・実データ・他のコンテナを変更していない。

元checkoutのハンドアウト未コミット差分は保持する。今回main、AWS/ECR/ECS/共有DB/CloudFront、Stripeの実アカウント/Price/課金、Secrets/IAM、税登録/税計算、容量/継続費用への操作はない。workflowは通常pushでCIのみを起動し、デプロイを起動しない。先行記録3804dbc5の[CI run37198930051](https://github.com/sheepdog0820/iaia/actions/runs/37198930051)はhead一致・completed/success・全6ジョブsuccessを後続確認したが、今回修正のCIとは区別する。

[管理削除/所有者付け替え方針](SUBSCRIPTION_OWNERSHIP_POLICY_2026-10-04.md)は回答待ちで、この移行に方針変更を混入していない。[完了済みfavicon反映](TABLENO_FAVICON_DEPLOYMENT_2026-10-04.md)や固定6b6c570cの反映承認へ今回候補を追加しない。先行f4ea34caのOS HIGH3/計39件・共有DB・実決済/RAK・SMTP/worker・外部連携・性能/復旧・税務/事業者条件等は未達のままで、[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。

復旧は修正保持のfix-forwardを優先する。この変更のrevertにDB移行は不要だが、旧グローバル設定書き換えを再導入する。未反映なので稼働版の切戻しは不要。後続main/AWS反映は対象SHA・配布物・影響を固定した別承認で扱う。

## 保存証跡

保存先 `C:/tmp/iaia-stripe-client-20261004`。生成物/合成設定はGitに含めない。

| 証跡 | SHA-256 |
| --- | --- |
| targeted-initial.log | 1861ce26fefece0df6e4fcad29104296b55ddea9f064277b72eceb3d53f140bf |
| final-sqlite.log | 860d87e5ca08fefd1449658d7d6bc7c068bf3790abd4a197c94c5180a3212203 |
| final-pg-confirmed.log | 815717ab412f7cf77d3aeb5b7dc105972c2c02a6ea08f4229025217412541447 |
| coverage-sqlite.log | acaa1bba8784e254fd5ca0f0ef565b4c3440571dd919c7f4e2434cad0ee6d9bd |
| coverage.json | 43e82a8c65307a467ad6396182c4caed6218508b2a345d99bc5c4e99de863a30 |
| coverage-changed-lines.log | d7ec40c0d4897c08cee8f84ecef4fba9f485eb85f0acc47deca089642a7e79e8 |
| bandit-final.json | f25f0678b630e9a9cde091b865c4a2f3a0bfc00cab4a14ba1e575be0f75713b4 |
| bandit-production-new-tests.json | 2932dbd5c5ae8ab0b5524f04ebe9ed6b45c96322c3e764d3ebcf61cabc971200 |
| review_migration.py | 51db6fd2b3cb101e09f71bc427b181886cd2fdbcc7023fbebc05777bef775731 |
| review-migration.log | 47c10fc8f7c6ace3024a7deb22b87ebb6d113067874db79b7007757684a294de |
