# Google投入結果とworker状態の保全（2026-10-06）

## 対象・再現

親候補は `72136cf9cf5ae3128cb9b92ba1fc225e0bb9d787`、専用ブランチは `codex/google-dispatch-state-20261006`。Calendar/Sheets新規・両再試行・セッション自動同期の5経路を対象にする。main/AWS/共有DB/Secrets/課金/容量/承認対象は変更しない。元worktreeの別作業13項目を保持する。

投入関数の `.delay()` と `celery_task_id` 保存が同じ例外処理に含まれ、診断ID保存だけの失敗でも `queued=false` になった。さらに呼出元の無条件 `mark_failed()` が、投入中にworkerが開始・成功・失敗したジョブを古いオブジェクトから失敗へ上書きし、Calendar同期情報にも失敗を保存した。

テストファーストのREDは新規7メソッドを実行し、32 failure/2 error・PG専用1省略（0.878秒）。ID保存失敗・worker先行・期限/開始履歴・削除のケースを含み、後続の同一TestCaseトランザクションへの影響も記録している。単なるテスト準備失敗として扱わない。

## 修正した契約

- `.delay()` が正常に戻った場合と診断ID保存を分離する。ID保存失敗だけで投入失敗にしない。新しい警告ログは固定の運用文言のみで、ID/出力内容/資格情報/例外本文を追加しない。
- 投入失敗の保存は同じPK/owner/type、期限内、`QUEUED`、`started_at IS NULL` の条件付きUPDATEに限定する。workerのRUNNING/SUCCEEDED/FAILED、開始履歴、結果、進捗、終了日時を遅れたpublisherから上書きしない。削除されたジョブを再作成しない。
- 同じトランザクションで、Calendar同期のPK/user/session/created_atとPENDINGを照合して失敗状態を更新する。削除・同PKの新世代・既に保存された同期結果を変更しない。
- Calendar新規APIの `sync_status` は投入後に対象の正確な世代から取得する。削除・置換時は `null`、正常/既存失敗時は従来の状態文字列。画面はこの項目を参照せず、ジョブ一覧を更新する既存処理を維持する。
- broker未接続の未開始ジョブは従来通りFAILEDにし、既存の日本語再試行案内を維持する。HTTP202、`job_id`、`queued`、再試行の `retry_of` は維持する。

## 検証

隔離したホストPython 3.11.1とPostgreSQL 18.3を使用する。PGは512 MiB/2 CPU、loopback `127.0.0.1:55444`、専用の合成DB・ユーザー・volumeのみ。SQLiteは使い捨てメモリDB。外部provider HTTPは禁止し、broker/Google応答はmock。実Google・実brokerの成功とは区別する。

- 初期SQLite：7メソッド中6成功・PG専用1省略（0.736秒）。追加の境界を含むPG対象試験9成功・省略0（3.242秒）。
- 初回広域：Google関連23モジュール190件＋文書39件、PG229成功・省略0（126.071秒）、SQLite222成功・PG専用7省略（91.213秒）。
- fixture整理後の最終広域：PG229成功・省略0（123.142秒）、SQLite222成功・PG専用7省略（89.347秒）、両終了0。先行の初回ログ/coverageも別名で保持する。
- 別接続の実PG workerが開始または完了した後に投入応答を失うCalendar/Sheetsの4ケースで、publisher終了後も保存状態が不変、最終成功、HTTP送信1回を確認する。
- 新規試験は5経路の正常投入・ID保存失敗・worker先行の3状態・broker不通・ジョブ/同期削除、期限/開始履歴、owner/type変更、同期結果保存済み/同PK新世代を確認する。元FAILEDジョブの再試行でも元記録が不変。
- 本体4ファイルの追加実行文26・分岐2は両DBで100%。初回新規試験の未使用fixture分岐（PG1文1分岐）は削除して最終再実行し、新規試験252文62分岐はPG100%・除外0。SQLite212/252文・54/62分岐の未実行分はPG専用メソッドのみで、省略7の全体実行結果と区別する。
- Black/isort/flake8/Banditの対象は5 Pythonファイル。最終品質確認（Bandit指摘/解析エラー0）とworkflowのPG選定追加/YAML確認、差分空白確認は合格。新しいUI文言はなく、APIの既存日本語エラーを明文で照合する。UI構造/JS変更・実ブラウザー操作なし。ソースレビューに追加の指摘なし。

## 制約・残課題

この修正は永続outbox/配送一度だけ保証ではない。`.delay()` が例外を返した場合の `queued=false` はpublisherが成功を確認できなかった意味で、配送されていない保証ではない。未開始ジョブがFAILEDになった後でも既存workerはFAILEDから再開できる。新ジョブの手動再試行と元配送が重複する可能性、画面の「開始できませんでした」という案内、job未commit/外側transactionやDB障害/応答消失の整合性、lease/worker消失回復は残る。

新規API・自動同期・再試行の投入前PENDING初期化や、同じ同期を扱う別ジョブの競合、enqueue時点の世代/セッション版固定は未解決。workerのHTTP後の外部結果を取り消さず、同期/ジョブの最新状態を外部サービスとの完全な原子操作にはしない。実配送、期限/部分出力UI、永続Google接続先IDの方針確認も別途必要。

GitHub Issueの新規作成は403 `Resource not accessible by integration` で失敗した。権限変更や別認証で回避せず、本記録と受入表に残す。親CI `37431920504` は17:05 JST確認時点5成功/Playwright実行中。今回候補の全CI/通常配布物/実Google/AWSは未確認。

17:05:30 JSTにフルcontainer ID/name/label/image、volume labelとmount先を照合し、test DB数0/fixture public tables数0を確認して今回のcontainer/volumeだけを停止・削除した。残存container/volume/55444 listenerは0。合成PGデータは削除済み、source/archive/通常イメージ・別作業は保持する。

証拠は `D:/tmp/codex-google-dispatch-state-20261006/` のRED/初期/最終ログ、coverage JSON、補助runner、Bandit結果、cleanup/SQL記録に保持する。復旧は未反映の今回修正を候補から外すか、専用ブランチでrevertして検証する。共有DB/schema変更はない。HIGH3等のOS指摘・承認待ちの実課金/常設worker/性能/復旧等は引き続き未達、正式公開No-Goを維持する。
