# Google同期の全5経路: 固定本文・受付台帳・配送意図の同時保存

## 対象と未完了の境界

親は `75b0fb541010d0ae286c15cffa9673a43a3afd7a`、作業ブランチは `codex/google-write-intake-20261007`。[受付台帳基盤](GOOGLE_WRITE_ADMISSION_2026-10-06.md)をCalendar API、Sheets API、Calendar retry、Sheets retry、セッション自動同期の全5経路へ接続する。[対象世代・排他設計](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md)の受付部分であり、**workerはまだ台帳の固定snapshotを消費せず、対象共有の実行holder・HTTP intent/receipt・独立unknown journalは未実装**。先行3件の別Calendar job二重実行、古いreceiptによる後続PENDING上書き、Sheets結果不明後の別job書き込みは、今回だけでは解消しない。正式公開No-Goを維持する。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/実データ、実Google/Stripe/OAuth、Secrets/IAM、実課金/通知、常設容量/継続費用は変更しない。favicon8567f49fの承認を拡張しない。新model/migration/依存/設定/公開API/UIは追加しないが、先行0059/0060の未配備テーブルを必要とするため、そのまま共有環境へ反映できる状態とは報告しない。

## 実装と利用者への影響

- 内部 `google_write_intake` が実際の認可済み対象からsnapshotを導出し、全5producerが配送前に直接呼ぶ。queue関数だけをmockしても受付が存在する。job、admission、対象sequence、SyncのPENDING、既存の暗号化outboxは同じ外側transactionで確定し、途中失敗/rollback/savepoint rollbackで破棄する。callback喪失は確定済みoutboxを失わせない。
- 最新DBのactive owner・enabled・scope・接続binding・資格情報identityを再確認する。Calendarはuser/session/sync IDの一致と現在の閲覧権限、Sheetsは既存values bindingを検査する。受付自体をworkerの実行認可に置き換えず、HTTP前の最新認可確認は今後も必要とする。
- Calendarは既存UUID5の予定keyと本文構築を共通helperへ移し、既存workerのHTTP動作は変えない。受付snapshotはsyncのPK/user/session/created_at、接続世代・credential identity、primary/event ID、既知予定かどうか、upsert/cancel、受付時の予定本文を暗号化保存する。日付なし/取消はevent=Noneと明示operationを保持する。新規POSTのidは本文に埋めず、将来workerが固定event_idから構成する責務として残す。
- Calendarは論理user/sessionと物理account UID/primary/eventの2対象を採番する。Sheetsは検証済みspreadsheet全体を共有対象とし、別owner・別Google接続・別A1 rangeでも同じcounterを使う。これは受付順であり、まだ実行の直列化ではない。本文/UID/資格情報identityは暗号化snapshot内、resource keyは安定SHAで、access/refresh tokenは新snapshotへ保存しない。hashを認可や匿名化と扱わない。
- producerはjob→sort済み対象→Sync更新の順にする。Calendar APIのupdate_or_createをget_or_createへ変更し、retry/自動同期でもSync更新を台帳登録後に移す。旧予定の再連携時の移動・削除・復活方針は決定しない。
- 手動API/retryの不正受付は固定日本語400で、job/受付/配送/元retry markerをrollbackする。自動同期は初期段階で失効owner・欠落資格情報を省略し、受付中の `InvalidGoogleWriteAdmission` だけをowner単位のsavepointで取り消す。セッション編集や他ownerの正常受付を壊さず、本文/ID/例外詳細なしの固定日本語warningを残す。RuntimeErrorやDB障害を成功に変換しない。
- job削除の子行が増えたことに伴い、期限処理の返却数を全CASCADE削除行数ではなくAsyncJobの削除件数へ修正する。保存期限・削除対象は変えず、残るtarget counterはunknown holderではない。削除後も未解決送信を防ぐ独立journalは次の実装が必要。

主な変更は `schedules/google_write_intake.py`、`integration_views.py`、`job_views.py`、`tasks.py`、新規受付/実PG競合テスト2ファイル。PG CI対象に両moduleを追加し、`tests/unit/test_docker_entrypoint.py` で対象の欠落を検査する。

## 最終検証

最終値は同一source SHAの `revalidated` 広域34 modulesとcoverageを採用する。変更前/途中の計測は混ぜない。

| 確認 | 結果 |
| --- | --- |
| PostgreSQL 18.3 広域回帰 | 389成功・省略0、217.230秒 |
| SQLite 広域回帰 | 367成功・PG専用22省略、141.859秒 |
| 新規受付・実PG競合 | 新規20試験成功、2 modulesの348文72分岐先100%・除外0 |
| 製品差分coverage | 4ファイルの差分92文16分岐先100%・未実行/除外0 |
| 品質・schema | Python7のBlack/isort/Flake8/Bandit成功、指摘/除外/抑制0、CI YAML有効、Django check成功、makemigrations --check --dry-runで差分なし |

全5実受付のcallback喪失・配送だけmock・外側/savepoint rollback・途中保存障害、固定Calendar本文、scope/enable/active/閲覧失効、values/sync改変、欠落credential、自動受付失敗の部分rollback、両owner順での正常受付保全、実セッション編集APIの500→200、削除件数とprivate行消去を確認した。セッションAPIの失効は受付地点に限定した合成faultで、実OAuthや別接続での同時失効の実証とは区別する。即時配送拒否の新規試験はqueueをFalseにする限定mockで、実broker拒否とは区別する。

