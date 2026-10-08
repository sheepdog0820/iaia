# Google送信中の退会・削除・期限処理の境界検証

## 判定と範囲

基準は `1d393b510a7733a341bccb6e14da283675f52a36`。専用worktreeで、既存の
独立送信記録に不足していた回帰テストを追加する。製品/schema/依存/保持・解除方針は変更しない。
[対象制御設計](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md)のT08の部分証拠であり、
全cleanup競合・privacy条件や正式公開の完了ではない。正式公開 **No-Go**。
main/AWS/共有DB/実ユーザーデータ/Secrets/IAM/課金/容量/通知は変更しない。

## 追加した境界

実API→暗号化受付/outbox→実taskの経路を使い、brokerだけを未接続にする。
模擬POST/PUTのcallbackで、実DBにINTENTが保存済み・HTTP中atomicなしを確認してから
次の処理を実行し、正しい200応答またはTimeoutを返す。

| 対象 | cleanup/期限処理 | 応答条件 | ケース数 |
| --- | --- | --- | --- |
| Calendar | 無課金利用者の正式退会helper、job削除、保存期限後のexpire task、session削除、sync削除、実行期限後の分類 | 正しい200 / 応答喪失 | 12 |
| Sheets | 同じ退会helper、job削除、保存期限後のexpire task、実行期限後の分類 | 正しい200 / 応答喪失 | 8 |

退会では実 `delete_account_after_billing_check` を呼び、Stripe client取得0を確認する。
保存期限/実行期限はDBの時刻を過去へ設定する決定的試験で、実際に7日待った証拠ではない。
各ケースは独立した合成利用者/予定/DB状態を持つ。別owner/別Google identityのSheets後続や、
同PK session/新syncのCalendar後続は実APIから受付し、未解決対象を迂回できないことを検査する。

- 未解決18ケースはUNKNOWN/closed_atなし・全holderを保持。応答喪失10件はrequest UNKNOWN、正しい応答10件はKNOWN/200を保持する。
- Calendarのsession/sync削除後に正しい応答が届く2件だけは、現在sourceのFAILEDと全request KNOWNにより既存の終了条件を満たす。FINISHED/closed_at/holder解除を検査し、単なる削除や時間経過で解除したとは扱わない。
- source jobが消える12件はadmission/outbox/reservationと暗号文がCASCADE削除されても、独立execution/request/allocationとbinding/digestを維持する。
- session/sync/実行期限の8件はjobの受付暗号文を保持し、開始済みoutbox暗号文は消去済み。削除した本文の保持期間を承認・確定した証拠ではない。
- 旧配送20件の追加HTTP/トークン取得0・journal変更0。未解決後続16件はtarget-waiting/QUEUED/cipher保持、追加HTTP0、相手のjob UUID/token/bindingのAPI露出なし。
- 別利用者による元job照会は404。独立journalの合成token/予定名/owner名/シートIDの平文不在とtarget keyのdigest形式を検査する。hashを匿名化保証とはしない。

## 検証の証拠

証拠は `D:/tmp/codex-google-cleanup-20261009`。
既存製品の不足テストは初回から成功し、製品修正を要するREDは発生していない。
別のCI選定テストはProduction Database jobへの新module不在でRED1失敗となり、選定追加後に成功。
初回SQLite/PG各21成功・省略0、最終局所PG21成功・省略0。
新module215文/32分岐先は全実行・除外0。Black/isort/Flake8/Bandit・YAML parse/選定確認は成功。
最終広域回帰はSQLite462件/184.745秒（435成功・PG専用27省略）、PG462件/336.258秒
（全成功・省略0）、どちらも終了0。新moduleは双方215文/32分岐先すべて実行・除外0。
変更3文書の相対リンク276件に欠落なし。

ローカルPython3.11.1/Django5.2.15と、loopback PostgreSQL18.3またはmemory SQLiteを使う。
PGは固定image/read-only/512MiB/2CPU/合成tmpfs・永続volumeなし、既存55450 listener不在と
新fixtureのpublic表0を確認してから試験する。Requestsの未mock外部送信は禁止、一時mediaのみ。
記録の6 source/workflow hashを実行前後に照合する。

### 固定配布物での追加確認

既存の通常679配布image
`sha256:6de91d2a3c3fb4d2d4254c656b893352098a40d3dbd1bb3a75b7707c7e238874` に
新moduleと隔離runnerだけをread-onlyでmountし、製品コードを書き換えず20ケースを実行した。
Python3.11.17/Django5.2.17、20成功/7.451秒・省略0・終了0・OOM false。
CI選定の1件は配布対象外のworkflowを使うsource試験で別途検査し、runtimeでは製品境界20件を選定する。
製品/fixture/追加testの8ファイルはhostとhash一致、image内実行前後も不変だった。
新通常imageを構築した検証や全配布ソースの再監査ではない。
非root10001/read-only/cap-drop ALL/no-new-privileges、512MiB/1CPU、PG専用namespaceのloopbackを使い、
未mock外部Requestsと実メールを禁止する。実Google・共有環境ではない。

source/runtime test DBの消去とbase DBのpublic表0を確認した。専用PGとruntimeの正確なID/label/image/
mount/stateを確認後に2container/tmpfsを撤去、PGの停止終了0/OOM false・所有container残0を確認。
固定image・source/archive・script/log/coverageと元checkoutの別作業を保持した。

親1dの[CI 37857790244](https://github.com/sheepdog0820/iaia/actions/runs/37857790244)は局所検証中に
4成功/2実行中だったが、後続確認で2026-10-09 08:31 JSTに全6成功で終了した。
head SHAとbranchの一致も確認した。今回追加21件のCI成功を意味しない。
同branchの実行中runをcancelしないようpushを保留していたが、先行runが成功で終了したため通常pushへ進める。

今回は全てtask直接呼出・同一接続のcallback順序制御で、実HTTP/独立workerの競合・長い遅延適用・
実Google/共有AWSの証拠ではない。退会後のGoogle旧予定の扱い、保存期間/解除・限定回復の承認、
鍵/バックアップprivacy、legacy停止/drain/移行、他のT01〜T15条件、HIGH2と課金・性能・復旧等は残る。
既存favicon承認は拡張しない。共有環境未反映のため切戻し不要で、test/CI/文書の取り消しは通常revert。
