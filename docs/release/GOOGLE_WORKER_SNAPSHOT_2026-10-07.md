# Google workerの固定受付情報・送信本文検査

## 対象と未完了の境界

親は `d84e051e82bdbf5dfd91924cbfbee5f1e8c4b337`、作業ブランチは `codex/google-worker-snapshot-20261007`。[全5経路の固定受付](GOOGLE_WRITE_INTAKE_2026-10-07.md)を実際のCalendar/Sheets workerへ接続した。受付時の本文・操作・対象を消費する部分実装であり、[対象世代・排他設計](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md)の共有holder、FIFO実行順、HTTP intent/receipt、job削除で消えないunknown journalは未実装。先行の別Calendar job二重実行、古いreceiptによる後続PENDING上書き、Sheets結果不明後の別job書き込みは、この単位だけでは解消しない。正式公開No-Goを維持する。

main/AWS/共有DB/実データ、実Google/Stripe/OAuth、Secrets/IAM、実課金/通知、常設容量/継続費用は変更しない。アイコン8567f49fの承認を拡張しない。新model/migration/依存/設定/公開API/UIはない。ただし先行の未配備台帳schemaが必要なため、そのまま共有環境へ配備できるとは報告しない。

## 実装と利用者への影響

- 新しい `schedules/google_worker_snapshot.py` が、最新jobのowner/type/created_at/payloadと受付行の一致、暗号文・採番の認証、snapshotのversion/kind/接続/credential/構造、syncのincarnation、導出した対象keyと予約行の一致を検査する。型を含むcanonical JSONで比較し、署名だけを認可として扱わない。欠落・改変・legacy受付を現在のsessionから補完・再登録しない。
- Calendarは受付時のupsert/cancel、日時なし、primary/event IDと本文を使用する。受付後の題名/本文/日時変更・取消/再開を混ぜない。新規IDは固定sync keyと一致し、既知IDの差し替えや同PKの別syncは拒否する。先行処理が同じ決定的IDを保存していても、受付内容を現在の本文へ置き換えない。既存のGET/強いETag/条件付きPUT・DELETE/409対応は維持する。
- Sheetsは呼び出し側valuesのbinding/対象選択を検査した後、独立した固定snapshotの行を使う。token取得中や前chunkの応答中に元の行が変わっても後続chunkへ混ぜない。最初の送信前の受付喪失は固定日本語FAILEDとし、既知のchunk適用後の喪失はUNCERTAINを保持して通常retryを拒否する。全出力の原子性やexactly-onceを保証しない。
- worker内部に検査済みの独立copyを保持し、各Calendar HTTPと各Sheets chunkの直前にDBの受付を再認証・照合する。認証済みの別本文への差し替えも続送を止める。最新のactive/scope/visibility/接続/token/実行有効性/同期行検査は残す。DB lockをHTTP間ずっと保持する方式ではない。
- 正常系の旧fixtureは、workerをmockせず実際の受付helperで固定情報を作る方式へ更新した。Sheets合成配送helperは、試験用の新しい意図を組み立てる場所であることを明示し、productionの欠落受付修復に使わない。日時・外部IDの試験設定を受付前へ移しただけで、URL・認可・ETag・再試行の拒否条件は緩めていない。
- 台帳moduleの古い説明を更新し、PostgreSQL CI対象へ新規20試験のmoduleを追加した。静的CI検査でその欠落を検出する。

現段階では、共有holderとjob claimの原子化は未接続で、受付検査は既存のRUNNING/配送receipt確定後である。無効受付のjobは送信せずFAILEDになるが、同期行の表示を世代別に保全する完成形ではない。新規job同士の待機、後続PENDING保全、旧FAILEDの対象世代による拒否は次の作業である。

## 最終検証

同じ最終ソース18パスの実行前後SHAとbackend間一致を確認し、広域35 modulesを測定した。

