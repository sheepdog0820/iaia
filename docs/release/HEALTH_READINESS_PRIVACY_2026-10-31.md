# readiness応答の診断情報保護（2026-10-31）

## 問題と変更

HTTP Host制限の前提を点検する中で、`tableno/health_views.py`がDB/キャッシュの検査失敗を`f"error: {exc}"`として公開readinessへ返していた。例外に接続先・利用者名・認証情報等が入った場合、`DEBUG=False`でもこの明示的な応答は除去されない。合成の例外で再現したもので、稼働AWSで秘密値の漏えいを観測したという意味ではない。AWS・実ユーザーの行データや秘密値へ接続していない。

失敗した依存先の`checks`値を固定の`error`へ変更する。例外の文字列化・種類の公開・新たなtracebackの記録は行わない。正常時の`ok`、失敗時503、`status=degraded`、失敗した依存先の名前を持つ`errors`、時刻、片方が失敗しても両方を検査する動作は維持する。例外の文字列化自体が失敗する場合にも503を返す。

これは機械向けhealth応答の変更で、新しい画面文言はない。リポジトリ内の運用手順とクライアントはHTTP statusや正常時の`checks=ok`で判定しており、旧例外本文への依存は見つからなかった。既存テストの`error:`前方一致も、固定値`error`の厳密な検査へ更新した。リポジトリ外の監視が例外本文を解析しているかは未確認であり、障害時の診断は依存先名と非公開の運用情報で行う。

## 再現・検証・自己レビュー

- 修正前は6失敗・4成功。DBだけ、cacheだけ、両方の失敗で合成の接続先/認証情報を含む本文が返り、文字列化できない例外では応答生成も失敗した。失敗ログはGit管理外に保持する。
- 修正後のhealth回帰は6件・5 subtests成功。正常時の使い捨てDB/ローカルcache確認に加え、合成の私的情報が応答へ出ないこと、両検査の実行、slash有無、実cache checkerのround-trip不一致を確認した。製品コードの認証や検査を無効化していない。
- error reporting/access loggingを含む関連試験はSQLite/PG18.3とも20件・28 subtests成功、省略0。SQLiteではhealthの全32実行文・4分岐を実行し、除外0だった。この結果を他のモジュール全体の100%検証とは扱わない。
- 初回coverageはread-onlyなcheckoutの`.coverage`へ書こうとして試験開始前に失敗した。製品コードを変えず出力先を使い捨てscratchへ直し、同じ対象を再実行して上記成功を確認した。初回の失敗ログも保持する。

差分、応答の互換性、例外情報の経路、ルートの両表記、既存監視手順を自己レビューした。修正範囲に未解決の実装指摘はない。Black/isort/Flake8/Bandit、UTF-8/LFを確認する。固定commitからの通常配布物、実ドライバの接続失敗、最終CIは候補PRへ結果を追記し、親候補の成功をこの変更の検証として流用しない。

## 候補・承認・復旧

PR #46の承認対象`a6f88882`は変更せず、別worktree/ブランチから同PRの上にDraftを準備する。mainマージ・AWS配備・共有DB変更・実データ操作・IAM/Secrets/OAuth・費用・外部通知は含まない。モデル/マイグレーション・依存lock・HTTP Host設定も変更しない。

復旧はrevert PRだが、戻すと例外本文の公開と文字列化失敗が再発する。実DBの切戻しは不要である。HTTP Host制限の実効確認、OS/native52指摘等の残課題と、F/B/I/Q/O全25条件を満たすまでの正式公開No-Goは継続する。

ローカル証拠：`tmp/readiness-privacy-red-sqlite-20261031.log`、`tmp/readiness-privacy-green-sqlite-20261031.log`、`tmp/readiness-privacy-related-coverage-sqlite-20261031.log`、`tmp/readiness-privacy-related-coverage-sqlite-corrected-20261031.log`、`tmp/readiness-privacy-coverage-sqlite-corrected/coverage.json`、`tmp/readiness-privacy-green-pg-20261031.log`。合成fixtureの環境ファイルはGitへ含めない。
