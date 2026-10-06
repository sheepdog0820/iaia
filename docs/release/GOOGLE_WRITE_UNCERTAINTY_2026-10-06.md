# Google書き込みの応答喪失と結果不明（2026-10-06）

## 対象・判断

作業基点は `315f43bf92fd8375fcd79774436eca2855932599`、専用ブランチは `codex/google-write-uncertainty-20261006`。先行の[実worker・通常配布物検証](GOOGLE_RUNTIME_OUTCOME_2026-10-06.md)では障害・遅い応答を検証した。今回のREDで、実行期限内の書き込み応答喪失を既存workerが通常失敗から自動再送することを再現した。この修正は、その曖昧な書き込みを結果不明として保存し、自動再送・同一job再配送・通常の再試行APIによる再適用を止める。

正式公開は **No-Goを維持**。durable outbox、同期対象をまたぐ世代fence、結果照合・限定回復、実Google/AWS検証、運用・性能・復旧等の完了ではない。今回のschema変更はないが、先行migration `schedules/0056` を含む未反映のschemaを前提とする。共有DBへの適用・mainマージ・AWS反映の承認は拡張しない。

## 動作と利用者への影響

| 状況 | jobの扱い | 再送・状態保持 |
|---|---|---|
| Calendar POST/PUT/DELETE、Sheets PUTでRequests例外、HTTP 408または500以上 | `uncertain` | 自動retryなし。固定日本語案内・終了時刻を保存し、payload・進捗・実行UUID・期限を保持 |
| 書き込みの成功応答が不正なJSON/型、Calendar予定ID不一致、Sheetsセル数が不正 | `uncertain` | 適用済みの可能性を残す。通常失敗として再試行可能にしない |
| Sheetsの先行chunkが成功済みで、後続chunkのHTTP拒否 | `uncertain` | 先行セルを再送で書き戻さない。部分進捗を保持 |
| Calendarの書き込み前GET失敗、最初の書き込みに対する通常の4xx拒否（408以外） | 従来の失敗処理 | 従来の再試行を維持。Calendar 409照合、412競合停止、取消404/410等の既存処理も維持 |

`uncertain_google_job` は既存の所有者・job種別・RUNNING状態・実行UUID・期限・保存期限を条件とする更新を使う。旧実行、削除済みjob、状態変更後の遅い応答では更新しない。Calendarの曖昧な応答では同期行を成功/失敗へ推測更新せず、削除された同期行も再作成しない。provider例外・応答本文・接続先・認証情報は新しい案内や例外へ入れない。既存の日本語結果不明表示・再試行400を利用し、UI/CSS/保存期間を変更しない。

