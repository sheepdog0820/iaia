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

## OS監査の初回失敗と専用キャッシュでの完了

初回はDocker Scout 1.24.0のindexingが共有キャッシュのtimeoutで終了1となった。その後、[Docker公式の設定](https://docs.docker.com/scout/how-tos/configure-cli/)に従い、`DOCKER_SCOUT_CACHE_DIR` に新規専用ディレクトリを指定して同一イメージを再監査した。共有キャッシュは削除・変更していない。

- コマンド: `docker-scout cves local://tableno:history-permissions-fec10aa0 --only-package-type deb --format sarif --output <report> --exit-code`
- 268パッケージをindexing、脆弱な14パッケージに36指摘（HIGH 2 / MEDIUM 1 / LOW 33）。終了1であり、脆弱性ゲート合格ではない。
- レポート: `C:/tmp/runtime-os-fec10aa0-isolated-20260922.sarif.json`
- SHA-256: `3e3bfab1a1bc22471e12229fe84be14cf4217fc3189eaa1c44f0c17b014afad3`
- 一時イメージアーカイブが他プロセスに使用中という削除警告は残ったが、指摘抽出とSARIF生成は完了した。専用キャッシュは保持し、強制削除していない。

### HIGH指摘の適用条件の確認

- `CVE-2026-82560`（perl）: [Debianの説明](https://security-tracker.debian.org/tracker/CVE-2026-82560)はPod::TextのPOD整形処理を対象とする。同一イメージの通信禁止・使い捨てコンテナで `perl-base 5.40.1-6+deb13u1` の存在を確認したが、`find /usr -path '*/Pod/Text.pm'` は結果なし、`perl -MPod::Text` はモジュール不在で失敗した。対象モジュール不在という限定的証拠であり、正式な適用除外・リスク受容は行っていない。
- `CVE-2026-85091`（zlib）: 実際の `zlib1g` は `1:1.3.dfsg+really1.3.1-1+b1`。[Debianの説明](https://security-tracker.debian.org/tracker/CVE-2026-85091)の上流影響バージョン記述とDebianパッケージ判定に差があるが、それだけで誤検知とは判断しない。バイナリ/ソースへの適用性と修正版の確認が残る。

両方とも今回の監査では `not fixed`。指摘数を減算せず、正式公開No-Goを維持する。実AWSのイメージを監査したものではない。
