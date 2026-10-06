# Google連携の通常配布物検証（4535c03f）

## 固定対象・一致検査

対象は `4535c03f62814133620fb0313c9ad545bff8cb02`。証跡用ブランチは `codex/google-runtime-4535c03f-20261006`。[開始取得](GOOGLE_JOB_START_CLAIM_2026-10-06.md)までの対象・内容・所有権・再入対策を、[先行a266dd12配布物](GOOGLE_RUNTIME_A266DD12_2026-10-06.md)と同じ通常Dockerfile/.dockerignoreで再検証した。今回は製品ソース・依存・設定を変更せず、本書と受入表を更新する。

- 完全SHAのgit archiveを専用ディレクトリへ展開して構築した。未反映候補であり、main/AWS稼働版ではない。
- image ID `sha256:3631f825c95784298c0fe91d1182435b4f3d88d08c3956aa379bc1e4d2b14393`、タグ `tableno:google-runtime-4535c03f`。OCI revisionは対象の完全SHA、amd64/Python 3.11.17/user tableno/通常entrypoint `/entrypoint.sh`、1,286,107,237 bytes。
- 選定source/assets 699件はarchiveとimageで欠落・追加・SHA-256不一致0、Python cache0。entrypointのbytes一致。アプリ・画面・静的資産・unit/integration試験・lock・manage.pyを選定しており、除外されたMarkdown等を全ファイル一致の主張に含めない。
- インストール済み111 packagesと最初の10 image layersは先行a266dd12と一致し、依存構築はCACHED。OS HIGH3を解消する再構築や、native全閉包の証明ではない。
- /appは通常image由来でread-only。source overlay・追加pip install・製品追加patchはない。読取manifest helperとGoogle試験runnerだけを/evidenceへread-only mountし、試験中のmock/HTTP遮断は検証用処理と区別する。

## 隔離条件・実測

専用PG 18.3はnetwork none・公開port/volume mountなし、256 MiB/1 CPU・データ512 MiB tmpfs。Google試験containerだけがそのnetwork namespaceを共有し、127.0.0.1:5432の合成DB `google_runtime_fixture`を使う。Google試験は2 CPU/2 GiB、設定試験はnetwork none・1 CPU/1 GiB、read-only root/cap-drop ALL/no-new-privileges・一時/tmp・通常entrypoint。自動migrate/collectstaticは無効。Django test DBの移行はこの隔離DBだけで行い、実DB・実資格情報・外部サービスに接続しない。

| 対象 | 最終結果 |
| --- | --- |
| Google連携・非同期ジョブ（19 modules） | 160成功・省略0、52.397秒、終了0 |
| local/production設定・アクセスログ・本文/SDK/Sentry保護（6 modules） | 70成功・省略0、48.490秒、終了0 |

Google対象は `accounts.test_google_grant_concurrency`、`tests.integration.test_google_job_authorization` と、schedules配下の `test_async_jobs`、`test_external_integrations`、`test_google_calendar_delivery`、`test_google_calendar_revocation`、`test_google_calendar_event_guard`、`test_google_connection_guard`、`test_google_credential_guard`、`test_google_dispatch_targets`、`test_google_job_target_guard`、`test_google_queued_connection`、`test_google_refresh_concurrency`、`test_google_refresh_integrity`、`test_google_sheets_delivery`、`test_google_sheets_destination`、`test_google_sheets_content_binding`、`test_google_sheets_ownership`、`test_google_job_start_claim`。設定対象はtests.unit配下の `test_local_settings`、`test_production_settings`、`test_server_access_logging`、`test_error_reporting_privacy`、`test_sdk_logging_privacy`、`test_sentry_sdk_privacy`。両集合は非重複で計230種類。hostでの文書39件は別計数で、通常imageから除外されるMarkdownの試験をimage成功へ合算しない。

