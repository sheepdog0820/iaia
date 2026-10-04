# Stripe検証コマンドのAPI例外・SDKログ保護（2026-10-04）

## 対象と再現

基点 `f355df1cee28a1f0211f27e300eeb55957caf1a9`、専用ブランチ `codex/stripe-command-error-redaction-20261004`。`billing_stripe_remote_check` と `create_stripe_development_prices` はSDK例外をそのまま伝播し、`billing_verification_record` は例外文字列をMarkdownへ保存していた。SDK 16.0.0も例外を投げる前に応答本文・エラーメッセージ・POSTデータをログへ出す。詳細設定 `stripe.log` / import時に保存された `STRIPE_LOG` はPython loggingを経由せず標準エラーにも出すため、例外文字列の置換だけでは不十分だった。

実SDKとメモリ内HTTP transport、利用不能な合成キー・メールアドレスを使い、401/403応答、商品/月額/年額作成の失敗、予想外live Productの無効化失敗を再現した。初回REDは23 failed/3 passed（subtest失敗を含む）。実Stripeへの通信・課金は行っていない。

## 修正と利用者への影響

- 両コマンドに共通の同期実行ラッパーを追加。SDK例外は固定の日本語分類（認証/権限/通信/呼び出し制限/API）と検証済み整数HTTPステータスだけを返す。本文・request ID・code・param・headerは出さず、例外チェーンも表示しない。予期しない例外も固定文へ置換する。
- 実行中のSDK loggingを固定文へ置換し、引数・例外・スタック文字列を除く。ContextVarでスコープを分離し、並行する別スレッド・終了後・ネストした実行のログは維持する。StripeClientのキー/API版/ログ設定を一時的に変更しない。
- SDK直接出力につながる `debug` / `info` 設定では、クライアント生成・API呼び出し前に失敗する。設定を無効にしてプロセスを再起動してから検査する。logging側のINFO/DEBUGハンドラーは保護対象で、停止対象はSDK直接出力設定。
- Productの無効化要求が失敗しても「無効化済み」と断言していたfinally処理を修正。予想外モードではPrice作成を停止し、無効化状態の確認を要求する。API失敗では成功マーカーを出さず、結果確認まで再実行しないよう案内する。補償操作・自動再試行を新たに追加していない。
- 確認記録は予期しない例外の本文/クラス名を保存しない。既存のCommandErrorによる設定検査結果は維持する。

対象は上記コマンドのAPI例外とSDKログ。正常な確認出力（イベントID等）・既存の設定/応答検査エラーは従来どおりで、任意の秘匿値を含むCommandErrorの文字列を汎用除去する実装ではない。Web処理・worker・別コマンドのログ全体、任意のカスタムlogging filter、将来のSDK変更まで安全性を保証しない。SDK内部のSTRIPE_LOG参照は固定SDK 16.0.0に対して検証した。API/SDK更新時にはこの境界の再試験が必要。

