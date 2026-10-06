# Google配送IDの型・UUID境界

## 根拠・変更・利用者への影響

親は `28af6db86fa75a03ca67cfe3e4e9e621e3f42df6`、専用ブランチは `codex/google-dispatch-identity-20261006`。[配送中の有効性確認](GOOGLE_JOB_ACTIVE_GUARD_2026-10-06.md)後も、queueから不正なjob IDを受けるとORMがValidationError/TypeError/ValueErrorで停止し、Sheetsの文字列・小数・boolのowner値は整数へ暗黙変換され得た。合成利用者pk=1ではTrue/文字列1/小数1.0で実Task.runがexportedまで進むことを修正前に確認した。同じ数値の所有者を表す不正型の再現であり、別所有者への認可突破や実Googleへの配送事故を観測したという主張ではない。

- worker受信時にjob IDを厳密なUUIDまたは長さ45以下の文字列として検査し、UUIDへ正規化する。不正型・不正表現を既存の内部結果`invalid-job`で返す。整数/bool/bytes/list/dictの暗黙変換はしない。
- Sheetsのowner IDは厳密なintかつ0より大きいsigned 64-bit範囲に限定する。Calendarの同期IDに既にある同じ境界を維持する。不正型はDB参照、認可・token取得、HTTP、retry、状態変更の前に終了する。
- 正常な実API生成ジョブのUUID/canonical/大文字/hex/braces/URNの6表現は配送できる。保存済みowner/type・接続・対象・内容・現在所有権・開始取得・配送中有効性の確認は省略しない。解析は標準UUIDに委ね、認識可能な表現をこの6種類だけと主張しない。
- queue producer、Celery serializer、引数数/kwargsの検証、モデル/schema/保持期限は変更しない。新しい利用者向け文言は0件であり、画面描画は変更しない。

## TDD・検証と証拠範囲

修正前SQLite REDは4メソッドで15 failure/28 error（1.319秒）。subtestを個別atomicで隔離し、前の例外によるトランザクション破損を後続ケースの根拠にしない。不正job ID 14種類×2 worker、Sheets owner 15種類、正常UUID 6表現×2 worker、不存在の有効UUID 3種類×2 workerを検証する。拒否時は全job/同期行が不変、token・HTTP・retryが未呼出で、不正型のケースはworker内DB問い合わせ0件を確認した。

- 初期PG GREENは新旧20成功/省略0（8.716秒）。最終22ラベルはPG212成功/省略0（116.778秒）、SQLite207成功/PG専用5省略（総212、86.992秒）。文書39件、既存の実PG並列競合5・Calendar実Requests loopback8ケースを含む。新規4メソッド自体にDB別省略はない。
- 両DBで本体追加差分18実行文/10分岐（helper10/4、Task8/6）、新規テスト全62文/20分岐が100%、欠落0。リポジトリ全体100%という主張ではない。
- 変更Python3ファイルのBlack/isort/Flake8/Banditは終了0、Bandit指摘・警告0。UTF-8/LF・差分、所有者境界・正常互換・日本語文言をレビューし、対処すべき指摘なし。重要な利用者向け文言の追加がないため新規日本語表示assertion/ブラウザー検証は不要。
- Python3.11.1/Django5.2.15、合成設定と空ENV_FILE、SQLite in-memory/専用PostgreSQL18.3（127.0.0.1:55443、512MiB/1CPU）で実行した。実データDB・実Google・実brokerへアクセスせず、loopback以外の未Mock HTTPは禁止する。
- テストDB/fixture public tableが0件であることと、専用container ID/label・volume/mountを再照合して削除した。残container/volume/55443 listenerは0。削除したのは合成試験データのみで復元対象ではない。ログ・coverage・runner・metadataは保持し、元checkoutの別作業13項目は保持した。
- 2026-10-06 15:44 JSTのCI観測では4535c03fの37422087169は全6成功。1690508eの37422589768は5成功/Playwright失敗で、job112135034658の終端ログは299 passed/1 flaky（17.5分）、Firefox account-deletionのsignup page.gotoが操作30秒でtimeoutし終了1。trace未精査のため原因を断定せず、再試行成功をCI成功へ置き換えない。親28af6db8の37424071695は4成功/Unit・Playwright実行中。新候補の全CI・通常配布物・実Google/AWSは未確認。

ローカル証拠は `D:/tmp/codex-google-dispatch-identity-20261006-` に続く `red.log`、`green.log`、`postgresql-tests.log`、`sqlite-tests.log`、`run.py`、`pg-metadata.json`、`cleanup.json`、両DBの`coverage.json`。最終coverage SHA256はPG `00b65668549b2cfc6f1fe109d5a1426e74732f678905504ce8a6d31447aa39eb`、SQLite `b769f04d9820321983f31b27648ca2f058c6880e22f1414ecabbffaf6c2356e6`。先行CI終端ログは[失敗run](https://github.com/sheepdog0820/iaia/actions/runs/37422589768)で確認した。

## 未確認・承認境界・復旧

今回の範囲はworker受信時の識別子検証であり、queue全入力の型・producerの識別子結合・引数数、実broker配送や実Googleの成功、再接続後の既存予定/永続外部ID方針を完了扱いしない。原子的HTTP取消/絶対期限、試行lease・FAILED duplicateとretryの識別、別job同一同期の競合、途中出力案内/プロセス停止/遠隔応答喪失の回復等は残る。先行Playwright失敗は別の調査対象として保持する。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/実ユーザーデータ、schema/migration、Secrets/IAM、課金/常設容量/継続費用、外部通知は変更しない。完了済みfavicon8567f49f承認や固定6b6c570c反映案を拡張しない。復旧は通常revertでschema逆移行不要だが、不正型の配送/ORM例外を再導入するためfix-forwardを優先する。OS HIGH3/native閉包・実課金/連携/性能/運用/復旧/事業者対応等は未達のまま、[正式公開](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goを維持する。
