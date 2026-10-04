# プレミアム再同期修正の通常配布物検証（2026-10-04）

## 固定候補と来歴

対象は `cea7e76b847727c5244cc03a4d1454d7949cae20`。先行の[通常候補3492d3d3](PROMO_RUNTIME_CANDIDATE_2026-10-04.md)に、[権限再同期の競合・監査原子性](PREMIUM_RECONCILIATION_INTEGRITY_2026-10-04.md)を加えた候補である。mainのfavicon・画像ギャラリー・依存修正と、CCFOLIA/ICS・コード利用/失効の修正を保持する。

差分のない専用checkoutから通常Dockerfileで構築した。タグ `tableno:reconcile-candidate-cea7e76b`、image ID `sha256:46795320922764a1bc2065f8c161e8d317cb0f2f5c1588a6d9026660d4a666f4`。Dockerfile/requirements.lock/entrypoint/移行ファイルは3492d3d3から変更なし。依存・apt層はキャッシュを使用し、新しいOS更新の取得とは扱わない。両イメージの先頭10層が同一で、全14層のうちアプリCOPY以降を更新した。OCI revision label/署名はなく、ECRへは未push。

accounts/api/schedules/scenarios/support/tableno/static/templates内の対象拡張子、requirements.lock/entrypoint、コード利用・失効・再同期の競合テスト3ファイルを、追跡578ファイルとして列挙した。ホストHEADのSHA-256を検査入力にし、imageで全件存在・同一を確認した（欠落0・不一致0）。Python caches0、Pythonパッケージ111件。対象外の全filesystem・nativeビルド閉包・署名来歴の証明ではない。

## 配布物内の401回帰テスト

新imageのアプリ・テストソースは重ね替えず、隔離PostgreSQL18.3で396件全成功（80.216秒・省略0・終了0）。先行の試験対象と照合して、カレンダー購読クラスとfeed encodingの5件を別実行で補完し、こちらも全成功（2.867秒・省略0）。対象重複なしで計401件であり、396件だけを先行389件+新規12件の全範囲と誤認しない。

対象はbilling/削除ガード/既存課金競合、paid_feature_lifecycle、premium_code_serialization、promo_revocation_integrity、premium_reconciliation_integrity、課金メール配送/監視、Stripeの複数停止理由・請求/イベント順序・Checkout再試行/順序・Dispute再試行/回復/順序・Portal解約、CCFOLIA版往復/export/6版API、購読認可/文字エスケープ/ICSダウンロード/calendar API。補完は `schedules.test_external_integrations.CalendarSubscriptionTestCase` と `tests.integration.test_calendar_feed_encoding`。

設定だけをread-only mountし、DBは合成・メールlocmem・cache locmem・メディア一時領域とした。既存CCFOLIA試験には、先行記録で公式archive SHA-256照合済みのNode v20.20.2を工具としてread-only mountした。今回node binaryのSHA-256は `6295488653f0d93b0a157841746fef7e72cc4328cfb60c4bbe0ca2668a836ffd`。imageへのNode追加やアプリ差し替えはない。Stripeはmockで実課金・実配送の証拠ではない。HTTP警告・外部障害ログは異常系の期待結果。

## 通常起動と実HTTP・再同期操作

