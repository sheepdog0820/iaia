# GoogleジョブのDB確定後投入（2026-10-06）

## 対象と結論

基準は記録 `dbb17be7743e78db51a8db467c6dac0a5a287aa9`、アプリ `28ac2bc7d63dfeb49092f2643e975da56953bd0e`。専用ブランチ `codex/google-dispatch-commit-20261006` で、Google Calendar/Sheets/両retry/セッション自動同期の投入を、外側のDB transaction確定後まで待つようにした。rollback/savepoint rollbackでは対応する配送を破棄する。**durable outboxの完成ではない**。

最終回帰は実PG **265成功/省略0、142.612秒**、SQLite **256成功/PG専用9省略、95.411秒**。製品差分は3ファイル **34文・20経路100%/除外0**。main/AWS/共有DB/schema/Secrets/IAM/課金/容量/通知は変更せず、正式公開No-Goを維持する。

## 修正と利用者への影響

- queue helperは、通常autocommitなら既存の即時投入結果True/Falseを返す。atomic内では `transaction.on_commit` を登録しNone（確定待ち）を返す。手動autocommit無効でatomic外なら送信しない。
- APIでは確定待ちを `queued=false` として返し、未配送・成功を断言しない。jobはqueuedのまま保ち、既存の日本語「履歴で確認」案内とjob IDを利用する。Falseの実投入失敗だけを即時failedとして記録する。
- commit callbackは登録時のjob ID/所有者/種別、queued、未開始、未失効を再検査。削除、所有者/種別変更、running/failed/succeeded/uncertain/開始済み等なら送信しない。Sheetsの引数はdeep copyで登録時の内容を固定する。
- 確定後のbroker/publish失敗は、既存の条件付きfailure helperを使い、日本語固定案内を保存する。worker開始/成功/失敗、再作成された同期行は巻き戻さない。callbackのDB等の予期しない例外は固定ログだけにし、既に確定したrequestを500に変えない。記録に失敗したqueued jobの回復は未実装。
- GoogleのHTTP/接続世代/所有者/content binding/実行UUID/結果不明のworkerガードは変更していない。provider適用後の結果照合や、旧FAILEDメッセージ/別job/同一同期対象の完全fenceを実装したものではない。

## TDD・検証範囲

初回REDは8テストで30失敗/11エラー/PG専用1省略。確定前のtask ID保存、broker/publisher呼び出し、savepoint rollbackでも配送することを再現した。11エラー等には、未制限MagicMockのtask ID保存がtransactionを壊したfixture要因も含み、41件の独立した製品不具合とは数えない。初回GREENは7成功/1省略。追加境界を含む新規12テスト＋既存dispatch9テストのSQLite局所回帰は19成功/2省略（2.350秒）。初期ログは保存した。

新規12テストは、5producerの外側commit/rollback、nested rollback、5経路×broker/publish失敗、両種別×9状態変更、引数変更、eager、欠落job、手動transaction、確定後DB例外のprivacy、両種別×worker結果/再作成同期、実PG独立connectionの可視性を検証する。独立接続ではcommit前のjob不在・callback未実行とcommit後のjob可視を確認した。これは**別プロセスCelery/実Redis/実HTTPの今回候補の検証ではない**。publisher/transport/eager相当のテストにはmockがあり、先行[28ac通常実worker検証](GOOGLE_WRITE_RUNTIME_2026-10-06.md)を今回の実worker証明として流用しない。

既存dispatch stateテスト8件は、Django TestCaseの暗黙transaction内で送信する仮定を取り除き、TransactionTestCaseのautocommitで元の即時投入競合を維持した。通常の単体テストのrollback transaction内で、brokerへメッセージを漏らさない効果はあるが、broker未mockテストを全て個別特定/隔離したという証明ではない。新モジュールをProduction Database CIの明示対象に追加した。

Python3.11.1で対象5PythonファイルのBlack/isort/flake8/Banditが全終了0、whitespace成功。記録変更後の文書39テストも成功（0.037秒、実DB setupなし）。staged 9 textのUTF-8/LF/BOM/文字化け検査は成功。差分・既存日本語案内・queued boolean・認可/所有者/再送・例外privacy・相対リンク・証拠hashを自己レビューし、対応が必要な指摘なし。新しいUI文言/JS/CSS/テンプレート変更はない。今回候補の通常Docker配布物・Scout・ブラウザー・全課金/背景透過/負荷/実Google/AWSは未検証。親28acのCI全6成功は確認済みだが、今回候補CIの成功とは区別する。

## 残課題・課題登録

commit後、callback前/中のproducer停止では配送意図を失い得る。jobと配送意図の同一DB transaction、独立relayのclaim/再試行/監視、Google側結果照合/限定回復、同期対象の世代fence、結果不明の保存期間、安全な実worker再起動試験が引き続き必要。[GitHub Issue下書き](GOOGLE_DURABLE_DELIVERY_ISSUE_DRAFT_2026-10-06.md)に受け入れ条件を記録した。

GitHub open Issues読取は成功し、既存の#1は別のキャラクターUI課題。新Issue作成はintegrationの403 `Resource not accessible by integration` で失敗、CLIも未認証。Issueは作成されておらず、記録更新は未完了。認証/権限設定を変更せず下書きを保存した。先行OS HIGH3、実OAuth/通知/課金、常設worker、性能、整合性ある復旧等も未達である。

## 撤去・復旧・証拠

合成PG18.3を固定image、read-only root/512 MiB/2 CPU/tmpfs、localhost専用55444で作成。外部provider HTTPは禁止したhost runnerで、合成test DBだけ作成/migrate/削除した。20:36:49 JSTにfull ID/name/label/image/mount/portとtables0/test DB0を確認し、専用PG containerと合成tmpfsを撤去（停止0/OOM false、対象container/volume残数0）。ログ/helperを保存し、元checkoutの別ハンドアウト作業13項目は保持した。合成データはhelperから再作成できる。コードを戻す場合はこの専用修正コミットをrevertする。共有schema変更はない。

証拠は `D:/tmp/codex-google-dispatch-commit-20261006/`。全体テスト・公開/運用ゲートの合格やAWS反映済みとは扱わない。

| 主な証拠 | SHA-256 |
|---|---|
| `red-sqlite.log` | `6c7bcbcdf503ffc67dc69f08f9f5ee0d361917e6e7495aeb633b3c39877005f0` |
| `regression-pg-final.log` | `b45299054835811e3abd2752eb96cf4c9fa3d2e1e6f472451c729a1e18f3b497` |
| `regression-sqlite-final.log` | `dd6d40c6598e348a380f0a97733c0aa47bf24a049974e2b9c14affa773fd92f7` |
| `coverage-diff.json` | `8747b50ad8a57f13c643285cf67e334f32bbe6a16c8822e5caa35b931e4bd380` |
| `quality.json` | `cec427bca78a0f8283b00982955529f46652f55b3ed228c4fd84f07b67c8bf87` |
| `cleanup.json` | `9c141d99955ec8edf82cf94ec29e47c12d6617c9e06c73d113bb29da099d8743` |
