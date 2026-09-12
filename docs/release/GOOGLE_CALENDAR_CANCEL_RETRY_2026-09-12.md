# Google Calendar取消の再試行

## 問題と修正

Google側で予定の削除が完了した直後に応答を失うと、再試行はHTTP 410になる場合がある。従来の取消処理は204/404だけを完了とし、410では失敗・再試行を続けていた。DELETEの410も削除完了として同期記録をDELETED、ジョブをSUCCEEDEDへ更新する。外部予定IDは保持する。

Googleの[エラー処理ガイド](https://developers.google.com/workspace/calendar/api/guides/errors)は、削除済み予定への削除要求でも410が返ると説明している。この扱いは予定DELETEだけに限定する。

## 検証

- 基準コミット8924734d。通常イメージaws-pre-f97c7809へ変更対象のソース・テストと隔離設定を読み込んで実施。
- Python 3.11、使い捨てメモリSQLite、Docker network none、Google通信はモック。実Google・共有DBへの変更なし。
- 修正前はTimeout後の410で再試行例外となることを確認（5テスト中1エラー）。
- 修正後は同じ外部IDへの2回のDELETEで終了、同期エラー消去・同期日時保存・ジョブ成功を確認。
- 401/403/429/500は成功とせず、同期記録・ジョブがFAILEDになることを4サブテストで確認。
- Calendar配送、Googleジョブ認可、外部連携、非同期ジョブの37テスト成功。Black/isort/flake8と差分検査成功。追加のユーザー表示文言なし。

実行対象: `schedules.test_google_calendar_delivery tests.integration.test_google_job_authorization schedules.test_external_integrations schedules.test_async_jobs`。

## 状態と残条件

前回の文書更新8924734dは[main CI](https://github.com/sheepdog0820/iaia/actions/runs/34457381157)・[作業ブランチCI](https://github.com/sheepdog0820/iaia/actions/runs/34457372933)ともcompleted/successを2026-09-12にAPIで確認した。今回の取消修正のCIとは別の結果である。

今回の修正は作業ブランチで検証し、mainマージ・AWS反映は未実施。DB移行、データ一括変更、権限、Secrets、費用への変更なし。コードを戻す場合は旧来の410失敗が再発する。

実Googleの配送試験、取消後のセッション再開、並行処理を含む全ライフサイクルは未完了。正式公開とI04全体をこの試験だけで合格としない。Stripeはユーザー指定で保留を継続する。
