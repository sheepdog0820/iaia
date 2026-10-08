# Google共有対象の実行権・独立送信記録（ローカル部分実装）

## 対象と公開判断

2026-10-08。基準アプリは77192584719631d7b7002f07d68ca57561bfc046、作業ブランチは `codex/google-target-execution-20261007`。無料KP登録修正579dd6f8を作業ブランチへfast-forwardで取り込んだ。579のCI37545025884はhead SHA一致・completed/successを読み取り確認したが、その成功は本書の製品変更のCI成功ではない。

本単位は[対象排他の設計](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md)のworker/HTTP/receipt接続を進めるもの。**正式公開はNo-Go**。限定回復・共有運用・実Google・通常新配布物を完成したとは扱わず、既存のfavicon反映承認を拡張しない。

## 製品変更と利用者への影響

- 同じCalendar論理対象/物理予定、同じspreadsheet全体の受付sequenceを参照し、対象lockを一定順に取って実行権を一つに限定する。Sheetsは別owner/接続/非重複rangeでも同じ対象になる。後続受付をlatest-winsで捨てない。
- 対象待ちではjobのRUNNING化、配送DELIVERED化、暗号化配送意図の消去、token取得、HTTPを行わない。未開始jobは既存relayの再配送対象として残る。
- `GoogleWriteExecution` / `GoogleWriteExecutionTarget` / `GoogleWriteRequest` の内部3テーブルと対象の開始sequence/tokenを追加する。元job/ownerへのFKではなく独立したUUID snapshotを保持し、元jobの期限・削除で結果不明の禁止を消さない。記録の保持方針は未決定で、共有配備前の判断が必要。
- 送信前intentをDB確定してからHTTPを呼ぶ。HTTP中はDB lockを保持しない。結果不明/保存失敗では対象を再利用せず、時間経過だけの解除はない。既知の送信境界が閉じ、現行tokenのjobが成功/失敗で終了した場合だけ解除する。単なるFAILED更新は解除ではない。
- Calendarの既知event IDを保持し、後続受付のPENDING/last_errorを古いreceiptで上書きしない。元job削除後もreceiptは保持し、削除済みjob/syncを作り直さない。
- 独立allocationをdomain-separated HMACで検証する。markerだけの消失/sequenceとallocationの同時改変/別jobのtoken/署名材料不在では送信・偽解除を拒否する。任意のDB全体改変への安全性や匿名化を保証するものではない。
- 記録にURL・セル/予定本文・資格情報の平文を重複保存せず、request digest/ordinal/状態/statusのみを保持する。内部テーブル・共有相手のjob情報を新しい公開APIへ露出しない。
- 新migration0061は隔離DBだけで実行。逆移行はACTIVE/UNKNOWNだけでなくFINISHED記録も残る限り拒否する。PG/SQLiteの書き込みlock下で検査し、未検証DBも日本語のエラーで拒否する。空journalでの往復は既存migration試験で検証する。
- PostgreSQL CIの明示対象へ新テストを追加。pushが起動する既存workflowはCIのみで、AWSデプロイ操作はない。

主要変更は `schedules/google_target_execution.py`、`google_job_lifecycle.py`、`tasks.py`、`models.py`、migration0061と対応テスト/CI。画面レイアウト・料金・OAuth scope・依存関係は変更しない。

## 検証と失敗記録

HTTPはmockを原則とし、既存の隔離loopback試験を含む。未mock Requestsは禁止、developer env/Secretsを読み込まず、メモリSQLiteまたはlocalhost:55450の専用PG18.3だけを使用する。共有AWS/Googleに対する動作証明ではない。

先行の失敗を削除しない。追加整合性RED3件は2失敗/1エラー、広域324件は183失敗/3エラー/23省略、初回coverage PG421件は1失敗、逆移行3件とCI欠落1件は全4失敗、未検証DB逆移行1件は未実装エラーだった。独立TestCaseの状態漏れはrollback helperで分離し、実commitのTransactionTestCaseは別対象を使って古いjournalを残した。認可・incarnation・ETag・unknownの拒否assertionを削除して通したものではない。結果不明後のCalendar新job再送期待は、追加HTTPなしの待機へ更新した。

関連GREENはSQLite70件中67成功/PG専用3省略、PG88成功/省略0。広域 `regression-second` はSQLite431件中407成功/24省略（205.496秒）、PG431成功/省略0（342.289秒）。同一source inventoryを照合し、製品差分241文/56分岐先と新規rollback helper10文/2分岐先は100%・除外0。新規テストの到達しない補助コードを整理した後の最終同一ソース検証は以下に記録する。

