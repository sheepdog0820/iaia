# Google同期先の世代・排他制御: 再現結果と実装設計候補

## 状態と対象

2026-10-06。製品コードの調査対象は `a91be6b887e12ffeabb7b0d35bc1e0a6d009204a`。**本記録は不足の再現と設計候補であり、対象単位の排他制御を実装・合格・配備した記録ではない。** アプリ、schema、依存関係、公開設定は変更していない。正式公開はNo-Goを維持する。

[手動再試行の元ジョブ停止](GOOGLE_RETRY_SUPERSESSION_2026-10-06.md)は、同じ元ジョブの再開・二重受付を止める部分対策である。別の新規同期、セッション更新による自動同期、別のSheets出力は `retry_of` を共有せず、同一同期先の結果不明・実行中・新しい受付を検査しない。この範囲を次の実装単位にする。

## 現行コードで確認した不足

専用の合成データを使い、製品の実際のclaim・HTTP直前ガード・task本体を呼び出した。外部HTTPはmock、未mock Requestsは全面拒否。独立したSQLiteメモリDBと専用PostgreSQL 18.3で各3ケースを確認した。PGでの実行も各ケースは同一接続の順序制御であり、独立worker/接続の競合実測ではない。

| ケース | 制御した順序 | 観測した現行動作 | 必要な保護 |
| --- | --- | --- | --- |
| Calendarの別ジョブ | 同じsyncへのjob A/Bをそれぞれclaimし、両方のHTTP直前ガードを通す | RUNNINGが2件、mock書き込みが2回許可された | 対象共有の実行権を一つに限定する |
| Calendarの遅い完了保存 | AのPOST応答callback中に別job Bを作成しsyncをPENDINGにし、その後Aの応答を保存 | A成功・BはQUEUEDのまま、syncはSYNCEDへ上書きされた | 外部予定IDの既知receiptは保持し、新しい受付のPENDING表示を壊さない |
| Sheetsの別ジョブ | AのPUTをTimeoutでUNCERTAINにし、同じシート/開始位置へ別job Bを実行 | AはUNCERTAINのまま、Bのmock PUTが1回許可され成功した | 対象の結果不明を別job・別owner・別接続でも迂回させない |

これらの診断assertionの `OK` は**不足が再現した**という意味であり、安全性の受け入れ試験成功ではない。新規の製品テストとして危険な挙動を固定していない。別Googleアカウントから共有Sheetを操作する競合、実Googleでの遅延適用、実HTTP・broker・別workerは今回の観測範囲外である。

調査した主な経路:

- `schedules/google_job_lifecycle.py`: `claim_google_job_start` はjob行をロックするが、別jobの共有対象をロックしない。
- `schedules/tasks.py`: `_calendar_request` はjob/同期行の存在・認可・資格情報を検査するが、対象共有の実行権を持たない。`_save_current_calendar_sync` は同期行のincarnationと手動retry系列を守るだけである。
- `schedules/integration_views.py` / `schedules/job_views.py` / `schedule_session_google_syncs`: 新しい受付でPENDINGとjobを作るが、対象の受付世代を固定しない。
- Calendarはtask開始時にsessionを読み、実行中のinstanceから予定を構成する。受付時点の予定snapshotは未固定。Sheetsはvalues bindingと暗号化配送意図で内容を固定している。
- `expire_async_jobs` は期限を過ぎたjobを削除する。jobへのFKだけを排他の根拠にすると、削除によって結果不明の禁止が消える。

## 不変条件

1. 同じ対象へ未完了の書き込みを認可する実行権は最大一つ。新しい受付は古い送信中処理を取り消したことにしない。
2. jobの期限、taskのtime limit、outboxの5分claim、HTTP timeout、workerの停止は、Google側処理終了・未適用の証明ではない。時間経過だけで対象の実行権を再利用しない。
3. 開始済みholderの記録はjob削除・owner/session/sync削除・接続更新で自動解除しない。結果不明をFKのCASCADE/SET_NULLで「空き」に変換しない。
4. 認可、実行token、資格情報、immutable対象と内容をHTTP直前に照合する。排他機構は現行の認可を代替しない。古いworkerのlease再取得や古いFAILEDの自動再適用を認めない。
5. 新しいqueued受付と、古い実行の既知receiptは別物。実際の予定IDを失わず、後続の状態表示を古い完了/失敗で上書きしない。
6. この排他の保証対象はTablenoの送信同士。Google上の人間/他アプリの変更をすべて直列化する保証、exactly-once保証、Sheets出力全体の原子性は宣言しない。

