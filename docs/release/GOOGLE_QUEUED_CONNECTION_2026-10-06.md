# Google待機ジョブを作成時の接続先に固定（2026-10-06）

## 対象・動作

- 親コミット: `0c9b9e5a59f587316982f41dd1e40afbb4052585`。ブランチ: `codex/google-queued-connection-20261006`。
- 前回までのHTTP直前ガードはworker開始後の変更を検知するが、待機中に接続先が変わると、新しい接続先を開始時の正しい接続として選び直していた。
- Calendar API受付、Sheets API受付、自動Calendar同期の3経路で、ジョブ作成時に`google_connection`をpayloadへ保存する。連携ID/利用者ID/接続日時と、最新token行/account/app/UIDを、既存SECRET_KEYを使った用途別HMAC-SHA256で64文字の不透明な値にする。access/refresh tokenはハッシュ入力にも含めず、UID/識別情報自体もpayloadへ追加保存しない。DBスキーマ・秘密鍵・権限の変更なし。
- workerは現在の連携/資格情報を開始時に照合し、不一致・欠落・不正形式ではtoken取得/refresh前に固定日本語エラーで終了する。追加HTTP/自動retryなし、Calendar同期/ジョブを失敗として完了する。認可喪失の既存エラー、日時/範囲/ID検証、途中の失効/接続変更チェックは維持する。
- 接続先を保存していない旧ジョブも停止する。実行時の接続先を旧ジョブへ後付けしない。利用者は接続先を確認して新しいジョブを作成する必要がある。接続変更後の新ジョブが新しい固定値で成功することを確認した。
- 同じtoken行/account/app/UIDでの待機中の通常access更新は接続先変更としない。前回のworker開始後のaccess照合と、通常refresh/設定保存の継続を維持する。Google側の実際のtoken所有者/有効性をDBの識別値だけで証明するものではない。
- tokenがないremote API要求は既存の日本語再連携エラー/400で受け付けない。Sheetsのローカルプレビューは維持する。クライアントから渡された`google_connection`は採用しない。

## TDD・検証

- 初回7件は89 failure/15 error。非nullのpayloadへNULLを保存したfixtureと、queue mockの未設定戻り値がレスポンスJSONへ混入したfixtureを訂正した。次の7件は102 failure/0 error。
- 待機中のaccess回転だけでは接続先が変わらないことを仕様に合わせて正例へ分離し、修正前8件で96 failure/0 errorを確認した。実装後、前回2 moduleを含む25件成功（4.622秒）。
- 日本語レビューで、旧ジョブにも「連携設定が変更された」と断定する説明を訂正する必要を確認。表示試験11件で96 failure/0 errorを再現し、開始時照合のエラーを「ジョブ作成時のGoogle接続先を確認できません。接続先を確認して再実行してください。」へ分離した。処理途中の変更エラーは維持する。追加文言のBlack検査が最初は失敗したため当該ファイルだけ整形し、整形後の版で再検証した。
- 最終新規10件には105 subtestを含む。APIの5モード×13変更65例、自動同期13例、未変更成功6例、3生成経路の秘匿3例、待機中access更新2例、旧/不正payload12例、再作成成功2例、試験用署名鍵変更2例。他にremote拒否/ローカルプレビューとクライアント値無視を確認する。
- APIは実Django/DRFルートとDBジョブ作成を通し、queueの呼出し引数をそのまま実workerへ渡す。OAuth再接続保存receiverやallauth解除も前回の実DB fixtureを再利用する。Celery/broker/provider HTTPはmockであり、実Google/実ブラウザー/実AWSではない。解除メールもmock/メモリ内に限定する。
- 既存の手作りジョブfixture 8 moduleへ作成時固定値を追加した。Sheetsの繰り返しfixture生成は1 helperへまとめ、ガードをmockで迂回しない。
- 先行SQLite114件は108成功/PG専用6省略（25.486秒）。クライアント値と鍵変更の2件を追加した先行116件はSQLite110成功/6省略（34.448秒）・PG116成功/省略0（50.375秒）。文言訂正後も同じ116件がSQLite110成功/6省略（35.756秒）・PG116成功/省略0（52.182秒）だが、以下の最終整形後の証拠と区別する。
- 最終整形後の116件はSQLite110成功/PG専用6省略（34.828秒）、PostgreSQL116成功/省略0（50.948秒）。文書試験39件も成功。コミット対象16ファイルのUTF-8/LF・ステージ済み差分の空白検査を確認した。
- 本体差分31実行文/14分岐、新規テスト176文/38分岐100%。新モジュール全18文/6分岐100%。worker全体74%、連携views全体97%であり、全機能・実通信を100%検証したという意味ではない。
- 対象13 PythonのBlack/isort/Flake8/Bandit、空白検査成功。Banditの合成fixtureに限定したB105/B106例外に対する「no failed test」警告は残るが、指摘項目は0。日本語エラーを完全一致確認し、資格情報/UIDを表示しない。自己レビューの文言問題を修正し、追加の要修正事項なし。
- CI YAMLのparse/PG対象追加を確認。workflowはDjango CIのみで、codexブランチの通常pushにAWSデプロイは含まれない。全CIはpush後に別途確認する。
- callbackの`isolated write failure`/500等は既存rollback負例の期待ログ。実環境の成功/障害と混同しない。

