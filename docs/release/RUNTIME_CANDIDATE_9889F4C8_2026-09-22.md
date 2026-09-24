# Stripe・Google統合候補9889f4c8の配布物検証

対象は `9889f4c8903658e6dfa0ddf4b25b8901e74b9bc9`。Stripe候補bb61b0e6に、期限不明のGoogleアクセストークンをrefreshする修正・テスト・証跡を追加した統合候補である。main、AWS、共有DB、Secrets、権限には反映していない。

## CIと通常イメージ

- [GitHub Actions run 35675930275](https://github.com/sheepdog0820/iaia/actions/runs/35675930275)はUnit / Integration、Playwright、production-database、system、lint-security、infrastructureの全6ジョブ成功。
- クリーンな専用worktreeから通常Dockerfileで `tableno:google-token-9889f4c8` を作成。イメージIDは `sha256:af008fa03e3fa2f870ff40e596237750815cb2cfc3a45b221133e7032685819d`。
- `python:3.11-slim` のローカルdigest `sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9` は、2026-09-22確認時のレジストリ最新digestと一致した。

ネットワークなしの一時コンテナ内でDjango check、マイグレーション差分なし、Google連携クラス16件成功を確認した。イメージ内の `schedules/google_tokens.py` と `schedules/test_external_integrations.py` のSHA-256は同じコミットのホストファイルと一致した。

さらに外向き通信を禁止した専用DockerネットワークでPostgreSQL 18.3・Redis 7-alpine・通常entrypointを起動した。全マイグレーション、collectstatic（227ファイル、617後処理）、Daphne起動、`/health/ready/` のdatabase/cacheともok、`migrate --check`成功を確認した。一時コンテナとネットワークは終了後に削除し、不在を確認した。実RDS、S3、Google API、Stripe API、SMTPは使用していない。

## OS再監査

Docker Scout 1.24.0で、このイメージを直接debパッケージ対象として再スキャンした。259パッケージ、14脆弱パッケージ、36指摘（Critical 0 / High 2 / Medium 1 / Low 33）、終了コード2であり、合格扱いにしていない。Git管理外のSARIFは `C:/tmp/runtime-os-9889f4c8-20260922-v124.sarif.json`、SHA-256は `e970d0a297894c0113b10fc03e2b6d1e43125dd18e14a9e0af56c03d124a9ac5`。要約は[結果JSON](RUNTIME_CANDIDATE_9889F4C8_2026-09-22.json)に保存した。

結果とSARIFハッシュはbb61b0e6の[直前監査](RUNTIME_OS_BB61B0E6_2026-09-22.md)と一致した。

- HIGH CVE-2026-82560はScoutがDebianソースパッケージperlへ付与するが、配布物の実体はperl-baseで、問題の `Pod::Text` と `pod2text` は存在しない。アプリにもPerl/POD整形経路はない。指摘自体は抑制しない。
- HIGH CVE-2026-85091のzlibはDebian trixieで修正版なし。アプリからgzwrite/gzprintf/gzvprintfの直接呼び出しはないが、全間接経路の非到達は未証明のため未解消を維持する。
- MEDIUM CVE-2025-45582のtarはEssentialパッケージで、アプリにtar展開経路はない。独断でEssentialパッケージを削除しない。

公式Python 3.11の `slim-bookworm` も同じ条件で比較したが、ScoutはCritical 3 / High 14 / Medium 13を報告した。zlib回避にもならず重大度を増やすため、古いDebian系へ切り替えない。独自zlibバックポートや未検証ベースへの変更も行わず、Debian／公式Pythonイメージの更新を追跡する。

## 判定と制約

アプリ・CI・通常配布物のローカル検証は成功した。OS指摘、実外部連携、共有DB移行、AWS反映、常設worker/beat/Redis、実メール、性能・復旧・運用条件は未完了であり、正式公開No-Goを維持する。

2026-09-22の再確認でorigin/mainは `d875d028ede0b3172780d54d4baacdb226a1d3b3`、候補の祖先である。stg.tableno.jpのHTTP readinessはdatabase/cacheともokだった。AWS CLI資格情報は同時点で取得できず、ECS/RDSの前回確認値を最新確認へ読み替えない。反映前にAWS認証と稼働定義・バックアップを再確認する。