## 対象の識別と受付順

### Calendar

論理対象はローカルuser/sessionの組。現在のsyncのPK/created_at、接続binding、credential identityは**受付内容のincarnation/認可証拠**として別に固定する。syncの削除・再作成や再連携で論理対象の未解決holderを迂回させない。

既存の外部予定を扱う場合は、Google account identity・primary・event IDで物理対象も識別し、別の論理対象が同一外部予定を扱う場合の衝突を止める。必要な複数対象lockは正規化された一定順序で取得する。現行primary固定を独断で変更しない。

再連携時の旧予定を残す/移す/削除する方針は未承認。旧接続に属する予定を新接続へ移したものとみなさない。論理対象のholderを維持し、資格情報・外部予定の由来が不明なら送信を止める。方針未決定は、ローカルのモデル・排他・認可・正常系の実装まで止める理由にはしない。

### Sheets

初期実装は**spreadsheet全体**を共有対象とする。同じspreadsheet IDはowner・Google account・range・接続世代にかかわらず同じ排他対象へ解決する。行列の重なり、大小文字/引用されたsheet名、既定sheetのaliasを開始セルの文字列比較で判定しない。非重複rangeも直列化される性能上の制約を検証・説明する。

現在の `normalize_spreadsheet_id` が検証したopaque IDを使い、勝手なcase-fold/Unicode変換/URL解釈を加えない。Googleが同じリソースと解釈する別表記の存在は未検証なので、別表記を許す経路があるなら正式公開前にcanonicalな同一IDへ解決するか拒否する。

共有target IDを公開APIへ露出しない。内部resource keyの候補はversion付きnamespace/型付きcanonical表現からのSHA-256で、接続SECRETのローテーションによって排他対象が変わらない設計にする。hashは認可でも匿名化保証でもない。小さい内部IDは推測可能であり、アクセス制限・削除/保存方針の審査を必要とする。認証token、UID、セル本文、予定本文を平文で新しいtarget台帳へ重複保存しない。

### 共通受付順

初期案は対象のtransaction内で確定した単調sequenceによるFIFO。API受付時刻やUUID順から後付けしない。**別の出力をlatest-winsで黙って捨てない**。Calendarの中間更新の集約やSheetsの非重複並列化は別の将来設計とする。

古いFAILEDを自動retryできるのは、まだ後のsequenceが開始されておらず、その実行の未解決書き込みがない場合だけ。後のsequenceが一度開始したら、古いsequenceはjob行をQUEUED/FAILEDへ戻しても開始不可。手動retryは既存の元停止markerを維持し、明示的な新しい受付sequenceとして扱う。

## 永続モデルと送信プロトコルの候補

名称は仮称。まだmodel/migrationを追加していない。

- `GoogleWriteTarget`: 一意resource key/version、最後の受付sequence/開始sequence、active job UUID・execution token・sequence、未解決送信の状態。active UUIDはjobのnullable FKだけに依存させない。TTLによる自動unlockなし。
- `GoogleWriteAdmission`: jobとtarget/sequence、immutable対象incarnation・接続/内容binding、必要な暗号化snapshot。複数targetを使うCalendarでも同じ受付単位として扱う。
- `GoogleWriteAttempt`: holder token、送信前intent、試行番号、既知receipt/unknown、必要最小限の照合digest。原本jobの7日削除とは独立した未解決禁止を維持する。無期限保存を利用者へ約束せず、保持項目・解消条件・退会時扱いは配備前に確定する。

受付はjob・admission・Calendar snapshot・既存暗号化outboxを同一transactionで確定し、rollback時は全て破棄する。全5producerで共通の受付helperを呼ぶ。queue関数をmockしたテストでもadmissionが存在するよう、配送関数だけに受付を隠さない。Calendar本文は既存outboxの暗号化方式を再利用する候補であり、cipher消去後の結果照合に必要なdigest/receiptを別途最小限保持する。

