# StripeClient移行候補の通常配布物検証（2026-10-04）

## 固定対象と配布物

対象は `2ff6a4c8797eadebb54965c218e7c6da69b98eb0`。[先行f4ea34ca配布物](BILLING_RUNTIME_F4EA34CA_2026-10-04.md)に、[Stripeクライアント設定分離](STRIPE_CLIENT_ISOLATION_2026-10-04.md)と検証記録を加えた候補である。mainの画像ギャラリー/favicon/依存更新、CCFOLIA/ICS、課金/管理/所有者照合の修正を保持する。今回のリポジトリ変更は検証記録のみ。

固定SHAの `git archive` から通常Dockerfileで構築した。タグは `tableno:stripe-runtime-2ff6a4c8`、image IDは `sha256:6e4cc074705120fd6e411adc1cb82c03ab846f0594846c336f039d27258a15fa`。revision labelは上記SHA、実行ユーザーtableno、entrypoint `/entrypoint.sh` を確認。ECR push・署名検証はしていない。

Dockerfile/requirements.lock.txt/entrypoint/accounts移行は前候補から変更なし。先頭10層はf4ea34caのimageと同一（全14層）。依存層をキャッシュ利用しており、新しいOS修正の取得ではない。対象拡張子のaccounts/api/schedules/scenarios/support/tableno/static/templatesとtests/unit/integration、lock/entrypoint/manage.pyの選定済み追跡670ファイルをarchiveとimageのSHA-256で照合し、欠落0・不一致0・Python caches0を確認した。Pythonパッケージ111、Stripe 15.5.1/Django 5.2.17。全filesystem/nativeビルド閉包の証明ではない。

## ソースを重ね替えない回帰試験

通常image内のソースとテストをそのまま使用し、隔離PostgreSQL 18.3で529テスト全成功・省略0（121.443秒、終了0）。アプリ/テストのoverlayはしていない。設定ファイルとNode工具のみread-only mountした。Node v20.20.2は既存工具で、今回もbinary SHA-256 `6295488653f0d93b0a157841746fef7e72cc4328cfb60c4bbe0ca2668a836ffd` を照合した。imageにNodeや代替アプリソースを追加していない。

対象は課金/認証/退会ガード/競合、Stripe再試行/順序/Dispute、メール配送/監視、コード利用/失効/再同期、管理操作/手動付与/フォーム/所有者照合、6版API/CCFOLIAの6版7版往復、ICSの文字/時刻/購読認可/calendar API。新規14件では実SDKを外部I/O不能のメモリーtransportにつなぎ、並行したキー/API版分離、実シリアライズ/冪等ヘッダー、ページング、実HMAC署名、購入/401後の回復/Portal/退会/管理コマンドを確認した。他の回帰試験は既存のmockも使用する。実Stripe API/実決済を確認したものではない。

fixtureは専用PG・locmemメール/cache・一時メディアで、実データには接続していない。意図した異常系の400/401/403/404/500/503やtracebackはログに残る。全ログの警告/エラー0や性能基準達成を意味しない。

## 通常起動と27件の実HTTP