同じimageの通常entrypointをaws-pre型の合成設定で起動した。PG18.3の固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7` はnetwork none・公開ポートなし・512 MiB・DB tmpfs。Redis7.4.11の実image IDは `sha256:5509c0097c6064aa8a3b1df58f1d950e67090fffa6678ae8f3f1dc2385f12deb`（先行試験のRedis digestとは異なる）。Redis128 MiB/Web512 MiBはPGのnetwork namespaceを共有する。外部決済・S3を使わず、SMTPは到達不能なloopback、購入開始/課金メール配送は無効。

空DBの全移行とcollectstaticが成功し、Daphneが起動した。静的232件/624 post-process、check --deploy0問題、migrate --check終了0、readiness200/DB・cache正常。billing_release_gateは `ok checkout-disabled` で、有料公開ゲート合格ではない。共有AWSの移行履歴・設定を証明していない。

先行の実HTTP19件が全成功した。readiness、ログイン画面、アイコン4URLの元bytes一致、CCFOLIA helper bytes一致、ICSの停止GET/HEAD拒否・再有効化・参加資格喪失・token再発行・ダウンロード文字/UTC、無料の通常利用者の6版/7版API往復と所有者/能力値/幸運保持を確認した。

初回HTTP harnessは、WebのstaticfilesがDocker volumeではないため、volumes-fromではmanifestを取得できず、fixture作成前に終了1となった。Webが実際に収集したstaticfilesを専用ディレクトリへコピーし、検査コンテナへread-only mountして再実行した。検証設定の修正であり、アプリ・権限・期待値は変更せず、初回を成功として数えていない。

コード利用/失効の先行13操作と、再同期の追加10操作、計23操作も全成功した（16 HTTP操作・7管理コマンド確認）。harnessの先行13件表示と最終23件表示は同一実行の経過であり、合算して36件にはしない。

- 先行13操作: 未認証401、初回コード利用・同コード再試行、expiry dry-run/実失効/再試行、失効後の別コード利用、CSRF付き管理者の旧コード保持/現在コード失効/再試行、手動付与保持。
- 再同期コマンド3操作: dry-runは利用者/監査不変、実行でactiveの付与とcanceledの停止を各1件、再実行で0件。actorなし・source/status/subscription_id等の既存metadataも確認。
- 管理画面7 HTTP操作: 課金changelist取得、CSRFなしPOST403/データ不変、activeの付与1件と再試行0件、canceledの停止1件と再試行0件、手動付与の保持0件。日本語の件数表示、正しいactor・subscription_id、監査件数を照合した。

管理者session・DRF Tokenは隔離fixtureで、実ログイン/OAuthの成功ではない。通信はloopback HTTPとproxy-HTTPSヘッダー。CookieJarもこの検証に限りHTTPでsecure cookieを返す設定で、TLS/ALB/ブラウザーCookie保護の証拠ではない。実Stripe署名Webhook、外部カレンダー受信、実CCFOLIA、実メール/AWS/S3は未検証。

今回専用Web/Redis/PGコンテナは停止・削除し、PG tmpfsとRedis匿名volumeの合成データを破棄した。fixtureから再作成可能で、他のコンテナ・実データは操作していない。

## 静的資産・全監査・CI

Web収集manifestは232 mappingで3492d3d3との差分0。全配信ファイルbytesや最新AWS manifestの照合ではない。

既存Docker Scout1.24.0の専用cache・NO_CACHE=true・無抑制全監査は268 indexed/16 vulnerable packages/39 CVE（HIGH2/MEDIUM2/LOW35、Python0）、終了1。先行候補とのCVE ID差分0、SARIF SHA-256一致。Windows archiveのfile-in-use警告はあるがindex/全結果/SARIFは出力された。組込み1.5.0はバージョン確認だけで、この全監査の根拠にはしていない。

新版1.26.0は[公式release](https://github.com/docker/scout-cli/releases/tag/v1.26.0)で解析エンジン更新を確認し、Windows archiveとchecksumsを専用工具ディレクトリへ取得した。GitHub release APIのasset digestと公式checksumsの両方を照合してから実行した。archive SHA-256は `d4cf08647b79ab56adaf482e760135d4b0524a5e1f194fd31f0f20cf4ec01a94`、checksums fileは `9710319ac40dcce1de750544d24f9f07dc81f440cab401f17f6288a79bb18de8`。署名検証ではなく、既存Docker plugin・アプリ依存・システム設定は置き換えていない。

新版も専用cache・NO_CACHE=true・無抑制で同じimageを全監査した。292 indexed/16 vulnerable packages/39 CVE（HIGH2/MEDIUM2/LOW35、Python0）、終了1。39 rule/resultの全てがDebianパッケージに対応し、1.24.0とのCVE ID差分は0。この実行にはarchive警告はなかった。解析対象の増加を確認したが、OSゲートは未合格のままで、抑制・リスク受容は行っていない。

候補[CI run37187834100](https://github.com/sheepdog0820/iaia/actions/runs/37187834100)はhead SHA一致、最終結果は5項目success・playwright failure。PGログには今回の新規テストを含むコマンドと `341 passed, 9 warnings, 54 subtests passed in 71.84s` があり、対象が省略なく成功したことを確認した。Unit / Integrationは2036 passed/48 skipped/159 warnings、883.00秒・coverage87.40%。この48省略を、配布物内401件の省略0と混同しない。

Playwrightは233 passed/1 flaky（11.9分）。WebKitのaccount-deletion.spec.ts:31でキャンセル後の確認modal count0を待機中にテスト全体30秒の上限へ達した。再試行成功でもfailOnFlakyTestsによる終了1であり、成功扱いにしない。設定・期待値・再試行基準は変更していない。

失敗artifact11297347955を取得し、GitHub digestとarchive SHA-256の一致を確認してから展開した。traceではnewPageが362507.782→386247.580 ms（23.740秒）。キャンセルclick完了392190.103 ms、count確認開始392190.737 msに対し、afterEach開始392486.389 msで約0.296秒しかなく、確認は392845.101 msにテスト全体timeoutで終了した。fixtureによる時間計測の切り替えもあるため、hook開始時刻から単純に正確な30秒deadlineを推定しない。modalからshowクラスが除かれたsnapshotと暗いbackdropだけの失敗画像を確認した。ブラウザー初期化がテスト予算の大部分を消費した証拠はあるが、その遅延原因・modal cleanupの独立不具合は未確定。Bootstrap hideが表示中に無視されたと断定せず、通常予算でのブラウザー再現とfixtureの時間配分を次の調査対象とする。全CI成功・OSゲート合格・main/AWS反映の条件は未達。

## 証跡と反映境界

専用証跡は `C:/tmp/iaia-reconcile-candidate-cea7e76b`。工具・合成env・大量生成物はGitへ含めない。

| 証跡 | SHA-256 |
| --- | --- |
| reconciliation_http_probe.py | 970afd9fbabef82735649533afdc1f345feb46c3e502cd7fbd29099acfb3e373 |
| inspect_candidate.py | a0999d34f822d18a566a1588ee9c652df9f0ee0c2b9cd1ea70ca9435be7d8379 |
| staticfiles/staticfiles.json | 6beffe6fc2a3e1c98133b0b5ecf8c03fc19ca12fa10fbed0234dfd49279ad6e4 |
| runtime-full.sarif.json（1.24.0） | 4924d757f193ce8edc27492ad5006bea0a41b61bb61c0d57c7221fb5b1f48f39 |
| runtime-full-126.sarif.json（1.26.0） | 40a6eeb91bd9060cc86e1b1161e15786647126a09d407d64a1ff323f3c24ee1b |
| cea7e76b-playwright-artifacts.zip | a310cfacaeb4c60cc190ca12c168524e86850163e1c87c22e2d6cd99e63aacf4 |

mainは読み取りで8567f49fと再確認。今回AWS状態は読み直しておらず、先行定義54の確認時刻を現在へ繰り上げない。mainマージ・ECR push・ECS更新・共有DB変更・S3書込み/CloudFront無効化・Secrets/IAM・課金/税設定・容量/継続費用変更は未実施。元checkoutのハンドアウト差分は保持した。[6b6c570c専用反映案](AWS_APP_APPROVAL_6B6C570C_2026-10-04.md)の対象を変更せず、完了したfavicon承認も転用しない。

通常配布物の未検証は今回の限定範囲で解消したが、管理者直接付与/停止/復旧の全経路・OSゲート・実AWS/課金/外部連携・総合性能/復旧/運用・本番税務確認は未達。修正を保持するfix-forwardを優先し、[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。
