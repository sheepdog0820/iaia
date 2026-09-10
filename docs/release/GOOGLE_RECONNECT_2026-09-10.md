# Google再連携の実環境確認

2026-09-10、利用を承認されたChromeの既存Googleアカウントを使い、開発環境 `stg.tableno.jp` の再連携を実施した。

## 確認できたこと

- 連携設定の「未連携」からGoogle認可画面へ進み、既存アカウントの認可を完了した。
- コールバック後、連携設定が「連携済み」に変わり、再読み込み後も維持された。
- Calendar events、Sheets、プロフィール、メール、openidの既存権限が表示された。新しい権限の追加はない。
- カレンダー同期・スプレッドシート出力の設定は両方OFFを維持した。イベント作成、シートへの書き込み、既存データの変更は行っていない。

トークン・認可コード・ICS購読URLは証跡に含めない。Google認可画面には未確認アプリの案内があり、正式公開に向けたGoogle側の審査・公開設定の確認は残る。再連携成功はトークン更新や実際の同期の成功を意味しない。

## 同期処理の残条件

AWSの読み取り調査で、稼働中のECSサービスはWebのみであることを確認した。worker/beatのタスク定義は存在するがサービスは稼働しておらず、WebのCeleryブローカー設定もない。現在の状態では通常の非同期Google同期を実行できない。Webのヘルスチェックのcache成功は、処理待ち行列の稼働確認ではない。

後続作業は、ブローカーとworkerの構成・通信経路・継続費用を確定し、承認後に起動すること。beatはハンドアウト公開や期限切れ処理も動かすため、既存データへの影響を別途確認する。TerraformのRedis有効化はWebセッション保存方式も切り替えるため、そのまま適用しない。

Google Calendarの現行実装はprimaryカレンダーへ書き込む。実試験では対象と削除範囲を限定したテストイベントを準備する。Sheetsも専用試験先と対象キャラクターを限定する。既存データ全件の出力で代用しない。

## 費用の予備調査（未承認・未作成）

東京リージョン、730時間/月、Linux Fargateの0.25 vCPU・0.5 GiBタスクを前提とする。AWS公開価格表のCPU $0.05056/vCPU時、メモリ $0.00553/GiB時、Redis cache.t4g.micro $0.025/時、公開IPv4 $0.005/時から計算した。

| 仮構成 | 月額概算 |
| --- | ---: |
| worker 1台 + Redis 1台 + 公開IPv4 1個 | $33.15 |
| workerとbeat各1台 + Redis 1台 + 公開IPv4 2個 | $48.04 |

税・ログ・通信・CPUクレジット等を含まない追加費用の概算で、正式構成の見積もりではない。既存ネットワークとの適合、エンジンバージョン、スケジュール処理の影響、復旧手順を詰めてから承認を求める。新規リソース作成や継続費用の追加は未実施。

価格出典: [Fargate](https://aws.amazon.com/fargate/pricing/)、[東京ECS価格表](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/ap-northeast-1/index.json)、[東京ElastiCache価格表](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonElastiCache/current/ap-northeast-1/index.json)、[公開IPv4](https://aws.amazon.com/vpc/pricing/)。2026-09-10確認。