| 確認 | 結果 |
| --- | --- |
| PostgreSQL 18.3 | 410成功・省略0、260.380秒 |
| SQLite | 388成功・PG専用22省略、154.773秒 |
| 製品差分 | tasksの31文8分岐先＋新helperの66文28分岐先、100%・未実行/除外0 |
| 新規worker試験 | 20試験、346文82分岐先100%・除外0（両backend） |
| 合成Sheets helper | 全22文2分岐先100%・除外0（両backend） |
| 品質・schema | Python17のBlack/isort/Flake8/Bandit成功、指摘0、新しい抑制なし。CI YAML有効、Django check成功、makemigrations --check --dry-runで差分なし |

実際のAPI受付を経た固定本文・取消/再開・日時なし・既知ID・決定的IDの先行receipt、source metadata/credential型/構造/暗号文/採番の改変、同PK sync置換、token取得中とGET間の受付喪失/認証済み差し替え、Sheets複数chunkの元行変更/受付喪失を検査した。旧回帰の実Requests loopbackやPGロック試験も含むが、今回のsnapshot試験のproviderはmockであり、独立Celery/Redis・新しい通常配布物の対象競合・実Google・AWS・ブラウザー・最新OS監査の証明ではない。

T04の固定本文/incarnation、T09の欠落受付・型/改変拒否に部分証拠を追加するが、実行順序や共有holderを含むT02–15全体を合格にしない。旧予定の再連携方針、暗号文/unknownの保存・消去・退会条件、移行/drain/限定回復も残る。

## 失敗の保持・自己レビュー・証拠

初期の固定本文REDは6試験で18失敗。構造/credential/新規IDの追加REDは14試験で14失敗3エラー、Sheets部分適用後の受付喪失は1失敗だった。最初の広域404件は旧受付なしfixture等で418失敗1エラー/PG専用22省略。正常系fixture更新後は両backend409件で予定IDを受付後に変更した6ケースが失敗した。設定を受付前へ移し、CI欠落REDの29件中1失敗を保持して対象を追加した後、最終同一ソース410件を取り直した。失敗を省略・期待値緩和・本体legacy fallbackで消していない。

変更差分、本文と対象のbinding、同PK置換、最新認可、HTTP間の再検査、部分適用と通常retry、例外への本文/資格情報非露出、日本語案内をレビューした。新規表示は既存の固定日本語受付エラー/結果不明案内で完全一致assertionがある。画面要素の変更はなく、ブラウザー描画で未確認の新デザインはない。この修正単位の未解消指摘はないが、共有対象の競合不足は前述のまま残る。stagedのUTF-8/LF・文字化け・全差分・新規ローカルリンクを確認してからcommitする。元checkoutのハンドアウト別変更13項目は保持し、混ぜない。

証拠は `D:\tmp\codex-google-worker-snapshot-20261007`。PGは固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、read-only・512MiB/2CPU・localhost55449のみ・合成tmpfs・volumeなし。所有ID/name/label/image/port/state、public tables/test DB/他active connection0を照合し、7:20:43 JSTにcontainer/tmpfsを撤去した。停止終了0/OOM false、残container/volume0。合成データはfixtureから再作成可能で、全成功/失敗ログ・coverage・SHA・cleanup証拠は保持する。

親d84e051eの[CI run 37536144017](https://github.com/sheepdog0820/iaia/actions/runs/37536144017)はhead SHA/branch一致と全6項目successを確認した。今回候補のCIは通常push後に別途確認する。workflowは検査のみで作業ブランチpushからAWS配備は起動しない。GitHub open Issueは別件#1のみ、先行403/CLI未認証による新Issue未作成は維持し、[下書き](GOOGLE_DURABLE_DELIVERY_ISSUE_DRAFT_2026-10-06.md)へ結果を記録する。権限変更はしない。

ローカルでの取り消しは当該commitのrevertで可能だが、共有反映時は旧workerが台帳を無視する危険を扱い、送信停止・証拠保持・drainを含む別実施案が必要。共有DBのDROPや、未解決送信を解除するための旧worker再開は行わない。

次は対象共有holder/FIFO開始、HTTP intent/receiptと独立unknown journal、outbox対象待機、後続PENDING保全・古いtoken拒否・全lock順、cleanup/legacy/drain/限定回復、UI、通常配布物の実プロセスfault、承認済み実Googleを順に進める。OS HIGH3、実課金・外部連携・常設運用・性能・復旧・公開方針も未達で、正式公開No-Goを維持する。
