# 承認済みRDSスナップショット復元試験

2026-09-08、ユーザーが[復元試験案](RDS_RESTORE_APPROVAL_2026-09-08.md)を承認し、指定スナップショットを別の非公開RDSへ復元した。検査コンテナは終了0、ログの `read_only=true` を確認。これは限定したDB復元試験の成功であり、正式公開・サービス全体の復旧完了ではない。

## 実行対象と結果

- AWSアカウント083773015316、東京。元DBは `tableno-aws-pre`、指定snapshotは `rds:tableno-aws-pre-2026-09-07-16-06`。PostgreSQL 18.3、暗号化20GB。
- 復元先は `tableno-restore-drill-20260908`。db.t4g.micro、Single-AZ 1c、gp2、非公開、専用SG。自動minor更新なし、拡張監視間隔0、Performance Insights無効。元DB・既存SG・Secretsは変更していない。
- 検査イメージは承認済み46530ebc。専用ECRタグ `restore-probe-bfe1ce1c` のdigestは `sha256:efb73e776c3d7cf066f4af9ff0d65175fe62d41a5c07312d69be9cc7b50c141e`。
- 専用タスク定義 `tableno-restore-drill-20260908:1`、タスクID `46e18b0daa0d405faef56ca8ea4b1c66`。CPU256/512MiB、UID10001、root filesystem read only、capabilities ALL drop。task roleなし、既存execution roleとDB_PASSWORDの既存Secret参照1件を使用。
- 通常entrypointを迂回し、120秒制限の検証コマンドだけを実行。アプリ配備・DB移行・メール・Stripe・S3操作を起動しない。
- 復元開始20:15:36 JST、AWSの復元イベント20:18:26、検査タスク作成20:21:31、コンテナ開始20:22:02、停止20:22:29、削除要求20:23:10。待機を含め2時間の計画内で検査を終了した。

## 照合した範囲

CloudWatch `/ecs/tableno-aws-pre` の `restore-drill-20260908/probe/46e18b0daa0d405faef56ca8ea4b1c66` からJSONを取得し、終了0と合わせて照合した。

- PostgreSQL major 18、read_only=true。
- accountsは0063まで、schedulesは0054まで。accounts/0064・schedules/0055は未適用。
- キャラクター登録表の列はaccess_scope、created_at、edition、id、share_token、updated_at、user_id。
- ロールの一意制約はidとparticipant_id。複数ロール0件、重複ロール組0件。
- 復元検査だけで付加するserver_majorを除いたレポートは、[本日12:44の元DB検査](DATABASE_PREFLIGHT_2026-09-06.md)の保存結果と一致した。全テーブルのデータ内容や件数を比較した結果ではない。

ローカル証跡はGit管理外の `tmp/rds-restore-approval-20260908/`。承認済みtemplateのSHA-256を実行前に照合し、作成応答・タスク状態・ログを保存した。接続設定を含む生JSONは公開文書へコピーしない。

## 後片付けと既存環境

20:25:34 JSTに後片付けを完了した。作成応答のID・ARNと専用タグを照合して、停止済みタスクの定義をINACTIVEへ変更し、専用DBを最終snapshotなし・自動バックアップ削除付きで削除。ENIがなくなったことを確認してSG間の参照を解除し、専用SG2件を削除した。専用ECRタグだけを削除し、元イメージや他タグは削除対象にしなかった。

最終の読み取り確認では専用DB・自動バックアップ・SGが存在せず、専用タグの照会はImageNotFoundException。元DBはavailable、既存サービスはタスク定義40・desired/running=1/1、20:25:59のreadinessはDB/cacheともokだった。復元開始から後片付け完了までは約10分。共有アプリ・元DB移行・S3ポリシーは未変更。

## 限界と残作業

S3ファイルの復元、全テーブル・画像参照の照合、復元後のアプリ起動、同時書き込み中の整合性は今回の承認範囲に含まない。約7分でDB検査を終えたことを、[RTO4時間・RPO24時間](RELEASE_CRITERIA_DECISIONS_2026-09-08.md)のサービス全体の達成証拠にはしない。実画像との整合、切り替え、主要操作、監視まで含む復旧検証が残る。

費用は承認案の1 USD以内を目標に、検査終了後ただちに後片付けを開始した。実請求額は未確定であり、予算目安を確定請求額として報告しない。
