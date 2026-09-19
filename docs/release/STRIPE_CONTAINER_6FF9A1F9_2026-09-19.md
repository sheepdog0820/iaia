# 削除経路修正を含む配布コンテナの検証

候補 `6ff9a1f9b9fe965b2461de0694530d3e18ffda96` のクリーンな専用worktreeから `tableno:stripe-candidate-6ff9a1f9` をビルドした。[結果JSON](STRIPE_CONTAINER_6FF9A1F9_2026-09-19.json)の4項目すべて成功。

- 配布イメージから隔離PostgreSQL 18.3へマイグレーションを適用し、migrate --checkが成功した。
- 配布イメージ内で削除経路の9回帰テストが成功。通常・管理者API、管理画面単件/一括の保護、拒否時のデータ/ログのロールバック、無料利用者の削除を確認した。
- 配布イメージ内の5ソースファイルのSHA-256が、対象コミットのファイルと一致した。対象は管理画面、管理者API、API共通処理、利用者ビュー、共通退会サービス。
- 通常entrypointでWebを起動し、HTTP readinessのdatabase/cacheがともにokだった。

前候補0f6b81feからDBマイグレーション・requirements.lock.txt・Dockerfile・entrypointに差分がないことをgitで確認した。既存データ保持・旧版読み取り・バックアップ復元は[前候補の検証](STRIPE_CONTAINER_0F6B81FE_2026-09-19.md)を参照し、今回同じ試験を再実施したとは扱わない。

検証用Web・DBコンテナと専用内部ネットワークは終了・削除済み。実Stripeへの接続、実メール送信、ECR登録、共有DB変更、mainマージ、AWS反映は行っていない。ソース側の実Stripe検証は[4削除経路の接続試験](STRIPE_DELETION_PATHS_API_2026-09-19.md)を参照。

候補6ff9a1f9の[CI run 35436261975](https://github.com/sheepdog0820/iaia/actions/runs/35436261975)は全6ジョブ成功し、対象SHAとrun全体のsuccessを確認した。[CI記録](STRIPE_CI_6FF9A1F9_2026-09-19.json)を参照。対象SHAを明示した反映承認を得るまではmain・AWSへ反映しない。CI合格は実AWSのStripe接続や配送基盤の検証を意味せず、正式公開判定は引き続きNo-Go。