[Google Calendarのエラーガイド](https://developers.google.com/workspace/calendar/api/guides/errors)は一般的な500等のbackoffを説明しており、「結果が不明なら未適用」という保証ではない。[Sheetsのエラーガイド](https://developers.google.com/workspace/sheets/api/troubleshoot-api-errors)も503・timeoutを扱う。このアプリでは、外部編集・先行chunk・応答喪失を考慮し、照合なしの曖昧な書き込み再適用を成功回復として扱わない。これはTableno側の判断であり、Googleがすべての500で適用済みと保証するという主張ではない。

## 検証の範囲

- 新規6テストメソッド。Calendar作成/更新/取消/409後PUT・Sheetsの5経路×4障害、2種の書き込み×5不正ACK、読み取り失敗、部分出力後403、最初の403、実loopbackの適用後切断を検証する。未知の結果に対する再試行400・job数不変・再配送時の追加HTTPなし、同期行保持も確認する。
- 実loopbackのCalendar/Sheets各1ケースは、Requestsが実HTTPを送り、合成providerが本文を読み取って適用を記録した後、socketを閉じる。合成token取得とCelery retry観測はmock、task本体は同一プロセスの `.run`。実Redis/Celery別worker・ASGI HTTP・実Google OAuthではない。
- 最初のREDは3メソッドの10失敗/20エラー。既存の自動retryと通常失敗を再現し、実装前の `red.log` を保持した。
- 初回の全Google回帰は両DBとも5失敗/6エラー。不正な更新ACKに対する旧期待値を結果不明へ変更し、ステータス未指定のMockをHTTP 200に修正した。結果不明を通常失敗へ戻すために製品条件を緩めていない。
- 後続SQLite回帰で既存正常loopbackの1ケースが結果不明となる失敗があり、`regression-sqlite-final.log` を保持した。HTTPフィクスチャはPOST/PUT本文を読まずに返信していたため、返信前に本文を消費するよう修正した。未読本文と切断が失敗原因だったことを例外ログで断定してはいない。意図的な適用後切断は独立fixtureで残して再検証する。
- 最終回帰はGoogle関連25モジュール＋文書39テストの計253。PostgreSQLは **253成功/省略0、119.578秒**、SQLiteは **245成功/PG専用8省略、76.787秒**。両方終了0、テストDBは削除済み。アプリ全機能の全テストや実Googleの証明ではない。
- 実際の製品差分は両DBで **30文・8分岐経路100%、除外0**。内訳はlifecycle追加3文、write outcome新規10文/2経路、tasks追加17文/6経路。coverage JSONとGitの実差分行を突き合わせた。tasks全体・全アプリの100%とは区別する。
- CIのPostgreSQL明示対象にも新規テストを追加する。差分対象9 PythonファイルのBlack/isort/flake8/Bandit・差分空白チェックは終了0。Banditは既存の合成token用nosecに警告1件、検出された問題0。UTF-8/LF/BOM/文字化けと日本語案内を確認し、source自己レビューに今回の追加修正を要する指摘は残さない。

隔離PGは18.3の固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、512 MiB/2 CPU、RO root/tmpfs、volume/bind mountなし、127.0.0.1:55444のみ公開。ホストPythonは3.11.1。20:01:25 JSTにfull ID/name/label/image/mount/portを照合し、public表0・test DB0、停止終了0/OOM falseを確認して専用containerとtmpfsを撤去した。task labelのcontainer/volume残数は0。SQLを含む証拠・helperを保持し、元checkoutの別ハンドアウト作業13項目は保持した。

## 未完了・反映境界

- 新規API操作から別jobを作る経路や同じ同期行を使う別jobを完全にfenceするものではない。実行中のHTTPは取消不能で、別job・外部利用者の編集・再連携先の扱いは別途設計/検証が必要。
- 読み取り失敗や最初の通常4xxは既存retryを維持する。Celeryの全失敗/再配送を恒久的に禁止する修正ではない。HTTP 2xxが正常に検証されても外部の実データ一致・正確に1回の適用は保証しない。
- Sheetsの正常dictで省略された `updatedCells` を0と扱う既存仕様は変更しない。完全なremote照合、部分結果の永続照合履歴、cancel/reconcileは未実装。
- 保存期限は既存7日。結果不明を長期監査履歴として保存する仕様ではない。未送信intentのdurable outbox/producerのDB commit境界も未解消。
- 今回の通常イメージbuild/配布物照合/新規Scout/性能/背景透過/実ブラウザー試験は未実施。先行通常imageのHIGH 3件を解消済みとは扱わない。今回候補の全CI成功も未確認。
- mainは実施時点の読取で `8567f49f8d411bad7f732afaeebad85357eeca09`、今回AWSは読取も変更もしていない。DBは合成・隔離テストのみ。実ユーザー/共有DB/Secrets/IAM/課金/容量/外部通知の変更なし。
- 将来反映時はworkerを含む展開順序・待機/実行中job・全未適用migration（先行accounts 0065–0067等も含む）を確認した別の承認案が必要。今回のローカル復旧はこの修正を親へ戻す方法だが、新しく結果不明になったjobを機械的に再送してはならない。

## 証拠

実行証拠は `D:/tmp/codex-google-write-uncertainty-20261006/`。各実行のログを別名で保持し、初回失敗を上書きしない。`run_suite.ps1` はENV_FILE/AWS/Sentryを空にし、ローカル設定・合成SECRET・SQLite memoryまたは検証専用PostgreSQLに限定する。HTTPは既知の隔離loopback以外を禁止する。repo内に秘密情報・生成DB・画像・ログをコミットしない。

文書更新後の39テストも終了0（0.036秒）、staged 12 text filesの文字コードチェック・cached差分空白チェックは合格。root証拠34ファイルのSHA-256を `sha256-manifest.json` に保存した（manifest自身とcacheサブディレクトリは対象外）。

主要証拠のSHA-256（同ディレクトリ、全文hashは別途manifest）:

| ファイル | SHA-256 |
|---|---|
| `red.log` | `9eb0e5f147e161fc3b2ade60119670ec222281f0d54c9ed415e4d36b5f72ceb2` |
| `regression-sqlite-verified.log` | `412ecb4393d87c03b5ab79fdc3df0b36f62642fea29ed1fb1680cb8074f78fea` |
| `regression-pg-verified.log` | `9a3871eda799c7bc2f9b33c928bfd6d926cd5b6bb23e36ebfcbb3bf94b00a92c` |
| `coverage-diff.json` | `6b3fe184e35f2bddd6b3e58d8a47a61c5055805746461035854e48facc910c0a` |
| `cleanup.json` | `536c01944afbe2413b6c0df25e640aeab07cd4678817f470c0d66c839146ac80` |
