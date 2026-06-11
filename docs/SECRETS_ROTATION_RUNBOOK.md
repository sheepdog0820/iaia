# Secrets ローテーション運用手順（ISSUE-051）

最終更新日: 2026-06-12

## 目的

- 本番/ステージングで利用している秘密情報を安全に更新する。
- 更新後にアプリケーションの稼働を確認し、異常時に即時ロールバックできる状態を維持する。

## 対象

- `SECRET_KEY`
- `DB_PASSWORD`
- `REDIS_URL`（必要時）
- OAuth クライアントシークレット（Google / Discord / Twitter）
- メール送信パスワード
- `SENTRY_DSN`（必要時）

## 前提

- Secrets は AWS Secrets Manager または AWS Systems Manager Parameter Store で管理する。
- ECS Task Definition の `secrets` で各キーを注入するか、JSON Secret を `AWS_SECRETS_JSON` / `AWS_SECRETS_FILE` 経由で注入する。
- 実行者は以下権限を持つ:
  - `secretsmanager:GetSecretValue`, `secretsmanager:PutSecretValue`
  - `ssm:GetParameter`, `ssm:PutParameter`
  - `ecs:DescribeServices`, `ecs:UpdateService`

## 変更前チェック

1. 現在の稼働状態を確認する。
   - `/health/live` が `200`
   - `/health/ready` が `200`
2. 現在の Secret のバージョン情報を控える（ロールバック用）。
3. 変更対象キー、対象環境（stg/prod）、実施時間を記録する。
4. 同時間帯のデプロイ作業がないことを確認する。

## 標準手順（推奨: stg -> prod）

1. ステージング環境の Secret を更新する。
2. ECS サービスを `force-new-deployment` で再起動する。
3. 疎通確認を実施する（後述の確認項目）。
4. 問題がなければ本番環境の Secret を同様に更新する。
5. 本番 ECS サービスを `force-new-deployment` で再起動する。
6. 本番の疎通確認を実施し、結果を記録する。

## 更新コマンド例

### Secrets Manager（単一キー）

```bash
aws secretsmanager put-secret-value \
  --secret-id tableno/aws-prod/DB_PASSWORD \
  --secret-string 'new-strong-password'
```

### Secrets Manager（JSONまとめ管理）

```bash
aws secretsmanager put-secret-value \
  --secret-id tableno/aws-prod/app-config \
  --secret-string '{"SECRET_KEY":"...","DB_PASSWORD":"...","REDIS_URL":"..."}'
```

### SSM Parameter Store

```bash
aws ssm put-parameter \
  --name tableno/aws-prod/DB_PASSWORD \
  --type SecureString \
  --value 'new-strong-password' \
  --overwrite
```

### ECS 再デプロイ

```bash
aws ecs update-service \
  --cluster ecs-tableno \
  --service svc-tableno-prod \
  --force-new-deployment
```

## 変更後確認

1. `/health/live` が `200`
2. `/health/ready` が `200`
3. Webログイン（通常ログイン）成功
4. 主要OAuthログイン（Google/Discord/Twitter）成功
5. DB接続エラー/Redis接続エラーがログに出ていない
6. エラー率が通常範囲内（CloudWatch）

## ロールバック手順

1. 直前の Secret バージョンへ戻す。
   - Secrets Manager: 直前バージョンに `AWSCURRENT` を戻すか、旧値を再投入する。
   - SSM: 旧値を `put-parameter --overwrite` で再設定する。
2. ECS サービスを `force-new-deployment` で再起動する。
3. `/health/ready` が `200` に戻ることを確認する。
4. インシデント記録に以下を残す:
   - 発生時刻
   - 影響範囲
   - 原因キー
   - 再発防止策

## 運用ルール

- `SECRET_KEY` は「計画メンテナンス枠」でのみ更新する（全セッション失効の影響が大きいため）。
- 本番は必ずステージング検証後に実施する。
- 1回の作業で更新するキーは最小限にする（原因切り分け容易化）。
- 実施ログはチケット（ISSUE-051）に紐付けて残す。
