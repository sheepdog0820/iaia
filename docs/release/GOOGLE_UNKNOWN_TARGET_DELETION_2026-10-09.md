# 応答不明とCalendar対象削除の独立接続検証

## 対象・判定

2026-10-09。基準 `cb0874d58df7f4bed3d724e9b5fd9efa3f20a2e1`、製品コードは679と同じ。
[先行KNOWN200の削除/完了競合](GOOGLE_TARGET_DELETION_CONCURRENCY_2026-10-09.md)へ、応答喪失時の独立接続ケースを追加する。
[共有対象の受入条件](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md)のT08に関する部分証拠であり、全cleanup/退会/privacy/共有運用の合格ではない。
実Google・実利用者・共有DB・AWSを変更/検証しておらず、正式公開No-Goを維持する。

## 追加ケース・実観測

既存 `schedules/test_google_target_deletion_concurrency.py` へ `GoogleUnknownTargetDeletionTest` を追加する。
実API→暗号化受付/outbox→実taskを使い、外部brokerとGoogle HTTPだけを模擬する。
模擬POSTはTimeoutを返す。Google側で実際に適用されたかどうかを試験したものではない。
送信前INTENTとHTTP中の非atomicを確認し、実 `_receive_request` のatomicが完了した**後**に計測gateを置く。
receipt保存をmockせず、外側transactionも足さない。

session削除/sync削除 × DELETE実行が先/UNKNOWN receipt確定が先の4ケース。
cleanupとworkerは異なるthread/PG接続、observerはさらに別接続で、全ケースで異なる3 backend PIDを確認する。
DELETEは実行済み・未commit、UNKNOWN receiptはcommit済みの重なる時点で次を観測する。

- cleanupは `idle in transaction`、workerは非atomic/`idle`。
- 両接続の `pg_blocking_pids` は空、Lock待機なし。
- observerには未commit削除前のsyncがまだ見える一方、独立送信記録はACTIVE/UNKNOWN receipt/received_atあり。
- 2対象のholderは元execution tokenを保持する。DELETE/receiptの計測順序も両パターン一致。

この二処理は別行を扱うため、成功応答後のsync UPDATEとの実ロック競合とは異なる。
実際に存在しない共通行ロックをfixtureで追加して「Lock競合を検証した」とはしない。
gate解放後に実削除commitを確認してworkerを継続し、UNCERTAIN job/UNKNOWN execution/closed_atなしを確認する。
各ケースの元送信はPOST1、その他HTTP0。削除syncを再作成せず、session削除時はsessionも存在しない。

## 再作成・期限後の禁止

対象がない状態の旧配送はinvalid-job、トークン照会/HTTP0、journal不変。
同じsession/sync PKで異なるcreated_atの合成行を作り、実APIで後続受付を行う。
後続はtarget-waitingでトークン照会/HTTP0、QUEUED/PENDINGと暗号文を保持する。
旧UNCERTAIN配送はinactive-jobで新syncを変更しない。
元jobだけを保存期限外へ設定し、実 `expire_async_jobs` でjob/admission/outboxを削除した後も、同じ後続はtarget-waiting。
元execution/requestは全フィールド不変、新syncも不変で、2対象の未解決禁止を迂回しない。
時間経過・削除・再作成を結果確定とみなしたり、UNKNOWNを自動解除する変更はない。
異常伝播対照1件でworkerのfixtureエラーが成功へ変換されず、gate/接続が解放されることも確認する。

## 検証・計測訂正

- 初回PG11件は8.028秒で成功したが、外部runnerのcoverage対象名が別module名になっており未取得。
  未取得をカバレッジ合格とせず、runner指定だけを訂正して再測定した。製品のRED/修正ではない。
- 最終PG11件成功（8.237秒、skip0）。既存KNOWN競合4/異常対照1、追加UNKNOWN4/異常対照1、既存CI選定1。
- SQLite11件はCI選定1成功/PG専用10省略（0.001秒）。初回計測警告と訂正後の記録を両方保持する。
- 関連PG94件成功（68.555秒、skip0）。今回/先行cleanup二module/Calendar削除guard/worker snapshotを選定。
- test module全体345実行文/50分岐先100%、未実行/除外0。先行175文/28分岐先からの追加分も全実行。
- 当該PythonのBlack/isort/flake8/Bandit終了0。合成日本語データ/検査文をレビュー、製品UI変更なし。
- 文書39件成功（0.035秒）、変更3文書の相対リンク286件の存在確認、4変更ファイルのUTF-8/BOM/LF・差分検査を実施。ソースレビューで残る指摘なし。

## 固定image・片付け

既存679通常image `sha256:6de91d2a3c3fb4d2d4254c656b893352098a40d3dbd1bb3a75b7707c7e238874` に、
追加test/先行fixture/runnerのみ3つのread-only bindを置く。Python entrypointの追加検査で、通常entrypoint起動確認ではない。
KNOWN4/UNKNOWN4/異常対照2の10件が4.351秒で成功、skip0/終了0/OOM false。
製品/fixture8source hashはhostと一致・実行前後不変、追加testのhost hashも実行前後不変。
source Python3.11.1/Django5.2.15、runtime Python3.11.17/Django5.2.17。
非root10001/read-only/cap-drop ALL/no-new-privileges、512MiB/1CPU、tmpfs media、locmem email、未mock Requests禁止。
専用PG namespace内loopbackのためnetwork noneではなく、実Redis/別Celery processの検証でもない。
imageの新規build/全スキャンは行わず、既知OS HIGH2未合格を維持する。

証拠: `D:/tmp/codex-google-target-unknown-deletion-20261009`。
空の専用PG18.3/tmpfsを使い、両test DBの破棄と二つのbase DBのpublic表0を確認した。
正確なID/name/label/image/mount/stateを検査後、runtime/PGの2container/tmpfsを撤去。
PG停止0/OOM false、所有container残0。source/image/script/logと元checkoutの別作業13項目は保持する。

## 変更範囲と残項目

変更は既存test moduleと記録だけ。PG CIは既にこのmodule全体を選定している。
製品/schema/依存/保存・退会・解除方針/main/AWS/共有DB/Secrets/IAM/OAuth/課金/容量/費用/外部通知は変更しない。
今回のテストを取り消すには作業ブランチで通常revertでき、実環境の切戻しは不要。
[Sheets認可方針](SHEETS_TARGET_AUTHORIZATION_DESIGN_2026-10-09.md)の回答と修正、全producer/relayのLock順、
保存・退会/privacy/key rotation/legacy停止・drain/限定回復/実Google/共有運用、OS HIGH対応等は未完了。
旧予定の移行・削除やUNKNOWNの解除を承認済みとみなさず、favicon承認も拡張しない。
先行cb/73d CIは確認時点で実行中。今回のcommitのCIとは別で、全6成功・マージ可能・配備完了とはしない。
