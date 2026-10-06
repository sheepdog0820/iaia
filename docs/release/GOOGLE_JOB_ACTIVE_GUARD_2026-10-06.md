# Google配送中のジョブ有効性・状態保存

## 根拠・変更・利用者への影響

親は `1690508e334300a8aaa3a04f427b3f3f05e47e90`、専用ブランチは `codex/google-job-active-guard-20261006`。[開始取得](GOOGLE_JOB_START_CLAIM_2026-10-06.md)と[通常配布物](GOOGLE_RUNTIME_4535C03F_2026-10-06.md)後も、token取得中/Calendarの要求間/Sheets分割間に期限超過・削除・完了が起きた場合、workerは送信や古い状態保存を続け得た。削除後のsave(update_fields)はDatabaseErrorになる。実Googleの配送事故を観測したものではなく、実DB操作と合成応答で再現した。

- token取得前、Calendar各HTTPの認可確認前/送信直前、Sheets各chunkの認可確認前/送信直前に、元UUID/owner/type・現在RUNNING・期限内の行が存在するか再確認する。失効した場合は内部結果`inactive-job`で停止し、その後の配送をしない。これを外部サービスの原子的取消とは扱わない。
- Google処理の進捗/失敗/成功保存を、同じ有効条件付きの単一DB UPDATEへ置き換える。更新0件は専用例外で停止する。削除済み行を再作成せず、別の完了記録や期限超過行を上書きしない。モデル/schemaや他種類のjobの保存方法は変更しない。
- Calendarの失敗はjobの条件付き保存が通った場合だけ同期行へ保存する。無効化後のtoken/HTTP/応答形式/認可エラーで同期行を古い失敗にしない。無効なjobについての自動retryも当該保存段階で停止する。
- 最後に確認できたCalendarの遠隔結果は同期行に保持する。応答受領後にjobが失効しても、受理済みの作成/更新/削除をなかったことにはせず、jobの完了記録は条件付き保存で保護する。Sheetsで受理済みの途中出力を巻き戻す機能ではない。
- 開始UPDATE直後のrefresh_from_db中にcleanup削除された場合も、取得失敗として送信せず終了する。専用例外だけを境界decoratorで処理し、wrapsでTaskの情報を保持する。未知例外を成功へ変換する処理ではない。
- 既存のFAILEDからの通信retry・明示再試行、接続/資格情報/対象/内容/所有権確認、ETag/RAW/100行分割・日本語エラーを維持する。新しい利用者向け文言は0件。保持期間・期限・cleanup条件を変えず、期限超過のRUNNING行を独断で再実行/解放/延長しない。

## TDD・検証と証拠範囲

初回REDは7メソッドで7 failure/62 error（1.258秒）だったが、削除例外でTestCaseのトランザクションが壊れた後続波及と、Calendar PUTの合成応答不足を含む。個別atomicと一致する予定応答へfixtureを修正したREDは42 failure/27 error（2.959秒）、その内訳は実際の削除済み保存DatabaseError 23と、予期しないretryへMockを返したfixtureのTypeError 4である。後者はretryを正規Retry例外のfixtureへ整理し、製品の例外分類を緩和していない。両REDログを保持し、69件すべてが独立した製品不具合という主張にしない。

- 初期PG GREENは新旧14成功/省略0（6.439秒）。レビューで開始UPDATE/再読込間の削除を追加し、修正前のPGは1メソッド2 subtest error/0 failure（0.150秒）のDoesNotExistを再現後、取得失敗へ対処した。現在owner/type変更の拒否も追加した。
- 新規9メソッドは実APIでjobを生成し、Task.runを実行する。token取得/最後の資格情報確認/各Calendar経路の要求間/認可・通信・応答失敗・最終遠隔応答/開始再読込の境界で実DB行を変更する。Sheetsは実APIから100所有キャラクター＋headerの101行を生成し、最初の100行送信後に残る1行を止める。
- 最終PG208成功/省略0（115.264秒）、SQLite203成功/PG専用5省略（85.021秒）。21 modulesで文書39、Calendar実Requests＋loopback8ケース、PG認可/refresh/開始競合5試験を含む。今回provider HTTP/queueはfixture mock、他のunmocked Sessionは専用runnerで遮断する。今回の無効化境界はcallbackによる実行順制御で、実broker/実Google/常設worker/最新配布物/AWSの証拠ではない。
- 本体差分62実行文/4分岐（lifecycle追加28/4、tasks差分34/0）は両DBで100%。lifecycle全39文/6分岐、新規試験全211文/56分岐も両DBで100%。全アプリ100%の主張ではない。対象3 PythonのBlack/isort/Flake8/Bandit合格・指摘0。PG CIの選定にも新規moduleを追加した。
- 文書追加後の文書回帰39件も0.036秒で成功し、相対リンク3件を確認した。日本語説明・新規利用者文言0件・実測/未確認の区別を自己レビューし、追加の要修正事項なし。

最終coverageは `D:/tmp/codex-google-job-active-guard-20261006-postgresql-coverage.json`（SHA-256 `a17960f7f25b99f1ff33fc91aa138d94338a4042f1546339041fa77c60e5f9e0`）と `D:/tmp/codex-google-job-active-guard-20261006-sqlite-coverage.json`（`e113bec18585c36cc4797c7a10760129ec62b23143c20deb8c2ec91b9176889d`）。同prefixのRED/初期GREEN/最終ログ・外部HTTP遮断runner・PG metadata/cleanup JSONを保持する。

専用PG `2bb0b3981ef8` の完全ID/name/label・127.0.0.1:55442・匿名volume `722202d51de7` を照合した。test DB0/public fixture tables0を確認後に停止・自動削除し、container/volume/55442待受残数0。元checkoutの無関係13変更・実データ・検証記録は削除していない。

## CI・未確認事項・復旧

先行4535c03fの[CI 37422087169](https://github.com/sheepdog0820/iaia/actions/runs/37422087169)は5成功/Playwright実行中、親1690508eの[CI 37422589768](https://github.com/sheepdog0820/iaia/actions/runs/37422589768)は4成功/Unit・Playwright実行中を実際に再確認した。同じ生きているrunを使い、観測待ちで再起動しない。今回の全CI・通常image・実環境は別検証である。関連open Issueはなく、先行Issue作成403のため権限変更や再作成をせず、受入表と本書へ記録する。

存在確認とHTTPは原子的でなく、その間の変更やin-flight送信/token refreshを取り消せない。SQL条件の時刻は評価時点であり、長いDB待機を含む絶対期限の強制を証明しない。別jobが同じCalendar同期を処理する競合、FAILED後の遅延duplicateと正規retry/実行試行の識別、プロセス停止/未知例外・遠隔応答喪失の回復、永続接続先と外部ID・既存予定方針、queue全入力型・実Google/OAuth審査などは残る。寿命/保持期間・失効時の利用者への途中出力案内を完了扱いしない。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/実ユーザーデータ、schema/migration、Secrets/IAM、課金/常設容量/継続費用、外部通知は変更しない。完了済みfavicon8567f49f承認や固定6b6c570c反映案の候補を拡張しない。復旧は通常revertでschema逆移行不要だが、失効後配送/上書き/削除例外を再導入するためfix-forwardを優先する。受理済み遠隔変更はrevertで取り消せない。OS HIGH3/native閉包・実課金/連携/性能/運用/復旧/事業者対応等の未達を保持し、[正式公開](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goである。
