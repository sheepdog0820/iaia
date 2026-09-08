# 復元DB検証プログラムの準備

`scripts/ops/run_restore_preflight.py` を追加した。既存の `release_database_preflight` のSQL・トランザクション保護を再利用し、復元タスク専用の接続前チェックと最小Django設定で起動する。実AWSリソースの作成・接続・DB復元はしていない。

## 実行契約

新しい空のPythonプロセスで、リポジトリルートをimport可能にして実行する。新イメージなら `python -m scripts.ops.run_restore_preflight`、既存ECRイメージを使う案では監査済みファイル本文を `python -c` に渡す。後者では、使用イメージ内の既存検査コマンドが検証したソースと同じであることを先に照合する。外側のタスクentryPointに120秒のtimeoutを設定する必要がある。

必須設定はDB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD、RESTORE_EXPECTED_HOST/RESTORE_SOURCE_HOST/RESTORE_EXPECTED_DB_NAME。expected hostは復元APIの応答、source hostは元DBのdescribe応答から固定する。これらの値の一致だけでAWSリソース所有権を証明したとは扱わず、実行側で専用ID・タグを照合する。

- 接続前にホストの完全一致、元DBとの不一致、専用のtableno-restore-drill接頭辞と東京RDSドメイン、DB名の一致、ポート5432、必須設定を検査。不一致は接続せず終了1。
- PostgreSQL接続はconnect_timeout=5秒、sslmode=requireを強制。環境のDB_SSL_MODE等では弱めない。requireは暗号化を必須にするが、CA・ホスト名検証のverify-fullを実証するものではない。
- プロジェクトsettings・INSTALLED_APPS・起動時移行・外部クライアントを読み込まない。既存SECRET_KEYやOAuth・Stripe・メール等のSecretsは不要。task roleを付けない制限は別途のタスク定義で行う。
- PostgreSQL 18系と接続DB名を確認後、既存検査を実行。read-only確認・移行履歴・レジストリ列・ロール制約・複数/重複ロール件数を出力。元の検査のstatement_timeout=5秒、lock_timeout=1秒を使用する。
- 検査完了後にだけJSONを出力し、DB接続を閉じる。例外全文・SQL・接続情報・パスワードは出さず、失敗時は固定日本語メッセージと終了1にする。

## 検証結果

回帰テストは追加前のimport失敗を確認してから実装した。単体8テストが成功。接続先・元DB・DB名・ポート・必須値の拒否、最小設定、エンジン不一致、read-only不成立、例外時の接続終了・出力抑制、プロセス入口を検査。新コード46実行行・12分岐は100%実行した。Black/isort/Flake8、差分・文字コードと自己レビューに問題なし。

実接続は外向き通信・公開ポートなしの専用internal Dockerネットワーク、PostgreSQL 18.3のtmpfs、1日有効の合成自己署名証明書で実施。RDS形式のホスト名はこのネットワーク内のテスト用aliasであり、実RDSのDNSではない。候補46530ebcイメージ内で、未変更のランチャー本文を標準入力から実行した。

1. 最小の合成スキーマとロール2件を作成。TLS接続でread_only=true・server_major=18・複数ロール参加者1件を確認。意図的に無効なDJANGO_SETTINGS_MODULEを渡しても、プロジェクト設定を読み込まず成功。
2. 既存検査のSELECT位置へCREATE TABLEを試験用に差し込むと終了1。テーブルは作成されず、元のロール2件は維持された。stdoutは空でSQL・パスワードはstderrにない。
3. 誤った合成パスワードで終了1。stdoutは空、パスワード・ホスト名はstderrにない。
4. 所有タグを照合して専用DBコンテナ・ネットワークを削除し、残存なしを確認。

初回の単体テスト用mockは未設定のDjango LazySettingsを評価して失敗した。明示的なmockへ変更し、共有モジュールの接続オブジェクトを汚染しないよう元Commandを先にimportした上で再検証した。アプリDBや認証の変更ではない。

証跡はGit管理外のtmp/test-restore-launcher.py、tmp/restore-launcher-results、tmp/restore-launcher.coverage。合成TLS検証は実RDS証明書・Secrets注入・ECR起動・IAMの実証ではない。次に既存イメージdigestと検査ソースを照合し、最小タスク定義・SG/復元/削除の操作案を仕上げる。[実行構成案](RDS_RESTORE_EXECUTION_DRAFT_2026-09-08.md)の承認待ちの境界は維持する。
