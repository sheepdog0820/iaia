# 直近の情報保護・報酬修正のPostgreSQL検証

2026-09-08、アプリ候補 `59f07079` をローカルの隔離PostgreSQL 16で検証した。共有AWSのDB、ストレージ、Secretsは使用していない。

## 実行条件

- PostgreSQLイメージID: `sha256:80f4c7a5e91618546dce5b4fe60cf03b14c0f9efa7e40157278d122772ced8d2`。
- ホストへのポート公開は127.0.0.1だけ。DBファイルはコンテナのtmpfsに配置し、検証専用の資格情報を使用。
- Windows Python 3.11.1、psycopg2 2.9.12、Djangoのlocal設定。実稼働イメージ・本番設定全体の再検証ではない。
- テスト専用DBはDjangoのテストランナーが作成・破棄。メディア保存先はTemporaryDirectoryで分離して終了時削除。
- 対象: `schedules.test_session_rewards`、`schedules.test_reward_concurrency`、`schedules.test_attachment_error_privacy`、`schedules.test_handout_attachments`、`schedules.test_handout_download_access`。

## 結果

36件成功、skipなし、14.523秒、終了0。SQLiteでは省略される報酬の同時反映を実行し、2要求が200、成長記録が1件だけとなることを確認した。参加キャラクター差し替え後の誤反映防止、添付内部エラーの秘匿、秘匿添付のダウンロード拒否も成功。

終了後に所有ラベルを照合して専用コンテナを削除し、同名コンテナが残っていないことを確認した。ローカル証跡はGit管理外の `tmp/release-pg-59f07079.py` と `tmp/release-pg-59f07079.log`。

今回の報酬API回帰ケースが継続的にPostgreSQLでも実行されるよう、既存のproduction-databaseジョブに `schedules/test_session_rewards.py` を追加した。新たな本番反映・共有DB操作・外部課金のジョブは追加していない。

## CIと残条件

後続のCI補完候補10d21e42は[全5ジョブ成功](https://github.com/sheepdog0820/iaia/actions/runs/34191048141)を確認した。production-databaseの完了ログに追加した `schedules/test_session_rewards.py` が含まれ、284成功・38サブテスト成功・9警告、80.60秒だった。これは下段の過去候補59f07079の途中状態とは別の確定結果である。

候補59f07079の[CI](https://github.com/sheepdog0820/iaia/actions/runs/34190819633)は確認時点でlint-securityとsystemが成功、Unit / Integration・production-database・playwrightは実行中。ローカル36件の成功でCI完了・正式公開可能とは判定しない。今回のCI対象追加後のジョブ成功も確認する。

共有環境へのアプリ反映・未適用マイグレーションの適用、実S3/CDNでの保護、Stripeを含む実外部連携検証は引き続き未完了。以前に誤更新された成長記録の復元を証明する検証ではない。
