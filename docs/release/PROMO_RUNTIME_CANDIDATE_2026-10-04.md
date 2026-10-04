# プレミアムコード競合修正の通常配布物検証（2026-10-04）

## 固定対象・来歴

アプリ候補は `3492d3d381d7ccdd0744eee774b479f7f9b831cf`。[コード利用時の競合防止](PREMIUM_CODE_SERIALIZATION_2026-10-04.md)と[失効・監査の原子性](PROMO_REVOCATION_SERIALIZATION_2026-10-04.md)を含む。先行6b6c570cのCCFOLIA/ICS、mainのfavicon・画像ギャラリー・依存修正を保持する。

差分のない専用checkoutから通常Dockerfileで構築した。タグ `tableno:promo-candidate-3492d3d3`、image ID `sha256:9f5a3c0bb4ee0d7c6f9922fc7e619d7b1285af717b798048a40a00e0291df275`。依存・apt層はキャッシュを使用し、requirements/Dockerfile/entrypointは6b6c570cと同じ。新しいOS更新を取得したという証拠ではない。OCI revision label/署名はなく、ECRへ未push。

accounts/api/schedules/scenarios/support/tableno/static/templates内の対象拡張子、requirements.lock/entrypoint、新規競合テスト2ファイルの追跡577ファイルを列挙し、imageに全件存在・SHA-256一致を確認した。欠落0・不一致0、Python caches 0、Pythonパッケージ111件。検査対象外の全filesystem・nativeビルド閉包・署名来歴は証明していない。

## 配布物内の389回帰テスト

新イメージのアプリ・テストソースは重ね替えず、隔離PostgreSQL 18.3で389件全成功（82.801秒、省略0、終了0）。先行のファイルoverlayによる315件だけでなく、実際の配布イメージに両修正が含まれ、関連CCFOLIA/ICS機能も保持することを確認した。

対象はbilling/削除ガード/既存課金競合、paid_feature_lifecycle、premium_code_serialization、promo_revocation_integrity、課金メール配送/監視、Stripeの複数停止理由・請求/イベント順序・Checkout再試行/順序・Dispute再試行/回復/順序・Portal解約、CCFOLIA版往復/export/6版API、購読認可/文字エスケープ/ICSダウンロード/calendar API。外部Stripeはmockで、メールはlocmem。

設定ファイルだけをread-only mountし、DBは合成・メールlocmem・cache locmem・メディア一時領域とした。既存CCFOLIAテストに必要なNode v20.20.2のLinux binaryを検証工具としてread-only mountした。これは先行[通常配布物検証](ICS_CCFOLIA_RUNTIME_CANDIDATE_2026-10-04.md)で公式SHASUMS256と照合した同じbinaryで、imageへNodeを追加していない。署名照合は未実施。異常系HTTP/Stripe例外ログは期待結果であり、予期しないテストエラーはない。

## 通常起動・実HTTP・管理操作

