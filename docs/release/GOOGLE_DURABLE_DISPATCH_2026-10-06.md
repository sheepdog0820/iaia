# Google未開始ジョブの永続配送（ローカル部分実装）

## 対象・承認境界

基準は `62573a06f6fb00c3f7b7ad4247b23716d03d904a`、専用ブランチは `codex/google-durable-dispatch-20261006`。Calendar/Sheets/両retry/自動同期の配送意図をDBに保存し、producerのcommit後callback喪失やbroker投入失敗でも、未開始の同一ジョブを回復できるようにした。正式公開 **No-Go** は維持する。

完了済みアイコン8567f49fの承認や固定6b6c570c反映案へ追加しない。mainは今回の読み取り照合でも8567f49f。main/AWS/ECR/ECS/CloudFront、共有DB/実データ、Secrets/IAM、実課金/通知、常設容量/継続費用を変更していない。新migration **0057・0058は隔離テストDBのみ**。常設worker/beat/Redisを起動した証拠ではなく、共有環境のschema適用・自動再投入運用には別途具体的な反映計画と承認が必要。

## 配送と状態の契約

- 5つのproducerをatomicにし、`AsyncJob` と `GoogleJobDispatch` を一緒に確定する。rollback/savepoint rollbackで両方を破棄する。意図の保存失敗は確定せず500となり、外部送信はしない。
- commit callbackは低遅延の補助に留め、永続意図を正とする。broker停止・publish応答喪失だけでジョブをFAILEDにしたり新規ジョブを作ったりしない。
- relayはoutbox行だけをPG行ロックし、UUID claimと5分期限を確定してからpublishする。未確認投入は60秒から最大3600秒の待機、投入ACK後もworker開始まで60秒待機で再投入可能。brokerが受理したこととworkerが開始したことを区別する。
- 開始時の既存ジョブ条件付きclaimとoutbox受領・暗号文消去は同一transaction。worker受領または新claimを古いpublisherの結果で巻き戻さない。QUEUEDかつ未開始・期限内のジョブだけをrelayし、running/succeeded/failed/uncertain/期限切れ/所有者・型・payload変更/削除済みCalendar対象は再投入対象外。対象外の暗号文は消去し、元ジョブ状態を変更しない。
- `dispatch_google_jobs --limit 1..1000` は上限付きの投入コマンド。Celery taskは既定100件、beat定義は60秒。期限切れclaim・期限欠落claimを一括回復し、同時relayで有効claimを2重取得しない。SQLiteの並列行ロック保証は主張しない。
- API応答はatomic内で構築されるため、通常の実配送経路でも `queued=false` となる。これは未投入や失敗の断言ではなく「応答構築時点で投入未確認」。既存の日本語案内はジョブIDを保持して履歴確認へ誘導する。成功表示への改善・実ブラウザーでの最新候補確認は残る。
- この修正は未開始の配送回復のみ。同じジョブの開始済み再配送は既存worker guardで拒否するが、旧FAILEDメッセージと新しい別ジョブ・同じ同期対象の世代fence、Google側結果照合、開始後停止/結果不明の限定回復、完全なexactly-onceを実現したとは扱わない。

## 内容保存・暗号化・削除

配送に必要な引数（Sheetsは登録時点の正確なセル値を含む）をAES-256-GCMで暗号化する。既存 `SECRET_KEY` と固定purposeからHMAC-SHA256で別用途鍵を導出、乱数12 byte nonceを使用。AADにはjob UUID・所有者・型・作成日時・payload digestを結び、別ジョブへの移植、snapshot変更、鍵変更、改ざん、不正引数は外部送信せず固定日本語エラーで終了する。鍵・OAuth token・セル値・暗号文を例外ログへ出さず、job API serializer/adminにも追加しない。既存Google接続/内容HMACを維持する。cryptographyは既存依存で追加・lock変更なし（host49.0.0、配布lock50.0.1）。

worker開始時、対象外判定、配送情報異常時は暗号文を空にする。ジョブ削除ではoutboxをCASCADE削除する。ジョブの既存7日期限を使用するが、beatが稼働していない環境で期限ちょうどの自動消去を保証しない。DB物理頁・バックアップの完全消去も保証しない。既存SECRET_KEYの変更は未配送情報を復号不能にするため、鍵ローテーション時は未配送の扱いを計画する必要がある。鍵更新やfallbackの追加はしていない。

0057は1テーブル追加。0058でPG FKをDBの `ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED` にし、SQLiteではjob削除triggerを追加した。旧アプリへ戻しても、残した新テーブルのFKが旧アプリによるjob削除を妨げないようにする。逆移行→再移行、旧アプリ相当のraw job DELETEを両DBでテストする。共有DBでの逆移行は行っておらず、逆移行は未配送意図を削除するため通常のアプリ切戻しでは**0058までのschemaを保持**する。未反映なので今回は実環境切戻し不要。

