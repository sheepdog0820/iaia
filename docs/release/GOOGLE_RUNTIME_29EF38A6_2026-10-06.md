# Google連携の通常配布物検証（29ef38a6）

## 固定対象・一致検査

対象は `29ef38a65553d2cd453af78671146fd75b18e82b`、証拠用ブランチは `codex/google-runtime-29ef38a6-20261006`。[先行337c7cc9配布物](GOOGLE_RUNTIME_337C7CC9_2026-10-06.md)以降の[Calendar対象削除ガード](GOOGLE_CALENDAR_DELETED_TARGET_2026-10-06.md)・[投入結果とworker状態の保全](GOOGLE_DISPATCH_STATE_2026-10-06.md)を含む。製品ソース・依存・設定は変更せず、本書と受入表の2文書を更新する。

- 完全SHAのgit archiveを専用ディレクトリへ展開し、通常Dockerfile/.dockerignoreで構築した。mutable checkoutのsource overlayや追加pip install、製品patchは行わない。
- image ID `sha256:8d0228736282a4d22f3377c7b97de97a2579f8ef31cf0436800568f3dc41357a`、タグ `tableno:google-runtime-29ef38a6`、1,286,226,108 bytes。OCI revisionは対象の完全SHA、amd64/Python 3.11.17/user tableno/通常entrypoint `/entrypoint.sh`。実際の通常image内 `python --version` も照合した。
- 選定source/assets 703件はarchiveとimageで欠落・追加・SHA-256不一致0、Python cache0、entrypoint bytes一致。先行と同じaccounts/api/schedules/scenarios/support/tableno/static/templates/tests(unit/integration)配下の選定拡張子、lock/entrypoint/manage.pyを対象にする。全tracked files、Markdown、TypeScript E2Eの一致を主張しない。
- インストール済み111 packagesと最初の10 image layersは先行337c7cc9と一致。依存構築はCACHEDであり、依存更新やAPT候補の最新確認、native閉包/脆弱性解消とは区別する。
- build log先頭にDocker pipe prefaceの診断があるが、buildは終端0、固定image生成とsource照合を確認した。途中観測のtimeoutを失敗扱いにして再buildしていない。

## 通常配布物の実行試験

/appは通常image由来のread-only、cap-drop ALL/no-new-privileges、一時/tmp、通常entrypoint。空ENV_FILE、local環境、自動migrate/collectstatic/dev-user作成の無効化を明示する。Google試験だけが読取runnerを/evidenceへread-only mountし、fixtureのHTTP mock/遮断と製品修正を区別する。

専用PG 18.3はnetwork none・公開port/volume mountなし、256 MiB/1 CPU、512 MiB tmpfs。Google試験は同じnetwork namespace内の `127.0.0.1:5432` の合成DB `google_runtime_fixture` のみへ接続し、2 CPU/2 GiBで実行する。設定試験はnetwork none・1 CPU/1 GiB、SQLiteの隔離設定。実DB・実資格情報・外部サービスに接続しない。

| 対象 | 結果 |
| --- | --- |
| Google連携・非同期ジョブ（23 modules） | 190成功・省略0、66.039秒、終了0 |
| local/production設定・ログ/SDK/Sentry秘匿情報保護（6 modules） | 70成功・省略0、67.312秒、終了0 |

Google対象は先行21 modulesと `schedules.test_google_calendar_deleted_target` / `schedules.test_google_dispatch_state`。設定対象はtests.unit配下の `test_local_settings`、`test_production_settings`、`test_server_access_logging`、`test_error_reporting_privacy`、`test_sdk_logging_privacy`、`test_sentry_sdk_privacy`。両集合は非重複の計260種類。host文書試験は別計数で、imageから除外されたMarkdownの試験を通常配布物成功に合算しない。

- PG専用7メソッド（別接続競合6メソッドと時間制限付きロックprobe）を省略せず実行した。Celery Task本体は実行するが、broker/queueと多くのprovider HTTPはfixtureのmockであり、常設worker/実brokerの受信や実Googleを証明しない。
- Calendar実Requestsのloopback8ケースは遮断前に元transportを保持し、その試験だけが動的127.0.0.1宛先を許す。他のunmocked Session.requestはrunnerで拒否する。遠隔版変更4ケースは変更0、未変更4ケースは変更1でIf-Matchをwire確認する。実Googleの認可/ETag/write/OAuth審査とは区別する。
- 新しい対象削除・投入状態試験をimageから実行し、削除後の保存/同PK新世代保全と、別接続workerが開始/完了した後にpublisher応答を失う4ケースを通過する。先行hostの成功を代用していない。
- 初回PG readinessは初期化中で `no response`、同じcontainerを再確認してreadyになった。再作成や試験前停止はない。両試験containerは終了0/OOMなしを確認した。
- 17:14:43 JSTに全3 containerの完全ID/name/label/image/保存先を照合し、test DB0/fixture public tables0をSQL確認した。終端の試験container2個を削除し、専用PGを停止・自動削除して合成tmpfsを破棄した。対象labelのcontainer/volume残数0。ソースarchive・通常image・ログ/helperと元worktreeの別作業13項目を保持する。

