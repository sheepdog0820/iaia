# Web機能 完成作業フロー

最終更新: 2026-06-12

## 適用範囲

AWS IaC、OpenAPI、非同期処理、外部連携、グループ連携、ゲスト導線、リアルタイム通知を変更する際の共通フローです。

## チケット単位の作業順

1. 受け入れ条件と公開インターフェースを確定する。
2. モデル、URL、権限、既存テストを確認する。
3. 失敗するテストを先に追加する。
4. 最小実装でテストを成功させる。
5. 権限、競合、冪等性、失効、外部API失敗時の挙動を追加検証する。
6. 対象テスト、アプリ単位回帰、全体回帰を順に実行する。
7. Playwrightで利用者の操作導線を確認する。
8. OpenAPI、Terraform、Markdown、差分品質ゲートを実行する。
9. `ISSUES.md`、`ISSUES_CLOSED.md`、仕様書を更新する。
10. 1チケットまたは依存関係が閉じた単位でコミットする。

## 完了ゲート

```powershell
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py test --noinput
python manage.py spectacular --file openapi.yaml --validate
npm run test:e2e -- --project=chromium
coverage run manage.py test
coverage report
terraform -chdir=infrastructure/terraform fmt -check -recursive
terraform -chdir=infrastructure/terraform validate
terraform -chdir=infrastructure/terraform plan -refresh=false -input=false -lock=false -var-file=environments/offline-plan.tfvars.example
git diff --check
```

PlaywrightはローカルDjango DBを共有して関連レコードを作成するため、設定上 `workers: 1` で直列実行します。

`check --deploy` のローカル設定警告とOpenAPIの既存警告は、終了コードとエラー件数を記録します。本番設定の検証は `APP_ENV=aws-pre` または `APP_ENV=aws-prod` と必要なダミーSecretを指定して別途実行します。

リポジトリ内の構文・依存検証には `offline_plan=true` のダミーplanを使用します。このモードはAWSメタデータを固定値へ置き換え、認証確認とrefreshを行いません。認証済みの検証アカウント、実在するRoute 53 Hosted Zone、ACM/DNS方針を使うplan/applyはGo/No-Go工程へ引き継ぎ、`offline_plan`を有効にして実環境へ適用してはいけません。

## 外部連携の失敗時原則

- Discord、Google、Celery brokerの障害でセッション作成・更新をロールバックしない。
- 外部処理は `AsyncJob` または配信履歴へ失敗状態を保存する。
- 再試行対象は冪等キーまたは外部イベントIDで重複を防ぐ。
- トークンとWebhook URLをレスポンスやログへ平文で再表示しない。
- WebSocket接続不能時は既存ポーリングを継続する。

## リリース引き継ぎ

- AWS実適用前に `docs/specifications/AWS_RELEASE_WORKPLAN.md` を確認する。
- media、DB、障害対応は `docs/runbooks/` のRunbookを使用する。
- 実環境のDNS、ACM、通知先、予算、削除保護をGo/No-Go記録へ残す。
