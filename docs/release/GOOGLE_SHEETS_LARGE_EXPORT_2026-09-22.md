# Google Sheets大規模出力の進捗・失敗表示（2026-09-22）

## 結論

Google Sheets出力を100行単位に分割し、各送信成功後にジョブ進捗を更新するようにした。途中の通信失敗では、それまでの進捗を保持し、「途中まで出力されている可能性」があることと再試行方法を日本語で表示する。外部APIの例外本文、スプレッドシートID、外部応答本文は失敗理由へ保存しない。

実装コミットは`235aab4a`（`fix: track large Google Sheets exports`）。

正式公開判定は引き続きNo-Goである。この検証はローカルSQLiteとGoogle APIのmockによるもので、実Google資格情報、実シート、Celery worker、AWS環境は使用していない。

## 実装内容

- 出力行を100行ずつ送信し、A1形式の開始行をチャンクごとに進める。
- 205行の例では、`'Large Export'!B7`、`'Large Export'!B107`、`'Large Export'!B207`へ100行、100行、5行を送信する。
- 各チャンク成功後に進捗を10〜90%の範囲で更新し、全件成功時に100%へ確定する。
- 途中失敗では成功済みチャンクの進捗を保持し、部分反映の可能性を明示する。再試行は同じ値で先頭から上書きするため、成功済み範囲を重複追加しない。
- API受付時と旧ジョブ実行時の両方で、出力範囲をA1開始セルとして検証する。不正な範囲はGoogle APIへ送信しない。
- `updatedCells`が不正な型の場合も外部応答値を露出せず、安全な固定文言で失敗させる。
- 連携未設定エラーと画面ラベルを日本語化した。

Google公式の[`spreadsheets.values.update`](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/update)および[Sheets API v4移行資料](https://developers.google.com/workspace/sheets/api/guides/migration)を確認した。A1表記の開始セルだけを指定した場合、送信値の行列サイズから更新対象が決まる仕様を利用している。

## ローカル検証

対象コマンドはローカルのPython 3.11仮想環境、Django 5.2.15、SQLiteテストDBで実行した。

- TDDのRED: 大規模出力2件、範囲検証1件、日本語エラー1件が既存実装で期待どおり失敗した。
- GREEN: `schedules.test_google_sheets_delivery` と `schedules.test_external_integrations.GoogleIntegrationTestCase` の26件が成功した。
- 205行を3リクエストへ分割し、送信直前の進捗が10%、49%、88%になることを確認した。
- 201行の2リクエスト目をTimeoutにし、進捗49%と安全な部分反映警告が残ることを確認した。
- 不正A1範囲、旧ジョブの不正範囲、不正`updatedCells`、空出力、単発通信失敗、JSON不正応答を確認した。
- Black、isort、flake8、`git diff --check`が成功した。
- 変更したGoogle Sheets分割処理・入力防御の全分岐を対象テストで実行した。共有モジュール全体の行カバレッジ値は、無関係なCalendar/Discord等を同時に含むため、この限定実行の合否判定には使用していない。

## 未検証・承認境界

- 実Googleシートへの限定データ出力、実トークン失効、実workerによる再試行は未検証。
- 候補コミットのGitHub Actions、通常Dockerイメージ、隔離PostgreSQL 18/Redis検証は未実施。
- mainマージ、共有DB変更、AWS反映、Secrets・OAuth権限変更、継続費用を伴う操作は行っていない。
- I05完了には、承認済みの専用シートと限定キャラクターを使った実出力・権限・失効・再試行確認が必要である。
