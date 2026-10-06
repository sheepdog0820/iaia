# Google結果不明検出の通常配布物・実worker検証（2026-10-06）

## 結論・固定対象

[実行期限・結果不明の修正](GOOGLE_EXECUTION_OUTCOME_2026-10-06.md)を通常imageへ構築し、実PG/Redis/HTTPによるworker強制停止8ケース、元配送4件の復元、生存workerへの遅い応答4ケースで検証した。期限経過後の結果不明・進捗/入力/実行IDの保持・再試行拒否・追加送信なしを確認した。先行[29ef実worker停止](GOOGLE_WORKER_CRASH_2026-10-06.md)のrunning固定とは違い、修正後の通常配布物で判定できた。ただし自動回復・実Google・長期保存・公開合格ではなく、正式公開 **No-Go** を維持する。

固定コミットは `f1f9c44375b1482d82deb9c6a2f015d054abaf0b`、証拠ブランチは `codex/google-runtime-outcome-20261006`。今回のリポジトリ変更は本書と受入表だけで、製品source/schema/依存・設定の追加変更を含まない。

- 完全SHAのgit archiveを専用 `D:/tmp/codex-google-runtime-outcome-20261006/source/` へ展開し、通常Dockerfile/.dockerignoreで構築した。
- imageは `sha256:9735d7a06d7772336d7be323ff4746cf05f4f71918153f0b7e48a9323bacd70a`、タグ `tableno:google-runtime-f1f9c443`、1,286,313,486 bytes、amd64/user tableno/通常 `/entrypoint.sh`。OCI revisionは固定コミット、imageの実Pythonは3.11.17。
- 選定source/assets **705件**の欠落/追加/SHA256不一致0・Python cache0・entrypoint bytes一致。先行と同じアプリ/static/templates/tests(unit/integration)の選定拡張子、lock/entrypoint/manage.pyが対象で、全tracked filesやMarkdown/TypeScript E2Eの一致を主張しない。
- インストール済み111 packagesと先行29efの依存側10 image layersの差分0。依存構築はCACHEDで、APT候補の最新調査・native閉包やOS問題解消ではない。
- /appの差替え、source overlay、追加pip installはしない。実broker/worker試験ではtask/queueをmockせず、回帰のmockは後述のとおり区別する。読取helperだけを/evidenceへmountする。通常entrypoint/read-only root/cap-drop ALL/no-new-privilegesで実行する。

## 通常配布物の回帰

専用PG 18.3の固定image、network none・公開port/volume mountなし・512 MiB/2 CPU・DB512 MiB tmpfs。Google試験は同じnamespace内 `127.0.0.1:5432` の合成DB `google_outcome_fixture` に限定し、test DBをDjangoが分離する。2 CPU/2 GiBのGoogle回帰、network none・1 CPU/1 GiB・/tmp SQLiteの設定回帰を並列実行した。空ENV_FILE/local/自動migrate・collectstatic・dev-user作成無効、S3/Sentry無効、実資格情報なし。

| 対象 | 実測 |
| --- | --- |
| Google連携・非同期ジョブ24 modules | 208成功・省略0、68.357秒、終了0/OOMなし |
| local/production設定・SDK/Sentry/ログ保護6 modules | 70成功・省略0、64.735秒、終了0/OOMなし |

両集合は非重複の計278種類。前者は先行23 modulesに `schedules.test_google_execution_outcome` の18メソッドを追加し、新しい実PG行ロック待機2ケースを省略せず実行した。多くのprovider/queueは既存unit fixtureのmockだが、Calendar loopback8ケースは元Requests transportを保持し、その他のunmocked HTTPを拒否する。以下の実broker/worker/HTTP試験はこれとは別である。host文書39件も通常imageの278件に合算しない。

## 実worker強制停止8ケース

上記PG namespaceのloopbackに固定Redis 7.4.11を起動する。128 MiB/1 CPU・/data64 MiB tmpfs・save/AOF無効、合成認証、broker DB7/result DB8。各appは1 GiB/1 CPU、soloまたはprefork/concurrency1、gossip/mingle/heartbeat/beatなし。Requests transportだけを許可Google URLから `127.0.0.1:8015` の合成HTTPへ置換する。製品の実Celery配送・claim/認可/DB処理を通す。SheetsはRAW/ヘッダー17セルで、キャラクター行や複数chunkは今回対象外。

