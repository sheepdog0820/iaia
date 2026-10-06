# Google資格情報の削除・差し替え後の追加送信停止（2026-10-06）

## 対象と修正

- 親コミット: `e75c35f5414e60ddb1e44989d92d9690d8210563`。ブランチ: `codex/google-credential-guard-20261006`。
- 連携行ID/接続日時のガードだけでは、SocialAccount/Tokenの直接変更・削除やallauth解除後も取得済みtokenで送信できた。連携行が有効のまま残る場合を対象とする。
- token取得/refresh前に、同じ選択規則（当該利用者のGoogle token、最新ID）でtoken ID/account ID/app ID/UIDを取得する。各Calendar HTTP直前とSheets各チャンク直前に、現在の最新tokenと照合する。返されたaccess tokenと現在DB値も比較し、途中の回転・別行/別アカウントへの切り替えを見逃さない。
- token値の比較はPythonで行い、新しい確認SQLのWHEREにaccess/refresh tokenを入れない。識別情報/資格情報をジョブやログへ新規保存しない。初期snapshotにはaccess/refresh tokenを含めない。
- 観測した変更・削除は既存の固定日本語エラー/`connection-changed`で終了し、追加HTTP/自動retryをしない。Sheetsは部分進捗/部分出力の説明を維持する。通常refreshは返された新access値が同じ行に保存された場合に継続できる。
- 認可喪失の既存エラー、日時なしCalendar、欠落tokenの既存ValueError、最後のHTTP受理後の成功を維持する。HTTP中のDBロック・migration・外部送信を追加しない。
- mock tokenだけで成功していた既存5試験moduleのfixtureに、対応する所有者のSocialAccount/Tokenを追加した。安全チェックをmockで迂回する修正ではない。

## TDD・検証

- 新規クラスは前回の送信境界matrixを継承し、11種類の資格情報変更に置換する。token削除、account削除、UID/provider/所有者/app変更、token再作成、account差し替え、同じaccess値を持つ最新token追加、access回転、実allauth解除が対象。
- 初回7テストは99 failure。解除済みfixtureを再解除する想定外の追加HTTPでも302を要求した1ケースを訂正した。修正前の10テストでは計101の失敗を確認し、実装後は前回7件を含む17件が成功（2.919秒）。
- 新規10テストには149 subtest（停止99、最後の受理後成功44、通常refresh2、設定保存2、初期tokenなし2）と、解除fixture・SQL秘匿の独立試験を含む。
- 解除はDjango Clientで実`socialaccount_connections`のPOST/form/削除/signalを通し、302とaccount/tokenの削除を確認する。他のログイン方法を用意し、解除通知メールだけmock、メールbackendもメモリ内に限定する。実ブラウザー/Google接続/外部メールではない。
- SQLiteの最終関連106件: 100成功/PG専用6省略（29.920秒）。PostgreSQL 18.3隔離DBの同じ106件: 全成功/省略0（42.984秒）。先行SQLite105件も100成功/5省略だが最終証拠と区別する。
- 本体差分15実行文/6分岐、新規テスト78文/28分岐100%。`google_tokens.py`全体45文/14分岐100%。worker全体は70%であり、全経路・実Googleの100%網羅とは扱わない。
- 対象8 PythonのBlack/isort/Flake8/Banditと空白検査が成功。合成fixtureに限定したB105/B106例外は実資格情報ではなく、productionコードを対象外にしない。B105例外の親ASTに対するBanditの「no failed test」警告は残るが指摘項目は0。
- YAML検査の初回はstep配列の固定位置指定でIndexError。runを持つstep全体の探索へ検査コマンドを訂正し、parse/PG対象追加を確認した。変更11ファイルのUTF-8/LF・空白検査、文書テスト39件成功。日本語の固定エラーを完全一致確認し、資格情報や外部応答を表示しない。
- callbackの`isolated write failure`/500は既存rollback試験の意図したログ。Bad Request、期限切れICS、brokerなし等も負例の期待結果であり、試験失敗ではない。
- 新規moduleを既存PG CIに追加する。workflowはDjango CIのみで、通常のcodex pushにAWSデプロイは含まれない。今回の全CI結果はpush後に別途確認する。

最終証拠:

- `D:/tmp/codex-google-credential-guard-20261006-final-pg-coverage.json`。SHA-256: `82af21b9f059ce9f2a0ff4907a0c98ebf71a1bd7104831feb8429bc1035ad706`。
- `D:/tmp/codex-google-credential-guard-20261006-final-sqlite-coverage.json`。SHA-256: `76d275f668774da925684a09c756335deb58d6d6b8947b0391bcd9068858fb30`。
- 専用PG container `377154a1d457`のID/name/label/loopback portを確認し、Django試験DB0の後に停止・自動削除。匿名volume `6101f95468d0`と55437待受が残っていない。試験記録は保持する。実ユーザーデータの変更・削除なし。

## 残条件・反映境界・復旧

- provider HTTPはmock。送信直前のDB照合後の競合・開始済みHTTPの原子的取消・同じID/UID/tokenへ戻る履歴は防げない。外部での失効はDB更新なしでは判定できず、実Googleのtoken有効性・実AWS・全CIを証明しない。
- worker開始前の接続変更をキューへ固定する設計、Calendar外部予定IDの接続先別管理、過去アカウントの予定移行/削除は別条件。解除後の連携UI/設定フラグの整理も今回行わない（試験では有効フラグが残ったまま停止することを確認）。
- 既存refresh保存時の比較SQLには従来のtoken比較が残る。今回の秘匿試験は通常の未期限token送信と新しいガードのSQLを対象とし、全SQL/logの資格情報秘匿を証明しない。
- mainは確認時`8567f49f`。親e75のCIは4項目成功/Unit・Playwright実行中。faviconのmain/開発AWS承認は実施済みであり、今回の修正へ拡張しない。今回main/AWS追加反映・共有DB/schema・Secrets/IAM・課金/容量変更・外部ユーザー通知なし。
- 元worktreeのハンドアウト別作業13項目を保持する。自己レビューで追加の要修正事項なし。
- 復旧は今回のコミットをrevertする。Googleが受理済みの予定/出力はrevertで戻らない。
- [正式公開の受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Go。HIGH3・実連携/課金/運用/性能/復旧の未達を維持する。