- 最新の開始競合1試験（Calendar/Sheetsの2 subtest）を含む、実PGの別接続開始/認可/refresh競合5試験を省略せず通過した。Celery Task本体は実行するが、broker/queueとprovider HTTPの多くは既存fixtureのmockであり、常設worker・実brokerの重複受信を証明しない。
- Calendar実Requestsのloopback8ケースも通過した。遮断前に元transportを保持した当該試験だけが動的127.0.0.1宛先を許し、他のunmocked Session.requestは全体runnerで拒否する。If-Matchをwireで確認し、遠隔版変更4ケースは変更0、未変更4ケースは変更1。実Googleの認可/ETag/writeやOAuth審査の証明ではない。
- 設定試験の初回commandは `ENV_FILE` の空値指定が不足し、manage.pyが既定の `/app/.env.development` を要求して試験開始前に終了1となった。対象containerの終端を確認後、検証commandへ `ENV_FILE=` を指定して再実行した。初回ログ・失敗metadataを残し、製品変更・観測timeoutによる再起動・試験失敗の成功扱いをしていない。Google runnerは開始前に空値を明示する。
- 最終containerは両試験終了0/OOMなし。SQLでtest DB0/fixture public tables0を確認後、全4 containerの完全ID/name/label/保存先を照合した。試験container3個を削除し、専用PG `3c69469d5d13` を停止・自動削除して合成tmpfsを破棄した。対象labelのcontainer/volume残数0。実データ・ソースarchive・image・ログ/helperは削除していない。

## CI・残条件・承認境界

文書追加後、hostの文書回帰39件を0.035秒・終了0で確認した。相対文書リンク3件・本書のSHA-256表8件・全15証拠manifestを実ファイルと照合した。日本語説明と実測/未確認の区別を自己レビューし、追加の要修正事項なし。製品表示文言やformatter対象Python/JavaScriptは変更していない。

固定候補の[CI 37422087169](https://github.com/sheepdog0820/iaia/actions/runs/37422087169)は確認時点でSystem/Infrastructure/Lint-Securityの3成功、Unit-Integration/Production Database/Playwright実行中。生きている同じrunを確認し、今回のローカル配布物230成功や先行候補の全CI成功と区別する。

今回新規OS scan・実U2NET/Web HTTP一式・負荷試験は行っていない。OS HIGH3/native閉包、取得後停止/期限超過・failed後duplicate識別・別job同一同期の競合・永続接続先と予定IDの方針、実Google/Discord/X/ICS/CCFOLIA、実課金/共有DB/worker/SMTP、AWS性能/復旧・事業者運用などの公開条件は残る。[正式公開](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goであり、正常配布物の選定回帰だけで全条件達成とはしない。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/schema/実ユーザーデータ、Secrets/IAM、課金/常設容量/継続費用、外部通知は変更していない。完了済みアイコン8567f49fの承認や固定6b6c570c反映案にこの候補を追加しない。元checkoutの無関係13変更を保持する。文書の復旧は通常revertで、製品imageや共有環境・遠隔データに影響しない。

## 保存証拠

`D:/tmp/codex-google-runtime-4535c03f-20261006/` にarchive/build・source/runtime manifests・読取helper・試験runner・初回/最終ログ・初回/最終container metadata・SQL/cleanup JSONを保持する。以下のSHA-256と全15証拠の `evidence-sha256.json` を使い、生成物はGitへ混入しない。

| ファイル | SHA-256 |
| --- | --- |
| source.tar | 925504f804b28733d0ac7c5478c72bc818abc055c01723d36757a33f36c4e834 |
| distribution-check.json | f32ff22fba7c6e47f93006a2f1e43119c4ee3aceb37ae726dd57946497548738 |
| regression-google-pg.log | cbb4527ef4e096dba8740131ad0c73c4f30eea3a2c1b5e91dbff95abf36eb5b8 |
| regression-settings-recheck.log | 4a4a5b27c139e8add9258992b38f22b059635e09334183c8ee585f594018072d |
| regression-settings.log | 39fbe6ad0339acc89ee6a92a31a1f4bc76a2768fcd73940c78566bcb88f2d44c |
| runtime-containers.json | ca389341d7e636459fc392a649a94db22fd5e6d0b49a919a8ae9d0f0b29b5fe5 |
| sql-cleanup.json | 3fedddeb04a5957e1818a04988102a617cc58c2b7de6ede50673b80d9a880c6a |
| runtime-cleanup.json | fd309e9d3a834d45e4839aed6b4b2d6778d8232e9533ab5e40afb840fdafcb55 |
