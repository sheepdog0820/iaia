# WebSocket通知のOrigin制限（2026-10-31）

PR #45の固定head `5f82dba5`を通常Dockerfileで構築したimage `8106f14e`の追加検証で、許可外Originと合成のログイン済みCookieを持つ接続が受理され、合成のprivate通知を受信することを再現した。隔離PG/Redisと合成利用者だけで実施し、AWS・実ユーザーのデータには接続していない。実ブラウザのCookie送信条件や、稼働AWS上での悪用可能性まで確認したという意味ではない。

## 原因と変更

`tableno/asgi.py`は通知WebSocketへ`AuthMiddlewareStack`を適用していたが、Originを検証していなかった。[Channels公式のセキュリティ説明](https://channels.readthedocs.io/en/stable/topics/security.html)に従い、その外側を`AllowedHostsOriginValidator`で囲む。Originのhostを既存の`ALLOWED_HOSTS`に照合し、許可外・欠落・null・不正形式を拒否する。Originを認証の代わりにはせず、セッション認証・利用者ごとの通知group・匿名拒否は維持する。

WebSocketのブラウザクライアントは`window.location.host`へ接続し、Originをブラウザが付ける。今回JavaScript/UIは変更しない。非ブラウザの接続元も許可されたOriginを指定する必要があり、Originなしの接続は拒否される。許可hostの追加やwildcard化、IAM/Secrets/OAuth等の設定変更は含まない。HTTPルーターや通知データの保存・配送処理も変更しない。

## 再現と検証

- 通常配布物の実通信では、HTTP readiness200・匿名WebSocket403の後、許可外Originが合成利用者の通知を受信した。Cookie/行データをログや証拠に保存せず、固定の失敗分類と対象image/sourceだけを保存した。
- 修正前に回帰を追加し、Originなし・null・不正形式・外部host・許可hostに似せたhostの5 subtestsが接続成功のため失敗することを確認した。許可host/port・大文字hostの接続、匿名拒否、通知の利用者分離も同じ実ASGI入口・セッションで確認する。
- 修正後はSQLite/PG18.3とも4件・7 subtests成功、省略なし。既存WebSocketモジュールはPG CIの明示対象に入っていなかったため追加し、正規接続の既存fixtureにもOriginを明記した。製品認証のmockや無効化は使っていない。
- プロジェクト既定のcoverage設定はASGIを除外していた。製品設定を変えず、専用の一時設定で入口を計測し、8実行文すべてを実行した。ASGI入口の結果を、第三者ライブラリや配布物全体の100%検証へ拡張しない。
- 拡張した通知/設定試験は隔離PGで64件・12 subtests成功、省略なし。初回は検証用runnerの`USE_REDIS_CACHE=False`が子processのTLS設定probeへ継承され、1件失敗/63件成功となった。製品コードを変えず不要な強制指定を除くと同じ失敗ケースと全64件が成功した。失敗ログも保持している。

Black/isort/Flake8/Bandit、UTF-8/LF、PG CIの対象、実装差分と既存ブラウザの接続方式を自己レビューした。この修正範囲の未解決の実装指摘はない。新たな利用者向け文言はない。固定commitからの通常配布物の再構築、同じOrigin拒否を含む実通信、最終CIの結果は候補PRへ追記する。修正前imageの成功や、Origin検証を含まない旧試験の成功は、この修正の証明として使わない。

## 候補・承認・復旧

旧PR #45の`5f82dba5`へのマージ確認は、追加検証の失敗を受けて取り下げた。旧headと成功/失敗記録は保持し、修正を含む新しい統合headの検証が揃ってから対象を提示する。旧対象への回答を新しいheadの承認へ流用しない。mainマージ・共有DB適用/実データ修復・AWS反映・費用/権限変更・実Stripe・外部通知・正式公開は行っていない。

復旧はOrigin制限のrevert PRで、戻すと許可外Originの問題が再発する。モデル/移行・依存lock・既存ALLOWED_HOSTS・公開条件は変更しない。OS/native52指摘・未除外exit2と、全25条件を満たすまでの正式公開No-Goは維持する。

ローカル証拠：`tmp/release-group-security-protocol-failure-20261031.json`、`tmp/websocket-origin-red-sqlite-20261031.log`、`tmp/websocket-origin-green-sqlite-20261031.log`、`tmp/websocket-origin-green-pg-20261031.log`、`tmp/websocket-origin-entrypoint-coverage-proof-20261031.json`、`tmp/websocket-origin-related-pg-20261031.log`、`tmp/websocket-origin-related-pg-cleanenv-20261031.log`、`tmp/websocket-origin-settings-env-check-20261031.log`。秘密/合成セッションを含む一時環境ファイルはGitへ含めない。