APIはASGI経由ではなく、Django APIClientから実APIView/DB/serializerを呼ぶ。202/queued=true、HTTP到達・進捗10・実行UUID/既定960秒期限を確認し、HTTP受信後未適用、または合成外部適用後応答保留でready markerを出す。hostは完全ID/name/label/image/mount/namespaceを照合して対象worker container全体へSIGKILLを送る。8 workerすべて終了137/OOMなし。preforkの子だけの停止、ECS停止猶予、実hard/soft limit試験ではない。

replacement worker後の5.0388～5.0443秒、計160 snapshotで期限内の元jobがrunning/追加HTTP0のままであることを確認した。期限内の同一job手動配送8件はinactive-job。**worker死亡を即断する判定ではない。** 合成DBの `execution_deadline` だけを過去へ変更して、各worker方式で次の4経路を通す。実時間16分の待機や製品設定変更ではない。

| 対象・外部適用（solo/prefork各1件） | 最初の判定経路 | 判定後 |
| --- | --- | --- |
| Calendar未適用 | 要求した所有job詳細 | 結果不明/進捗10、再試行400 |
| Calendar適用後応答前 | 所有者一覧・uncertainフィルター | 同上 |
| Sheets未適用 | 所有job再試行 | 同上・新job/配送なし |
| Sheets適用後応答前 | 実expire_async_jobs | 同上・未期限切れの削除0 |

全8件で日本語案内・検出終了時刻を保存し、payload/進捗/result/開始/実行UUID/診断ID/保存期限を保持した。詳細200/uncertain、内部UUID/実行期限/payloadの公開なし、再試行400・同一案内。判定後の手動同一job配送8件もinactive-job/DB行無変更・追加HTTP0だった。実HTTP計8回/合成providerエラー0、未適用4件は外部変更0・適用後4件は変更1回ずつ。Calendar4同期はpending/外部ID空のままであり、結果照合・同期行の回復は未実装。

acks_lateはfalse、reject_on_worker_lostはnull。soloの元taskは実Redis unackedに残り、preforkの元taskはそこに残っていない。設定だけで配送済み/喪失を断言しない。5秒観測から永久不配送や自然な長時間回復を推定しない。

## 元メッセージの復元・実HTTPの遅い応答

soloの元delivery tag/task ID4件を実Redisとjobで照合し、該当unacked_index時刻を0へ変更して実Kombu `restore_visible(interval=1)` を呼んだ。既定visibility_timeoutは3600。**1時間待った試験ではなく隔離Redisへの時刻経過注入**で、task差替えや新task.delayによる代用ではない。

別の実prefork workerが元ID4件を受信し、Celery SUCCESS/inactive-job、製品jobは結果不明/進捗10/全DB値保持だった。HTTP禁止transportの禁止marker0、queue/unacked/index0。Celery SUCCESSをGoogle連携成功とは扱わない。その後に合成保存期限を過去へ変更し、実expire_async_jobsが8 jobを削除、pending同期4件を残した。既存通常7日保存を変えず、結果不明の永久保存・外部取消・回復を保証しない。

追加で生存中prefork worker/concurrency1を使い、Calendar/Sheets×遅い200応答/適用後socket切断の4ケースを実loopback HTTPで確認した。HTTP受信・適用後に応答を保留し、合成DBの実行期限を過去へ変更・実詳細APIで結果不明へ分類してから応答を解放した。4件すべてCelery inactive-job、結果不明/進捗10/全job値保持、再試行400、外部変更各1/追加送信なし/providerエラー0。workerの停止やTask.retryのmockではない。

Calendarの遅い200は既存処理どおり同期行だけsynced/外部ID保存となり、socket切断はpendingのままだった。これはjob UUIDが同期行まで完全にfenceする証拠ではない。両方ともjobは結果不明のままで、外部結果の確定・回復UIは別途必要。12 HTTPケースの実行UUIDは12種類、HTTP計12/合成適用8/providerエラー0。

## 新規OS監査・CI・残条件

既存の固定Scout1.26.0（git ee73e17cd5243bd85c30416b274c339ad5e2f284）を新しい専用cacheで実行し、固定タグが上記image IDであることを照合した。既定docker scoutは1.5.0だったため、それを1.26と誤認せず既存の1.26 binaryを明示した。追加インストールや抑制・only-fixed/base除外・リスク受容なし。

