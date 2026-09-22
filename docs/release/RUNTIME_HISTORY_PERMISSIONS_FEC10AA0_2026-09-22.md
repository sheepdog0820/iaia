# 非公開関連情報保護を含む配布候補

- コミット: `fec10aa06d0337e4fb773cc98c7a2e8abd4c0d09`、構築時差分なし。
- イメージ: `tableno:history-permissions-fec10aa0`
- ID: `sha256:1658cb0b53a2a32e14464561d9d91f9676197e55ece84151bc75a229ff0c553b`
- 通常Dockerfileを使用（依存層はキャッシュ利用）。`scenarios/serializers.py` のホスト/配布物SHA-256は `ffd2e78bc6ee0e4dad7e69720d313d0cbf0b8d8beb87efeaa96c851a6f28d7a2` で一致。

## 検証

- 外部通信禁止の一時コンテナで履歴権限・探索者履歴・履歴キャッシュの関連19テストがSQLiteで成功（1.291秒）。
- Docker内部ネットワーク（Internal=true、公開ポートなし）、tmpfs PostgreSQL18.3、Redis7-alpineで同じイメージを検証。
- aws-pre設定・通常entrypointで全マイグレーション、静的227ファイル収集/617後処理、Daphne起動が成功。
- 同じ配布物からローカルテスト設定と隔離PGで19テスト成功（1.377秒）。テストDBは終了時に削除。
- aws-pre設定のmigrate --check、check --deployが終了0。実HTTP readinessは200、database/cacheともにok。
- 名前・イメージ・公開ポートなしを確認後に専用3コンテナと内部ネットワークを削除、不在を確認した。tmpfs試験データは破棄、イメージは保持。

実AWS・RDS/S3・外部認証/決済・メールは未使用。新候補のCIは別途必要。先行d9a61f4cのCI全6ジョブ成功をこの修正へ拡張しない。OS指摘と正式公開No-Goは維持し、反映案は新候補への更新が必要。

## OS監査の再実行失敗

Docker Scout 1.24.0で新イメージのdeb監査を試みたが、イメージ保存後のindexingで「failed to initialize cache: cache may be in use by another process: timeout」となり終了1。新候補のOS監査成功/指摘件数を得たものではない。終了後にdocker-scoutの実行中プロセスは見つからなかったが、共有キャッシュは削除していない。キャッシュ障害の安全な解消または独立した監査で再実行が必要。直近で完了した44a18301の監査36指摘を未解消として保持する。
