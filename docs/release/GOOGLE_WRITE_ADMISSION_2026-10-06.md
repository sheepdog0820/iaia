# Google同期の受付台帳・固定スナップショット基盤

## 対象と未完了の境界

親は `57a240f4a3fa6eaf16a03e0ac49f594993f4a45a`、作業ブランチは `codex/google-write-admission-20261006`。[対象世代・排他設計](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md)の第1段階として、内部受付台帳・transactionで確定するFIFO番号・改変検知付き暗号化snapshotを追加する。**全5producer、Calendar本文の受付時固定、worker/HTTP/receipt、対象待機にはまだ接続していない。** 別Calendar jobの二重実行、古いreceiptによる後続PENDING上書き、Sheets結果不明後の別job書き込みという先行3件の不足は、今回の基盤だけでは解消しない。正式公開No-Goを維持する。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/実データ、実Google/Stripe/OAuth、Secrets/IAM、実課金/通知、常設容量/継続費用は変更しない。faviconのコミット8567f49fの反映承認を拡張しない。新しい依存・公開API・設定・UIは追加しない。新migration 0059/0060は使い捨て隔離DBでのみ検証する。

## 追加した仕様

- `GoogleWriteTarget` はversion・型・namespace付きcanonical JSONのSHA-256をresource keyとし、確定受付番号だけを保持する。Calendar論理user/session、物理account UID/primary/event、Sheetsのspreadsheet全体を別namespaceで識別する。Sheetsはowner/range/接続世代をkeyに含めず、同じ検証済みopaque IDは共有対象となる。大小文字やUnicodeを独断で正規化せず、既存spreadsheet ID検証を使う。SECRET変更でも対象keyは変わらない。
- `GoogleWriteAdmission` はjobの一意受付、owner/type/作成時刻、payload/allocation digest、snapshot binding、暗号文を持つ。`GoogleWriteReservation` は1〜2対象の受付番号を持ち、同対象の番号・同受付の対象を一意制約で守る。job削除はprivateな受付・予約・暗号文を消し、対象counterは残す。counterは**実行holderでも結果不明の禁止でもない**。
- 内部 `register_google_write` は未開始・期限内QUEUED・現行owner/type/作成時刻/payload・手動retry元停止を検査し、source jobを先に、対象keyを常にsort順でロックする。対象初回作成もtransaction内で行い、各対象の単調sequenceを採番する。時刻・UUID・latest-winsには依存しない。rollback/savepoint rollback/途中保存失敗では番号やprivate行を残さない。最大signed bigint到達時は受付を止める。
- snapshotはlock待機**前**にnative JSONとしてbytesへ固定する。tuple/non-string key/NaN/未対応型など、JSON化で意味が変わる入力を拒否する。既存SECRET_KEYから用途別HMAC鍵を導出したAES-256-GCM、ランダム12-byte nonce、受付/job/owner/type/時刻/digestを含むAADで保存する。新しいSecretは作らない。同jobの同内容再受付は同じ暗号文・番号を返し、対象/本文/metadata/予約/暗号文の改変を修復・上書きしない。
- resource key・payload digestは認可や匿名化の保証ではない。snapshotを開く内部helperも実行認可を与えない。実際の対象/接続/権限/本文を安全に導出する責務は、次のproducer接続単位で実装する。SECRETローテーション後の既存cipher復号は今回対応せず、安全側に拒否する。
- 0059は3テーブルと制約を追加し、legacy jobを推測してbackfillしない。0060はPGの2つのFKを正確に検出してDB側CASCADEへ変更し、SQLiteは2つの明示的triggerを追加する。旧アプリのraw job DELETEでもprivateな受付・予約は削除し、counterを残す。reverse0060は通常の遅延FK/triggerなしへ戻す。予期しないbackendや欠落/複数FKは停止する。
- 既存durable dispatchのmigration試験は終了時の復元を0058固定から、試験開始時の最新leafへ変更する。0059/0060がある環境で後続試験のtableを消す後処理の不足を直した。新規migration試験も同じ復元方針にする。reverse/legacy job保全/raw DELETEの元assertionは維持する。

## 検証結果

2026-10-07 00:03 JSTまでに、同一の最終Python 8 source SHAで広域32 modulesを確認した。`sealed` の証拠を最終値とし、変更前の計測を混ぜない。

| 確認 | 最終結果 |
| --- | --- |
| PostgreSQL 18.3 広域回帰 | 368成功・省略0、180.677秒 |
| SQLite 広域回帰 | 349成功・PG専用19省略、122.385秒 |
| 新規台帳/競合/schema試験 | PG31成功、新規2 modulesの452文44分岐先100%・除外0 |
| 製品差分coverage | models/helper/0059/0060の178文48分岐先100%、未実行/除外0 |
| 品質・schema | Python 8 filesのBlack/isort/Flake8/Bandit成功・指摘0、Django check成功、makemigrations --check --dry-runで差分なし |
| 文書 | 更新後の関連39試験成功、変更12 filesのUTF-8/LF/相対リンク・日本語表示文言を確認 |

