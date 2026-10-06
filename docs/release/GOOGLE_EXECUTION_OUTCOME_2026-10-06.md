# Google実行期限・結果不明の検出（2026-10-06）

## 対象と判断

親 `001addcce40cba19d73d69ca1dd330fe78b97f93` の[実worker停止検証](GOOGLE_WORKER_CRASH_2026-10-06.md)で、停止後のGoogleジョブが `running` のまま回復しない問題を確認した。この修正は「実行期限を過ぎた結果を成功・未配送と断言せず、結果不明として表示する」第一段階であり、自動復旧・再送・正式公開合格ではない。正式公開 **No-Go** を維持する。

作業ブランチは `codex/google-execution-outcome-20261006`。元worktreeのハンドアウト関連変更を混ぜず、mainへ直接コミットしない。アイコン `8567f49f` のmain・開発AWS反映承認は今回のアプリ・DB変更を含まない。共有DB・AWS・課金・Secrets・容量・実ユーザーへの通知を変更していない。

## 変更仕様

- `AsyncJob` に nullable な実行UUID `execution_token` と索引付き `execution_deadline`、状態 `uncertain`（結果不明）を追加する。migrationは `schedules/0056_asyncjob_execution_outcome.py`。UUID・期限・payloadをAPIへ新たに公開しない。
- Googleジョブの既存条件付き開始UPDATEで毎回新UUIDを採番する。期限は現在DBの `expires_at` と実行予算の短い方。実行予算は `max(900, CELERY_TASK_TIME_LIMIT) + 60` 秒、未設定・無効値は960秒。長い設定は尊重する。元 `started_at` は既存仕様どおり保持する。
- Google Calendar/Sheetsの `running` だけを対象とし、実行期限以下になった行を結果不明へ条件付き更新する。旧行の期限NULLは `started_at`、なければ `created_at` と実行予算で判定する。これはworker死亡の証明、heartbeat、更新可能leaseではない。
- 所有者の一覧・要求した所有ジョブ詳細・再試行のアクセス時に判定する。他人の要求・未認証アクセスでは変更しない。一覧は状態フィルター前に分類する。既存期限清掃も判定するが、beatの新規設定はしない。
- 正常な読み取りで対象がない場合はUPDATEを試みない。対象がある場合はDB書き込みが必要であり、DB障害時の成功を保証しない。判定UPDATEは同じ条件を再評価し、並列完了や新しい開始を上書きしない。
- 判定後は固定日本語案内・検出時刻を保存し、入力・進捗・結果・開始時刻・診断ID・実行UUID・期限を保持する。`finished_at` はこの状態への検出時刻であり外部処理の完了時刻ではない。
- 送信直前・進捗・成功・失敗の既存ガードに実行UUIDと期限を追加する。旧実行の遅延更新を拒否し、結果不明の再試行は400、新規job/配送なしとする。画面には「結果不明」と外部結果確認の案内を表示し、再試行ボタンは表示しない。
- 連携ジョブ欄の警告文字色を限定指定する。スマートフォンは表内横スクロールで案内列の極端な縦伸びを防ぎ、日本語ラベル付きの領域をキーボードでも移動可能にする。既存の他状態・他ページの配色を変更しない。

## 検証記録

証拠は `D:/tmp/codex-google-execution-outcome-20261006/`。通常の開発DBや実Googleに接続せず、専用SQLite・合成ユーザー・実PostgreSQL 18.3の使い捨てtmpfsを使用した。PGはlocalhost限定55444・512MiB/2CPU、今回Docker networkはbridgeでありnetwork noneではない。

