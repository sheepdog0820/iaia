# 同期用RedisとWebのログイン保存設定の分離

## 目的と変更

従来のTerraformではElastiCacheを有効にすると、Celeryの処理待ち行列だけでなく、Webキャッシュ、ログイン情報の保存先、WebSocket通知も同時に切り替わった。DBにある既存のログイン情報がRedisへ自動移行されるわけではないため、開発環境の同期処理を追加するだけでログイン継続に影響する構成だった。

`enable_redis_web_state` を追加した。初期値trueでは従来構成を維持する。falseにすると、ElastiCacheをCeleryのブローカー・結果保存に使いながら、DBセッション・ローカルキャッシュ・WebSocket通知無効を維持できる。Redis通信のTLS証明書検証は維持する。

開発環境の起動案で指定する値は次のとおり。ただし、この記述やコードのコミットはAWSへの適用承認ではない。

```hcl
enable_elasticache     = true
enable_redis_web_state = false
enable_nat_gateway    = false
enable_worker_service = true
enable_beat_service   = false
```

`extra_environment` で同名の環境変数を上書きする既存構成がないかも、実施前に確認する。既存の全Terraformを一括適用せず、稼働Web定義・イメージ・背景透過権限等との差分を照合する。夜間のWeb/DB停止スケジュールとworkerの稼働時間も別途整合させる必要がある。

## 検証結果

- 修正前のTerraformテストで、ブローカー専用設定でもWeb保存方式が切り替わる失敗を再現した。
- 修正後、NATあり/なし、ブローカー専用、従来のRedis有効、Redisなしの5構成がすべて成功した。providerはモックで実AWSへの操作なし。
- 実際の本番用Python設定を別プロセスで読み込み、DBセッション・ローカルキャッシュ・WebSocket無効と、TLS付きCeleryブローカー/結果保存URLが両立することを確認した。関連23テスト成功。
- Terraformのfmt/validate、PythonのBlack/isort/flake8、差分確認に合格。Terraform/HCLの改行も既存の編集規約と合わせLFへ明示した。アプリの新しい画面文言はない。

これは設定の検査であり、Redis接続・Google実同期・既存ブラウザのログイン継続を実環境で検証した結果ではない。承認後の反映時には同じChromeセッションで再ログインなしに利用できることを確認する。

## 影響・復旧・残作業

AWSへの適用、共有DB・実データ・Secrets・権限の変更、リソース作成、費用追加は未実施。現在のWeb定義45は変更しない。設定変更は作業ブランチ上で戻せる。実反映時の復旧は反映直前のWeb定義へ戻し、新workerを停止する手順を用意する。

公開までの残条件として、Redis/workerの具体的な作成・保護・監視・停止範囲と費用の承認、実接続試験、限定したGoogleテストデータの同期、beatを含む定期処理の検証がある。[概算費用とGoogle認可の確認](GOOGLE_RECONNECT_2026-09-10.md)、[通信経路の修正](WORKER_NETWORK_FIX_2026-09-10.md)も参照。