## 新規OS監査・CI・残条件

既存Scout **1.26.0**（git ee73e17cd5243bd85c30416b274c339ad5e2f284）を固定image IDに対して、新規cache/tempで実行した。292 packages、16 vulnerable packages、39指摘（CRITICAL0/HIGH3/MEDIUM1/LOW35、Python0）、終了2で未合格。抑制、only-fixed、base除外、リスク受容を行わない。先行337c7cc9 SARIFとのCVE/severity/package差分0、SARIF bytesも同一だが、今回の新規実行ログ・終了metadataを保存する。

HIGHは `CVE-2026-102010` / `CVE-2026-95619`（gcc-14 14.2.0-19）、`CVE-2026-85091`（zlib 1:1.3.dfsg+really1.3.1-1）、いずれもreportのfixed versionは `not fixed`。今回APT候補/native閉包の再調査は行わず、Python0・source一致・回帰成功でHIGHを解消したとはしない。

17:17 JST確認時点の固定候補[CI 37433985459](https://github.com/sheepdog0820/iaia/actions/runs/37433985459)はInfrastructure/Lint-Security/Production Database/Systemの4成功、Unit-Integration/Playwright実行中。先行72136cf9の[CI 37431920504](https://github.com/sheepdog0820/iaia/actions/runs/37431920504)は全6成功を確認済み。今回の通常配布物260成功や先行全6成功を、今回全CI成功の代用にしない。同じ生きたrunを中断・再実行しない。

実U2NET/Web HTTP一式・ブラウザー・負荷試験は今回行っていない。OS HIGH3/native閉包、outbox/投入応答不明・外側transaction/未commit・lease/failed duplicate・別job同一sync版競合・永続Google接続先IDの方針、実Google/Discord/X/ICS/CCFOLIA、実課金/共有DB/常設worker/SMTP、AWS性能/復旧・事業者運用等は未達。[正式公開](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goのまま維持する。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/schema/実ユーザーデータ、Secrets/IAM、課金/常設容量/継続費用、外部通知を変更しない。完了済みアイコン8567f49f承認や固定6b6c570c反映案に追加しない。文書変更の復旧は通常revertで製品image/共有環境/遠隔データに影響しない。GitHub open Issueは無関係なUI #1のみで、先行の関連Issue作成403を別認証/権限変更で回避しない。

文書追加後のhost文書回帰39件成功（0.036秒・終了0）、表の実ファイルSHA-256 10件と相対文書リンク4件を照合した。現checkoutの選定source/assets 703件も試験archiveと一致し、製品差分を混ぜていない。日本語・実測/未確認の区別・差分を自己レビューし、追加の指摘なし。formatter対象の製品Python/JavaScript・UI文言を変更しない。

## 保存証拠

`D:/tmp/codex-google-runtime-29ef38a6-20261006/` にarchive/build、image inspect、source/runtime manifests、runner/command、試験ログ/container metadata、SQL/cleanup、Scout SARIF/log/summary/終了metadataを保持する。生成物をGitへ混入しない。

| ファイル | SHA-256 |
| --- | --- |
| source.tar | 32819ae7367f31095266c4b28d0ab8a9f90a4f7c0928ef3cfd0fc0a542684d47 |
| distribution-check.json | d2e3d1283eeef4be2dbe6402c3fd581228dd3c26b4093f42a9c32f9e3f193203 |
| regression-tests.log | 99ef6a71aab68ea5b78a01cdfd2d0e1ae6d4382d849fc306c6171ada097a1844 |
| regression-settings.log | f426c35a4ef42e55190410189f2cc4d3eb11315b534fa716f57edaae9b2528fe |
| scout.sarif.json | f7928c21ead7b05de6ea774993e0a92db59c0ceef768ff0b0559d573170957df |
| scout-summary.json | f4dffc52de70925fc263d4fd55ae3bfb5690342f961f3ac2e81db161e7c95a27 |
| runtime-containers.json | ffa0f6fa0850d1be0dcbd0ad981da2a812abb3269d0d6aade30bb13fbd910d1d |
| sql-cleanup.json | 3df5805dc05c3f2663860b255f30eda86d2344e6421326a000f195d51d06e3bd |
| runtime-cleanup.json | c6dfa4f53de11ec1d94e610f40344e32c4454a20898b0c7594d452a14b4a088f |
| runtime-python-version.log | 686560bcd94a5a3fe8187b7c4fc49beaff41c87eccb79908cd3da863ec30e52e |
