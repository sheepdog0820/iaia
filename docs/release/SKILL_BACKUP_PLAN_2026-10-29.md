# 0068前の非公開バックアップ・復元確認案（2026-10-29）

ユーザーの「未定なのでバックアップ案を作成」に基づく実行前の案。バックアップ作成・実データ複製・AWS変更・費用発生の承認ではなく、いずれも未実施である。

## 対象と取得方法

対象はアカウント083773015316・東京リージョンの共有開発RDS `tableno-aws-pre`だけ。本番は含めない。06:34 JSTの読み取りではPostgreSQL18.3・db.t4g.micro・20GB gp2・Single-AZ・非公開・暗号化済み・自動バックアップ7日だった。夜間停止によりRDSはstopped、Webはdesired/running=0。停止中にsnapshotは作成せず、通常起動後にavailableを再確認する。予定外の早期起動を含めない。

旧`bonus_points`と`other_points`の分割を含むDBインスタンス全体を、同じAWSアカウント・リージョン・既存KMSキーで暗号化された手動RDS snapshotとして保管する。S3やローカル端末へ実データを持ち出さず、snapshot共有属性は空のままとする。ID案は`tableno-aws-pre-pre0068-20261029-a`で、実際の作成応答のARN・時刻・元DB ARN・専用タグを記録する。同名があれば上書きせず、対象を再確認する。

[AWS公式](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CreateSnapshot.html)によると、Single-AZのsnapshot取得は数秒〜数分のI/O停止を伴う場合がある。手動snapshotは自動バックアップの7日保持では失効しない。保管は取得から7日を案とし、確認後の対象snapshot削除を承認範囲へ含める。移行が未実施・復元確認が不合格などで保存継続が必要な場合は、削除せず延長と費用を確認する。定期自動削除は設定しない。

## 別DBでの復元確認

復元先案は`tableno-restore-drill-0068-20261029-a`。元snapshotのARNを固定し、同じVPC/subnet group内へdb.t4g.micro・20GB gp2・Single-AZ・非公開の専用RDSを新設する。元DBへの上書きやアプリのDB接続先変更を行わない。[復元は既存DBへの上書きではなく新しいDBインスタンスを作成する操作](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_RestoreFromSnapshot.html)である。

専用SGをprobe用と復元DB用の2件作成し、probeから復元DBの5432だけを許可する。probeには必要なDNSとECR/Secrets/CloudWatchへの443送信を設定し、公開受信は開けない。既存のDB/Web用SG・IAM・Secretsは変更しない。既存execution roleでDB_PASSWORDだけを注入し、Stripe/Google等のSecretは渡さない。

既存ECRへ専用タグ`pre0068-probe-20261029-a`の検証イメージを一時送信し、専用Fargateタスク定義`tableno-restore-drill-0068-probe-20261029-a`を登録、0.25vCPU/512MiB・単発15分以内を案として起動する。アプリやworkerを起動せず、最小Django設定の読み取り専用probeだけを動かす。接続先の期待ホスト/DB名・元DBとの不一致・PostgreSQL18・TLSを確認し、DBが強制するREAD ONLYで履歴・制約・両版の旧ポイント集計を検査する。実データや認証情報をログへ出さない。既存execution roleをイメージ取得・Secret注入・ログ送信に再利用し、コンテナ自体にはAWS task roleを付けない。ECS Execも無効とする。

この段階はsnapshotの復元経路と0068前のデータを確認するための限定した試験であり、S3画像・全テーブルの完全一致・本番切替・RPO24h/RTO4hの達成を証明しない。snapshot取得後も利用者更新が続けば、そのsnapshotは後日の移行直前バックアップとは扱えない。実0068適用時には、全書き込み経路の停止・その時点の新しいsnapshot・復元可能性・固定した移行対象を別途確認する。

## 費用案

10月29日06:31〜06:38 JSTのAWS Price Listと公式料金資料で確認。無料枠・圧縮・レイヤー共有による値引きを使わず、1か月30日として計算する。USD・税別で、実請求の強制上限ではない。

