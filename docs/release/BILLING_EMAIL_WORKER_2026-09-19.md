# 配布イメージの課金メール定期配送・worker再起動試験

候補 `6ff9a1f9b9fe965b2461de0694530d3e18ffda96` の通常配布イメージ `tableno:stripe-candidate-6ff9a1f9`（ID `sha256:5e8f4f132ae472f0bd2a5d64c7019e501aab0303bfecfa9860f1769a64e7f702`）で、実Celery beat・Redis 7・worker・PostgreSQL 18.3・隔離SMTP受信器を接続した。[結果JSON](BILLING_EMAIL_WORKER_2026-09-19.json)の5項目が成功。

## 試験条件

Dockerの専用internalネットワークを使用し、ホストへのポート公開や外部SMTPへの通信は行わない。合成利用者1人と請求失敗・監査・配送待ち各1件を作成した。宛先は `billing-worker@example.test` のみで、受信器もこの宛先を検査した。実利用者・共有DB・Stripe APIは使用していない。

アプリソースは差し替えず、専用設定モジュールでSMTP接続先と送信元を隔離先にした。既存の毎分beatスケジュールとDBの再試行時刻は変更しない。workerは実Celeryのsolo/concurrency=1。AWS予定構成や複数workerの性能を再現するものではない。

## 観測結果

1. beatが配送タスクを発行し、workerが受信。SMTP受信器が最初のDATAを451で拒否すると、attempts=1、pending、transport_error、60秒後のnext_attempt_atがDBに保存された。
2. workerを停止・削除しても配送記録は同一だった。別コンテナでworkerを起動し直した。
3. 保存した期限到来後、beat経由で再送され、attempts=2、sent、監査のemail_sent=trueとなった。手動で期限を前倒ししたり配送関数を直接呼び出したりしていない。
4. 送信後、追加のタスクをRedis経由で発行して処理完了を待っても、SMTPへの到達は2回（拒否1・受理1）、DB試行回数は2のままだった。
5. 19:32:00 JSTの定期処理はnext_attempt_atの約0.1秒前に走ったため送信せず、次の19:33:00に受理された。再試行間隔60秒は最短の待ち時間であり、毎分の巡回待ちが加わる。負荷・停止時にはさらに遅れるため60秒以内の配送保証とはしない。

初回の試験は期待するエラー分類をnot_acceptedとして失敗した。実装は明示的に作成したSMTP接続の例外をtransport_errorとして保持し、ログで451拒否とpendingを確認できた。試験側の期待値をこの経路に合わせ、使い捨てDBから全工程を再実行して成功した。アプリ実装の修正は不要だった。

## 証拠・限界・後片付け

再現スクリプトはGit管理外の `C:/Users/endke/Workspace/iaia/tmp/billing_worker_probe_20260919.py`。結果と各コンテナログは `C:/Users/endke/Workspace/iaia/tmp/billing-worker-proof-20260919/`。試験後、専用5コンテナ・匿名ボリューム・内部ネットワークの削除と不在を確認した。

これはローカルでの実タスク配送とworker再起動の検証である。実AWSのネットワーク/IAM、SMTP認証・TLS、実受信箱への到達、複数worker、SMTP受理直後の異常終了、Redis/DBの障害復旧、監視通知は未検証。SMTP受理とDB更新の間で停止すると重複する可能性は残る。既存の[配送実装記録](BILLING_EMAIL_DELIVERY_2026-09-19.md)と併せて扱う。

main・AWS・Secrets・常設リソース・実メールを変更していない。課金公開とメール配送の実環境有効化は、接続・費用・宛先の承認後に検証する。正式公開No-Goは維持する。
