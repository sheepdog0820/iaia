# WebSocket通知のOrigin制限（2026-10-31）

PR #45の固定head `5f82dba5`を通常Dockerfileで構築したimage `8106f14e`の追加検証で、許可外Originと合成のログイン済みCookieを持つ接続が受理され、合成のprivate通知を受信することを再現した。隔離PG/Redisと合成利用者だけで実施し、AWS・実ユーザーのデータには接続していない。実ブラウザのCookie送信条件や、稼働AWS上での悪用可能性まで確認したという意味ではない。

## 原因と変更

`tableno/asgi.py`は通知WebSocketへ`AuthMiddlewareStack`を適用していたが、Originを検証していなかった。[Channels公式のセキュリティ説明](https://channels.readthedocs.io/en/stable/topics/security.html)に従い、その外側を`ConfiguredOriginValidator`で囲む。Channelsの`OriginValidator`へ、既存の`CSRF_TRUSTED_ORIGINS`と`PUBLIC_SITE_URL`だけを渡し、許可外・欠落・null・不正形式を拒否する。HTTPの`ALLOWED_HOSTS`はOriginを許可する根拠にしない。Originを認証の代わりにはせず、セッション認証・利用者ごとの通知group・匿名拒否は維持する。

WebSocketのブラウザクライアントは`window.location.host`へ接続し、Originをブラウザが付ける。今回JavaScript/UIは変更しない。非ブラウザの接続元も許可されたOriginを指定する必要があり、Originなしの接続は拒否される。既定の開発設定はlocalhost/127.0.0.1のHTTP 8000番を含む。別port/aliasを使う場合も、既存の明示的なOrigin設定が必要である。空の設定と全体wildcard `*`は許可を与えない。Djangoの明示的な`https://*.domain`はChannelsの`https://.domain`へ変換し、指定domainの範囲だけを許可する。許可先の追加やIAM/Secrets/OAuth等の設定変更は含まない。HTTPルーターや通知データの保存・配送処理も変更しない。

## HTTPのwildcardから独立した最終方針

10:08/10:15 JSTの読み取りで、稼働ECS定義55の平文宣言は`ALLOWED_HOSTS=*`、`CSRF_TRUSTED_ORIGINS=https://stg.tableno.jp`、`PUBLIC_SITE_URL=https://stg.tableno.jp`だった。Secretsの値や実効設定は取得しておらず、宣言の確認に限る。AWSの作成・更新・削除は行っていない。

初期修正の`AllowedHostsOriginValidator`はHTTPのwildcardを引き継ぐため、この宣言では安全性の根拠にできない。固定head `24f7d88e`の当時のCIやlocalhost設定の通常配布物検証は保持するが、最終候補の合格とは扱わない。実ASGI入口をwildcard設定の中で読み直す回帰で拒否の失敗を再現し、さらにHTTPで個別許可したhostだけでもOriginを許していた中間案の失敗を再現した。最終実装ではHTTPのhost許可を一切参照しない。

最終のSQLite/PG18.3は各12件・24 subtests、省略0で成功した。実セッション・利用者分離・匿名拒否に加え、HTTP wildcard、HTTPだけで許可したhost、全体wildcardの拒否、公開URLのみの許可、明示subdomainと似せたdomainの境界を確認した。通知/設定/システムを含む関連PGは86件・29 subtests、省略0で成功した。入口と新middlewareは各8実行文を100%計測し、報告分岐数は0である。第三者ライブラリ全体の網羅を意味しない。Black/isort/Flake8/Banditと差分の自己レビューも成功した。

固定commitからの通常配布物は、上記の稼働宣言と同じ文字列を使う隔離PG/Redis環境で再検証する。`https://stg.tableno.jp`はOrigin設定/ヘッダーとして使うだけで、接続先は専用ローカルcontainerである。実AWS・実ユーザー・共有DBには接続しない。HTTP Host/ALB側の制限、Secretsを含む実効設定、承認後の実環境反映は別途必要であり、この変更で完了したとは扱わない。

## 再現と検証

- 通常配布物の実通信では、HTTP readiness200・匿名WebSocket403の後、許可外Originが合成利用者の通知を受信した。Cookie/行データをログや証拠に保存せず、固定の失敗分類と対象image/sourceだけを保存した。
- 修正前に回帰を追加し、Originなし・null・不正形式・外部host・許可hostに似せたhostの5 subtestsが接続成功のため失敗することを確認した。許可host/port・大文字hostの接続、匿名拒否、通知の利用者分離も同じ実ASGI入口・セッションで確認する。
- 修正後はSQLite/PG18.3とも4件・7 subtests成功、省略なし。既存WebSocketモジュールはPG CIの明示対象に入っていなかったため追加し、正規接続の既存fixtureにもOriginを明記した。製品認証のmockや無効化は使っていない。
- プロジェクト既定のcoverage設定はASGIを除外していた。製品設定を変えず、専用の一時設定で入口を計測し、8実行文すべてを実行した。ASGI入口の結果を、第三者ライブラリや配布物全体の100%検証へ拡張しない。
- 拡張した通知/設定試験は隔離PGで64件・12 subtests成功、省略なし。初回は検証用runnerの`USE_REDIS_CACHE=False`が子processのTLS設定probeへ継承され、1件失敗/63件成功となった。製品コードを変えず不要な強制指定を除くと同じ失敗ケースと全64件が成功した。失敗ログも保持している。

以下は初期修正の履歴であり、HTTP wildcardに対する最終修正の結果とは区別する。新たな利用者向け文言はない。固定commitからの通常配布物の再構築、同じOrigin拒否を含む実通信、最終CIの結果は候補PRへ追記する。修正前imageの成功や、Origin検証を含まない旧試験の成功は、この修正の証明として使わない。

## 固定配布物とCIの月末fixture補正

Origin修正のcommit `c75542ab`から通常image `b9c8a1f2`を構築した。HTTP readiness200/DB-cache ok、匿名403、不正Origin403、認証済みRedis/msgpack通知、別利用者への非配送、切断に成功し、配布物内の技能/グループ/認証/WebSocket関連187件も成功した。Git由来564ファイルとentrypoint一致、UID10001/root read-only・pip/pytestなし・製品source上書きなし、実111 package監査0件を確認。OS101 packageの一覧は旧候補と一致し、同じimageのScout1.29は52指摘（C2/H9/M6/L35）・未除外exit2で不合格。専用ローカル資源は09:45 JSTに削除・absenceを確認した。

同commitのCIでは、システム試験のカレンダーfixtureが1件失敗した。UTCで当月を問い合わせる一方、UTC月末19時に生成したセッションは日本時間では翌月になるため、正しく日本時間の月境界で絞るAPIには対象がなかった。固定したUTC時刻でも旧fixtureの失敗を再現し、fixtureを日本時間で作成して、その保存した時刻の月を問い合わせる形に修正した。UTC月末の日本時間の同日と、UTCでは月末/日本時間では翌月になる2条件を固定し、返る月とイベントのタイトル集合を明示的に検証する。期待値を空や任意の1件へ弱めず、製品APIは変更していない。

補正後のシステム試験は14件成功・省略0件。カレンダーの予定取得も同じ固定時計に従い、試験後は時計とタイムゾーンを復元する。これはテスト/文書だけの後続commitで、Origin修正や依存・モデル/移行には差分がない。最終headのCI・通常配布物の結果はPRで区別して追記する。ローカルの再現は`tmp/calendar-system-month-end-red-20261031.log`、成功は`tmp/calendar-system-month-end-green-20261031.log`と`tmp/calendar-system-month-boundaries-green-20261031.log`、CI失敗の生ログもGit管理外に保持する。

## 候補・承認・復旧

旧PR #45の`5f82dba5`へのマージ確認は、追加検証の失敗を受けて取り下げた。旧headと成功/失敗記録は保持し、修正を含む新しい統合headの検証が揃ってから対象を提示する。旧対象への回答を新しいheadの承認へ流用しない。mainマージ・共有DB適用/実データ修復・AWS反映・費用/権限変更・実Stripe・外部通知・正式公開は行っていない。

復旧はOrigin制限のrevert PRで、戻すと許可外Originの問題が再発する。モデル/移行・依存lock・既存ALLOWED_HOSTS・公開条件は変更しない。OS/native52指摘・未除外exit2と、全25条件を満たすまでの正式公開No-Goは維持する。

ローカル証拠：`tmp/release-group-security-protocol-failure-20261031.json`、`tmp/websocket-origin-red-sqlite-20261031.log`、`tmp/websocket-origin-green-sqlite-20261031.log`、`tmp/websocket-origin-green-pg-20261031.log`、`tmp/websocket-origin-entrypoint-coverage-proof-20261031.json`、`tmp/websocket-origin-related-pg-20261031.log`、`tmp/websocket-origin-related-pg-cleanenv-20261031.log`、`tmp/websocket-origin-settings-env-check-20261031.log`。秘密/合成セッションを含む一時環境ファイルはGitへ含めない。
