# Google連携の通常配布物検証（2026-10-06）

## 固定対象と配布物

対象は `a266dd121fe65558484ee3cc7a8711dfa7a2fff8`。証跡用ブランチは `codex/google-runtime-a266dd12-20261006`。先行の[Calendar予定照合](GOOGLE_CALENDAR_EVENT_GUARD_2026-10-06.md)までのGoogle修正を通常配布物で確認する。今回は製品ソース・依存関係・設定を変更せず、本書と受入表だけを追加更新する。

- 固定コミットのgit archiveから、通常のDockerfile/.dockerignoreで構築した。Webのmain/AWS稼働版とは別の未反映候補である。
- image IDは `sha256:46b133cfc8188eb1056abe26de1f36eba7eb4bc6e023ee4dbda0953aaa46d896`、ローカルタグは `tableno:google-runtime-a266dd12`。OCI revision labelは対象の完全SHAと一致する。amd64・Python 3.11.17・user tableno・entrypoint `/entrypoint.sh`、1,285,999,423 bytes。
- 選定した693 source/assets（アプリ・画面・静的資産・unit/integration試験・lock/entrypoint/manage.py）のSHA-256はarchiveとイメージで欠落/追加/不一致0。Python cache0、`/entrypoint.sh`と製品entrypointのbytes一致。
- 前回[39b43286通常配布物](SENTRY_RUNTIME_39B43286_2026-10-06.md)とインストール済み111 packagesおよび最初の10 image layersが一致し、依存構築はCACHED。すべてのnative build閉包の検証や、新しいOS脆弱性監査の合格を意味しない。
- 試験中のsource overlay・追加pip install・アプリ/SDK monkey patchの製品追加なし。Google試験runnerと読取manifest helperは `/evidence` のread-only mountだけで、`/app`はimage由来かつread-only。runnerのHTTP遮断と試験自身のmockは実サービスへの送信を防ぐ検証用処理である。

## 隔離条件・結果

専用PostgreSQL 18.3はnetwork none・公開portなし・256 MiB/1 CPU、データは専用512 MiB tmpfs。Google試験containerだけがそのnetwork namespaceを共有し、127.0.0.1:5432の合成DB `google_runtime_fixture`を使う。実DB・実認証情報・外部サービスを接続しない。Google試験は2 CPU/2 GiB、設定試験はnetwork none・1 CPU/1 GiB。双方ともread-only root・cap-drop ALL・no-new-privileges・一時/tmp、通常entrypointから明示的な試験commandを実行し、自動migrate/collectstaticを無効にする。Django試験DBの移行は隔離DBだけに適用する。

| 選定範囲 | 結果 |
| --- | --- |
| Google認可/接続/資格情報/待機ジョブ・Calendar/Sheets/refresh競合（13 modules） | 110成功・省略0、25.526秒、終了0 |
| local/production設定・アクセスログ・本文/SDK/Sentry保護（6 modules） | 70成功・省略0、56.463秒、終了0 |

Google対象は `schedules.test_google_calendar_event_guard`、`test_google_calendar_delivery`、`test_google_calendar_revocation`、`test_google_connection_guard`、`test_google_credential_guard`、`test_google_queued_connection`、`test_external_integrations`、`test_google_sheets_delivery`、`test_google_sheets_destination`、`test_google_refresh_integrity`、`test_google_refresh_concurrency`（後続10名もschedules配下）、`accounts.test_google_grant_concurrency`、`tests.integration.test_google_job_authorization`。設定対象は `tests.unit` 配下の `test_local_settings`、`test_production_settings`、`test_server_access_logging`、`test_error_reporting_privacy`、`test_sdk_logging_privacy`、`test_sentry_sdk_privacy`。両集合は非重複で合計180種類、文書試験は含まない（Markdownは通常imageから除外される）。