エラーの種類に応じた処理と、通信/APIエラー時に操作結果を不明として扱う方針は[Stripe公式のPythonエラー処理](https://docs.stripe.com/error-handling?lang=python)を公式CLIで参照した。稼働環境用キーは別Sandboxの最小権限RAKを推奨し、発行・権限設定・Secrets更新は未実施。

## 検証

| 検証 | 結果と境界 |
| --- | --- |
| 初回GREEN | 関連33 passed/114 subtests passed。初期9試験と既存RAK/StripeClient試験 |
| 最終SQLite・coverage | 関連36 passed/120 subtests passed、4既存Django警告、2.12秒。新規12試験と既存RAK/StripeClient試験。合成transportのみ |
| 整形・文書更新後の再検証 | 関連36件＋文書39件＝75 passed/126 subtests passed、4既存警告、2.26秒。同じ共通処理43文/8分岐100%。上の件数と重複するため合算しない |
| 新規共通処理coverage | 43文・8分岐とも100%、未実行0 |
| PostgreSQL広域回帰 | **609 tests、111.883秒、OK、省略0**。先行34モジュール561件＋新規12件＋本番設定36件。課金/Webhook/削除・所有者/認証/CCFOLIA/ICS/行ロックを含む |
| Black/isort/Flake8 | 変更Python7ファイル成功、他ファイルの整形なし |
| Bandit | アプリ4ファイル・変更Python7ファイルの双方で指摘0/読込エラー0、終了0。広域CI/OS全体の合格とは別 |

PG試験は既存通常イメージ `tableno:stripe-runtime-529c30c7`（`0013941872077af98a6a6be4d2e2dfdb544d57db137b51dfbb89ca8ff0a9da4c`）に今回ソースをread-only mountした回帰試験で、**今回の通常配布物検証ではない**。PostgreSQL 18.3はnetwork none・公開ポートなし・tmpfsの合成DB、アプリも同じ隔離network namespace・read-only/tmpfs・隔離設定/Nodeのみを使用した。試験終了後はアプリが自動削除され、PGのID/image/network/port/mountを照合して停止・削除した。削除したデータは再作成可能な試験DBだけで、実ユーザーデータは扱わない。ログ/イメージは保持する。

新しいエラー表示は日本語。実差分と、成功・権限拒否・途中失敗・例外チェーン・直接ログ拒否・並行/ネスト/終了後の挙動を自己レビューした。権限不足をスキップして成功にする変更はない。今回CI・通常配布物・AWSでの検証は別途必要。

基点f355df1cの[CI](https://github.com/sheepdog0820/iaia/actions/runs/37209632857)は最終failure。他5ジョブはsuccessで、先行のproduction設定fixture失敗はUnit / Integrationでは解消したが、Playwrightは290 passed/1 flaky・終了1。Firefoxのaccount-deletion試験で最初のsignupページ遷移のload待ちが30秒でtimeoutになった。再試行成功を全体成功へ置換せず、証跡の精査/再現が残る。今回変更はこのブラウザー失敗の修正ではなく、自動再実行・判定緩和もしていない。

## 承認境界・復旧・公開判断

mainは読み取り照合で `8567f49f8d411bad7f732afaeebad85357eeca09`、AWSは今回再照合/変更していない。mainマージ/デプロイ/ECR・共有DB移行/実キー/Secrets/IAM/Stripeアカウント・Product/Price/Webhook/実メール・容量/費用は変更せず、faviconや旧候補の承認は流用しない。元checkoutのハンドアウト未コミット変更を保持する。Stripe Tax/automatic_taxも変更せず、販売対象・有効な税務登録の確認は未完了。

復旧は今回コードを通常revertする。DB移行・データ復旧は不要だが、API例外とログの漏えい、および無効化成功の誤表示を再導入する。エラー後に作成コマンドを再実行する前に、承認されたSandboxの状態を人間が確認する。

先行候補のOS39指摘（HIGH3/MEDIUM2/LOW34、Python0）は未解消。実RAK認証/最小権限、Endive Sandbox実API・署名Webhook、共有DB/worker/メール、管理運用方針、外部連携/性能/復旧/事業者・税務運用等も未完了。[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。

## 保存証跡

保存先 `C:/tmp/iaia-stripe-command-errors-20261004/`。REDには合成値だけが含まれる。生成ログ/coverage/レポートはGitへ追加しない。

| 証跡 | SHA-256 |
| --- | --- |
| red.log | 747022d4e001d8187966b3ce066f940d981cf9d4952493344788ac6d6d310e40 |
| green.log | 1fca0b1efc749a20a5fcdbadb7351408edcb2c915186ddb57a4385b2fb101c51 |
| coverage-tests.log | 65eee6e2207e49a2edd0f534d11cb3f05282440af9cbd031d95e00ad177c6a1f |
| coverage.json | fc9c2841dce1ea955d12cc51634fd586096af3b2df4288adba03e65786f7564b |
| postgres-regression.log | 5e36cf2234589a6750ac931c434ef1e23a356715786a134fb6181fc9419d840c |
| bandit-app.json | 9c631336dea1ff85a161f84ad42f9e181ba70e844357cf01e3bcf25d72df36b4 |
| bandit-changed.json | eee7f475d62d14f049265b4370cc186237e6395c8bd1c9eb0b0a104eed3df87a |
| final-tests.log | 3fe0be198afe8c8ecf5c46ed558b1ca0994e7fe404f25b2cd5eace39f2e03924 |
| coverage-final.json | bc81b3b7302587783decc616be1d3570e6b06f365d2e6843a02bcd9201961775 |