実PGの異なる接続PIDに対し、対象行のFOR UPDATE待機を2接続、同jobのsource行を2接続、snapshot変更試験のsource行を1接続で観測してからlockを解放した。初回対象作成と逆順2対象の並列受付は対象2件・各sequence 1/2を確認し、同jobは一つの受付を再利用した。呼出元の本文をlock待機中に変えても受付前の固定内容を復号する。対照対象の独立採番・別owner共有Sheet・時刻を逆転したFIFO・rollback/savepoint/途中保存失敗・raw DELETE/schema反転を検証した。PGで0060のSQLite分岐を通す部分はfake schema-editorによるguard試験であり、実SQLiteのtrigger/schema/raw DELETEは別途SQLite回帰で確認している。

T01のhelper単独の原子性、T11のhelper単独のlock順、T13の暗号文/基本schemaは部分的な証拠を得たが、**全5producer・全ワークフロー・ログ/backup等を含む各受入項目全体は未合格**。通常新配布物、実worker/Google、画面、retention、unknown保持の証明へ読み替えない。

先行REDと失敗のログは証拠ディレクトリに保持する。初回module未実装、key設定例外、raw DELETEのFK残存、JSON暗黙変換、待機中の呼出元snapshot変更を再現して修正した。実PGのsourceロック観測でSQLが1023文字に切られてFOR UPDATE位置が見えなかったため、必要な5列だけSELECTするようにし、FOR UPDATEの観測条件を弱めなかった。CLIのLabelsの渡し方によるimport失敗はhelper呼出しを配列に直し、製品失敗と区別する。初回広域PGは旧migration試験の復元不足で後続4ケースがmissing tableとなり、成功扱いにしていない。Banditの固定内部SQL補間1件・合成key字句2件は明示的固定SQL/合成fixture定数へ整理し、除外・抑制を使わない。

実PG独立接続の受付競合を検査するが、独立Celery/Redis/実Googleの競合証明ではない。実行中にunmock Requestsを拒否し、既存のloopback HTTP試験だけ専用経路で許可する。SQLiteではPG専用競合を省略し、SQLiteに行ロックの保証を主張しない。

## 証拠・自己レビュー・復旧

証拠は `D:\tmp\codex-google-write-admission-20261006`。PGは固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、read-only・512 MiB/2 CPU、localhost:55447のみ、合成tmpfs・volumeなし。SQLiteは実DBを開かないmemory DB。実行前後の変更Python source SHAを照合し、同じ最終sourceのcoverageだけを採用した。所有container ID/name/label/image/port/mount/stateとSQL空状態を照合後、2026-10-07 00:03:04 JSTに専用PG/tmpfsの合成データを撤去した。停止終了0・OOM false・残container/volume0、public table/test DB/他active connection0。削除した合成データは復旧対象ではなく、失敗ログ・検証/品質/schema/cleanup/SHA証拠は保持した。元worktreeのハンドアウト別変更13項目は保持・未stageのまま、混ぜていない。

親57a240f4の[CI run 37476516543](https://github.com/sheepdog0820/iaia/actions/runs/37476516543)、先行アプリa91be6b8の[CI run 37473902407](https://github.com/sheepdog0820/iaia/actions/runs/37473902407)は、10月6日23:56頃の読み取りで各head SHA一致・全6ジョブ成功を確認した。これは今回の新候補CIの成功を意味しない。今回の作業ブランチpushが起動するworkflowは検査であり、AWS反映を起動しないことを事前に確認した。GitHub Issueは先行403/CLI未認証により未作成のままで、下書きを更新する。

新規表示文言は例外案内・model文字列表現・schema検査の日本語を確認し、重要な固定例外案内をテストした。API/画面への台帳露出は追加していない。この基盤単位の自己レビューで未解消の修正指摘はないが、上記の未接続/正式公開課題は残る。テスト・レビュー・コミット用skillに従い、無関係な整形を混ぜず、UTF-8/LF/相対文書リンク・stage済み文字列の整合を確認する。ブラウザー確認・通常新配布物・新規OSスキャン・実Google・AWSは今回未実施。直前OS HIGH3は未合格のまま。新しいcounterはowner削除後も残り、小さい内部ID等をhashだけで匿名化したとみなさない。counter/将来holder・attemptの保持/退会条件と旧予定の再連携方針は未承認で、共有配備前に判断が必要である。

隔離DBのschema forward/reverseはlegacy jobを保持し、台帳はbackfillせず、reverse0059では台帳のデータを消すことを試験する。共有環境へDROPを実行する復旧許可ではない。この未接続基盤のコード取り消しはcommitのrevertで行い、共有schema適用が将来承認された場合はデータ保持・送信停止を含む別復旧案を用意する。未来のholderを消して旧workerへ戻す手順として流用しない。

## 次の安全な実装単位

[Issue下書き](GOOGLE_DURABLE_DELIVERY_ISSUE_DRAFT_2026-10-06.md)の全5producerで実対象とCalendar本文を固定し、job/admission/outboxを同時commitする。さらにworker/HTTP intent/receipt/target waiting/独立unknown journalを接続し、設計のT01〜T15を個別に合格させる。現在のproducerはsync行を更新/ロックするため、受付helperのjob→対象lock順をそのまま後付けするだけでなく、workerの対象→syncを含む全経路のlock順を統一して両順序を実測する。helper単独の並列合格を全ワークフローのdeadlock不存在としない。
