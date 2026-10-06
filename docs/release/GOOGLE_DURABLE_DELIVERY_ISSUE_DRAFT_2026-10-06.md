# GitHub Issue下書き: Googleジョブの永続配送と結果不明の安全な回復

2026-10-06の新Issue作成はintegrationの403（Resource not accessible by integration）で失敗、CLIは未認証。**Issueは未作成**。既存open #1のキャラクターUIとは別課題であり、認証/権限変更は行っていない。次回の書き込みは利用可能な正規の権限を確認してから行い、未確認のIssue番号を割り当てない。

## 目的

Google Calendar/Sheetsを正式公開できる品質にするため、DB確定とCelery投入の隙間、再配送、結果不明、同期対象の世代競合を解消する。部分修正・ローカル成功のみで完了にしない。

## 現在の部分実装と証拠

- アプリ28ac2bc7は応答喪失/408/5xx/不正ACK/部分Sheets後続拒否を結果不明へ分類し、自動再適用を抑止。親CI全6成功。
- [通常28ac実worker](GOOGLE_WRITE_RUNTIME_2026-10-06.md): 回帰284成功、実PG/Redis/Celery/Requestsの28ケース（結果不明22/成功6）、追加28重複配送のHTTP0を確認。実Google/AWSではない。
- [今回のDB確定後投入](GOOGLE_DISPATCH_COMMIT_2026-10-06.md): commit待機/rollback破棄、PG265成功/省略0、SQLite256成功/PG専用9省略、製品差分34文20経路100%。callbackはメモリ内であり、durable outboxは未実装。

## 完成の受け入れ条件

- [ ] jobと配送意図を同じDB transactionで永続化し、commit直後のproducer停止でも回復可能にする。Sheets内容binding、所有者・接続世代・privacyを維持する。行データの保存/暗号化/期限/ログ扱いを明文化し、既存payloadへの非公開平文の追加で済ませない。
- [ ] 独立relayのclaim/期限/再試行/失われたpublish応答を検証する。running/succeeded/uncertain/失効/削除済みjobを自動再送せず、実workerの重複受信でも外部HTTPを再適用しない。
- [ ] 旧メッセージ・旧FAILED job・新しい別job/同期対象世代をfenceし、同一予定/Sheets領域の競合を安全に扱う。
- [ ] Google側結果照合と限定回復を設計・実装・検証する。結果不明を成功/失敗と推測せず、保存期限処理だけで痕跡を消さない。
- [ ] 通常配布物・実Redis/別worker/独立producer/プロセス停止/再起動のfault試験で上記を証明する。
- [ ] 承認済み範囲で実Google OAuth更新/失効/連携設定変更を検証し、常設worker/監視の運用証拠を揃える。

## 承認境界と公開判断

main/AWS/共有DB/migration適用/Secrets/IAM/費用/実ユーザー変更・通知は別の具体案と承認が必要。この下書きは実行承認を拡張しない。OS HIGH3、実外部連携、課金、性能、復旧等の不足も残るため正式公開No-Goを維持する。
