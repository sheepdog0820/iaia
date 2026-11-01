# 所有権状態を含む合成DB・メディア復元（2026-11-01）

main `72ad82999739747ba16cf6ad8fda84a0a8bee3fa`と同じtreeの通常配布物を使い、0069追加後のDBとメディアを、隔離ローカルの別DB・別ディレクトリへ復元した。合成データの照合と権限検査は成功した。正式公開はNo-Goのままで、実RDS/S3復旧や承認済みRPO24h/RTO4hの合格ではない。

## 固定対象と実行範囲

- imageのrevisionは`dac04381efe03341055c4ffac2472792af2e15ac`、image IDは`sha256:ddb493e310c75d7b93b1f9312b87e00d99d1801e12b1784c13ba640fbda9fb8f`。mainとのtree一致は`26a59c5dc82ec5d8abec8e48a0da80b686e3f5bd`で確認した。imageをmainのSHAへ付け替えたものではない。
- 通常imageのアプリソースは上書きせず、検査payloadとローカル用設定だけを別パスへmountした。production設定のmiddleware・認証・権限を使い、DB、media、メール、brokerは使い捨てのローカル用へ設定した。
- PostgreSQL18.3、外部通信不可のinternal network、公開ポートなし、tmpfsのPGデータを使用した。DB接続は初期化用管理ロール・非TLSであり、本番の最小権限/TLS検証ではない。
- すべて合成データ。実DB・S3・Stripe・外部通知への操作、AWS資源の作成や費用変更はない。

## 手順と結果

1. 空の合成source DBを最新移行まで作成し、全11ファイル項目と、所有権の申請中・移譲済み・期限切れを作った。
2. `pg_dump --format=custom --no-owner --no-acl`とmedia archiveを取得し、別DBへ`pg_restore --exit-on-error --single-transaction`した。media未復元の状態では検査が失敗することを確認してから、別ディレクトリへ内容とパスを復元した。
3. 全テーブルの行内容ハッシュ・行数、シーケンスの値とis_called、制約定義と遅延設定、全ファイル参照・内容ハッシュを照合し、画像もデコード検査した。
4. 破損、所有権API、メディア権限を検査し、`migrate --check`とDjango system checkも成功した。
5. 応答で取得した同じIDのコンテナとnetworkを削除し、不在を再確認した。合成認証情報を含むenvファイルも削除した。

| 対象 | 結果 |
| --- | --- |
| 全テーブル | 95テーブル・664行、一致 |
| シーケンス | 91件、一致。復元後の追加IDも継続 |
| DB制約 | 1,149件の定義・遅延設定が一致 |
| ファイル項目・参照・実ファイル | 各11件、一致 |
| 所有権 | 19検査成功 |
| メディア権限 | 76検査、期待HTTPステータス・該当する本文/ZIP・非公開cache headerが一致 |
| 欠落・破損の検出 | media未復元1件と、追加の意図的な改変5件をすべて検出 |
| 後片付け | コンテナ・internal network・合成envファイルの不在を確認 |

所有権検査は、申請の所有者/対象者への表示、他adminからの秘匿、権限外の承諾/取消拒否、期限切れ拒否、復元後の承諾/辞退/取消、新旧所有者のadmin維持、所有者の退出拒否、元作成者の退出・削除後のグループ保持、所有者membership保護を確認した。直接の不正UPDATEでowner非NULL、申請者と対象者の相違、期限、グループごとの申請一意性、対象者FKの5制約も検査した。変更を伴う各検査はrollback後に全体一致を再確認した。

メディア権限は、秘匿HO添付、セッション/シナリオ画像、6版/7版の画像ZIP、問い合わせ添付、背景透過の状態・raw取得を対象に、所有者・割当先・一般メンバー・無関係・無効・匿名・権限付きstaff等の該当する組合せを検査した。Django APIClientを使った検査で、実HTTP/TLS配送の証明ではない。

追加の改変5件は、media破損、一般行の変更、移譲済みownerの変更、申請中レコードの削除、シーケンス値の変更である。改変を取り消した後の一致も確認した。集約記録とpayload・dump等のSHA256は[証跡JSON](RESTORE_OWNERSHIP_MAIN72_2026-11-01.json)に記録した。行データ、画像、認証情報、dump本体はコミットしていない。

## 先行試行の失敗と限界

先行試行は所有権検査途中のDB接続切断で未完了だった。独立検査helperが、APIClientにより既に閉じられた非streaming responseをrollback用transaction内で再度closeし、request_finishedが再発火した。helperの重複closeだけを除き、新しい使い捨てDBで全工程を再実行した。製品コードは変更していない。先行試行の失敗と後片付けの記録も保持し、集約JSONにhashを残した。

このfixtureは小さく、一部のアプリテーブルは空である。全テーブル一致は全業務状態の網羅を意味しない。ローカルファイルの内容/パスのみを復元し、Unix所有権・mode・時刻は復元していない。実S3世代・delete marker・DBとの時点整合、同時更新、RDS snapshot/PITR、ALB/CDN/browser配送、worker・課金/外部連携、アプリ切替は未検証である。ローカル検査の所要時間をRPO/RTO達成と扱わない。

共有DB適用前には[DB/メディア復旧の受け入れ条件](DB_MEDIA_RESTORE_ACCEPTANCE.md)に従い、全writer停止・直前backup・選択世代・切替先・失敗/結果不明時の復旧を具体化する。0069適用後の単純なコードrevertや旧taskへの差戻しを復旧策としない。固定対象のAWSコピー内5移行リハーサルについても、既存承認待ちの範囲を拡張・代用しない。