292 packages、16 vulnerable packages、39指摘（CRITICAL0/HIGH3/MEDIUM1/LOW35、Python0）、終了2で**未合格**。先行29efとのCVE/severity/package差分0。HIGHはgcc-14のCVE-2026-102010/CVE-2026-95619、zlibのCVE-2026-85091でfixed versionはいずれもnot fixed。新規実行日時/SARIF/終了metadataを保存するが、APT修正版やnative閉包の新規調査は今回行わない。

19:31 JST確認時点で固定f1f9c443の[CI 37448244522](https://github.com/sheepdog0820/iaia/actions/runs/37448244522)は5成功/Playwright実行中だった。同じ生きたrunを中断/再実行せず、19:37 JSTの再照合で全6項目成功を確認した。今回の証拠文書追加の全CIとは区別する。

実Google OAuth/refresh/write/ETag/公開審査、実AWS/常設worker・Redis・beat・監視、Web/U2NET/ブラウザー/負荷、SMTP/課金・性能・整合復旧・事業者運用等は今回未検証。durable outbox/producer transaction、自然な長時間回復、FAILEDの古い配送取得、別job/同期世代の排他、部分出力・遠隔編集との結果照合、長期証跡・限定回復UIは未完了。再接続後の旧外部予定方針は未回答の人間判断を維持する。OS HIGH3を含む未達条件が残り、正式公開No-Goを維持する。

## 清掃・承認境界・保存証拠

19:29:17 JSTに完全ID/name/label/image/namespace/mount/終了状態を照合して専用35 containerを削除した。回帰/client/replacement/restore/late workerは終了0、意図した8 workerのみ137、全OOMなし。最終SQLは未期限切れの結果不明4 job、Calendar pending5/synced1、合成user12、test DB0。Redis queue/unacked/index0。PG/Redis/tmpfsを破棄し、対象label container/volume残数0。通常image/archive/helper/source/証拠は保持し、合成データは再作成可能である。

同時点のmainは8567f49f。AWS/ECR/ECS/S3/CloudFront、共有DB/schema/実ユーザーデータ、Secrets/IAM、課金/容量/継続費用・外部通知を変更せず、完了済みアイコン反映承認に今回を追加しない。元worktreeの13 dirty項目を保持する。新migration 0056の共有適用・main/AWS反映には候補を明示した別承認と新旧worker排出/復旧計画が必要で、accounts0065～0067等を含む未適用migrationも対象稼働版から確認する。今回文書だけの復旧は通常revertで、稼働版や遠隔データに影響しない。

`D:/tmp/codex-google-runtime-outcome-20261006/` に以下の固定証拠とcommand/helper・個別case logs/inspect・manifests・SQL/Redis清掃を保存する。生成物や合成認証情報をGitへ混ぜない。

文書追加後のhost文書回帰39件成功（初回0.037秒・レビュー追記後0.045秒・終了0）、固定証拠10 SHA256と相対文書リンク2件を照合した。staged 2文書のUTF-8/LF/BOM/置換文字・差分チェックに合格し、日本語・mock/実配送/時刻注入・未達条件を自己レビューして追加指摘なし。formatter対象の製品Python/JavaScriptを今回変更しない。

| ファイル | SHA256 |
| --- | --- |
| source.tar | 64d98c6e0bf212bb721063867f9b3d5f19a14d6dc03aa3fe908f529c1acd35d1 |
| distribution-check.json | c266636e53575c368422f51dec20ccf771d1ba0e26ac49529a0336aa53874703 |
| regression-tests.log | f13539a936958fafbd30782878b87500abc6d7368671712d5521ffbed2650189 |
| regression-settings.log | 31adb3e63929e281c2b37db9905b6cce3e4e2b1bdf6a6eee7cb93913845c1f48 |
| results.json | ac5b177644bd07d12768101ad0363aa03c4b5cb399e81368b9893ef9ca065445 |
| restore-results.json | ed9d8ae7917ced713313b91f8a857fcc239a99156a054d52e8ec4eea1a292a04 |
| late-results.json | e9a861ac528caa6699bf385c76da2d369d9e74b525b32a0cb95eb548fdfa408a |
| scout.sarif.json | 1027ec99acf7f636d52ad912840d89c415a418d5169f99902866c6b6800b061d |
| containers-before-cleanup.json | 47f094c4cbf8fe877c80e6bc826ba6deff7fb5779f175efed477ec2dffd69611 |
| cleanup.json | 49c105dcacfb2a5554df223f0c69df358c0221c8825281c2939888f5dad45064 |
