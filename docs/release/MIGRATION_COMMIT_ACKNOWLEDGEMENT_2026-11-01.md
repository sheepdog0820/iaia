# 5移行のCOMMIT応答を失う場合の検証（2026-11-01）

共有0065〜0069の適用結果が不明になったとき、失敗メッセージだけをrollback確定の証拠にできないことを、合成データのTLS PostgreSQL18で検証した。製品コード・DB移行ファイルの変更はなく、既存commandの回帰テスト2件と結果の記録を追加する。

## 確認した2ケース

| 注入した障害 | 利用者側の結果 | 実DBの結果 |
| --- | --- | --- |
| 本物のCOMMITが成功した直後に、応答を失ったことを模したDatabaseErrorを発生 | 「確認前に再実行しない」旨の固定CommandError、成功JSONなし、例外中の私有情報は非表示 | 別のTLS/READ ONLY接続で5移行の履歴を確認。owner補完・技能合算は適用済みで、既存の利用者/課金・旧履歴は保持。計画は空で、再実行は拒否 |
| DBのCOMMITを呼ぶ前にDatabaseErrorを発生 | 同じ固定CommandError、成功JSONなし、例外中の私有情報は非表示 | 旧schema・グループ/所属・利用者/課金・技能・履歴に変更なし |

`connection.commit`の境界に障害を注入するテストであり、実ネットワーク断や実AWSのCOMMIT応答喪失を起こしたものではない。前者は本物のCOMMITを実行してから例外を発生させているため、SQL・MigrationExecutorを成功したように見せるだけのmockではない。後者はCOMMIT前の失敗を対照として使う。

## 実行範囲と品質確認

通常image `sha256:ddb493e310c75d7b93b1f9312b87e00d99d1801e12b1784c13ba640fbda9fb8f`（revision `dac04381`、main72ad8299と同tree）の製品コードを使用した。変更したテストファイルとローカル設定だけをreadonly mountし、製品ソースは上書きしていない。これは新しい配布物をビルドして試験したという記録ではない。

関連[テストモジュール](../../tests/integration/test_verified_release_migrations.py)は **25テスト成功・省略0**。PG接続ロールはNOSUPERUSER/NOCREATEROLEで、使い捨てtest DB作成のためCREATEDBを持つ。internal network、公開ポートなし、PGデータはtmpfs、実データ/外部サービスから隔離した。実行応答の同じIDのcontainer/networkを削除し、不在を確認した。合成envと一時TLS秘密鍵も削除した。

Black/isort/Flake8、差分と文字コード・日本語文書を確認した。新しい画面や利用者向け機能はない。基準の受け入れ条件や、既存のコピー内5移行の承認待ち対象は変更しない。

## 運用上の残作業

この結果は、実DBで結果不明が発生した場合の状態を確定するものではない。実行前に全writer停止・自動再開停止・直前backup・固定接続先を照合し、応答不明では同じtask IDを監視して履歴・schema・内容を読み取り比較する。例外・exit code・成功JSONの欠落だけで未適用と判断しない。再適用、旧Web再開、Schedulerの一括復旧は確認前に行わない。

比較用の事前記録、実backupからの比較/復元、DB/コード/staticの一体切替、適用後の前進修正または接続切替、監視期限と費用を含む実行案の完成が必要である。今回の共有DB/AWS/IAM/Secrets/Stripe/外部通知への操作は0。正式公開No-Goと元の全25条件を維持する。