workerはadmissionの存在・binding・FIFO・対象の空き・jobの現行tokenを検査し、対象holderとRUNNING/開始receiptを原子的に確定する。対象待ちならRUNNINGやDELIVEREDにせず、既存暗号化意図を消さず、後続relayの再配送対象として保持する。待機を失敗扱いしないが、jobの期限後の自動実行はしない。

HTTPごとに「このholderによる送信intent」をDBにcommitしてからHTTPを呼ぶ。DB lockをネットワーク通信の間ずっと保持しない。intent確定後・送信前のcrashも、外から区別できなければ安全側にunknownを保持する。Sheetsの複数chunkは途中でholderを譲らない。

確定応答の保存はtarget holder/token/attempt一致を条件とし、receipt・job完了・Calendarの外部ID保存・holder解除を同じtransactionで行う。後続queuedがあればCalendarの表示はPENDINGを維持する。source jobが消えていても証拠を消さず、syncの同PK置換を更新しない。古いtoken・別job・偽receiptは保存/解除できない。

**status=FAILEDだけでは解除しない。** 書き込み前の確定拒否、accepted chunk後の認可停止、通信不明、worker消失を区別する。未完了HTTPがなく、追加送信が現行tokenで禁止され、既知の全送信境界が閉じた証拠がある場合だけ解除できる。途中まで確定適用したSheetsはその事実を保持し、全出力成功としない。DB保存失敗はholderを残して次の送信を止める。

## 結果不明・移行・復旧

- 結果照会だけで、古いin-flight処理の後からの適用がなくなったことにはしない。停止/隔離の根拠、現在の対象内容、接続/権限、対象sequenceを照合した限定回復を別途実装する。未実装の管理ボタンや自動復旧を宣伝しない。
- Sheetsでは共有相手のjob ID、owner、セル内容、unknown原因を待機中利用者へ漏らさない。自分のjobの待機/確認必要だけを表示する。他人のholderを解除できない。未検証の任意spreadsheet IDで全体を永久blockできないよう、権限と資源上限を受付/実行で審査する。
- 旧workerは新target台帳を見ない。schema追加だけで安全になったことにせず、producer/relay/workerを止めてdrain確認し、未開始legacy jobの移行とRUNNING/UNCERTAINの保留を終えてから新workerを有効にする。止められない/旧処理終了を証明できない対象は送信しない。
- 既存legacy jobを開始時に「最新sequence」として遅延登録しない。失われた受付順・snapshotを推測して実行せず、未開始だけ安全に移行できる条件を定める。RUNNING/UNCERTAINの単純backfill/unlockは禁止する。
- ロールバックで新holder台帳をDROPしたり、markerを消して旧workerを再開したりしない。送信停止・証拠保持を基本とし、旧イメージへ戻す場合もその版が新台帳を無視する危険を扱う。
- shared DBへのmigration適用、main/AWS配備、実Google照会/書き込み、保存方針/利用者への約束、監視/基盤費用は別の具体的な承認対象。今回の設計はfavicon反映承認を拡張しない。

## 実装時の受け入れ試験（全て未実装/未検証）