## テスト・失敗記録

証拠は `D:/tmp/codex-google-durable-dispatch-20261006/`。テストは合成データ・隔離PG18.3/tmpfsとメモリSQLite、未mockのprovider HTTPは禁止。実Google/新候補のRedis・別Celery worker・通常配布image・Scout・AWS・ブラウザーの証明ではない。

- 最初のREDは未実装module import失敗。その後claim変更/closed row再登録で5失敗1エラー、旧アプリDELETEでFKエラー、最終レビューの削除済み同期先/期限欠落batchで2失敗を保持して修正した。
- 初回回帰42件は31失敗・2省略。旧「broker失敗=FAILED/healthy API=true」期待と、新しい保持状態・応答構築時点の違い、task-ID専用fixtureの広過ぎるUPDATE mockを修正した。後続42/23件の初期ログは借用TestCase import由来の7件重複を含み、最終distinct集計へ加算しない。借用はmodule経由に修正済み。
- 初回PGは0057のCREATEとFK置換を同じmigrationへ入れ、DjangoがFK作成をschema editor終了まで遅延するためセットアップ失敗。FK操作を0058へ分離し、失敗した自分の使い捨てtest DBだけを所有者・接続0確認後に削除し再検証した。失敗をPG成功として扱わない。
- 最終Google関連＋文書回帰はPG **290成功/省略0**（161.380秒）、SQLite **280成功/PG専用10省略**（総290、108.296秒）。新規distinct25件を含む。PG独立connectionの同時relay claim、全5producerのcommit/rollback/保存失敗、暗号化/改ざん/内容固定、投入ACKと開始receiptの競合、raw DELETE/移行往復などを確認した。
- 設定6 modulesは最初Windows hostで総64件・8エラー。Twisted循環importによるmodule発見失敗と、UTF-8子プロセス出力をcp932で読むエラーを保持する。既存Linux配布imageを依存runtimeとして、**現行ソースをread-only bind**・network none・entrypointをpythonへ置換した隔離試験では **70成功/省略0**（61.018秒）。現行通常imageを構築した証明とは区別する。
- Black/isort/Flake8/Banditは変更13 Pythonファイル成功。既存settingsのB105 nosec未検出警告は出るが、今回抑制を追加していない。日本語のmodel状態・固定エラー・command診断を確認した。`makemigrations --check --dry-run` はメモリDBでNo changes detected。
- 通常coverage設定はmigrationsをomitするため、外部の専用設定で新migrationも測定した。移行後の追加unsupported逆移行guardをRED1失敗→修正し、最終SQLite回帰は再び総290/280成功/PG専用10省略（82.353秒）。PG最終測定は290成功/省略0（153.901秒）。変更後0058のcoverageに変更前PG arcを混ぜず、最新SQLiteの移行往復・PG DDL生成正負mockで測定し、実PGのFK往復/DELETE成功証拠とは区別した。中間の旧source arc混在によるcoverage監査失敗も保持する。
- 最終製品差分は **240実行文・58分岐先100%、欠落/除外0**。新outboxは133文42分岐先、0058は28文10分岐先100%。settings追加は既存dictの継続行のため新実行文0だがbeat値のassertionとLinux設定70成功で検証した。全17 staged textのUTF-8/LF/BOM・差分検査成功、日本語状態/固定診断の手動レビュー済み。文書39成功・相対リンク5件有効を確認し、限定配送修正内に追加の未修正指摘は残らない。

隔離Linux設定containerと自分のPG/tmpfsを撤去した。PGのdefault fixture table0/test DB0、停止終了0/OOMなし、同label container/volume0を確認し、証拠を保持。元checkoutのハンドアウト関連13 itemsは変更・stageしていない。証拠ディレクトリのrootファイルは最終SHA-256一覧で照合する。

基準62573a06の[CI全6項目成功](https://github.com/sheepdog0820/iaia/actions/runs/37458377900)をSHAと照合した。今回の新候補CIはpush後に確認し、親の成功を転記しない。push workflowはCIのみでAWS反映処理はない。GitHub Issue書き込み403・CLI未認証は先行確認から変わらず、[下書き](GOOGLE_DURABLE_DELIVERY_ISSUE_DRAFT_2026-10-06.md)を更新するがIssue作成済みとは扱わない。

OS HIGH3、実OAuth/外部連携、Stripe/通知、worker常設運用、性能、復旧などの不足と[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は残る。
