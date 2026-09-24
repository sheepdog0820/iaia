# 開発AWSの課金・外部連携バックグラウンド処理の反映準備

## 現状の再確認

2026-09-19 17:13 JST頃、AWS CLIの読み取りで東京・アカウント083773015316の状態を確認した。ECS `tableno-aws-pre` のサービスはWebの1つのみで、希望1・稼働1・待機0、定義49の展開はCOMPLETED。実行中タスクも1つ。イメージdigestは `sha256:59542e45e5dc8e1e33cbf7202eb12911ffbb390156a778fe7eb11f0fe4c65f79` で、ECRタグ `aws-pre-d875d028` と一致した。readinessはDB・cacheともok。

購入設定はFalse、RUN_MIGRATIONSとRedis cache・LINE Celery設定もfalse。常設worker/beatはない。StripeとメールのSecret名はタスクに参照されているが、今回その値や有効性を調べたものではない。定義にメール配送有効化設定やCelery broker設定はない。9/10の一時worker/Redis試験は後片付け済みで、常設処理の稼働証明にはならない。

したがって、現在の開発AWSはStripe候補4d5a43ecの反映先としてまだ準備が必要であり、最新機能が稼働しているとは言えない。今回、AWSの変更・Secrets読み出し・DB接続やマイグレーション・外部通知は行っていない。

## 夜間運用の修正

既存のTerraformではWebとRDSのみが夜間停止対象だった。worker/beatを有効にすると、DB停止中もバックグラウンド処理が残る。既存の時間帯を維持して次を追加した。

| 対象 | 停止 | 再開 |
| --- | --- | --- |
| beat（定期処理の投入） | 01:57 | 08:02 |
| worker（処理実行） | 02:00 | 08:00 |
| Web（既存） | 02:00 | 08:00 |
| RDS（既存） | 02:05 | 07:30 |

既定タイムゾーンはAsia/Tokyo。停止・開始は希望台数の変更指示であり、指定時刻の完了を保証しない。起動完了、長時間タスクの終了、キューの復旧はAWS上の追加検証が必要。公開本番は夜間停止を前提にしない。

有効化されたサービスにのみスケジュールと限定したUpdateService権限を作る。worker/beatが無効なら従来の6スケジュールだけ、夜間停止自体が無効ならスケジュールを作らない。再開台数は設定値を使用し、明示的な0も維持する。実AWSのIAMやスケジュールは変更していない。

Terraformのmock providerによる9シナリオが成功し、validate/fmtも成功。最初に不足する停止・再開設定をテストで再現した。Windowsのfilter指定では0件となったため成功証拠にせず、フィルターなしで9件の実行を確認した。これは実インフラのapplyや稼働試験ではない。

## 追加費用の試算

2026-09-19、AWS Price List APIをus-east-1から読み取り、regionCode=ap-northeast-1、Linux/x86のオンデマンド単価を確認した。既存Web/DBとは別の増分。

| 項目 | 単価・構成 | 24時間稼働/月730時間 | 約18時間/日稼働 |
| --- | --- | ---: | ---: |
| worker | 0.5vCPU・1GiB | $22.49 | $16.87 |
| beat | 0.25vCPU・0.5GiB | $11.25 | $8.43 |
| public IPv4 | 各1個、$0.005/時間 | $7.30 | $5.48 |
| Redis | cache.t4g.micro 1ノード、$0.025/時間、常時稼働 | $18.25 | $18.25 |
| 合計 | ログ・通信・税等を除く | **$59.29/月** | **$49.03/月** |

Fargate CPUは$0.05056/vCPU時間（SKU KBQ3Q6DY9J327G8N）、メモリは$0.00553/GiB時間（JQEE6EF5FAF2AESH）。Redis標準ノード料金はMHCMQGJMFWFSRS2P。延長サポート料金のSKUとは区別した。IPv4はZP85FQT9FHKJRAG5。Fargateの価格公開日は2026-09-11、Redisは9/14、IPv4は9/17。夜間停止の数分差・起動/停止所要時間を丸めた概算であり請求上限ではない。

出典: [Fargate料金](https://aws.amazon.com/fargate/pricing/)、[ElastiCache料金](https://aws.amazon.com/elasticache/pricing/)、[VPC料金](https://aws.amazon.com/vpc/pricing/)。通信、CloudWatch、デプロイ中の重複タスク、メール、バックアップ、延長サポート等で変動する。NAT Gatewayは追加しない構成を想定した。無料枠・割引・為替は織り込んでいない。

## 反映前に揃える事項

Stripe候補のCI完了、共有DBへ0065～0067を適用する具体的な計画、常設Redis/worker/beatの作成差分、SG/IAM/Secrets・broker設定の変更範囲、既存環境とのTerraform差分照合が必要。現時点は実環境向けのapply計画ではなく、増設を無断で実行してよい状態ではない。

費用が既存の「1米ドル以内の試験」の許可範囲を超える継続費用であるため、常設構成の作成前に承認が必要。Stripe本番課金・実メール送信はこの構成検討に含めない。既存Webの通常反映と、基盤増設・権限変更・DB適用は対象を明示して扱う。

切戻しは新しいworker/beatの台数0・新規スケジュール無効化・Web定義49への復帰を基本とする。キューと未配送メールを確認するまではRedisや0067テーブルを削除しない。旧Webへ戻してもDBの追加テーブルは保持する。今回のTerraform変更だけを戻す場合はコードrevertであり、AWSには未適用なので実環境の復旧操作は不要。正式公開判定はNo-Goを維持する。