| ID | 試験と必須結果 |
| --- | --- |
| T01 | 同対象への新規API/自動同期/手動retry受付とoutboxを同時確定。rollback/savepoint rollbackではadmission/sequence/intentなし。全5producerを検証 |
| T02 | PG独立接続で同じCalendar対象の二つのworkerを開始。実lock待機を観測し、holder一つ、外部書き込み一つ、待機jobのcipher保持 |
| T03 | Aの書き込み中にB受付、A応答保存。既知event ID/receipt保持、Bはqueued・sync PENDING。Aから追加送信なし。B開始後にA旧メッセージが来てもHTTP0 |
| T04 | Calendar受付後session更新/取消・sync削除/同PK再作成。各admissionの固定snapshot/incarnationを守り、順序逆転・別sync更新・予定復活なし |
| T05 | Sheets同一/重なるrange・alias・非重複range・別owner/別Google接続を同一spreadsheet対象として直列化。相手の情報露出0。別spreadsheetは独立 |
| T06 | Sheets multi-chunk中のB受付とA停止/部分失敗。chunk間で実行権を譲らず、unknown後BのHTTP0、既知部分適用を全成功としない |
| T07 | intent保存前/後、HTTP適用前/後、応答後DB保存前のSIGKILL。実Redis/solo/prefork/独立relay/通常配布物で未知のholderを自動解除しない |
| T08 | lease/実行期限/保存7日を越え、job・owner/session/syncを削除しても未解決禁止を迂回不可。対応するprivacy/退会条件も検証 |
| T09 | 後のsequence開始後の古いFAILED自動retry、legacyメッセージ、偽token、改変payload/values/対象markerを全てHTTP前に拒否 |
| T10 | 既知成功/書き込み前確定拒否だけ安全に解除。DB rollback/保存失敗・期限後の遅い応答・同PK置換では証拠消失/偽解除なし |
| T11 | 対象初回作成・複数target・producer/retry/worker/relayの全lock順を両順序で実測。deadlock/無限待機なし、timeoutは未完了として扱う |
| T12 | 接続更新/取消/認可失効は新旧holderを分離して迂回せず、未承認の旧予定移行/削除をしない。共有Sheet待機の認可・上限/濫用防止 |
| T13 | 暗号文消去、API非露出、ログ/SQL/バックアップの機微情報、key/version変更時の対象一致、schema forward/reverse/旧版停止互換を確認 |
| T14 | queued/対象待ち/確認必要/期限切れの日本語表示、履歴/再試行、3ブラウザ、正常時の不用意な未配送警告と旧retryボタンの扱いを確認 |
| T15 | 限定回復の独立競合、旧HTTPの遅延到着、外部の人間編集を確認。Calendarの条件付き更新を維持し、Sheetsへ未証明のexactly-once/原子的全出力を約束しない |

実装順: (1) 台帳・受付/rollback・immutable snapshot、(2) worker/HTTP/receipt・outboxの対象待機、(3) cleanup・legacy/drain・限定回復、(4) UI・通常配布物の実プロセスfault、(5) 承認済み対象の実Google/共有運用。各単位は不変条件を満たすまで未配備とし、台帳だけの導入を世代fence完成と報告しない。

## 今回の検証・証拠・影響

証拠は `D:\tmp\codex-google-target-fence-design-20261006` に保持。`target_probe.py` が上記3つの不足をassertし、`run.py` はdeveloper env/Secretsを読まず、SQLite TEST=:memory:または専用PG localhost:55446/google_target_fixtureだけを許可する。`run.ps1` は調査した11 source/helperのSHA-256を実行前後に照合する。SQLite 3ケース/0.104秒、PG 3ケース/0.226秒、いずれも不足再現・追加発見の意味である。

PGは固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、read-only、512 MiB/2 CPU、localhostのみ、合成tmpfs、volumeなし。所有ID/name/label/image/port/mount/stateとSQL空状態を検証後、23:03:51 JSTにcontainer/tmpfsを削除した。停止終了0/OOM false、残container/volume0。ログ・診断source・SHA証拠を保持し、実ユーザー/元worktreeの別変更は触っていない。

親アプリa91be6b8の[CI run 37473902407](https://github.com/sheepdog0820/iaia/actions/runs/37473902407)は23:03頃の読み取り時点で4ジョブ成功、Unit / IntegrationとPlaywrightは実行中。head SHAの一致を確認した。全6成功と断言しない。今回の文書commitのCI、通常新配布物、実Google/AWS、独立workerの対象競合、安全性受け入れ試験、最新OSスキャンは未確認。先行OS HIGH3は未合格のまま。

文書差分は記述・リンク・UTF-8/LF検査と関連文書39試験を確認する。製品コードの変更がないため全アプリテストの再実行・新カバレッジ計測で安全性を代用しない。今回のmain/AWS/共有DB/migration/Secrets/IAM/課金/容量変更はない。文書のみの取り消しは当該commitのrevertで可能で、製品動作は変わらない。
