# 開発AWS環境のタブレノMCP

開発環境の `https://stg.tableno.jp/mcp` を、事前登録したCodexから利用する試験公開の手順です。利用者はタブレノにログインして、卓の予定と探索者シートへのアクセスを許可します。ツールはログインした本人に関係する次の卓、本人が所有する探索者の一覧と詳細を返します。

## 構成

| HTTPSの経路 | 処理するプロセス |
|---|---|
| `/mcp` 完全一致 | タブレノイメージで `python -m tableno_mcp.http` を実行する専用ECSタスク |
| `/mcp/oauth/authorize/`、`/mcp/oauth/token/`、`/mcp/oauth/revoke_token/` | 既存WebのDjango |
| `/.well-known/oauth-authorization-server`、`/.well-known/oauth-protected-resource/mcp` | 既存WebのDjango |

MCPタスクはポート8000で待機し、ALBのターゲットグループは `GET /health/live` を使います。タスクへのアクセスはALBからに限定します。Streamable HTTPはステートレスで、リクエストごとにトークンの有効期限、発行先、利用者、ツールの権限を確認します。PostgreSQLではツールのクエリを読み取り専用トランザクションで実行します。

認可サーバーはDjango OAuth Toolkitを利用します。認可コードは60秒、アクセストークンは15分で期限切れになります。リフレッシュトークンは利用のたびに更新され、最終発行から約8時間で期限切れになります。

## 反映の準備

1. Web・MCP用の候補イメージを同じコミットから作成します。既存の稼働イメージ、AWS構成の変更内容と費用、OAuth用DBマイグレーション、試験利用者とクライアント登録について承認を確認します。
2. `APP_ENV=aws-pre` のWebとMCPタスクに `TABLENO_MCP_ENABLED=True`、`TABLENO_MCP_CLIENT_ID`、`TABLENO_MCP_USER_IDS` を同じ値で設定します。利用者は開発DB内の数値IDをカンマ区切りで指定します。認可の対象を確認してから追加してください。
3. 候補イメージ・同じ環境設定の一回限りのタスクで `python manage.py migrate oauth2_provider --plan` を確認します。承認済みのOAuthテーブルを `python manage.py migrate oauth2_provider --noinput` で作成します。
4. Django管理画面のOAuth2 Providerでクライアントを登録します。クライアント種別はPublic、グラント種別はAuthorization code、クライアントIDは手順2と同じ値、同意の省略は無効にします。リダイレクトURIはCodexのループバックコールバックを登録します。クライアントシークレットはCodexの設定に入れません。
5. Webの候補版とMCP専用ECSサービスを反映します。ALBの `/mcp` 完全一致ルールをMCPターゲットへ向けます。既存の開発環境の停止時間に合わせてMCPタスクの停止・起動も設定し、アクセス制限・負荷上限・ログの扱いを確認します。

設定例は [ステージング環境変数のテンプレート](../../.env.staging.example) にあります。機能は初期状態で無効です。OAuthのDBテーブルには認可コードとトークンが保存され、ECS常駐タスクとALB経路の追加は運用費用に影響します。

## Codexでの確認

Codexの `~/.codex/config.toml` に開発環境の設定を追加します。例の `http://127.0.0.1:1455/callback` は、管理画面に登録するリダイレクトURIと完全一致させます。既存のローカル版とは別のサーバー名で利用できます。 [Codexの設定項目](https://learn.chatgpt.com/docs/config-file/config-reference)

```toml
[mcp_servers.tableno-aws-pre]
url = "https://stg.tableno.jp/mcp"
oauth_resource = "https://stg.tableno.jp/mcp"
scopes = ["sessions:read", "characters:read"]

[mcp_servers.tableno-aws-pre.oauth]
client_id = "<登録済みクライアントID>"
callback_port = 1455
callback_url = "http://127.0.0.1:1455/callback"
```

```powershell
codex mcp login tableno-aws-pre
```

- 未認証の `/mcp` が401を返し、`WWW-Authenticate` が対象リソースのメタデータを示す。
- 許可された利用者でタブレノへのログインと同意を完了し、新しいCodexチャットで自分の卓と探索者を参照できる。
- 許可リスト外の利用者、期限切れ・失効済みトークン、別のリソース向けトークンが拒否される。
- AWS側とアプリ側のアクセスログに認可ヘッダー、トークン、認可コード、リクエスト本文が残らないことを確認する。

## 無効化

MCPへの経路を閉じた後、Web側の `TABLENO_MCP_ENABLED` を無効にして認可の受付を停止し、対象クライアントの発行済み資格情報を失効させます。MCP専用サービスを停止し、Webと既存APIのヘルスチェックを確認します。
