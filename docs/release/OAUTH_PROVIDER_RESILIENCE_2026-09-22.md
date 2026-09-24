# X・Discord OAuth通信障害時の再試行案内

## 対象

- 基準: `c7786b6d`（統合候補 `9889f4c8` の検証記録を含む）
- 対象API: `/api/auth/twitter/`、`/api/auth/discord/`
- 対象処理: 認可コードのトークン交換、アクセストークンによる利用者情報取得、クライアント設定不足時の応答

XとDiscordのAPI認証は、プロバイダーのアクセストークンをバックグラウンド処理用に保存しない。そのため、Google連携で修正した保存済みトークンの期限判定は対象外とした。

## 再現と修正

- `requests.Timeout` をトークン交換と利用者情報取得へ注入する4ケースを先に追加した。修正前はすべてHTTP 500となり、利用者が再試行可能な外部通信障害と予期しない内部障害を区別できなかった。
- `requests.RequestException` を予期しない例外より先に処理し、XまたはDiscordとの通信失敗を示す固定の日本語メッセージとHTTP 503を返すようにした。ログはプロバイダー名と例外型だけを記録し、アクセストークンや例外本文を含めない。
- 認可コード経路でクライアントIDが未設定の場合、環境変数名を含むHTTP 500を返していた。外部設定を確認中であることだけを示す固定の日本語メッセージとHTTP 503へ変更した。
- Discordへアクセストークンを直接渡す既存経路はクライアントIDを要求せず、Discordの `/users/@me` で利用者を確認する仕様を維持した。

## ローカル検証

- RED: 新規通信障害4件は期待503に対して500、新規設定不足2件も期待503に対して500となることを確認した。
- GREEN: Google/X/Discord API、例外本文非露出、保存の原子性、停止済み利用者の拒否を含む49件が成功し、PostgreSQL専用2件だけをSQLite実行でskipした。
- Coverage.pyで `accounts/views/api_auth_views.py` は286実行対象行中260行を実行し91%。今回追加した実行対象7行はすべて実行され、未実行0行だった。JSON証跡はリポジトリ外の `C:\tmp\oauth-resilience-coverage-20260922.json` に保存した。
- Black、isort、Flake8、Bandit、`git diff --check` は対象3ファイルで終了0。Banditの既存nosec通知はテスト用の固定トークンに対応する。

## 固定候補のCIと配布イメージ

- アプリ候補: `659b357570f4ddd3049088ee94c7fa7f528c0eec`
- GitHub Actions: [Django CI run 35678996786](https://github.com/sheepdog0820/iaia/actions/runs/35678996786)。Unit / Integration、system、playwright、infrastructure、lint-security、production-databaseの6ジョブがすべて成功した。実行時間は2026-09-22 11:18〜11:35 JST。
- 実Dockerfileと固定依存から `tableno:oauth-resilience-659b3575` を作成した。イメージIDは `sha256:c2319d50f4e1dc7a1504ec3bc32888c7bc1fe2aecdce863cd92f8254351a8d82`。
- 同イメージを外部通信なしで実行し、上記49件が成功、PostgreSQL専用2件がSQLiteでskipした。
- 専用internalネットワーク、PostgreSQL 18.3のtmpfs、Redis 7で通常entrypointを実行した。全移行、静的227件の収集と617件の後処理、Daphne起動、`/health/ready/` のdatabase/cache `ok`、`migrate --check` を確認した。
- コンテナ内の変更3ファイルのSHA-256はホストの候補ソースと一致した。検証用app/DB/Redisコンテナとinternalネットワークは確認後に削除した。

初回の隔離起動は、PostgreSQL 18以降で非推奨となった `/var/lib/postgresql/data` へのtmpfs指定をDBイメージが拒否して停止した。アプリ起動・移行前の検証構成エラーであり、専用リソースを削除後、推奨の `/var/lib/postgresql` へ変更した最終実行だけを合格結果とした。

## 限界と公開判定

実X/Discord認可、取消、トークン失効、プロバイダー障害、callback URL、公開設定を操作した結果ではない。共有DB、Secrets、権限、外部利用者、費用への変更はない。I02/I03のローカル耐障害性を補強するが、実認可要件は未達のままで正式公開No-Goを維持する。

復旧はこの変更コミットを通常のrevertで戻す。ただし、外部通信障害が再びHTTP 500となり、設定不足時に内部設定名を返す旧挙動も復活する。
