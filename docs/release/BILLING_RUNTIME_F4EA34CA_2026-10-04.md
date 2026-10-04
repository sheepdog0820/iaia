# 課金管理・所有者照合修正の通常配布物検証（2026-10-04）

## 対象・来歴

固定アプリ候補は `f4ea34cae26e27ba0cca79335b83b389834e5ee3`。先行[cea7e76bの配布物](RECONCILE_RUNTIME_CANDIDATE_2026-10-04.md)に、[確認ダイアログ](CONFIRMATION_MODAL_LIFECYCLE_2026-10-04.md)、[管理操作](ADMIN_ACCESS_INTEGRITY_2026-10-04.md)、[手動権限](MANUAL_PREMIUM_INTEGRITY_2026-10-04.md)、[管理フォーム](SUBSCRIPTION_ADMIN_SAVE_INTEGRITY_2026-10-04.md)、[リクエスト所有者照合](BILLING_REQUEST_OWNER_INTEGRITY_2026-10-04.md)を加えた履歴である。mainの画像ギャラリー・favicon・依存更新とCCFOLIA/ICS修正を保持する。今回のリポジトリ変更は検証記録のみ。

`git archive` の固定ソースから通常Dockerfileで構築した。タグ `tableno:billing-runtime-f4ea34ca`、image ID `sha256:e7778f5d81c3d8d151c4092b4410a86d048d12d9f1f5700323d4bf462cc860fe`。OCI revision labelは上記SHA、entrypointは `/entrypoint.sh`、実行ユーザーはtableno。ECRへのpush・署名検証はしていない。

Dockerfile/requirements.lock.txt/entrypoint/accounts移行ファイルはcea7e76bから差分なし。依存・apt層をキャッシュ利用し、先頭10層が一致（全14層）。新しいOS修正の取得ではない。accounts/api/schedules/scenarios/support/tableno/static/templatesとtests/unit/integrationの対象拡張子、lock/entrypoint/manage.pyの追跡668ファイルをarchiveとimageのSHA-256で照合した。欠落0・不一致0・Python caches0・Pythonパッケージ111。全filesystem/nativeビルド閉包の証明ではない。

## 配布物内の回帰・通常起動

imageのアプリ・テストソースを重ね替えず、隔離PostgreSQL 18.3で関連490テスト全成功（74.387秒・省略0・終了0）。課金/削除ガード/競合、Stripeリトライ・順序・Dispute・Portal、メール配送/監視、コード利用/失効/再同期、管理操作/手動付与/フォーム/所有者照合、CCFOLIA 6版/7版、ICS購読認可/文字/時刻/calendar APIが対象。Stripeの回帰試験はmockで、実決済の証明ではない。

設定と工具だけread-only mountした。回帰設定は合成PG・locmemメール/cache・一時メディア。Node v20.20.2は既存検証済み工具で、今回binary SHA-256は `6295488653f0d93b0a157841746fef7e72cc4328cfb60c4bbe0ca2668a836ffd`。imageへNodeや代替アプリソースを追加していない。初回は存在しない `accounts.test_character_sheet_6th_api` を指定してimport error、終了1。正しい既存 `accounts.test_character_6th_api` に直して全対象を再実行した。初回を成功件数に含めない。

