# RDS復元試験の構成案

2026-09-08の読み取り結果に基づく実行準備案。実行承認の取得やリソース作成はまだ行っていない。[事前調査](RDS_RESTORE_PREFLIGHT_2026-09-08.md)に不足していたネットワークとタスクの分離方法を具体化する。合成データでの[PG18復旧](RESTORE_POSTGRES18_2026-09-08.md)と[候補46530ebcの本番設定起動](RUNTIME_CANDIDATE_46530EBC_2026-09-08.md)は成功している。

## 再確認した環境

profile tableno-pre、アカウント083773015316、東京。元DB tableno-aws-preはavailable・PostgreSQL 18.3・20GB、AZはap-northeast-1c。ECSサービスは定義40、desired/running=1/1を維持。今回も読み取りのみで変更していない。

- VPC: vpc-0959fc3a14ff33c30。DB subnet group: tableno-aws-pre。
- DB側のprivate subnet: subnet-0fe17aa76679aedf6（1a）、subnet-0b7a2475d54f2617f（1c）。
- ECS側のpublic subnet: subnet-05f2ce33f5bdc0eb1（1a）、subnet-0dfe8174130e4ab82（1c）。既存タスクはpublic IPを使用。
- このVPCのVPC endpointは0件。現構成のまま、インターネット向け通信を全遮断した新タスクでECR取得・Secrets注入・CloudWatch Logs配送ができるとは扱わない。

## 作成・変更・削除の対象案

試験識別子は `tableno-restore-drill-20260908`。実施日が変わる場合は新識別子を提示し、既存名との衝突検査を行う。名前だけで所有リソースとは判定せず、作成応答のIDと専用タグを記録する。

| 対象 | 操作案 |
| --- | --- |
| 復元DB | 上記識別子でsnapshotから1台作成。db.t4g.micro、Single-AZ、20GB gp2、非公開、元DBと同じ暗号化・subnet group、AZ 1c。既存DBを上書きしない |
| 専用DB SG | 受信TCP5432は専用検証タスクSGだけ。送信の既定allow-allは削除。既存DB SG・ECS SGは変更しない |
| 専用検証タスクSG | 受信なし。送信は復元DB SGの5432と、タスク準備・ログ配送用443。既定allow-allは削除。通常アプリが使うSGを付けない |
| 検証タスク定義 | 専用family、CPU256/メモリ512。既存execution roleを使用し、task roleは付けない。healthCheck・portMappingsなし。Pythonの読み取り専用probeを直接実行し、entrypointのmigrate/collectstatic/web/worker/beatを起動しない |
| Secrets | 既存DB_PASSWORD参照1件だけを注入。OAuth・Stripe・メール等のSecretsを複製しない。既存Secrets自体を更新しない |
| 接続設定 | DB_USER/DB_NAME/DB_PORTは既存定義と照合。DB_HOSTは復元APIで得た専用endpointを固定し、元DB endpointとの不一致を確認。既存環境設定を丸ごとコピーしない |
| ECS実行 | 同じclusterの単発タスク1件、public subnet 1c、public IPあり。サービス・ALBには登録しない。自動再試行なし |
| 終了 | 専用タスクSTOPPED、定義登録解除、専用DB削除（最終snapshotなし・専用自動バックアップも削除）、専用SG2件削除を確認。元DB・元snapshot・既存SG・サービスは削除対象外 |

443を許すため「ネットワークだけで全外部送信を防ぐ」設計ではない。アプリを起動せず、task role・外部サービスのSecretsを渡さず、監査したprobeだけを実行する制限と組み合わせる。より強い通信先制限にはVPC endpoint等の追加構成が必要であり、今回の少額単発案に無断で追加しない。

## 検査内容と終了条件

1. 実行直前にsnapshotのavailable・元DB・エンジン・暗号化・作成時刻を照合し、使用snapshot ARNを固定する。現在の元DBとsnapshotの件数が一致することは要求しない。
2. probe起動時に接続先を承認済み復元endpointと照合。元endpoint、別DB、空値なら接続前に失敗する。接続・statement・lock timeoutとプロセス制限を設定する。
3. SQLトランザクションをread onlyにし、その実効値とPostgreSQL 18系を確認。DB名・移行履歴・対象テーブルと制約の存在・件数だけを検査する。利用者名、メール、トークン、本文、接続情報、例外全文をログに出さない。
4. この段階では復元DBにも移行やデータ修正をしない。スキーマ・読み取り成功は検証できるが、画像整合性・実データの全内容一致・アプリ配備後の復旧・RPO/RTO達成の証拠とは区別する。
5. probeは120秒、タスクは起動待ち込み15分、試験全体は作成開始から2時間で打ち切り・後片付けへ進む。RDS availableだけを検査成功にしない。途中失敗でも専用リソースの残存と削除結果を報告する。

## 費用の概算

Fargateの東京Linux/x86単価をPrice List APIのusage typeで再取得した。CPUは0.05056 USD/vCPU時（SKU KBQ3Q6DY9J327G8N）、メモリは0.00553 USD/GB時（JQEE6EF5FAF2AESH）、有効日2026-07-01。最初の地域指定の100件には対象がなく、usage typeをFargateに絞って確認した。

| 仮定 | 概算USD |
| --- | ---: |
| RDS基本2時間＋20GB gp2 | 0.0576 |
| CPUクレジットの保守的な追加枠：2vCPU×2時間×0.075 | 0.3000 |
| Fargate 0.25vCPU/0.5GB×15分 | 0.0039 |
| タスクのpublic IPv4×15分 | 0.0013 |
| 小計 | 約0.363 |

[RDS公式料金](https://aws.amazon.com/rds/postgresql/pricing/)のT4g Unlimitedクレジット単価0.075 USD/vCPU時と、[VPC公式料金](https://aws.amazon.com/vpc/pricing/)のIPv4 0.005 USD/時を使用。CPU追加枠は観測した使用料ではなく高めの仮定。[Fargate料金](https://aws.amazon.com/fargate/pricing/)の最低課金・イメージ取得時間も考慮し、タスク稼働は15分で見積もる。

ログ・Secrets取得・同一AZ/リージョン通信・税・削除遅延は小計に未算入。イメージは既存の監査済みECRイメージをdigest固定して再利用する案で、新規保管費用を前提にしない。1 USDの予算案には余裕があるが、AWSの削除遅延時を含む課金の強制上限ではない。RDS停止だけではストレージ料金が残る。新規SG/復元DB/タスクの作成・削除と実データ複製は、既存の「1 USD以内」の許可だけで実行しない。

## 承認依頼までに仕上げるもの

- probeの実コード、接続先・read-only・秘匿ログの否定テストと合成PG18での成功結果。
- 再利用ECRのdigest、最小タスク定義のJSON、復元/SG/cleanupコマンドの正確な差分。実行前に対象IDと所有タグが一致しない場合は停止する検査。
- 検証ログを少量に限定する設定、追加費用の残項目、全体の停止・削除手順のレビュー。

以上が揃ってから、具体的な実データ複製・一時権限・作成削除・費用の範囲をまとめて承認依頼する。現段階で実行許可は求めず、無承認で実行もしない。