同じ固定imageの通常entrypointをaws-pre型の合成設定で起動した。PG固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7` はnetwork none・公開ポートなし・512 MiB・DB tmpfs。Redis固定image `sha256:2e1c703aab5fd50a33e1bccdff0ae62260fb34f2f6cb9d696275c82180619a35` とWebはPGのnetwork namespaceを共有する。外部決済・S3を使わず、SMTPは到達不能なloopback、購入開始/課金メール配送は無効。

空DBの全移行とcollectstaticが成功し、Daphneが通常起動した。静的232件/624 post-process、check --deployは0問題、migrate --checkは終了0。billing_release_gateは `ok checkout-disabled` で、有料公開ゲート合格ではない。共有AWS/DBの移行履歴や実効設定を証明していない。

先行harnessの実HTTP19件が全成功した。readiness DB/cache・ログイン画面・アイコン4URLの元bytes一致・CCFOLIA helper bytes一致、ICSの停止GET/HEAD拒否・再有効化・参加資格喪失・token再発行・ダウンロード文字/UTC、無料の通常利用者による6版/7版API往復と所有者/能力値/幸運保持を再確認した。

追加harnessは9つのHTTP操作と4つの管理コマンド確認、計13操作が全成功した。

- 未認証コード利用401、初回利用200・日本語の付与メッセージ、同じコード再試行で消費/付与監査を増やさない。
- expiry dry-runは変更なし、実失効1件・再実行0件・監査1件、失効後の別コード利用で新権限を付与する。
- 管理者の実changelist GETとCSRF付きaction POST。旧コードを選択しても現在の権限を保持し、日本語の0件表示。現在コードでは1件失効、再試行0件、監査に正しいコード/管理者を記録する。
- 手動付与監査がある場合、期限失効後も利用者のpremiumフラグを保持する。

管理者セッションは隔離fixtureとして作成したもので、実パスワードログイン/OAuth/実利用者管理の成功ではない。初回はDBセッションを固定使用したため、Redisセッションの通常設定では管理者ログイン画面へ転送された。件数assertが失敗して終了1となり、アプリの成功とは扱っていない。Cookie追跡だけを直した2回目も同じ認証不一致で失敗した。現在設定のSESSION_ENGINEを使い、Cookieをリダイレクトで保持し、最終URLが管理者changelistであることも検査するようharnessを修正。新しい合成利用者で成功し、アプリ・期待件数・権限条件は変えていない。診断時のUser固定importも誤りで失敗し、get_user_modelへ直して状態を確認した。

通信はloopback HTTPとX-Forwarded-ProtoによるHTTPS相当ヘッダー。管理者CookieJarもこの隔離検証に限りHTTPでsecure cookieを返す設定で、実TLS/ALB/ブラウザーCookie保護の証拠ではない。DRF Tokenと管理者sessionは合成。実Stripe署名Webhook、実CCFOLIA/カレンダー受信、実メール/AWS/S3は未検証。

検証後、今回専用のWeb/Redis/PGコンテナだけを停止・削除した。PG tmpfsとRedis匿名volumeの合成データは破棄済みで、fixtureから再作成できる。他のコンテナ/実データは操作していない。

## 静的資産・全OS監査・CI

収集manifestは232 mappingで6b6c570c候補との差分0。これはmapping比較であり、全配信ファイルbytesの照合ではない。AWSの現在manifestを再取得したものでもない。

Docker Scout 1.24.0、専用cache・NO_CACHE=true、無抑制の全パッケージ監査は268 indexed・16 vulnerable packages・39 CVE（HIGH2/MEDIUM2/LOW35、Python0）、終了1。6b6c570cレポートとCVE ID差分0・SARIF SHA-256一致。archive削除にWindows file-in-use警告があるが、index/全結果/SARIF出力は完了した。抑制・only-fixed・ベース除外・リスク受容・脆弱性解消はない。

候補[CI run 37185332518](https://github.com/sheepdog0820/iaia/actions/runs/37185332518)はhead SHA一致。今回確認時点でlint-security・production-database・infrastructure・systemがsuccess、Unit / Integrationとplaywrightは実行中。PGジョブログに新規のコード利用/失効競合テスト2ファイルを含む実行コマンドと `329 passed, 9 warnings, 50 subtests passed in 90.47s` を確認し、省略のない対象成功を照合した。CI全6成功とはまだ報告しない。

mainは読み取りで `8567f49f8d411bad7f732afaeebad85357eeca09` と確認した。今回AWS状態を読み直しておらず、先行記録の定義54/digestの確認時刻を現在へ繰り上げない。mainマージ・ECR push・ECS更新・共有DB変更・S3書込み/CloudFront無効化は未実施。

## 証跡・反映境界

専用証跡は `C:/tmp/iaia-promo-candidate-3492d3d3`。大量生成物・合成env・検証工具をGitへ含めない。

| 証跡 | SHA-256 |
| --- | --- |
| promo_http_probe.py（最終版） | 2d585c0cddfdf7317438d9e1144be0d7365139067e75b38c7ada0764a47acc05 |
| 先行http_probe.py | 8918df9748b4ff38973012e4852d6a799a3b2e62184435c3a69dd4267b38090c |
| staticfiles.json | 6beffe6fc2a3e1c98133b0b5ecf8c03fc19ca12fa10fbed0234dfd49279ad6e4 |
| runtime-full.sarif.json | 4924d757f193ce8edc27492ad5006bea0a41b61bb61c0d57c7221fb5b1f48f39 |

通常配布物の未検証は今回の限定範囲で解消したが、OSゲート・実AWS/課金/外部連携・総合性能/復旧/運用は未達。[6b6c570c専用の反映案](AWS_APP_APPROVAL_6B6C570C_2026-10-04.md)は固定対象のままで、この後続候補へ承認を転用しない。元checkoutのハンドアウト差分も保持した。復旧は誤消費/誤失効の修正を保持するfix-forwardを優先し、[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。