同じimageの通常entrypointをaws-pre型の合成設定で起動した。PG固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7` はnetwork none・公開ポートなし・512 MiB・DB tmpfs。Redis 7.4.11 `sha256:5509c0097c6064aa8a3b1df58f1d950e67090fffa6678ae8f3f1dc2385f12deb`（128 MiB）とWeb（512 MiB）はPGのnetwork namespaceを共有する。S3無効、SMTPは到達不能なloopback、実Stripeキーなし・課金メール無効で外部通信できない。

空の合成DBへの全移行、静的232件/624 post-process、Daphne起動、check --deploy（0問題）、migrate --check（終了0）、readiness HTTP200/DB・cache正常を確認。billing_release_gateは `ok checkout-disabled` で有料公開ゲート合格ではない。Web収集manifestは232 mapping、cea7e76bから追加/削除0・変更1（`js/arkham.f19def30ae11.js` → `js/arkham.ee6c14cf8a0b.js`）。最新AWSのstatic manifestや全配信bytesとの一致は未検証。

## 実HTTP・管理操作・所有者競合

通常Webへの先行19 HTTP、コード/管理41操作、所有者8 HTTPが最終実行で全成功、計68確認（61 HTTP・7管理コマンド）。管理harnessの13/23/41表示は同一実行の途中経過で、合算しない。各fixtureの再実行も重複加算しない。

- 基本19 HTTP: readiness/ログイン、アイコン4 URLと元bytes一致、CCFOLIA helper bytes、ICS停止GET/HEAD拒否・再有効化・参加資格喪失・token再発行・文字/UTC、無料の通常ユーザーの6版/7版API往復。
- 先行23操作: コード利用/再試行/失効、旧コード保護、手動付与保持、再同期dry-run/実行/再試行、管理者CSRFなし403、最新active/canceled権限同期とactor/監査照合。
- 追加18 HTTP: 実管理フォームの署名付きrevision、GET後更新の古いPOST拒否・全列/管理ログ不変、最新POSTの変更保存・未編集列保持、revision欠落の日本語拒否。停止/復旧/繰り返し/返金確認とactor・監査数、UserAdmin手動付与/無変更/解除とsource/metadataを確認。
- 所有者8 HTTP: 未認証Checkout/Portal各401、保存済みCheckoutのcustomer/metadata/client_reference/subscription_data.metadata不一致各400・保存レコード/監査不変。残る2件は実HTTPがPGの行ロックを待つことを別接続から観測し、所有者を変更してcommit後、Checkout/Portalとも日本語400、購入リクエスト/監査の新規作成0・双方の権限不変。

所有者試験だけ、同一imageの別Webを合成 `STRIPE_CHECKOUT_ENABLED=true`、`RUN_MIGRATIONS=false` で起動した。共有AWSの購入開始は変更していない。HTTP probeにStripe mockはないが、成功する購入や実Stripe連携を確認したものではない。管理session/DRF Tokenはfixtureで注入し、loopback HTTPにproxy-HTTPSヘッダーを付け、fixture CookieJarに限りsecure cookieを返す。実ログイン/OAuth/TLS/ALB/ブラウザーのCookie保護・UI表示・外部受信側の証拠ではない。

初回基本probeはPYTHONPATH不足でfixture作成前に終了1し、`/app:/fixture` を指定して再実行した。初回管理probeは「停止操作後、status=revokedのままで復旧操作だけで有料権限が戻る」と誤認して終了1。既存仕様では復旧はrevoked_at解除/同期でありstatus変更ではない。revoked状態では権限0、合成のactive状態更新を別途行った後は1、再試行は0を確認した。アプリや運用方針は変更せず、合成DBのみidentityを照合してflush・fixture再作成し、基本/管理probeを再実行した。

初回所有者probeは同一transaction内のpg_stat_activity snapshotを更新せず、ロック待機観測が8秒でtimeoutし終了1。transaction rollbackで要求が再開し、Stripe SDKの一覧取得がDNS遮断で失敗、HTTP503となった。この初回を成功・SDK呼出し0とは扱わない。実キー/外部通信/実課金はない。[PostgreSQL公式のsnapshot仕様](https://www.postgresql.org/docs/18/monitoring-stats.html)に従い、観測前に `pg_stat_clear_snapshot()` を追加した。新しい合成ユーザーで再実行し、ロック待機2件・8 HTTP全成功/終了0、Webログでも401×2/400×6を照合した。アプリ変更やAPI mockはしていない。

検証後、今回作ったWeb2/Redis/PGの完全ID・image・network・公開ポートなしを再確認して停止/削除した。PG tmpfsとRedis匿名volumeの合成データを破棄し、fixtureから再作成可能。生成ログ/工具は保存し、実データ・他のコンテナを変更していない。

## OS監査・CI・反映境界

Docker Scout 1.26.0の専用cache・NO_CACHE=true・無抑制全監査は292 indexed/16 vulnerable packages/39 CVE（HIGH3/MEDIUM2/LOW34、Python0）、終了2。SARIF生成は完了、今回archive警告なし。先行1.26.0のCVE IDとの差分0だが、zlibのCVE-2026-85091がLOW→HIGHに再評価されている。同じパッケージ/依存層でありアプリが追加した依存ではない。GCC14関連CVE-2026-102010/CVE-2026-95619もHIGHのまま。指摘抑制・ベース除外・リスク受容・OSゲート合格はしていない。過去HIGH2を現在の候補監査値に転用しない。

20:23 JSTに候補[CI run37197172008](https://github.com/sheepdog0820/iaia/actions/runs/37197172008)のhead SHA一致・completed/successと、Unit / Integration、production-database、system、infrastructure、playwright、lint-securityの全6ジョブsuccessを確認した。先行cea7e76bのCI失敗とは区別する。CI成功はOS/実決済/実環境ゲートの成功ではない。

同時刻の読み取りでmainは8567f49f、開発AWSは定義54・desired/running/pending=1/1/0・COMPLETED/HEALTHY、digest `sha256:adafc0705ded3dabf2a9d2223a5c460b48ff00b2c949f221a4edef3eedee695e`、readinessのDB/cache正常。favicon200、既存invalidation `I2IHZF7QNFDG98Y4IWLQSL6RKV` Completedを再確認した。承認済みアイコン反映は完了済みで、重複反映しない。今回main/ECR/ECS/共有DB/S3/CloudFront/Secrets/IAM/実課金/税設定/常設容量/継続費用を変更していない。元checkoutのハンドアウト未コミット差分を保持する。通常pushはCIのみでデプロイを起動しない。

[管理削除/所有者付け替え方針](SUBSCRIPTION_OWNERSHIP_POLICY_2026-10-04.md)は回答待ちで未修正。既存の誤結合/重複customer、実署名Webhook/実SMTP、外部連携・AWS性能/復旧・事業者/税務条件も未完了。RAK/SDK/API移行等はこの固定候補検証に混入していない。[6b6c570c反映案](AWS_APP_APPROVAL_6B6C570C_2026-10-04.md)やfavicon承認へ後続候補を追加せず、[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。復旧は修正を保持するfix-forwardを優先し、旧版への切戻しが各不備を再導入する点を明示する。この記録のrevertはアプリや稼働版を変更しない。

## 保存証跡

専用保存先は `C:/tmp/iaia-billing-runtime-f4ea34ca`。合成env・工具・大量生成物はGitに含めない。

| 証跡 | SHA-256 |
| --- | --- |
| source-manifest.json | e98191c05e55b6d1fef916dced06236945c8c330690fb6bacad41f290ac3cdc2 |
| inspection.json | d61fc42d4d1204fadf8b67734e1c03645a076fa8db7a46897b232279fbb41466 |
| regression.log | e211b1c84e8d4798faca06d77e8830a44eb9fd26ddc918d875b55d0518343336 |
| base-http.log | ab1c9a9ec1236aa0c2c6499dadaf21c28caffbd37b596c9aaf4ef83cefdf7b3e |
| admin_runtime_probe.py | a3c3c719f898c536927a899960fdf46a8b6aead238ed5354fbfd66bbcf1a9969 |
| admin-http.log | db819663853befb8b188dd8403874d6ac6103c969ad2dee50398dbae8bd01d10 |
| request_owner_http_probe.py | d0bd80586709d8ca95f6b1119ebea0d9feb2c7394ef749ea5de99cfec93ed30a |
| owner-http.log | bad9db744eb8971479054a87cd49d7ae500c577d573972e1850b470efcab0602 |
| staticfiles/staticfiles.json | 20af8bfd892374b30973bd097c015e79a355d09b3273868a8bf7806d709c11f0 |
| runtime-full.sarif.json | ff5919a16274e41e04ac1f4555739873fea74166e525c21dc840eef559cca6fa |