最終 `regression-final` はSQLite431件中407成功/PG専用24省略（205.330秒）、PG431成功/省略0（340.106秒）、両者終了0。675 sourceファイルの前後/両backend/現ソースのSHA-256不一致0、製品差分241文/56分岐先・新規35テスト601文/16分岐先・helper10文/2分岐先と既存テストの追加実行文/分岐も100%・除外0を確認した。テスト整理後も元のRUNNING更新拒否とlock観測timeoutのassertionを維持した。対象待機やunknownを成功扱いする変更はない。

実PGの独立接続で二つのCalendar workerが同対象lockを待つことをPID/pg_blocking_pidsで観測し、holder1・書き込み1・後続queued/cipher保持を確認した。別接続からHTTP前のINTENT確定を確認し、HTTP callback内の `in_atomic_block=False` も検査した。これは独立thread/DB接続の証拠で、実Redis/独立Celery processのSIGKILL証拠ではない。

Python3.11.1の変更21ファイルでBlack/isort/Flake8/Bandit終了0。Banditの既存nosec注釈に対する警告2件はあるが新しい除外を追加していない。makemigrations --check --dry-runはNo changes detected。日本語の内部stateラベルと逆移行エラーを確認し、英語のtask返値は非表示の内部識別子である。新画面変更はないためブラウザーでの新UI合格を主張しない。

文書更新後の公開記録/CI構成69テストも成功。差分の自己レビューで、このローカル実装単位に追加修正を要する問題は残っていない。ただし下記の未完了条件は共有配備・正式公開の阻害要因であり、実装単位のテスト成功をリリース可能と読み替えない。

証拠は `D:/tmp/codex-google-target-execution-20261007`（初期RED/回帰）と `D:/tmp/codex-google-target-integrity-20261008`（setup/source SHA/coverage/result/cleanup）。新runnerはschedules/tests等の追跡・未追跡ソースを測定前後に照合し、途中で編集した測定を合格証拠にしない。

21:48 JSTに所有containerの完全ID/name/label/image/localhost port/read-only/tmpfs設定を照合し、public table0・test DB0・他active connection0を確認して停止/削除した。終了0・OOM false、所有container/volume残存0、ログ・証拠保持。元checkoutの別作業は削除していない。本単位のcommit/push後CI・通常新配布物・実Google/AWSはこのローカル結果で代用しない。

## 未完了の受け入れ条件・共有配備前提

設計T01〜T15全体を閉じない。今回T02/T03/T05/T06/T08/T09/T10/T13の一部をローカル検証したが、以下は残る。

- T07: 通常新配布物、実Redis/solo/prefork/独立relayの各送信境界SIGKILL/DB障害・遅延HTTP。
- T08/T12/T13: owner/session/sync等の全削除・再連携/署名鍵変更・ログ/SQL/バックアップprivacy・保持/退会方針、共有Sheet受付の認可と資源上限/濫用防止。
- T11: producer/retry/worker/relay/cleanup/移行を含む全lock順・両開始順序。今回の限定PG観測だけでは全経路のdeadlock不在を証明しない。
- T13: 旧worker停止/drain、未開始legacy移行、RUNNING/UNCERTAIN保留、新旧版互換。journalが空でも旧版を安全に再開できるという意味ではない。
- T14/T15: 対象待ち/確認必要の日本語UI・3ブラウザー、照合と限定回復・独立競合・人間編集。結果不明の新job迂回や自動解除で代替しない。
- 実Google/OAuth公開審査、常設基盤、Stripe/AWS購入・メール、OS HIGH3、実AWS性能、RDS+S3復旧、法務/事業者/税務等の[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)。

## 承認境界・復旧

mainは読み取り照合で8567f49f。今回AWSを再照合・変更していない。mainマージ・ECR/ECS/S3/CloudFront・共有DB/実データ・Secrets/IAM・実課金/外部通知・容量/継続費用を変更しない。元checkoutのハンドアウト関連13項目を保持する。GitHub open Issueは#1の別UI課題のみで、本課題の新Issueは権限不足の先行記録に従い[下書き](GOOGLE_DURABLE_DELIVERY_ISSUE_DRAFT_2026-10-06.md)へ記録する。

未配備なので実環境の切戻しは不要。作業ブランチの変更は通常revertできるが、既存journalを消す逆移行や、新台帳を無視する旧worker起動は復旧方法にしない。共有反映する場合は対象SHA・現在の稼働版・drain・保持方針・送信停止/証拠保持を含む具体案と必要承認を別途揃える。
