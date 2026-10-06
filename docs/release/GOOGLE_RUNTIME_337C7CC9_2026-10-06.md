# Google連携の通常配布物検証（337c7cc9）

## 固定対象・一致検査

対象は `337c7cc9032bcba24bf4bd25f420c06a834f700f`、証跡用ブランチは `codex/google-runtime-337c7cc9-20261006`。[先行4535c03f配布物](GOOGLE_RUNTIME_4535C03F_2026-10-06.md)以降の[配送中ジョブ有効性](GOOGLE_JOB_ACTIVE_GUARD_2026-10-06.md)・[配送ID境界](GOOGLE_DISPATCH_IDENTITY_2026-10-06.md)を含む通常Docker配布物を検証した。今回は製品ソース・依存・設定を変更せず、本書と受入表の2ファイルだけを更新する。

- 完全SHAのgit archiveから専用ディレクトリへ展開し、通常Dockerfile/.dockerignoreで構築した。作業中のcheckoutをoverlayせず、main/AWS稼働版とは区別する。
- image ID `sha256:598028f8d9beb8e9f0b00217190d1c83db68922713089674bde8725b9a2cb918`、タグ `tableno:google-runtime-337c7cc9`。OCI revisionは対象の完全SHA、amd64/Python 3.11.17/user tableno/通常entrypoint `/entrypoint.sh`、1,286,165,826 bytes。
- 選定source/assets 701件はarchiveとimageで欠落・追加・SHA-256不一致0、Python cache0、entrypoint bytes一致。accounts/api/schedules/scenarios/support/tableno/static/templates/tests(unit/integration)の対象拡張子とlock/entrypoint/manage.pyを選定した。全tracked filesやMarkdown/TypeScript E2Eの一致を主張しない。
- インストール済み111 packagesと最初の10 image layersは先行4535c03fと一致し、依存構築はCACHED。依存層一致を脆弱性解消やnative全閉包の証明にしない。
- /appは通常image由来のread-onlyで、source overlay・追加pip install・製品patchなし。読取manifest helperと試験runnerだけを/evidenceへread-only mountした。runnerのmock/HTTP遮断は検証用処理と区別する。

## 隔離条件・実測

専用PG 18.3はnetwork none・公開port/volume mountなし、256 MiB/1 CPU、データ512 MiB tmpfs。Google試験だけがそのnetwork namespaceを共有し、127.0.0.1:5432の合成DB `google_runtime_fixture`を使用する。Google試験は2 CPU/2 GiB、設定試験はnetwork none・1 CPU/1 GiB、read-only root/cap-drop ALL/no-new-privileges、一時/tmp、通常entrypoint。空ENV_FILE・自動migrate/collectstatic/dev-user作成の無効化を明示した。Django test DBの移行は隔離DBのみで、実DB・実資格情報・外部サービスには接続しない。

| 対象 | 最終結果 |
| --- | --- |
| Google連携・非同期ジョブ（21 modules） | 173成功・省略0、59.405秒、終了0 |
| local/production設定・アクセスログ・本文/SDK/Sentry保護（6 modules） | 70成功・省略0、53.738秒、終了0 |

Google対象は先行4535c03f記録の19 modulesと `schedules.test_google_job_active_guard` / `schedules.test_google_dispatch_identity`。設定対象はtests.unit配下の `test_local_settings`、`test_production_settings`、`test_server_access_logging`、`test_error_reporting_privacy`、`test_sdk_logging_privacy`、`test_sentry_sdk_privacy`。両集合は非重複で計243種類。host文書39件は別計数であり、imageから除外されるMarkdownの試験を配布物成功へ合算しない。[登録開始条件](SIGNUP_READINESS_2026-10-06.md)の3ブラウザー87件は先行host結果であり、今回のimageで再実行した結果とはしない。

- 実PGの別接続開始/認可/refresh競合5試験を省略せず通過。Celery Task本体は実行するが、broker/queueとprovider HTTPの多くは既存fixtureのmockであり、常設worker・実brokerの重複受信を証明しない。
- Calendar実Requestsのloopback8ケースを通過。遮断前に元transportを保持した当該試験だけが動的127.0.0.1宛先を許し、他のunmocked Session.requestはrunnerで拒否する。If-Matchをwireで確認し、遠隔版変更4ケースは変更0、未変更4ケースは変更1。実Googleの認可/ETag/writeやOAuth審査とは区別する。
- 初回commandは環境変数DB_ENGINEへDjango内部ENGINE文字列を誤指定し、両containerとも `Unsupported DB_ENGINE` で試験開始前に終了1となった。終端を確認後、環境変数の仕様通り `postgres` / `sqlite` へ訂正し、別名containerで再実行した。初回ログ・metadataを保存し、製品変更や初回成功扱い・観測timeoutによる再起動はしていない。
- 最終両試験は終了0/OOMなし。SQLでtest DB0/fixture public tables0を確認し、全5 containerの完全ID/name/label/image/保存先を照合した。終端の試験container4個を削除し、専用PG `ae74a983ee14` を停止・自動削除して合成tmpfsを破棄した。対象labelのcontainer/volume残数0。実データ・ソースarchive・image・ログ/helperは削除していない。

