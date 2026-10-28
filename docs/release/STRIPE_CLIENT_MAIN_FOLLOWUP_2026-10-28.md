# Stripeのキー・API版をクライアント単位へ分離（2026-10-28）

## 対象と公式仕様

正式公開はNo-Goを維持する。[所有者確認のPR #15](https://github.com/sheepdog0820/iaia/pull/15)のhead `9d41e886ff1755cc7e23b223e68b8ec4a36de5ad` を基点に、別ブランチ `codex/stripe-client-followups-20261028` で既知 `2ff6a4c8` の製品差分・関連試験だけを選んだ。SDKの共有moduleへAPIキー・API版を書き込む従来のfactoryは、返した参照も同じmoduleであるため、別の設定での後続factory呼び出しが先の要求へ影響する。この不足を合成キーで再現した。実サービスでの混線や漏えいを確認した記録ではない。

接続アプリの資料検索は再認証が必要だったため、公開仕様を既存の資格情報なしで取得した。Stripe CLIのシステム版1.42.14を変更せず、[公式CLI v1.55.3](https://github.com/stripe/stripe-cli/releases/tag/v1.55.3)を作業用tmpへ展開し、release assetのSHA-256と公式checksumsを一致確認した。専用の資格情報なしconfigで `stripe docs /sdks`、`/sdks/server-side`、`/sdks/set-version` を読み取った。生成されたconfigの項目は表示設定・machine UUID・project名だけで、ログインやsandbox作成、Stripe資源の操作は行っていない。

実行中の固定SDKは15.5.1。[同じ版の公式README](https://github.com/stripe/stripe-python/blob/v15.5.1/README.md)と[クライアント実装](https://github.com/stripe/stripe-python/blob/v15.5.1/stripe/_stripe_client.py)で、キー・stripe_versionの指定、v1サービス、params/options、クライアントに結び付く署名検証を照合した。従来の依存宣言は12系も許可していたが、[12.0.0の実装](https://github.com/stripe/stripe-python/blob/v12.0.0/stripe/_stripe_client.py)には今回使う `v1` 名前空間がない。宣言だけを `stripe>=15.5.1,<16` に揃える。3ロックは既に15.5.1で、ロック・実パッケージの版を変更せず、全ロックがこの範囲に入ることを検査した。

## 修正と保持する挙動

- factoryは設定済みキーとAPI版を持つ `StripeClient` を返し、`stripe.api_key` / `stripe.api_version` を書き換えない。キー・API版以外の全SDK設定の分離や、実アカウントの資格情報変更を主張しない。
- 顧客・Checkout・請求管理・購読・請求・返金/紛争照合・削除前確認を、各クライアントの `v1` サービスへ揃える。再試行キーをoptionsへ、業務パラメータをparamsへ分け、保存済みパラメータを変更しない。
- Webhookはクライアントの署名検証/イベント復元を使う。重複処理、所有者確認、共有行ロック、権限・監査・退会の制約は保持する。
- 読み取り確認・ローカルWebhookスモーク・開発Price準備のコマンドも同じ呼び出し形式へ揃える。既存の実行可否・環境制約、月480円/年4,800円、通貨・Price照合や失敗時の扱いは変更しない。これらのコマンドを実Stripeで実行した変更ではない。
- 既存テストのmock先と引数の確認を新しいサービス契約へ揃える。所有者確認fixtureで修正済みのview/coreのpatch隔離も保持する。実SDKのtransport試験と分けて、既存の権限・状態遷移の回帰を継続する。

通常利用者の画面・料金・Secrets・送信先を変えず、API版の既定 `2026-02-25.clover` を保持する。Endive等へのAPI版変更は別の後続。HTTPタイムアウト/再試行回数を新たな運用方針へ変更する修正ではなく、実サービスでの互換性・性能・接続再利用は引き続き受け入れ確認が必要である。

## 検証

Python 3.11.18 / Django 5.2.17 / stripe-python 15.5.1の固定依存を使用。最初の新規単体回帰は7失敗・1成功。修正後は新しい単体/統合の **14テスト・17 subtestsが実PostgreSQLで成功、省略なし**、SQLiteでも同じ14テスト・17 subtestsが成功した。

無効な合成キーとメモリ内のHTTPClientだけを使い、SDKの実シリアライズとヘッダーを確認した。並行/別設定クライアントのキー・API版、作成要求の再試行ヘッダーと本文、12種のリソース操作、一覧/ページ送り、署名の正否とHTTPなしの検証、実Django APIからの顧客/Checkout・401後の同一要求回復、ポータル・削除前確認・読み取り/Priceコマンドを含む。実Stripeへの送信や、実ユーザーの課金・権限・削除は行っていない。

対象25 PythonファイルだけのBlack/isortは変更なし、Flake8とBanditは終了0。既存fixtureの不要になったnosec注記の補助警告はあるが、新しい抑制は追加していない。新規アプリUI文言はなく、既存の日本語エラーを維持した。証跡はGit管理外 `tmp/stripe-client-unit-red.log`、`tmp/stripe-client-pg-green.log`、`tmp/stripe-client-sqlite.log` 等に保持する。

### 計測方法による失敗の切り分け

最初の関連25モジュールの計測付き実行は315成功・192失敗（失敗数にsubtest失敗を含む）となり、途中の接続切断を検出した。接続のcloseを観測するだけの一時pluginで、リクエスト終了時にTestCaseのatomic内の接続が閉じられることを確認した。製品のDB接続処理やテストのassertを変えず、同じPostgreSQL最小ケースを比較した。

- 個別の6モジュールを計測対象に指定した場合は、同じHTTP試験が失敗する。
- 計測なしでは1テスト・2 subtests成功。
- 標準的なaccountsパッケージの指定では、同じ1テスト・2 subtests成功。

計測対象の初期化順等の内部原因は断定していない。失敗を省略扱いにせず、`tmp/stripe-client-pg-broad.log`、`tmp/stripe-client-owner-pg-probe.log`、`tmp/stripe-client-pg-close-trace.log`、`tmp/stripe-client-owner-pg-no-coverage.log`、`tmp/stripe-client-owner-pg-package-probe.log` に保持する。最終の関連回帰はパッケージ指定で計測し、変更した6製品モジュールのJSONを個別に照合する。全体試験・網羅率・通常配布物・最終CIは後続の追記で区別する。

パッケージ指定の最終実行は、既存の課金・退会の全経路・認証・運営コード・管理者操作・再試行/イベント順序・運用コマンド・文書の **25モジュール、488テスト・110 subtestsが実PostgreSQLで成功、省略なし**。製品のDB接続やassertは変更していない。変更した6製品モジュールの追加/変更実行文は **33/33**（billing15、削除5、view2、読み取り確認6、smoke2、Price3）を通過した。全accountsや製品全体100%という意味ではない。証跡は `tmp/stripe-client-pg-package-broad.log`、`tmp/stripe-client-pg-package-coverage/coverage.json`、`tmp/verify_stripe_client_changed_coverage.py`。この実行では診断用のclose観測pluginを使用していない。

## 承認・復旧と残り

DBスキーマ/移行、実データ、実Stripe、Secrets/IAM/OAuth、常設資源・費用、外部ユーザー通知を変更していない。先行PR後のbase変更と最終head・差分・CIを固定してmainへの追加マージ承認を別途求める。共有DB・AWS反映・公開の承認には拡張しない。

復旧はrevert PRだが、共有キー/API版への書き込みを再導入する。SDK/API版・制限付きキー・診断保護、実AWSの有料必須ゲート、外部連携・OS監査・性能・復旧等の正式公開条件は継続する。
