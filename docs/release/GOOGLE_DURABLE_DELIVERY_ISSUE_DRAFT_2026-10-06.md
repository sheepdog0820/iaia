# GitHub Issue下書き: Googleジョブの永続配送と結果不明の安全な回復

2026-10-06の新Issue作成はintegrationの403（Resource not accessible by integration）で失敗、CLIは未認証。**Issueは未作成**。既存open #1のキャラクターUIとは別課題であり、認証/権限変更は行っていない。次回の書き込みは利用可能な正規の権限を確認してから行い、未確認のIssue番号を割り当てない。

## 目的

Google Calendar/Sheetsを正式公開できる品質にするため、DB確定とCelery投入の隙間、再配送、結果不明、同期対象の世代競合を解消する。部分修正・ローカル成功のみで完了にしない。

## 現在の部分実装と証拠

- 最新の[2261adf7通常配布物・実プロセス回復](GOOGLE_DURABLE_RUNTIME_2026-10-06.md): 選定713 source/assets・111 packages/先行依存10層一致、通常回帰Google251/設定70の非重複321成功。実PG/Redis/Requests・solo/prefork×Calendar/Sheetsの16ケースでproducer commit後停止、relay停止の実5分期限、未消費message消失、制御されたACK喪失から同じjobを回復。期限内relay4回拒否・重複16配送の追加HTTP0・暗号文消去を確認した。候補CI全6成功。新規Scout HIGH3含む39/終了2は未合格。自分の83 container/tmpfsを撤去・証拠保持、main/AWS/共有DB/Secrets/課金/容量変更なし。自動常設回復/世代fence/結果照合/限定回復/実Google等は残る。

- アプリ28ac2bc7は応答喪失/408/5xx/不正ACK/部分Sheets後続拒否を結果不明へ分類し、自動再適用を抑止。親CI全6成功。
- [通常28ac実worker](GOOGLE_WRITE_RUNTIME_2026-10-06.md): 回帰284成功、実PG/Redis/Celery/Requestsの28ケース（結果不明22/成功6）、追加28重複配送のHTTP0を確認。実Google/AWSではない。
- [先行DB確定後投入](GOOGLE_DISPATCH_COMMIT_2026-10-06.md): commit待機/rollback破棄、PG265成功/省略0、SQLite256成功/PG専用9省略、製品差分34文20経路100%。その時点のcallbackはメモリ内でありoutboxなし。親62573a06のCI全6成功を後続で確認した。
- [未開始ジョブの永続配送](GOOGLE_DURABLE_DISPATCH_2026-10-06.md): jobとAES-GCM暗号化配送意図の原子的保存、5分claim/上限付きrelay、投入ACK後も開始まで保持、開始receiptと暗号文消去の同時確定を実装。最終PG290成功/省略0、SQLite280成功/PG専用10省略、read-onlyソースbindのLinux設定70成功。新migration0057/0058は隔離DBのみ。通常新配布物・実Redis/独立workerのproducer停止/再起動は未検証、旧FAILEDと新job/同期対象世代fence・結果照合・限定回復は未実装。共有運用・Issue全体完了とは扱わない。

## 完成の受け入れ条件

- [ ] jobと配送意図を同じDB transactionで永続化し、commit直後のproducer停止でも回復可能にする。暗号化・内容binding・同時保存・callback喪失・通常配布物の実producer停止/独立relay回復はローカル検証済み。鍵ローテーション・共有運用時消去・バックアップprivacyの証拠は残る。
- [ ] 独立relayのclaim/期限/再試行/失われたpublish応答を検証する。PG独立connection・実5分期限、実別relay/Redis/worker・メッセージ消失・制御されたACK喪失・実worker重複受信は新候補で確認済み。取消競合・常設監視/beat・実共有運用は残る。
- [ ] 旧メッセージ・旧FAILED job・新しい別job/同期対象世代をfenceし、同一予定/Sheets領域の競合を安全に扱う。
- [ ] Google側結果照合と限定回復を設計・実装・検証する。結果不明を成功/失敗と推測せず、保存期限処理だけで痕跡を消さない。
- [ ] 通常配布物・実Redis/別worker/独立producer/プロセス停止/再起動のfault試験で上記を証明する。
- [ ] 承認済み範囲で実Google OAuth更新/失効/連携設定変更を検証し、常設worker/監視の運用証拠を揃える。

## 承認境界と公開判断

main/AWS/共有DB/migration適用/Secrets/IAM/費用/実ユーザー変更・通知は別の具体案と承認が必要。この下書きは実行承認を拡張しない。OS HIGH3、実外部連携、課金、性能、復旧等の不足も残るため正式公開No-Goを維持する。