## 新規OS監査・CI・残条件

固定image IDへ既存Scout **1.26.0**（git ee73e17cd5243bd85c30416b274c339ad5e2f284）を使用し、新規cache/tempで全OS scanを実行した。292 packages、16 vulnerable packages、39指摘（CRITICAL0/HIGH3/MEDIUM1/LOW35、Python0）、scan終了2で未合格。抑制・only-fixed/base除外・リスク受容は行っていない。先行SDK runtime SARIFとのCVE/severity/package差分0で、SARIF bytesも同一だが、今回の新規実行ログ・終了metadataを別に保存する。

HIGHは `CVE-2026-102010` / `CVE-2026-95619`（gcc-14 14.2.0-19）、`CVE-2026-85091`（zlib 1:1.3.dfsg+really1.3.1-1）、いずれも今回reportのfixed versionは `not fixed`。今回APT候補やnative閉包の再調査は実施していない。Python0・ソース一致・回帰成功をHIGH解消とは扱わない。

2026-10-06 16:15 JSTの固定候補[CI 37427440562](https://github.com/sheepdog0820/iaia/actions/runs/37427440562)はSystem/Infrastructure/Lint-Security/Production Databaseの4成功、Unit-Integration/Playwright実行中。完全SHAを確認し、生きている同じrunを中断・再実行していない。先行25ef552eの全6成功や今回の配布物243成功とは区別する。以下の先行記録のCI未確認等は、それぞれ記録時点の状態として保持する。

文書追加後のhost文書回帰は39件成功・0.035秒・終了0。初回host commandは検証用TEST辞書の置換でDjango既定MIRRORを欠落させ、試験開始前にKeyErrorで終了1となった。既定辞書を保持してNAMEだけをメモリーへ指定するcommandへ訂正し、製品ファイル/DBを変更せず再実行した。表の実ファイルSHA-256 9件、相対文書リンク5件、証拠manifestを照合した。説明の日本語・実測/未確認の区別を自己レビューし、追加の要修正事項なし。製品UI文言やformatter対象Python/JavaScriptの変更はない。

実U2NET/Web HTTP一式・ブラウザー・負荷試験は今回は行っていない。OS HIGH3/native閉包、原子的取消・絶対期限/試行lease・failed後duplicate識別・別job同一同期の競合・永続接続先と予定IDの方針、実Google/Discord/X/ICS/CCFOLIA、実課金/共有DB/常設worker/SMTP、AWS性能/復旧・事業者運用等は残る。[正式公開](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goであり、選定回帰と通常配布物検証だけで全条件達成とはしない。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/schema/実ユーザーデータ、Secrets/IAM、課金/常設容量/継続費用、外部通知を変更せず、完了済みアイコン8567f49f承認や固定6b6c570c反映案へ追加しない。元checkoutの無関係13変更を保持する。変更文書の復旧は通常revertで、製品image/共有環境/遠隔データに影響しない。

## 保存証拠

`D:/tmp/codex-google-runtime-337c7cc9-20261006/` にarchive/build・image inspect・source/runtime manifests・helper/runner・初回/最終ログ・container metadata・SQL/cleanup・Scout SARIF/log/summary/終了metadataを保持する。SHA-256表と `evidence-sha256.json` を実ファイルと照合し、生成物はGitへ混入しない。

| ファイル | SHA-256 |
| --- | --- |
| source.tar | 00bb620622829f2904f4f2287bd1c787b8b76bade66d3b3f25c758092772f3ad |
| distribution-check.json | 2b2406e6073d941ffb00f175544e5eab2ac4b6f4e9700f0776ed37d3b97c16ef |
| regression-tests-recheck.log | 6ade589708a449c5daeadbcfbeeef967a40892700abe2ba0354221a066b0189a |
| regression-settings-recheck.log | 9c3cbcec9cc177ab1346e846f0ce36f4b40e6a14655305502a6add4ddff94ac3 |
| scout.sarif.json | f7928c21ead7b05de6ea774993e0a92db59c0ceef768ff0b0559d573170957df |
| scout-summary.json | c5c990a063928fe1254e6fae81c58d2a9f2f9d1544a616c2126bca6f4d36580b |
| runtime-containers.json | 93039dc2ea1d0bbd97406fe4290af9b7b6117fd328acac5c21f95447b96af21f |
| sql-cleanup.json | b7eaf42018010de716985c8b3d17e16e29868c06c9db42237471266c599c2c7f |
| runtime-cleanup.json | fff76718604a2cbf390d78a2d94b96a7f22fb221bc6e53dd4ca9716c9df1eac2 |
