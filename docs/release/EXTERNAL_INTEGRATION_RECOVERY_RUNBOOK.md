# 外部連携失敗復旧Runbook

最終更新: 2026-06-18

対象は Google Calendar / Google Sheets / Discord webhook / broker 障害です。実OAuth secret、refresh token、webhook URLは記録しません。

## 共通確認

1. `/integrations/` を開き、連携ジョブ状況とDiscord通知失敗履歴を確認する。
2. 対象の失敗理由、時刻、ジョブIDまたは配送IDを記録する。
3. CloudWatch Logs またはローカルログで同時刻の例外を確認する。
4. 再試行ボタンまたは再送ボタンを実行する。
5. 成功、再失敗、queue不可のいずれかを記録する。

## Google OAuth refresh token失効

- 症状: Google API呼び出しで認可エラー、または連携スコープ不足。
- 復旧: `/integrations/` の Google再連携導線から再認可する。
- 記録: ユーザー、失敗ジョブID、再連携後の再試行結果。

## Google Calendar API障害

- 症状: Calendar同期ジョブが `failed` になり、last_errorにAPIエラーが残る。
- 復旧: 障害が解消した後、`POST /api/jobs/<uuid>/retry/` または画面の再試行を実行する。
- 記録: 元ジョブID、retryジョブID、対象セッション、最終状態。

## Google Sheets大規模入出力

- 症状: import/export の進捗停止、サイズ起因のAPIエラー、broker不可。
- 復旧: 入力範囲や対象キャラクター数を分割し、再実行する。exportは保存済みpayloadから再試行する。
- 記録: spreadsheet_idは秘匿し、対象件数、ジョブID、失敗理由、再試行結果を残す。

## Discord webhook失敗

- 症状: Discord配送が `failed` になり、Discord通知失敗履歴に表示される。
- 復旧: webhook設定、event_type有効化、Discord側権限を確認し、失敗行の「再送」を実行する。
- 記録: delivery_id、event_type、attempts、last_error、再送後の状態。

## broker不可

- 症状: GoogleジョブまたはDiscord再送で `queued: false`、または broker unavailable のエラー。
- 復旧: Redis/worker/beat の起動状態、ECS service、CloudWatch logsを確認する。復旧後に再試行する。
- 記録: 発生時刻、Redis/ECS状態、復旧操作、再試行結果。

## 実資格情報検証記録

| 対象 | 実施日 | 結果 | 記録者 |
| --- | --- | --- | --- |
| Google refresh token失効 | 未実施 | 未確認 |  |
| Google Calendar API障害 | 未実施 | 未確認 |  |
| Google Sheets大規模入出力 | 未実施 | 未確認 |  |
| Discord webhook失敗 | 未実施 | 未確認 |  |
| broker不可 | 未実施 | 未確認 |  |
