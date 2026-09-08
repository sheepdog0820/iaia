# 実RDS復元試験の読み取り調査

後続更新: PG18の隔離復旧と本番設定起動は完了。[実行構成案](RDS_RESTORE_EXECUTION_DRAFT_2026-09-08.md)に専用SG2件・最小Secretsの単発タスク・削除範囲・CPUクレジット込みの小計約0.363 USDを整理した。probe/JSON/残費用の検証が残り、実行承認は未依頼。

2026-09-08、tableno-preプロファイルでdescribe-db-instances、describe-db-snapshots、describe-security-groups、Pricing GetProductsのみを実行した。新規リソース、DB接続、Secrets取得、権限変更は行っていない。

## 実環境との相違

共有RDS tableno-aws-preはPostgreSQL **18.3**、db.t4g.micro、Single-AZ、20GB gp2、暗号化あり、非公開、available。パラメーターはdefault.postgres18、オプションはdefault:postgres-18でin-sync。既存の隔離復旧記録はPostgreSQL 16.15であり、実RDSと同一メジャーバージョンでの互換性検証を完了した証拠にはならない。次に18系の使い捨てDBで候補を検証する。

最新スナップショットは `rds:tableno-aws-pre-2026-09-07-16-06`、作成UTC 2026-09-07T16:06:15.724000、18.3、暗号化済み、20GB、available。実行時は状態を再取得して対象を固定する。現行DBや画像と同じ時点のデータだとは扱わない。

現在のDB用セキュリティグループは、ECS側の1グループからTCP 5432を許可し、IPアドレスからの許可はなく、送信ルールは空。既存グループを復元先へそのまま使うと通常ECSからも到達し得るので、復元先の隔離が自動的に達成されるわけではない。

## 基本費用の根拠

AWS Price List APIの東京/PostgreSQL/Single-AZで照合したOnDemand単価（有効日2026-09-01）:

| 項目 | SKU | 単価 |
| --- | --- | --- |
| db.t4g.micro | YXENKSJFV9BXQF4N | 0.025 USD/時間 |
| gp2 | CAAHKCKRFNCCWMR5 | 0.138 USD/GB月 |

2時間ならインスタンス0.05 USD、20GBのストレージは730時間/月による概算で約0.0076 USD、合計約0.058 USD。これは基本2項目だけの試算であり、CPUクレジット、検証ECS、通信、ログ、バックアップ残存、税、削除遅延を含む総額上限ではない。停止してもストレージ料金は残るため、試験終了時は専用復元先の削除まで確認する。実請求額は未確認。

## 実行案を確定するための残作業

1. PostgreSQL 18系で隔離復旧・必要なアプリ検証を行い、16系との差を確認する。
2. 一意な専用DB名、同じサブネット、暗号化、非公開、最小到達範囲を決める。専用SGが必要なら作成・規則・削除を承認対象に含める。
3. 復元先だけを参照する検証タスクを用意し、外部通知/課金/worker/beatを起動しないことを確認する。元DBや元Secretsの更新は行わない。
4. 全体費用の試算、2時間等の試験期限、途中失敗時の削除手順と残存確認を揃える。ユーザーの1 USD以内の許可を、未積算の総額や未特定の権限変更へ拡張しない。
5. DB内容を会話に出さず件数・整合性・移行履歴を検証する範囲を定める。画像の特定世代とDBの対応が未確定なら、DB単独の復元試験として記録する。
6. 削除は復元先IDと所有タグを照合し、検証タスク停止後、試験用DBを最終snapshotを作らず削除する案とする。元DB・元snapshot・既存SGは削除対象に含めない。作成・削除の範囲をまとめて明示してから実行する。

[AWSの復元仕様](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_RestoreFromSnapshot.html)では復元は新しいDBインスタンスを作成する。パラメーターやネットワーク設定を省略すると既定構成になり得るため明示する。available直後にも遅延ロードが続く場合があり、availableだけを性能・復旧完了の判定にしない。[料金の取扱い](https://aws.amazon.com/rds/postgresql/pricing/)も最終見積時に確認する。

現段階は事前調査であり、実RDS復元・実データ複製の実施結果でも、その実行承認の依頼でもない。具体案が揃うまで読み取りと隔離された合成データ検証を進める。
