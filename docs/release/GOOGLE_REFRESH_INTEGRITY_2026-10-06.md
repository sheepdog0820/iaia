# Googleトークン更新と再接続・解除・並列更新の整合性（2026-10-06）

## 対象と変更

- 親コミット: `e499ce3c61f4f75d67e7332875b6703a467a3090`。ブランチ: `codex/google-refresh-integrity-20261006`。
- `schedules/google_tokens.py` の更新結果保存を、無条件のモデル保存から取得時の情報に一致する場合だけの条件付きUPDATEへ変更する。
- トークン行ID・account/app ID・元のaccess/refresh token・元の有効期限を比較し、Googleアカウントの利用者/provider/UIDも確認する。更新後に新しい接続情報を古い結果で上書きしない。保存対象が消えた場合も、行を再作成しない。
- 不一致は日本語の固定ValueErrorとして終了する。既存Calendar/Sheets workerはそれを捕捉し、ジョブを失敗として完了し、外部送信・自動再試行をしない。エラーにトークン・UID・外部応答を入れない。
- 通常の更新、有効期限のUTC正規化、refresh token/expiryが返らない場合の保持、期限内トークンの利用、既存の更新エラー保護は維持する。Google接続先・scope・ユーザー権限の定義は変更しない。
- 既存Google grant保存処理を変更せず、HTTP中にDBロックやトランザクションを保持しない。新規2テストモジュールを既存PostgreSQL CIジョブに追加する。

## TDDと再レビュー

1. RED: 初回SQLiteの6テストで5 failure/3 error。削除によるDatabaseErrorがTestCaseの外側トランザクションを壊して後続subtestに影響したため、workerごとの試験をsavepointで分離した。
2. 修正前の隔離PostgreSQLで8テストを実行し、7 failure/5 errorを確認（0.860秒）。同一行再接続・secret/期限/identity変更の上書き、別アカウント接続/解除後の保存エラー、同時更新の2成功を再現。両workerの削除ケースが独立して実行されたことも確認した。
3. 初案は関連68件に成功したが、それだけを完了証拠にしなかった。2つのUPDATEが同じ行のロック待ちになる条件を追加し、初案でも2成功が残ることを確認（3テスト中1 failure）。
4. 実際のDjango 5.2.15の更新SQL生成処理を確認。関連テーブルのjoin条件があると比較条件までID選択サブクエリへ移るため、アカウント照合だけを独立したサブクエリにし、トークン比較条件をUPDATE対象のWHEREに残す形へ修正した。
5. 最終版は、`pg_stat_activity`で2つのUPDATEの実Lock待機を確認してから行ロックを解放し、1成功/1安全な競合エラーを確認する。新しい接続または解除を別DB接続で先に確定させたケースも成功。待機観測の短い期限切れ負例も検証し、無期限に待たない。

## 最終検証結果

- Python 3.11.1/Django 5.2.15/隔離PostgreSQL 18.3: 新規9件とGoogle grant/OAuth callback/API/Calendar/Sheetsの計69テスト成功（19.752秒、省略0）。
- SQLiteの使い捨てメモリ内DB: 同じ69件中65成功・PostgreSQL専用4件省略（14.228秒）。省略を並列整合性の成功として扱わない。
- 最終coverage: `google_tokens.py` 全36文/12分岐、整合性テスト117文/10分岐、並列テスト98文/10分岐が100%。worker全体や外部Googleでの網羅性ではない。
- 対象3 PythonのBlack/isort/Flake8/Bandit・空白検査成功。Banditの初回LOW3は合成トークン引数であり、理由を付けて該当B106だけを除外した。最終検査の指摘は0で、親のfixture構築呼び出しにも除外コメントが適用される旨のwarning1は残る。
- 日本語の競合エラーを完全一致確認。自己レビューで、単純な成功試験では見逃すSQL競合を追加で修正し、最終差分の追加修正事項なし。
- OAuth callback回帰で出る`isolated write failure`の500ログは、既存の書き込み失敗・rollbackテストによる期待したログであり、最終テスト失敗ではない。

最終証拠: `D:/tmp/codex-google-refresh-integrity-20261006-final-coverage.json`。
SHA-256: `bdb776a1e19b1b1d063ca1220499063915421a94e154bdb0e48c6f4e0d262151`。
初案のcoverageファイルは最終版の証拠として扱わない。最終coverage取得後の変更は同じ行上の試験コメント表記だけで、実行コード/行番号/分岐は変更していない。

## 反映境界・残条件・復旧

- 実Google更新HTTPはmock。ローカルの合成ユーザーと使い捨てDBだけを使用した。対象をID/labelで確認して試験コンテナを停止・削除し、試験DBは残していない。記録は保持する。
- 今回は取得時のフィールド比較によるDB整合性を検証した。Google側の並列更新/refresh token回転の実際の有効性、完全に同じ値へ戻る変更履歴の検出、取得後・保存後の連携変更や実HTTP送信の原子的な取消は保証しない。
- 同時更新で負けたジョブは失敗として表示し、利用者が再試行する。別の接続情報に自動で切り替えて送信しない。
- main/AWS追加反映・共有DB/schema・Secrets/IAM・課金/容量・外部ユーザー通知の変更なし。既存favicon反映承認を拡張しない。今回の全CIはpush後に確認する。
- 復旧は専用修正コミットのrevert。Google側の認可/発行結果はrevertでは戻らないため、実認可を扱う時は接続状態の確認が必要。
- [正式公開の受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Go。HIGH3・実OAuth/連携・課金/運用/性能/復旧等の残条件は解消していない。
