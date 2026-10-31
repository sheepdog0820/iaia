# readinessのキャッシュ検査をリクエスト間で分離する（2026-10-31）

## 再現と変更

`_check_cache()`は共有の`healthcheck:probe`へ異なる時刻を書き、読み戻してから削除していた。同時に動く検査が同じキーを上書き/削除すると、正常なcacheでもreadinessが503になる。

実LocMemCacheのset完了を2スレッドで同期させる回帰を追加し、一方200・他方503を再現した。DB検査はこの競合試験だけ成功fixtureへ置き換え、cacheのset/get/deleteは実backendへ委譲している。別の回帰では不一致後に自身の検査キーが残ることも再現した。修正前は2失敗、修正後は2成功である。稼働AWSで障害を観測したものではない。

検査ごとにUUID付きキーを使い、書き込み成功後は`finally`で自身のキーだけを削除する。TTL10秒は維持し、setの結果が不明な場合や削除不能時も期限付きの技術用データに限る。cache全体のclearや、別のprobe/セッション/利用者データの削除は行わない。正常200・依存先失敗503・固定`error`と依存先名、実行時刻、HTTP Host/内部healthの境界は変更しない。

## 検証と自己レビュー

関連SQLite/本番設定の隔離PG18.3は各22件・28 subtests成功、省略0。競合時の両検査成功、書き込み済みキーの不一致後の削除、無関係な合成キーの保持、既存のhealth/情報保護/access loggingを確認した。health実装34実行文・4分岐は除外0で全実行した。この計測を他のモジュール全体の100%へ広げない。

差分、cacheキーの所有範囲、書き込み/読み戻し/削除の失敗時の応答、既存監視の判定とprivacyを自己レビューした。修正範囲に未解決の実装指摘はない。Black/isort/Flake8/Bandit、UTF-8/LFを確認する。画面文言・DB/schema・依存lockは変更しない。

固定commitの通常配布物を構築し、専用の実Redisを使った親配布物との比較、実HTTPの並行readiness、既存Host/WS・実driver障害・最終CIを検証して候補PRへ追記する。前候補の成功は今回の変更の検証へ流用しない。

## 候補・承認・復旧

PR #46/#47/#48の固定headは変更せず、別worktree/ブランチからDraftを準備する。mainマージ、AWS/共有DB・実データ・IAM/Secrets/OAuth・費用・実Stripe・外部通知は今回行っていない。

復旧はこの修正のrevert PRで、元の競合/期限までの検査キー残存が再発する。親候補のOrigin・readiness本文保護・Host制限は維持され、DB切戻しは不要。OS/native52指摘等と、F/B/I/Q/O全25条件を満たすまでの正式公開No-Goを維持する。

証拠はGit管理外の`tmp/cache-probe-isolation-red-20261031.log`、`tmp/cache-probe-isolation-green-20261031.log`、`tmp/cache-probe-related-coverage-sqlite-20261031.log`、`tmp/cache-probe-coverage-sqlite/coverage.json`、`tmp/cache-probe-production-pg-20261031.log`。合成fixtureの環境ファイルはcommitしない。
