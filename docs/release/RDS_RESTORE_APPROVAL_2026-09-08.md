# 実RDS復元試験の承認対象

2026-09-08にユーザーが本案を明示承認し、指定対象で実行した。検査は終了0、read_only=true、一時リソースの後片付けも完了。[実施結果と検証の限界](RDS_RESTORE_RESULT_2026-09-08.md)を参照。以下は承認時の実行案であり、「未実施」「承認依頼」はその時点の記録。

対象はaws-preのsnapshotを別DBへ復元する単発検査。mainマージ・アプリ配備・元DB移行・Stripe再開の承認とは別。以下の一時作成・権限設定・実データ複製・削除をまとめて承認依頼する。現在は準備のみで、AWS変更は未実施。

## 対象と手順

アカウント083773015316、東京、profile tableno-pre。元DB tableno-aws-preは変更しない。使用snapshotは `rds:tableno-aws-pre-2026-09-07-16-06`（2026-09-07 16:06:15 UTC、18.3、暗号化20GB、available再確認済み）。異なるsnapshotへ自動的に切り替えない。

1. ローカル `tableno-formal-release:46530ebc`（ID `sha256:1148c15382dd48b333f0976efe70aff65cf5ae20d81c072019ccb1a7d3ad8072`）を既存ECR tablenoの専用タグ `restore-probe-bfe1ce1c` に送信。取得したdigestをタスクに固定。既存タグを上書きしない。
2. 専用SG `tableno-restore-drill-20260908-task` と `tableno-restore-drill-20260908-db` を作成。既定の送信allow-allを除去し、taskからDBへ5432、taskから起動・ログ用443、DB受信はtaskだけとする。既存SGは変更しない。現VPCにIPv6関連付けはなく、同名SGも未作成と確認。
3. snapshotを `tableno-restore-drill-20260908` へ復元。db.t4g.micro、Single-AZ 1c、20GB gp2、非公開、暗号化、同じDB subnet group、専用DB SG。parameter/option groupを明示し、試験中の自動minor更新を無効にする。元DBの保存データを一時的に複製する操作である。
4. available後、応答のARN・endpoint・エンジン18.3・暗号化・20GB・専用SG・非公開・タグを確認。endpointを最小タスク定義に固定し、元DBと異なることを確認。余分な設定差分や未置換のplaceholderがあれば登録/実行しない。
5. 専用familyに検証タスク定義を登録。既存execution roleのみ、task roleなし。DB_PASSWORDの既存Secrets参照1件だけを注入。既存execution roleの同Secretに対するGetSecretValue許可を確認済みで、新しいIAM policyやSecrets更新は計画しない。
6. 既存clusterでFargate 1.4.0、CPU256/メモリ512、public subnet 1c・専用task SG・public IPの単発タスク1件を起動。サービス/ALBに登録せず、web/worker/beatやDB移行を起動しない。UID10001、root filesystem read only、capabilitiesはALL drop、ポート公開なし。
7. 120秒制限のPython probeで読み取り専用の移行履歴・スキーマ・ロール件数を検査。利用者名・本文・メール・接続情報・秘密値は出力しない。成功JSONと終了0を両方確認し、部分結果を合格にしない。

## 制限時間と後片付け

タスクはイメージ取得待ち込み15分、試験全体は復元開始から2時間で打ち切り・後片付けへ移る。自動再試行や2台目の作成はしない。AWS側がcreating等で削除を受け付けない場合は、状態を確認して削除可能になり次第削除し、超過と残存を報告する。課金を必ず2時間で止められる仕組みではない。

停止/削除前に作成応答のID・ARN・専用タグを照合する。名前の接頭辞だけで削除しない。専用タスクSTOPPED→専用定義登録解除→専用DB削除（最終snapshotなし、専用自動バックアップも削除）→ENI解放確認→専用SG間の相互参照解除→SG2件削除→専用ECRタグ削除の順。ECRは専用タグだけを指定し、他タグや共有レイヤーを対象にしない。

元DB・元snapshot・既存SG・既存ECSサービス・元Secretsは復旧/削除対象外。試験用DBのエラーを理由にこれらを変更しない。ログは既存 `/ecs/tableno-aws-pre` の専用prefixを使用し、既存の3日保持を維持する。後片付けの失敗は残リソースと次の削除操作を明示する。

## 検証済みの材料