最終証拠:

- `D:/tmp/codex-google-queued-connection-20261006-final-formatted-pg-coverage.json`。SHA-256: `e77f95a819a5c22261459e9b5baeedef8eef499c4f3213a50b31024a097b6b70`。
- `D:/tmp/codex-google-queued-connection-20261006-final-formatted-sqlite-coverage.json`。SHA-256: `3bd869619240b16558669aff0f12c42682f035cf58c6a3e84da587632436e12d`。
- 専用PG container `7017700b44f8`・`2b8ca8349a08`のID/name/label/loopback portを確認し、それぞれDjango試験DB0の後に停止・自動削除。匿名volume `71760343ce8b`・`217b4f38fb97`と55437待受なし。記録は保持し、実ユーザーデータの変更/削除なし。

## 残条件・反映・復旧

- 保護対象はDBへ固定値を取得して保存した時点以降の、観測できる接続先変更。同じID/UID/接続日時への戻り、DBチェック直後の競合、開始済みHTTP取消、DB更新を伴わないGoogle側失効、遠隔tokenの所有者証明は未解消/未証明。HTTP中のロック/長いtransactionは追加しない。
- 署名鍵を実際に変更すると旧固定値は一致しなくなるため再作成が必要。今回の鍵変更は`override_settings`による隔離試験のみ。既存SECRET_KEY/Secrets/IAMは変更していない。
- 将来のデプロイでは旧workerを残したまま保護済みと扱わず、API/workerの版と既存待機ジョブを確認すること。旧workerは新しいpayloadを照合しない。常設worker/Redisの構築・費用・本番反映を今回承認したり実施したりしない。
- Calendar外部予定IDのGoogle接続先別管理、解除後の設定UI整理、実OAuth/書き込み・実AWS/全CIは別条件。現在の修正だけで正式公開条件を完了にしない。
- 10月6日13:13 JSTの読み取り再確認でmainは`8567f49f`、AWSは定義54・1稼働/0待機・rollout完了、DB/cache正常、favicon HTTP 200。親0c9のCIは13:05の確認時5成功/Playwright実行中。favicon反映の承認は今回へ拡張せず、main/AWS追加反映・共有DB/schema・Secrets・課金/容量・外部ユーザー通知の変更なし。
- 元worktreeのハンドアウト別作業13項目を保持する。復旧は今回コミットのrevert。作成済み固定値は不要になっても残してよく、Googleが受理済みの出力/予定はrevertで戻らない。revert後は待機ジョブの接続先照合がなくなる点に注意する。
- [正式公開の受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Go。HIGH3・実連携/課金/運用/性能/復旧等の未達を維持する。
