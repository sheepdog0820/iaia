# 正式公開準備候補 a1a50b63 の検証結果

## 対象と通常配布物

対象は `a1a50b63ec7c027e1ed7221754d4a2bdddf3f527`。Calendar/Sheetsの異常応答・再試行、個人事業者の請求開示表示、日程確定の性能、ハンドアウト更新・削除のGM権限、一括作成の入力形式、一覧の関連取得、管理テストの検証漏れ修正を含む。main・開発AWSへは未反映。

git archiveから標準Dockerfileでイメージ `tableno-release:a1a50b63` を作成し、ビルド成功。イメージIDは `sha256:4fe25f339e5e10b2a58adaf4fdce589c921ddba066247fca5934e4cc66c95fb7`。accounts/schedules/scenarios/tableno/templates/static配下のPython・HTML・JavaScript・CSS計506ファイルのSHA256がarchiveと一致した。

ソース差し替えなし、ネットワークなし、メモリSQLiteと隔離テスト設定だけを使用して、ハンドアウト関連55テストが成功（1.875秒）。最初の実行はテストモジュール名を誤指定して失敗したため、実在する `schedules.test_player_slots_handouts` に修正して再実行した。アプリ修正やイメージ再ビルドは行っていない。削除失敗の503ログは故障注入テストの期待結果である。テスト用コンテナは終了・削除済み。

対象: `schedules.test_handout_bulk_validation`、`schedules.test_handout_list_queries`、`schedules.test_handout_write_permissions`、`schedules.test_handout_permissions`、`schedules.test_handout_management`、`schedules.test_handouts`、`schedules.test_player_slots_handouts`、`schedules.test_handout_deletion_retry`。

ビルド・検証スクリプトとログはGit管理外の `tmp/build-release-a1a50b63.py`、`tmp/verify-release-a1a50b63.py`、`tmp/release-a1a50b63-build.log`、`tmp/runtime-handout-a1a50b63-final.log` に保持する。

## CI

2026-09-12、[push CI 34697870980](https://github.com/sheepdog0820/iaia/actions/runs/34697870980)と[PR CI 34697872667](https://github.com/sheepdog0820/iaia/actions/runs/34697872667)の全6ジョブ成功を確認した。PR検査はmainとの仮マージ `8cdaff72418272718fd659e576ad7814a7f2c243`、headは上記a1a50b63。実際のmainマージは行っていない。

- 単体・統合: 両方1,828成功、30スキップ、159警告。push846.08秒、PR669.55秒。スキップを成功件数へ含めない。
- PostgreSQL 18.3: 両ジョブ成功。PRログは293成功・48サブテスト成功・9警告、83.44秒。対象モジュールを選択した検査であり、全テストのPostgreSQL実行ではない。
- ブラウザ: 両方186成功。push8.3分、PR10.4分。最終集計にflakyの記載なし。
- lint-security、infrastructure、system: 両方成功。

## 残る判断と検証

正式公開はNo-Goを維持する。Stripe実テストはユーザー指定で保留、Google実同期の試験案と追加構成は承認待ち。開示メールの受信・返信、非公開実情報の開示体制、画像の実AWS性能、OS脆弱性の残リスク、常設worker・監視・DB/S3を含む復旧目標などは未完了。[受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)全体を、この候補のCI成功だけで合格とはしない。

ローカル通常イメージの検査は、AWSへの配備や実サービスとの接続を証明しない。旧稼働版f97c7809への切戻しは、今回修正したハンドアウトの不正更新・削除の不備を再導入するため、復旧時にも権限修正を維持する必要がある。今回の検証で共有DB・AWS・Secrets・費用の変更は行っていない。