実PGのCalendar API/別元retry/自動同期で、最初のproducerがSync UPDATE待機する時点にtargetのNOWAITが正確にSQLSTATE55P03で拒否され、二つ目のproducerのtarget FOR UPDATE待機を別PIDで観測してからSync lockを解放する。両方202・連続sequenceを確認する。別owner/Google接続/rangeのSheets受付も同じtarget行で2接続の待機後にsequence1/2を確認する。観測timeoutは失敗とし、SQL本文は出力せず合成PID/テーブル名/長さだけを記録する。SQLiteに行lock保証を主張しない。

T01の全5producer受付原子性と固定本文に証拠を追加するが、T11は上記producerの特定競合順の証拠であり、複数owner/batch・対象初回作成・worker/relayを含む全lock順の完了ではない。T13も受付API非露出/暗号文の部分検証で、ログ/backup/共有privacyの全体合格ではない。独立Celery/Redis/通常新配布物/実Googleの対象競合、workerの固定本文消費、3ブラウザー、最新OS監査、AWSは今回未実施。

## 失敗の保持と自己レビュー

先行REDの台帳欠落、scope/enable/active/入力型/閲覧失効の不足を保持して修正した。最初の閲覧fixtureにはgroup所有者権限が残っていたため修正し、実際のvisible queryがfalseになるREDを取り直した。初回PG広域377件は削除件数1!=3で失敗し、その後の新規cleanupも1!=5を確認して修正した。初期385件SQLiteは363成功/PG専用22省略、PGは `.sqlstate` をpsycopg2例外から読むtest driver互換性で3エラー。`.sqlstate`/`.pgcode`を対応し、正確な55P03判定・lock待機条件は維持する。

追加した自動受付失効REDの初回fixtureは固定例外へ引数を渡したTypeError、セッションAPI初回は誤URLの404であり、製品再現とは区別する。修正後に受付失効3エラー・実セッション編集500を再現してからsavepointを実装した。品質helperのPowerShell引数展開失敗と、合成transport字句のBandit1指摘も保持し、引数配列と明示fixture変数へ修正した。新しい除外・nosec・判定緩和は使わない。

先行 `sealed` はPG388成功・SQLite366成功/PG専用22省略だったが、差分coverageで自動同期の即時配送拒否1文/1分岐が未実行だった。未合格のcoverage audit/失敗ログを残し、受付を保全してjob/Syncを失敗にするテストを追加した。製品コードは変えず、両backendの広域回帰とcoverageを同じ最終sourceで取り直した。

新規表示案内は既存の固定日本語400と自動同期の固定日本語warningで、テストに完全一致assertionを置く。secret/本文を例外logへ足さず、他ownerのjob情報をAPIへ露出しない。この受付単位の自己レビューで未解消の修正指摘はないが、前述のworker/全lock順/公開課題は残る。テスト・レビュー・コミット用skillに従い、UTF-8/LF/staged検査を終えてからcommitする。元worktreeのハンドアウト別変更13項目は保持し、混ぜない。

## 証拠・CI・復旧・次の作業

証拠は `D:\tmp\codex-google-write-intake-20261007`。PGは固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、read-only・512MiB/2CPU・localhost55448のみ・合成tmpfs・volumeなし。SQLiteはmemory DB。最終ソース8パスの実行前後SHAとbackend間一致を確認した。所有ID/name/label/image/port/mount/stateとSQL空状態を照合し、先行fixtureは6:37:02 JST、再検証fixtureは6:42:56 JSTに撤去した。各停止終了0・OOM false・public tables/test DB/他active connection0、残container/volume0。合成tmpfsのみを削除し復旧対象ではなく、全失敗/成功ログ・最初/再検証のinspect/cleanup/SHA証拠は保持する。

親75b0fb54の[CI run 37530738778](https://github.com/sheepdog0820/iaia/actions/runs/37530738778)は10月7日6:29頃の読み取りでhead SHA一致・全6成功を確認した。今回候補のCIとは区別する。workflowは検査のみで、作業ブランチ通常pushはAWS反映を起動しない。GitHub open Issueは別件#1のみ、先行403/CLI未認証による新Issue未作成は維持し、[下書き](GOOGLE_DURABLE_DELIVERY_ISSUE_DRAFT_2026-10-06.md)を更新する。権限変更や別アカウント探索はしない。

コード取り消しはcommitのrevertで行い、共有DBへDROP/逆移行を実行しない。将来配備では先行未配備migrationとworker移行・旧処理drain・送信停止/証拠保持・保存方針を含む別実施案を用意する。旧版workerへの切り戻しを安全なunknown解除とみなさない。

次はworkerが固定snapshot/FIFOを消費し、job削除で消えない対象holder・HTTP intent/receipt・outbox待機・独立unknown journalを実装する。後続PENDING保全、古いtoken拒否、全lock順、cleanup/legacy/drain/限定回復、UI、通常配布物の実プロセスfault、承認済み実Googleを順に検証する。OS HIGH3、実課金・外部連携・運用・性能・復旧・公開方針等は残り、受付単位の成功で正式公開No-Goを解除しない。