| 項目 | 計算・仮定 | 概算USD |
| --- | --- | ---: |
| snapshot保管7日 | 20GB × 0.095 USD/GB月 × 7/30 | 0.443 |
| 復元RDS 2時間 | db.t4g.micro 0.025 USD/時 × 2 | 0.050 |
| 復元DB gp2容量 | 20GB × 0.138 USD/GB月 × 2/720 | 0.008 |
| CPUクレジット追加枠 | 2vCPU × 2時間 × 0.075 USD/vCPU時 | 0.300 |
| 単発Fargate 15分 | 0.25vCPU・0.5GiB、東京の単価 | 0.004 |
| public IPv4 15分 | 0.005 USD/時 × 0.25 | 0.001 |
| 専用ECR保管 | 3GBを丸1か月保管する高めの仮定 | 0.300 |
| ログ・API・短時間の追加backup等 | 小口の予備 | 0.020 |
| 税・余裕前の合計 | | 約1.13 |

税・遅延等の予備を含む承認予算案は**2 USD**。復元DBは2時間以内、probeは15分以内を運用目標とし、超過見込みでは新規処理を止め、作成済み専用リソースの削除を優先する。AWSが作成・削除待ちの場合は時間/費用が超える可能性があり、残存を報告する。snapshotやECR保管は、DBを停止しても課金が続く。

単価の確認元: [RDS PostgreSQL](https://aws.amazon.com/rds/postgresql/pricing/)、[Fargate](https://aws.amazon.com/fargate/pricing/)、[ECR](https://aws.amazon.com/ecr/pricing/)。Price Listの識別子はbackup 8EP35HPTSYF38J3V、RDS実稼働YXENKSJFV9BXQF4N、gp2 CAAHKCKRFNCCWMR5、FargateCPU KBQ3Q6DY9J327G8N/Memory JQEE6EF5FAF2AESH、IPv4 ZP85FQT9FHKJRAG5。unused capacity reservationの別SKUは実稼働見積もりに使わない。

## 復旧・後片付けと承認範囲

失敗時に元DBや既存サービスを変更して復旧しない。probe停止・専用タスク定義登録解除・専用復元DBとその自動backup削除・ENI解放確認・専用SG2件削除・専用ECRタグ削除の順で片付ける。新設DBの削除は最終snapshotなしで行い、元snapshotを保持する。7日後のsnapshot削除は作成応答のARN・専用タグ・確認結果を照合して対象1件だけに行う。名前の接頭辞だけで削除対象を決めない。

実行承認で必要なのは、対象snapshot作成と7日保管/条件付き削除、実データを持つ復元DBの新設/削除、専用SG2件の新設/設定/削除、一時ECR送信/専用タグ削除、タスク定義登録/解除、単発タスク起動/停止、2 USDの予算案である。共有0068の適用・Web反映・本番公開・実Stripe操作はこの承認に含めない。

## 承認提示までの残準備

19操作のJSONテンプレートをGit管理外`tmp/0068-backup-approval-20261029/operations.template.json`へ保存した。SHA-256は`f742e71faa7064be95a76bcf3af291abb4543148138e4bdbcf8562db8178dd75`。ネットワークなしのbotocore1.43.80で全入力schemaの検査が成功し、AWSリクエストは0件である。実権限・起動・接続の成功を保証する検査ではない。

テンプレートのSG ID・復元endpoint・タスク定義ARN・task ARNは、承認後の作成応答と専用タグ/アカウント/リージョンを照合して置換する。ECR digestも、承認対象のローカルimage ID・revisionを確認して一時送信した結果だけを使う。既定のSG送信規則が想定と違えば停止して再確認する。既存リソースを代わりに指定しない。

今回CIで検出したAutobahn CVE-2026-116579は26.10.1への更新後、3ロックと通常配布物の実インストールの監査が既知0件となった。OS50指摘とTwisted RC2は残る。probeに使う統合候補の最終イメージ/ソース・CIを固定し、応答由来の値だけを置換する検査と実行時間帯を確定する。通常起動完了後の利用者が少ない時間帯を提案し、取得前後のreadiness確認とI/O停止時の連絡手順も具体化してから、実行可否を確認する。現時点は案作成と読み取り調査までで、AWS作成・実データ複製・DB移行は未実施である。