- [probe検証](RDS_RESTORE_PROBE_2026-09-08.md): 単体8件、新規46行/12分岐100%。合成PG18 TLS接続・書き込み拒否・認証例外の秘匿を確認。
- 同じ検証をUID10001・root filesystem read only・ALL capabilities dropで追加実行し、成功。合成DB/証明書だけを使い、専用コンテナ/networkは削除済み。
- [候補46530ebc](RUNTIME_CANDIDATE_46530EBC_2026-09-08.md)のアプリCI5ジョブと本番設定起動は成功。probeが再利用する既存コマンドのSHA-256は `c86e5a315bf362f3dabc87de6d9ecfe61743ca0b77f6c584daa9a8f7f7e4bfe9` で、イメージとbfe1ce1cのソースが一致。
- 既存ECRの6イメージについて、タグが示す6コミットのソースに検査コマンドがないことを確認。各イメージの全内容を再取得した検査ではないが、検証済みの再利用候補として採用できないため、前案の「既存イメージの無変更再利用」から一時送信へ変更。ECRはAES256・BASIC scan・replication rulesなしと確認。リージョンをまたぐ自動複製は計画しない。
- 最小タスク定義と16件のEC2/RDS/ECS/ECR操作payloadがbotocoreの入力schemaを通過。これはAWSの実行許可や実起動の成功を保証する検査ではない。

具体的JSONはGit管理外の `tmp/rds-restore-approval-20260908` に保存。task-definition.template.jsonのSHA-256は `63984f4730635b60c273e6ef82e6cdea81b09ec0215933fae6520c6c4add297f`、operations.template.jsonは `0196708eb1df3e4c45d3df7eedb94758b231b54c4a2b723580c63a650f5f069d`。埋め込んだprobe本文はbfe1ce1cと一致し、SHA-256 `ad2e2884f3455335557fa91ec3b455536405c12940a2cab6b291ccedf70777ad`。

placeholderは専用SGの作成応答、復元endpoint、送信image digest、登録定義ARN、起動task ARNだけで置換する。最終JSONで置換残り0・同じ安全設定・SDK形式・元リソース不一致を再確認する。SG送信の既定規則が想定と異なる場合は実際の規則を読み取り、専用SGの既定規則だけを除去する。候補や保護条件が変わる場合は、その差分を先に報告する。

## 費用

[構成案の基礎見積もり](RDS_RESTORE_EXECUTION_DRAFT_2026-09-08.md)約0.363 USDに追加項目を積算した。

| 項目 | 見積もりの仮定 | USD |
| --- | --- | ---: |
| RDS・CPUクレジット・Fargate・IPv4 | DB2時間、タスク15分、2vCPUのクレジット追加枠 | 0.363 |
| 専用ECR保管 | 非圧縮ローカル全容量1.289GBを丸1か月保存する高めの仮定 | 0.129 |
| DB追加バックアップ | 無料枠なしで20GBを2時間 | 0.006 |
| ログ・API等の小口枠 | 結果ログ1MB以内、単発Secrets取得と少数の照会 | 0.002 |
| 合計（税・予備費前） | | 約0.50 |

[ECR料金](https://aws.amazon.com/ecr/pricing/)は0.10 USD/GB月、同一リージョンのFargateへの転送は無料。実際は圧縮・レイヤー共有・試験後のタグ削除で変わる。[CloudWatch](https://aws.amazon.com/cloudwatch/pricing/)の東京ログ取り込みはPrice List APIで0.76 USD/GB（SKU CWB2GTZJXNX3TA6H）、RDS追加バックアップは0.095 USD/GB月（8EP35HPTSYF38J3V）を確認。既存Secretの保存期間・個数は増やさず、[Secrets Manager](https://aws.amazon.com/secrets-manager/pricing/)のAPI取得分だけが追加候補。

税・小口費用の予備を含む目安は約0.60 USD、承認予算案は1 USD。実請求額やAWS遅延時の強制上限を保証するものではない。1 USDを超える見込みが判明したら新しい作業を止め、既に作った専用リソースの削除を優先して報告する。

## 判断してほしい範囲

上記のECR一時送信、SG2件、snapshotの実データ複製、単発タスク、試験後の一時リソース削除を、1 USD予算案で実行してよいか。AGENTS.mdの「AWSリソースの作成・削除」「実ユーザーデータの変更・削除」「権限」「費用」の境界に該当する。既存の少額検証許可を、新しいSGと実データ複製への包括承認とは扱わない。元DBの読み取り検査の再承認を求めているわけではない。