専用PGのimageは `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、network none・公開ポートなし・512 MiB・DB tmpfs。Redis 7.4.11 `sha256:5509c0097c6064aa8a3b1df58f1d950e67090fffa6678ae8f3f1dc2385f12deb`（128 MiB）とWeb（512 MiB）はPGのnetwork namespaceを共有した。S3無効、SMTPは到達不能loopback、実Stripeキーなし・課金メール無効で外部通信できない。合成設定で通常entrypointを起動し、空DBへの全移行・静的232件/624 post-process・Daphne起動を確認した。

`check --deploy` は問題0、`migrate --check` は終了0。readinessはHTTP200/DB・cache正常。`billing_release_gate=ok checkout-disabled` は購入開始無効の起動条件確認であり、有料公開ゲート成功ではない。

通常Webの19 HTTPは全期待結果に一致（終了0）。readiness/ログイン、favicon等4 URLの元bytes一致、manifest内CCFOLIA helper bytes、ICS停止GET/HEAD拒否/再有効化/参加資格喪失/旧token失効/文字/UTC、無料通常ユーザーの6版/7版CCFOLIA API往復を確認した。初回fixture作成前に専用DB名・ユーザー表空・購入開始無効をassertした。静的manifest232 mappingはf4ea34caから追加/削除/変更0、manifest自体のSHA-256も同一。AWS側manifest・CloudFront全bytesとの一致は今回未検証である。

通常Webを停止後、同じimageの別Webを合成 `STRIPE_CHECKOUT_ENABLED=true` / `RUN_MIGRATIONS=false` / `RUN_COLLECTSTATIC=false` で起動し、追加8 HTTPを確認した。共有AWSの設定を変えたものではない。

- 未認証Checkout/Portal各401。
- 保存済みCheckoutのcustomer/metadata/client_reference/subscription_data.metadata不一致各400。日本語エラー一致、保存レコード/intent/監査不変。
- Checkout/Portal要求中の実PG行ロック待機を別接続から2件観測。所有者変更commit後は各400、双方の権限・監査・新規intentが変わらない。

追加8件も終了0、Webログの401×2/400×6と照合した。計27 HTTPで、先行候補の管理41操作は今回再実行しておらず加算しない。HTTP probeにStripe mockはないが、購入成功や実Stripeへの接続を確認したものではない。DRF Tokenはfixtureで注入し、loopback HTTPにはproxy-HTTPSヘッダーを付けた。実ログイン/OAuth/TLS/ALB/ブラウザー/外部受信側の証拠ではない。

今回の回帰/HTTP試験に初回失敗・再実行はない。ツール探索では既存 `docker scout` が1.5.0、`redis:7.4.11` タグが存在しないことを確認した。既存専用Scout1.26.0と、実体が7.4.11の固定Redis image IDを使用した。これらの探索を検証成功件数に含めない。

全テスト・監査終了後、Web2/Redis/PGの完全ID・image・network・公開ポートなしを再照合して停止/削除した。PG tmpfsとRedis匿名volumeの合成データを破棄し、fixtureから再作成できる。image・archive・静的生成物・ログ/工具は保存し、実データや他のコンテナを変更していない。

## OS監査・CIと公開判断

Scout1.26.0・専用cache・NO_CACHE=true・無抑制全監査は292 indexed/16 vulnerable packages/39指摘（HIGH3/MEDIUM2/LOW34、Python0）、終了2。SARIF生成は完了した。f4ea34caからCVE IDの追加/削除0、重大度変化0、SARIF bytesも同一。GCC14のCVE-2026-102010/CVE-2026-95619、zlibのCVE-2026-85091がHIGHのまま、report上のfixed versionはnot fixed。指摘抑制・ベース除外・リスク受容・OSゲート合格はしていない。

候補[CI run37200546871](https://github.com/sheepdog0820/iaia/actions/runs/37200546871)はhead `2ff6a4c8` と一致。21:08 JSTの確認時点ではproduction-database/system/infrastructure/lint-securityがsuccess、Unit / Integrationとplaywrightが実行中だった。完了前に全6項目成功・マージ可能とは扱わない。先行3804dbc5のCI成功とは区別する。

今回main、AWS/ECR/ECS/共有DB/CloudFront、実StripeのPrice/課金/Keys、Secrets/IAM、常設容量/継続費用、税設定は変更していない。元checkoutのハンドアウト未コミット差分を保持した。通常pushはCIのみでデプロイを起動しない。完了済みfavicon承認や[固定6b6c570c反映案](AWS_APP_APPROVAL_6B6C570C_2026-10-04.md)へ今回候補を追加しない。

StripeClient移行の通常配布物未検証は上記の限定範囲で解消した。SDK/API版の最新候補への更新とRAK/実Stripe/Webhook/SMTP/worker、[管理削除/所有者付け替えの運用選択](SUBSCRIPTION_OWNERSHIP_POLICY_2026-10-04.md)、OS/native閉包、共有DB・外部連携・AWS性能/復旧・事業者/税務条件は未完了。税登録やautomatic_taxの有効性も証明していない。[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。復旧は修正保持のfix-forwardを優先し、旧候補へ戻すと共有設定の書換え等を再導入する点を明示する。この文書のrevertはアプリ/稼働版を変えない。

## 保存証跡

専用保存先 `C:/tmp/iaia-stripe-runtime-2ff6a4c8`。合成env・工具・大量生成物はGitに含めない。

| 証跡 | SHA-256 |
| --- | --- |
| source-manifest.json | c4c1eb82327edf55d559567e06bee5526a7a5657943f7d54a1658276b85425aa |
| inspection.json | 1a1a2c9aff6baf0a02d046fe3f1c9c5600df5e3c9fd94953a46189b0576d593d |
| image-inspection.json | 9ee1754bbdac6406f0c0c052eb5f9b082d277d029430728ba1988b1c712ec002 |
| regression.log | 81933ed8eb2fbbfbb3c1f54d99d3022cb4deada32da2552984f38f41e8407567 |
| web-startup.log | 48f628cc6a774e97fbf3155a7712c581097077085fa33051d95a3c7ad4b6a498 |
| base-http.log | ab1c9a9ec1236aa0c2c6499dadaf21c28caffbd37b596c9aaf4ef83cefdf7b3e |
| owner-http.log | bad9db744eb8971479054a87cd49d7ae500c577d573972e1850b470efcab0602 |
| owner-web.log | 55e8ce49712e6f3c3ef0695ec4e894a467ff194bb9eadf2f686963f7a935f630 |
| staticfiles/staticfiles.json | 20af8bfd892374b30973bd097c015e79a355d09b3273868a8bf7806d709c11f0 |
| runtime-full.sarif.json | ff5919a16274e41e04ac1f4555739873fea74166e525c21dc840eef559cca6fa |
| scan-summary.json | f5ab7c406c83944d67c6f446e290fd30415975252a7ba25c7a83eaddd7a8b67d |
