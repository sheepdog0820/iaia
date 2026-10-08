# Google送信記録とcleanupの独立PostgreSQL競合検証

## 対象と判定

基準は `aab860c2ccf431b34a6b3f8aed46acf6176ad14b`。
[同一接続のcleanup境界](GOOGLE_CLEANUP_BOUNDARIES_2026-10-09.md)を補い、
[対象制御設計](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md)のT08/T11の部分証拠を追加する。
製品コード・schema・依存関係・保持/退会/解除方針は変更しない。
全cleanup・認可・移行・限定回復・実Google・共有運用や他の公開条件は未完了で、正式公開 **No-Go**。

## 実接続と処理順

Calendar/Sheets × 無課金利用者の正式退会/job削除/保存期限のexpire/実行期限の分類 ×
正しいHTTP 200/応答喪失 × cleanup先行/receipt先行の32ケースを独立したtest DB状態で検査する。
実API受付・暗号化outbox・実task・実cleanup helperを使い、brokerと外部HTTPだけを代替する。
実Googleへの反映を示す試験ではない。

各ケースはworker/cleanup/observerの3接続の `pg_backend_pid()` が異なることを検査する。
observerが `pg_stat_activity` / `pg_blocking_pids` で対象source行の実Lock待機と相手PIDを確認する。
helperの戻り値やEvent待機だけを実DB競合の証拠にしない。

- cleanup先行: INTENT確定後の模擬HTTP到達を確認してから、実cleanupをtransaction内で行い、commit前に保持する。workerの実receiptのsource行FOR UPDATEがcleanupを待つことを観測する。
- receipt先行: 実receipt関数内のsource行FOR UPDATEを実行後に待機させ、実cleanupのDELETE/UPDATEがworkerを待つことを観測する。receiptを実際に保存・commitした後、cleanupがcommitしてからworkerの完了処理を続ける。

receipt関数は原本を呼ぶ薄いwrapperと `connection.execute_wrapper` で順序だけ制御する。
DBの読み書き、receipt値、completion、lock待機はmockしない。HTTP中atomicなしを確認する。
sourceを失う前にworkerが成功完了する順序の全組合せを検査したものではない。
期限は合成DB時刻の設定で、実際の7日経過や実Googleの処理終了を証明しない。
receipt先行のexpireケースで観測するLockは、expire helper内の時刻設定UPDATEで発生することを明記する。

## 確認した結果

- 32ケース全てで実Lock待機を観測し、デッドロック/SQL timeout/無限待機は発生しない。
- 未解決executionはUNKNOWN/closed_atなし、全割当対象のholderを保持する。正しい応答16件はKNOWN/200、応答喪失16件はUNKNOWNを記録し、いずれもreceived_atを保持する。
- sourceが消える24件はjob/admission/outbox/reservationをCASCADE削除しても独立実行記録を失わない。実行期限の8件はsource UNCERTAINと受付暗号文を保持し、開始済みoutbox暗号文は消去済み。
- 古い配送32件は追加HTTP/トークン取得0・journal不変。別owner/Google identityのSheets後続を含む28件はqueued/target-waiting/cipher保持・追加HTTP0となり、旧execution/requestは不変。
- Calendarの退会後に別Googleアカウントへ旧予定を移す/消す方針や、その競合は今回の28後続に含めない。

別の計測異常対照1件ではworker関数へ意図的な例外を注入し、例外を成功/timeoutに変換せず伝播し、cleanup待機と接続を残さないことを検査する。実worker停止試験とは区別する。
CI選定1件は、新moduleがProduction Database jobにないRED1を確認後に追加して成功した。
初回競合試験には送信前cleanupが混ざる開始順の不備・expire UPDATEへの誤ったDELETE assertion・importしたTestCaseの重複選定があり、53件中10失敗/6エラーだった。製品REDとは扱わず、HTTP到達Event・実SQL種別・module aliasで計測を修正した。
修正後32競合+CI1のPG33件/23.196秒が成功し、計測異常対照追加後34件/23.996秒も成功した。

## 検証・隔離

証拠は `D:/tmp/codex-google-cleanup-races-20261009`。
source試験はPython3.11.1/Django5.2.15、専用loopback PostgreSQL18.3またはmemory SQLiteを使う。
developer env/Secrets・未mock Requestsは禁止し、一時media/合成DBのみ。source/workflow7ファイルの実行前後hashを照合する。
SQLiteでは競合/異常対照33件をPG専用としてskipし、CI選定1件だけ成功する。SQLiteの成功を実Lockの証拠にしない。
最終広域回帰はGoogle全moduleと外部連携/job/API/UI静的/公開文書を選定し、
SQLite496件/187.492秒（436成功・PG専用60省略）、PG496件/365.981秒（全成功・省略0）、
双方終了0。PGにも全32組合せの一意Lock記録を確認した。
新module226文/30分岐先はPGで全実行・未実行/除外0。
変更3文書の相対リンク279件に欠落なし。
公開文書の39試験も0.077秒で成功した。
Black/isort/Flake8/Banditと差分検査は成功。ユーザー向け画面/文言の変更はない。

固定679通常image `sha256:6de91d2a3c3fb4d2d4254c656b893352098a40d3dbd1bb3a75b7707c7e238874`
で、新旧cleanup test2 moduleと隔離runnerだけをread-only mountし、製品コードを変えず32競合+計測異常対照1の33件が15.755秒で成功・skip0・終了0/OOM false。
runtimeの32個のLock記録は全組合せが一意で、製品/helper/test9ファイルはhostとhash一致・実行前後不変。
Python3.11.17/Django5.2.17、非root10001/read-only/cap-drop ALL/no-new-privileges、512MiB/1CPU。
PG専用network namespaceのloopback/専用合成DBを使い、未mock Requests・実メールは禁止する。
新しい通常配布物の構築/全ソース再監査、実HTTP、Celery独立process、実Google/AWSの試験ではない。

source/runtime test DBは破棄済みで、二つのbase DBのpublic表0を確認した。
専用runtime/PGの正確なID/name/label/image/mount/stateを確認して2container/tmpfsを撤去し、
PG停止終了0/OOM false・所有container残0を確認した。image/source/script/log/coverageと元の別作業を保持する。

## 残課題と承認境界

session/sync削除の独立競合、producer/relay/retry等の全Lock順、credential更新/濫用防止、privacy/保存・退会後旧予定、鍵/backup、legacy停止/drain/移行、限定回復と他のT01〜T15・HIGH2・課金/性能/復旧等は残る。
先行1dのCI全6成功は確認済み。[aab CI 37860184627](https://github.com/sheepdog0820/iaia/actions/runs/37860184627)
は08:49 JSTの確認で4成功/Unit・IntegrationとPlaywright実行中。
今回の新commitのCIとは区別する。先行runをcancelしないよう別codexブランチへ通常pushする。
main/AWS/共有DB/実データ/Secrets/IAM/実課金/容量/外部通知は変更せず、favicon承認は拡張しない。
test/CI/記録だけの取り消しは通常revertで可能。共有環境は変更していないためECS/DB切戻しは不要。