- REDは新規16件で2 failure/27 error。最初のGREENの1 failureはテストのQuerySetキャッシュを参照した検証ミスで、再読み込み・値比較へ訂正した。関連開始/実行ガードを含む33件は31成功/PG専用2省略。
- 最初の全回帰は両DB各246件で5 failure。正常ジョブ閲覧でも空UPDATEを試み、既存の書き込み障害テストと競合したため、製品側に対象存在チェックと無UPDATEの新規回帰を追加した。既存テストを弱めていない。
- 最終件数・画面結果・カバレッジ・終了状態は後述の確定記録を参照する。PostgreSQL競合テストは別接続の実UPDATE行ロック待機を観測し、完了commit/失敗後の新開始commitの2ケースで判定更新0・最新状態保持を確認する。
- 初回の色実測は白字で2.1477:1となり不合格。テーマの `.bg-warning` 上書きが原因であり、局所CSS修正後は濃色 `[33,37,41]` / 背景 `[245,158,11]`、7.1828:1を実測した。初回失敗ログを保持した。初期141件成功は色実測・最終スマートフォン調整前として区別する。
- PC1280/スマートフォン390、実所有ジョブAPI、同一inline script、キーボード更新、戻る/再読み込み、主要6画面200、未認証302/401、不存在404、pageerror0を確認する。実Google OAuth・API受理ではない。
- migrationは隔離DBだけに適用し、`makemigrations --check --dry-run` は差分なし。既存coverage設定はmigrationを除外するため、migrationを100%行カバレッジとは称しない。
- Black/isortは対象Python6ファイル、Flake8/Bandit、差分・UTF-8/LF・日本語文言・自己レビューを対象にする。既存の英語状態token/Googleの固有名詞は維持し、新状態と案内は日本語。
- 親 `001addcc` の[CI](https://github.com/sheepdog0820/iaia/actions/runs/37443400796)は全6成功を確認した。今回の全CIはpush後に別途確認する。関連Issue作成は先行403で未完了、権限変更や別作者への切替はしていない。

## 未解決・反映条件・復旧

- 開始済みHTTPは取り消せない。Google側の受理後にjobが結果不明となり得る。Calendar同期行は既存処理で遅い受理応答を保存し得るため、AsyncJobのUUIDは同期行・別jobまでの完全なfenceではない。
- 既存の通常7日保存と期限清掃を変えない。期限切れの結果不明も削除されるため、永続証跡・長期結果保持を実装したとは扱わない。
- durable outbox、producer transaction、自然なbroker再配送、確定結果照合、限定回復UI、新job/同期世代の排他、常設worker/Redis/beat/監視は未完了。UUIDは取得後の実行を識別するもので、古い配送メッセージがFAILEDを新たに取得することまで禁止する不変の配送IDではない。新通常配布物での実worker強制停止は今回未検証。先行29efの実停止失敗を修正後の通常配布物成功と取り違えない。
- 外部予定の再接続後方針は人間の判断待ち。結果確認案内は移行・再紐付け方針や自動再送の承認ではない。OS HIGH3、実AWS課金・メール・性能・復旧等の未達も残る。
- main/AWS反映には今回候補を対象とする別承認が必要。共有migration適用も別承認が必要で、適用前に既存行数・DDLロック・稼働版・復旧版を確認する。新旧worker混在では旧workerがUUID/期限を理解しないため、停止/排出と順序を含めて計画する。
- 未反映なので現在の稼働復旧操作は不要。将来の承認済み反映で問題が出た場合は対象稼働版へ戻し、追加nullable列・索引・結果不明の記録は残す案を事前確認する。共有DBの逆migrationや外部予定の変更を自動実行しない。

## 確定記録

- 最終PG回帰247件は137.852秒で全成功・省略0。SQLite247件は90.214秒で239成功/PG専用8省略、いずれも終了0。新規18件を含み、Google関連24 moduleと文書39件の合計であり、アプリ全機能試験ではない。
- Python本体の差分39文・6分岐は両DBで100%。新規テストmoduleはPG253文・32分岐100%/除外0、SQLiteはPG専用40文・6分岐を未実行として明示する。追加inline JSの実関数1断片はV8 5区間・未実行0、inline全体の構文を確認したが画面全JSのカバレッジとは扱わない。
- 最終PC・スマートフォンの実API画面は日本語2状態、再試行なし、案内保持、実script/source一致（inline SHA256 `c3c3013a9055e9628d819282c2bd3fec45a1e8ce766aaf8da9005452c1e6a252`）、コントラスト7.1828:1、root横はみ出し0、戻る/再読み込み・主要6画面・未認証/不存在・pageerror0。スマートフォンの表内横スクロールと行高も確認し、PC/mobile/mobile-guidance PNGを目視確認した。
- 通常CIモードの新規画面6件は最終19.8秒で成功・retry/skip/flaky0。最終の実APIモード関連画面141件は321.856秒で全成功・retry/skip/flaky0（新規6、投入結果108、Google設定21、連携/ゲスト6）。Chromium/Firefox/WebKitで濃色・日本語・スマートフォンの表幅/行高/キーボード横移動を含めて確認した。実APIなのはジョブ判定/所有者/serializerで、無関係なGoogle設定API等は合成応答に隔離する。
- 文書39件成功。Python対象6ファイルのBlack/isort/Flake8/Banditは成功、Bandit指摘0。11 staged textのUTF-8/LF・BOM/置換文字/文字化け検査と差分チェックに合格、日本語追加文言と既存固有名詞・状態tokenを確認し、自己レビュー後の追加指摘なし。
- PG試験DB/基底public表0を確認して専用container/tmpfsを19:02:32 JSTに削除、タスクlabelのcontainer/volume0。画面終了後は所有PID/起動command/child/listenerを検証して専用サーバーを停止した。合成ユーザー3人・Google job2件（両方結果不明・進捗10）とmigration 0056のある専用SQLiteを監査して19:10:29 JSTに削除、8000閉鎖。監査JSONはUTF-8日本語正常であり、清掃時のconsole表示encodingの崩れをDB破損とは扱わない。合成データはfixtureで再作成可能、ログ/PNG/証拠を保持する。
- 19:10時点に9アプリsourceとroot証拠66ファイルのSHA256 manifestを保存した。後続コミット確認のログはこの時点のmanifest対象と混同しない。主要な固定証拠は以下。

| 証拠（証拠フォルダー内） | SHA256 |
| --- | --- |
| `regression-pg-final.log` | `e6919235aeb4b09168b74463b41918bd827e7bd2977e6571aa122e9b00c86317` |
| `regression-sqlite-final.log` | `932235ec673cbc7d6087cddb96942083b0d31a242fd71dd8e88b5a8e828191d6` |
| `coverage-final-summary.json` | `4a86d3b6cc9400351533de46c2e3c89a6e5ddaa23681dede73656694fdb133d7` |
| `browser-results.json` | `8bcc7bc2742a0e2ed6e6de7e7552dc9182c861d47de926794d444ba41457ac63` |
| `visual-results.json` | `d6e929eb1b8ae47af50eec9e7c977ad0ec1c8ffd83c06623b1bd0e62127dd3ff` |

19:02時点のremote mainは `8567f49f8d411bad7f732afaeebad85357eeca09`。AWSは今回読み取り/更新しておらず、現在の稼働状態を確認したとは称しない。元 `C:/Users/endke/Workspace/iaia` の別ブランチ・13 dirty項目を保持した。今回の全CI・通常配布物・実Google・常設運用・共有反映は未確認/未実施、No-Goを維持する。
