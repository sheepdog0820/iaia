# 一覧APIの構成別性能測定

測定日: 2026-09-08。対象コミット: `bca01195512dcfe81fb7003dfc4cd458b26799b4`。
Dockerイメージ: `tableno-formal-release:bca01195`、ID `sha256:896157a016396eacc5f408da6aefac140cf07a1a2214c6eddc21f53fdf9b39ca`。

## 結果

4構成それぞれ180リクエスト、合計720リクエストがHTTP 200。別途ウォームアップ36件もHTTP 200。同時アクセス時は小さいCPU構成ほど遅延する傾向が見られたが、各構成1回の測定であり、最適構成や本番の性能保証は未確定。

以下はp95（ミリ秒）。同時数は3種類のAPIを混在させた負荷全体の上限であり、各APIに同時10件ずつではない。

| アプリ構成 | 同時数 | キャラクター | シナリオ | セッション |
| --- | ---: | ---: | ---: | ---: |
| 0.25 CPU / 512 MiB | 1 | 480.9 | 172.8 | 576.2 |
| 0.25 CPU / 512 MiB | 10 | 6990.4 | 2804.5 | 3314.1 |
| 0.5 CPU / 1 GiB | 1 | 229.1 | 78.3 | 274.4 |
| 0.5 CPU / 1 GiB | 10 | 3058.9 | 1608.4 | 1476.8 |
| 1 CPU / 2 GiB | 1 | 129.3 | 46.9 | 174.1 |
| 1 CPU / 2 GiB | 10 | 1713.7 | 728.2 | 938.7 |
| 1 CPU / 512 MiB（診断用） | 1 | 139.4 | 55.0 | 157.0 |
| 1 CPU / 512 MiB（診断用） | 10 | 725.7 | 611.4 | 1948.3 |

1 CPU / 512 MiBはCPUの影響を調べるためのローカル診断用であり、Fargateには配備できない。1 CPU / 2 GiBと比べてもAPIごとの結果が一様ではなく、単発の数値を容量選定の確証にはしない。

## 実行条件と証跡

- ローカルDockerの内部ネットワーク。各構成は順番に実行し、毎回空のPostgreSQL 18.3（2 CPU / 1 GiB）とRedis 7（128 MiB）を用意した。実ユーザーデータは使用していない。
- クリーンなGitアーカイブから通常の本番Dockerfileでビルド。`APP_ENV=aws-prod`の通常entrypointで移行・静的収集・Daphne起動を実行。ローカルHTTP試験のためHTTPSリダイレクトは無効で、TLSや本番配備設定の合格証拠ではない。
- 合成データは10ユーザー、10グループ、1,000キャラクター（6版/7版各500）、100セッション、100シナリオ。先頭ユーザーのGETはキャラクター100件、セッション20件、シナリオ30件を返すことを別途確認。
- 負荷生成はアプリとは別のCPU制限なしコンテナ。既存の `tests/performance/read_load.py` を使用し、各API30件、同時数1と10、タイムアウト10秒。ウォームアップは各API3件で、10認証情報のうち先頭3ユーザーのみを使用。
- GET対象は `/api/accounts/character-sheets/`、`/api/scenarios/scenarios/`、`/api/schedules/sessions/?period=all`。パーセンタイルはnearest-rank。エラーを含む全リクエストが計測対象で、今回エラーは0。
- ローカル証跡は `tmp/performance-bca01195{,-half,-standard,-cpu1}/` の `run.py`、`seed.py`、`warmup.log`、`concurrency-1.log`、`concurrency-10.log`。認証情報を含む使い捨てenvはGitに含めない。
- 1 CPU / 2 GiBの測定後、同じデータで先頭ユーザーをAPIClientから取得しSQL回数を観測。キャラクター10、シナリオ4、セッション7、同一SQLの最大反復はいずれも1。これは当該データの観測であり、あらゆるデータでN+1がない証明ではない。
- 試験用コンテナとネットワークは所有ラベルを照合して削除。ローカルイメージと証跡ファイルは残している。

## CIと残条件

対象コミットの[PR CI](https://github.com/sheepdog0820/iaia/actions/runs/34201320678)と[push CI](https://github.com/sheepdog0820/iaia/actions/runs/34201317700)はいずれもUnit / Integration、system、lint-security、playwright、production-databaseの全5ジョブsuccessを確認した。

正式な想定負荷・p95等の合格値は未確定のため、性能判定は `not_evaluated` を維持する。次は合格値とデータ規模を確定し、反復測定・長時間負荷・実配備でのDB/ネットワーク/メモリを含む検証が必要。CPU増強だけで解決とせず、必要に応じてアプリ側の処理時間も追跡する。

AWSの容量や継続費用は変更していない。構成変更を提案する場合は、[Fargateの組み合わせ制約](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html)と料金を改めて照合し、月額増分を提示して承認を得る。共有DB・Secrets・権限・課金への変更はない。このコミットは文書のみで、取り消してもアプリ動作は変わらない。

Stripeは[再開タスク](STRIPE_CONNECTION_PENDING.md)のまま保留。実RDS復元、共有環境への反映、実サービス連携、OS監査の未解決条件などが残り、正式公開は未完了。
