# Google Sheets出力先のURL境界と入力検証（2026-10-06）

## 対象と原因

- 親コミット: `3e154ff74ada9be5333f3f0abeea2693f619076c`。ブランチ: `codex/sheets-destination-20261006`。
- workerがspreadsheet IDとA1範囲をURLに直接埋め込んでいた。実際の`requests.Request.prepare()`で、`'調査#2'!B7`の`#`以降がfragmentへ移り、HTTPの出力先パスに含まれなくなることを再現した。
- APIのIDは未検証で、数値・真偽値・コンテナ型や`.`/`..`も受理していた。ID空欄のプレビューと、不正入力の区別も必要だった。
- Google公式の[values.update](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/update)はID/rangeをpath parameter、valueInputOptionをquery parameterとして定義する。[A1記法](https://developers.google.com/workspace/sheets/api/guides/concepts)では特別な文字を含む名前に引用符が必要。今回引用符の自動補正やGoogle側のID許可文字の推測はしない。

## 変更と受け入れ条件

- IDとA1開始範囲をそれぞれ`quote(..., safe="")`でエンコードし、固定のSheets APIホストへ送る。`%`もエンコードし、1回のdecodeで元の値に戻ることを確認する。queryは従来どおり`valueInputOption=RAW`だけとする。
- APIは文字列IDを検証し、前後の空白を除く。型違い・`.`/`..`・内部のASCII制御文字/DEL・UTF-8にできないsurrogateは日本語の固定エラーで拒否し、ジョブ/queueを作らない。数値や真偽値をIDに変換しない。
- ID未指定/null/空文字は従来のプレビューを維持し、空白のみもプレビューとする。プレビューは外部送信しない。
- workerでも旧ジョブのIDとrangeを検証し、不正な場合はtoken refresh/PUT/retryより前に失敗として完了する。IDエラーは`invalid-spreadsheet`、rangeは既存の`invalid-range`。開始時の認可確認は引き続き最初に行う。
- APIのrange用CharFieldは既存の型/255文字上限を維持し、surrogateの自動英語エラーだけを既存の日本語rangeエラーへ置き換える。workerの共通range正規化にもUTF-8検査を行う。
- 17列・A1開始セル正規化・100行分割・進捗・RAWデータ・選択した所有キャラクター・再試行対象のsnapshot・失効確認は変更しない。既存分割試験はエンコード済みパスをdecodeして、B7/B107/B207の意味を引き続き確認する。

## TDD・検証

- 初回の起動はDB_ENGINEの値を誤り、テスト開始前に終了した。設定を`sqlite`へ訂正して使い捨てメモリ内DBで実行した。試験側のA1行番号の例とsurrogate JSON生成も訂正し、これらをアプリの不具合として扱わない。
- 修正前の最終7テストは34 failure/0 error。実リクエスト生成によるfragment/query/pathの分断、API入力・旧worker入力の受理、先にtoken refreshが動くことを再現した。
- 実装後の初回17件で、日本語surrogateエラーの不一致1件を検出。DRFの自動validatorより前に固定日本語で検証し直した。
- 新規7件には日本語/引用符/百分率/疑似query/スラッシュを含む6組×2チャンク、APIの不正ID11例、プレビュー4例、旧workerの不正ID13例、rangeのUTF-8異常を含む。疑似query/スラッシュ等は送信境界の負例であり、Googleが全てを有効なID/シート名として受け入れるという証拠ではない。
- 初回の関連80件は76成功・PostgreSQL専用4件省略（16.168秒）。再試行APIを加えた最終94件は90成功・同4件省略（29.602秒）。今回はURL/API検証の変更であり、PG専用の並列整合性試験をSQLite成功に含めない。
- 差分の本体48実行文/6分岐、新規テスト116文/10分岐は100%。worker全体は59文/16分岐のうち既存の1分岐が未実行であり、全体100%とは扱わない。
- 対象5 PythonのBlack/isort/Flake8/Bandit、空白検査成功。日本語ID/rangeエラーの完全一致、秘密値・外部応答をエラーに入れないことを確認。自己レビューで追加修正事項なし。

最終coverage: `D:/tmp/codex-sheets-destination-20261006-final-coverage.json`。
SHA-256: `851438c6293b72b40a900d102390df1987c9e22e13b0b5377df52eb931e43e8b`。
先行80件のcoverageは最終94件の証拠に置き換え、先行記録も保持する。
OAuth callbackの`isolated write failure`の500ログは既存のrollback負例であり、最終テストの失敗ではない。

## 反映境界・残条件・復旧

- Google通信/queue/token取得はmock、リクエスト生成だけは実Requestsを利用した。実Googleのデコード・受理・書き込み・OAuth、今回のPostgreSQL/ブラウザー/AWS/全CIを証明しない。
- 旧ジョブの手動再試行APIは変更しない。既存payloadの不正IDはqueueされ得るが、workerが送信前に失敗として完了する。Googleに存在するID、書き込み権限、sheet名の実在・記法は実連携で確認する。
- main/AWS追加反映、共有DB/schema、Secrets/IAM、課金/容量、外部ユーザー通知の変更なし。favicon承認を今回の修正へ拡張しない。元worktreeのハンドアウト変更13項目は保持する。
- 親3e154ff7のCIは5項目成功・Playwright実行中と確認。今回の全CIはpush後に確認し、親の成功を今回の結果としない。
- 復旧は今回の専用コミットのrevert。既にGoogleへ出力されたセルの復旧はrevertでは行われないため、実書き込みを伴う反映時は対象のバックアップが別途必要。
- [正式公開の受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Go。HIGH3・実連携/課金/運用/性能/復旧等の残条件は解消していない。
