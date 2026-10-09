# Calendar対象削除と完了保存の独立PostgreSQL競合

## 対象と判定

2026-10-09。基準 `73d2b4d0983513692274b049ac95251380f51f21`。製品コードは679と同じ。
[共有対象の受入条件](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md)のT08/T11の不足証拠を追加する。
[先行cleanup競合](GOOGLE_CLEANUP_CONCURRENCY_2026-10-09.md)はowner/job/保存期限/実行期限の両Lock順を扱った。
今回はCalendarのsession/sync削除と、KNOWN/200受領後の同期行保存の実ロック競合だけを扱う。
実Google、実利用者、共有DB、AWS、本番相当の全競合の成功ではない。正式公開No-Goを維持する。

## 実装・観測方法

新規 `schedules/test_google_target_deletion_concurrency.py` を追加し、実API→暗号化受付/outbox→実taskを使用する。
外部broker/Google HTTPだけを模擬し、受付・送信記録・receipt・完了・削除の製品処理/SQLは実行する。
HTTP中はatomic/DB lockを保持していないこと、確定INTENTを検査する。応答は合成200で、実Googleへの適用証拠ではない。
workerとcleanupを異なるthread/PG接続で実行し、observerも別接続とする。
実DELETEまたは実UPDATEがロックを取得した後に計測gateで待たせ、反対側の実SQL待機を `pg_blocking_pids` で確認する。
全4ケースで異なる3 backend PIDと同期行に対するUPDATE/DELETEのLock待機を観測する。
独立observerは待機中にACTIVE実行/KNOWN200 receipt/未解除holderを確認する。
計測異常が失敗として伝播する対照を1件置き、finallyでgateを解放し、接続を閉じる。
DB SQLやtask本体を成功mockへ置き換える検査ではない。

| 対象・先にロックする処理 | 実待機SQL | 元ジョブの終了 | 独立送信記録 |
| --- | --- | --- | --- |
| session削除が先 | workerの同期行UPDATE | inactive-job / FAILED | KNOWN200 / FINISHED |
| 完了保存が先、session削除 | cleanupの同期行DELETE | synced / SUCCEEDED | KNOWN200 / FINISHED |
| sync削除が先 | workerの同期行UPDATE | inactive-job / FAILED | KNOWN200 / FINISHED |
| 完了保存が先、sync削除 | cleanupの同期行DELETE | synced / SUCCEEDED | KNOWN200 / FINISHED |

全4ケースで削除されたsyncは再作成されず、session削除時はsessionも存在しない。
元実行の2対象と確定receiptは保持し、全送信がKNOWNかつ元sourceがFAILED/SUCCEEDEDの既存終了規則でholderを解除する。
削除や経過時間だけでUNKNOWNを解除する変更は行わない。
syncがない状態の旧再配送はinvalid-job、トークン照会/追加HTTP0、journal不変。

その後、session/syncの同じPKで異なるcreated_atの合成行を作り、新しい実API受付を行う。
旧SUCCEEDED配送はinactive-job、旧FAILED配送は既存retry開始規則を通るが、固定snapshotの世代不一致でinvalid-admissionとなる。
後者は旧FAILED行/新しい空送信実行の状態を更新するため「全状態不変」とは報告しない。
どちらもトークン照会/HTTP0、replacement sync不変、元KNOWN receipt/元実行不変。
新しい受付だけは別execution tokenでPOST1・synced/SUCCEEDEDとなり、その処理で元job/元実行/元receiptは変わらない。
未解決UNKNOWNの場合の送信再開を許可した証拠ではない。

## 検証結果と初回失敗

- 初回PG6件: 3失敗。CI選定欠落1件は追加テストのRED。
  残り2件は旧FAILEDの世代不一致拒否をinactive-jobとしたfixture期待値の誤り。
  製品を変更せずinvalid-admission/トークン・HTTP0/新行保全と、旧job状態更新の観測に訂正した。
- 最終PG6件成功、4.472秒、skip0。SQLite6件はCI選定1成功/PG専用5省略、0.001秒。
- 関連PG89件（今回/先行cleanup二module/Calendar削除guard/worker snapshot）成功、62.337秒、skip0。
- 新規test module175実行文/28分岐先を全実行、未実行/除外0、100%。製品変更のカバレッジではない。
- Black/isort/flake8/Banditは当該Pythonで終了0。日本語の合成データ/検査文を確認し、製品UI変更なし。
- 文書39件成功（0.077秒）、変更3文書の相対リンク284件の存在確認、5変更ファイルのUTF-8/BOM/LF・差分検査成功。ソースレビューで残る指摘なし。

## 固定配布物での再検証

既存679通常image `sha256:6de91d2a3c3fb4d2d4254c656b893352098a40d3dbd1bb3a75b7707c7e238874` を使用する。
追加test/先行fixture/runnerだけを3つのread-only bindで置き、製品source/依存を変更しない。
Pythonをentrypointに指定した追加検査であり、通常entrypointの起動確認ではない。
test classの4実競合+異常伝播対照1の5件が2.388秒で成功、skip0/終了0/OOM false。
製品/fixture計8source hashがhostと一致し、実行前後も同じ。追加testのhost hashも実行前後一致。
sourceはPython3.11.1/Django5.2.15、固定imageはPython3.11.17/Django5.2.17。
非root10001/read-only/cap-drop ALL/no-new-privileges、512MiB/1CPU、tmpfs media、locmem email、未mock Requests禁止。
専用PGのnetwork namespace内loopbackを使用するため、network noneの試験ではない。実Redis/broker/別Celery processの競合でもない。
image自体の新規構築・全再スキャンは行わず、既知OS HIGH2の未合格を維持する。

## 片付け・変更範囲・残項目

証拠: `D:/tmp/codex-google-target-deletion-20261009`。
空の専用PG18.3/tmpfsを作り、Djangoが両test DBを破棄したことと、二つのbase DBのpublic表0を確認した。
正確なID/name/label/image/mount/stateを検査して、終了済みruntimeとPGの2container/tmpfsを撤去。
PG停止0/OOM false、所有container残0。固定image/ソース/ログ/scriptは保持、元checkoutの別作業13項目は触れない。

今回の変更は新規test・PG CI選定・記録だけ。製品/schema/依存/保持・解除方針は変更しない。
main/AWS/共有DB/Secrets/IAM/OAuth/費用/課金/容量/外部通知の変更や、favicon承認の拡張はない。
先行a3 CI37861654235の全6成功を確認したが、今回のcommitのCIとは別の証拠。
送信応答喪失時のsession/sync独立競合・再連携/認可/保存/限定回復・legacy停止/drain/実Google/共有運用、
[Sheets認可方針](SHEETS_TARGET_AUTHORIZATION_DESIGN_2026-10-09.md)の回答と修正、OS HIGH対応、その他正式公開条件は未完了。
今回だけでT08/T11やGoogle全体を完了とはしない。取り消しは作業ブランチで通常revert可能で、実環境の切戻しは不要。
