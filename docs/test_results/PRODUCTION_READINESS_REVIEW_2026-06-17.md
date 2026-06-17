# Tableno 本番公開前レビュー結果（2026-06-17）

## 判定

**条件付き Go。** 中核画面と主要APIは到達可能で、限定ベータでは十分運用可能な完成度です。ただし、一般公開前は外部連携の失敗復旧と運用承認が必要です。

## 今回の修正

- セッション一覧の正規URLを `/api/schedules/sessions/view/` に統一し、旧 `/api/schedules/sessions/web/` は互換リダイレクトとして残しました。
- `GET /api/jobs/` と `POST /api/jobs/<uuid>/retry/` を追加し、ユーザー自身の外部連携ジョブを一覧・再試行できるようにしました。
- 連携設定画面に「連携ジョブ状況」を追加し、Google Calendar / Google Sheets の失敗理由と再試行導線を表示しました。
- Google Sheets export ジョブに `character_ids` を保存し、再試行時に元の出力対象を再現できるようにしました。
- ドキュメントとE2Eの旧セッションURL参照を正規URLへ更新しました。

## 公開前ブロッカー

- **P0: 実AWS適用承認**
  DNS、ACM、Secrets、予算、バックアップ、監視通知先、ロールバック手順の実値承認が必要です。これはコードだけでは完了できません。

- **P1: 外部連携の実運用検証**
  ジョブ可視化と再試行APIは追加済みです。実Google/Discord資格情報を使った失敗復旧の手動検証は本番前に必要です。

## 確認済みコマンド

- `python manage.py check`
- `python manage.py test schedules.test_async_jobs schedules.test_external_integrations`
- `python manage.py test tests.ui.test_ui_navigation tests.unit.test_health_endpoints tests.unit.test_runtime_env`

## 残リスク

- OpenAPI生成時に既存Serializer/ViewSetの型推論警告が多数出ています。スキーマ自体は生成されますが、外部API利用者向けには改善余地があります。
- ブラウザ実機でのレスポンシブ確認は別途必要です。今回の確認はDjangoテストとE2E対象更新が中心です。
- Discord配信失敗は `DiscordDelivery` に保存されていますが、今回の画面表示はGoogle系ジョブ中心です。Discord配信履歴の画面表示は次の改善候補です。