- Calendarの新規13試験/117 subtestを通常imageでも実行した。実Requestsの8 loopback HTTPケースでは取得したIf-Matchがwire上で保持され、遠隔版変更4ケースは変更0・retryなし、未変更4ケースは変更1。宛先は試験がbindした127.0.0.1の動的portのみ。実GoogleのETag/認可/書き込みを証明しない。
- 全Google試験を囲むSession.request遮断を設け、新規wire試験は遮断前に元transportを保持して当該loopbackだけを許す。PGの実ロック待機によるrefresh/認可競合4試験も省略せず通過した。Celery broker/dispatch・多くのHTTPは既存fixtureのmockで、常設worker運用・実OAuth・ブラウザー実操作の証明ではない。
- 初回の実行前チェックはPowerShellの空PortBindingsオブジェクトのCount判定で停止した。実inventoryは空オブジェクト・network none・公開portなし。プロパティ数での検査に訂正してから試験を開始し、隔離失敗や試験失敗を成功扱いしたものではない。
- 試験終了後、Django test DB0・fixture public tables0をSQLで確認。試験container2個はexit0/OOMなしを確認して削除。専用PG `555238930d79` は完全ID/name/labelを照合して停止・自動削除し、tmpfsの合成データを破棄した。対象labelのcontainer/volume残数0。ソースarchive・ローカルimage・ログ/helperは保持する。実データは変更/削除していない。

## CI・残条件・承認境界

文書追加後のhost文書試験39件は0.035秒・終了0。相対文書リンク2件と保存証拠12件のSHA-256を照合し、対象2文書のUTF-8/LF・空白・完全staged差分を確認した。日本語説明と実測/未確認の区別を自己レビューし、追加の要修正事項なし。製品の表示文言やformatter対象Python/JavaScriptは変更していない。

13:44 JST前後に固定候補の[CI run 37414514659](https://github.com/sheepdog0820/iaia/actions/runs/37414514659)を再照合し、Infrastructure・Lint/Security・Production Database・System成功、Unit/IntegrationとPlaywrightは実行中。実行中を成功扱いせず、文書push後の別runや先行版の全成功と区別する。

今回新しいOS scan・背景透過の実U2NET/Web HTTP一式・負荷試験は行っていない。先行39b43286の個別実証は候補全体の新しい実環境成功に読み替えない。OS HIGH3/native閉包、実Google/Discord/X/ICS/CCFOLIA、実課金/共有DB/worker/SMTP、AWS性能/復旧、事業者運用等の公開条件は残り、正式公開はNo-Goである。

main/AWS/ECR/ECS/S3/CloudFront・共有DB/schema/実データ・Secrets/IAM・課金/常設容量/継続費用・外部通知は変更しない。完了済みアイコン8567f49fの承認や固定6b6c570c案へこの候補を追加しない。元checkoutの無関係ハンドアウト変更は保持する。今回の文書の復旧は通常revertで、製品imageや共有環境を変更せず、Googleの遠隔データを復元する操作でもない。

## 保存証拠

以下は `D:/tmp/codex-google-runtime-a266dd12-20261006/` 配下のSHA-256。生成物はGitへ混入せず、今回の選定範囲を追跡する証拠として保持する。

| ファイル | SHA-256 |
| --- | --- |
| source.tar | 3af4a53b8aa800d3fc822022617ae26e5dd5b4480fd866a14c5cfb0d4c491c71 |
| build.log | 43d0b75fca4f096ab84ebe6d92d8c763a963dd076f0d5b9c853b899fe3f2a641 |
| distribution-check.json | 59c3f59408a3d4a14017a780a5ede80ef75e481176bf16c7d812ded39849a5b7 |
| source-manifest.json | dd9ab406f8a5106c8b9a48b2e680a045468fd4c0bc58fbbcc0ce8216382c22ff |
| runtime-manifest.json | a8f878dc4ec01782f82ea801856449f4a10ed72691ab1effcd1ee9460cc5b089 |
| regression-google-pg.log | 33875d2a58810c59fabd76edbd1bc3aef20c607c316cf0ae89ca9e68f86e6814 |
| regression-settings.log | 57e02ca42a9731bed67977a1fd9ae01e35904517d46f9a5bc7487494d8362e30 |
| run_google_tests.py | 8307f01df6ddc03fd8a78cf056905376cfdcfb6b983f8bb512d2edfa80b07b84 |
| inspect_distribution.py | 4c8e135d25b2e1584aaafadc0430f59ac06a8ddfb9b4d59be95dc39db2217b46 |
| runtime-containers.json | 159ac6dca6966369c159632aaa9599078b82341fca645700522616dac1f7656e |
| sql-cleanup.json | 734fefb91f647c03fc2400f5f2f35d897772bec448e04c51488dc4d6fb8535c4 |
| runtime-cleanup.json | 6bab38642bbcdb248a64d5154c63237ca82062f28dd73e3e0702aaf7a3155061 |
