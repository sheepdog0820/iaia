# 開発AWSの依存・構築セキュリティ更新案

## 判断する範囲

正式公開はNo-Goを維持する。これは公開承認ではなく、現在稼働している機能を保ったまま、依存関係・ベースイメージ・ビルド除外を更新する限定した開発環境反映案。mainへの追加マージとaws-pre反映は未承認・未実施であり、以下の事前条件を満たしてから明示承認の範囲で実行する。

旧 `fec10aa0` / タスク定義49の反映案は使わない。今回は現行AWS `c6226ddb` からDBマイグレーション、アプリのPythonソース、templates、static、entrypointの差分がない。共有DBの0065〜0067適用状況は未確認のままであり、今回の更新で適用・修復したとは扱わない。

## 固定候補と検証

| 項目 | 証拠・限界 |
| --- | --- |
| 対象アプリSHA | `0bfd3503e137dea54bb2e5c06e2d80c5b7321d87`、`codex/runtime-security-20261002` にpush済み |
| mainとの差 | main `35ecfd5c` から6コミット。現行AWSに既にあるシナリオ画像関連2件と、本タスクの確認記録・依存修正・構築修正・キャッシュ除外を含む。原worktreeの未コミットHO作業は含まない |
| 固定checkout | `git archive` から `C:/tmp/iaia-release-0bfd3503` へ展開。ローカル未追跡ファイルを入力にしない |
| ローカルイメージ | `tableno:release-0bfd3503`、ID `sha256:177817c6a1dec7428b318a0ca35fb523963cfe1bf035e02395460f15d12d8ea3`。revision labelは対象SHA。ECR未push |
| ソース一致 | アプリ・画面・静的資産等581ファイルをarchiveと実イメージのSHA-256で照合。欠落0・不一致0、Pythonキャッシュ0件 |
| 実依存 | oauthlib 4.0.0、PyJWT 2.15.1、urllib3 2.8.0を実イメージで確認。変更理由とロック監査は[依存更新記録](DEPENDENCY_SECURITY_2026-10-02.md) |
| 通常起動 | 外部通信不可のinternal network、公開ポートなし。使い捨てPostgreSQL 18.3/Redis 7、aws-pre設定、通常entrypointで空DB移行・静的228件/620後処理・Daphne起動成功 |
| readiness / 設定 | TLS終端後を模した `X-Forwarded-Proto: https` 付き内部HTTPで200、DB/cacheともok。`migrate --check` / `check --deploy` は終了0。ヘッダーなしの初回試行はHTTPSへリダイレクトされ、平文ポートへのTLS接続エラー。設定を弱めず正しいプロキシ条件で再確認した |
| 実イメージ回帰 | 認証・Google連携・Calendar/Sheets配送・画像共有・JWT等146件が隔離PGで成功、43.683秒、省略0。実OAuth/外部配送ではなく、外部API応答はmock |
| CI | [対象SHAのrun 37014059175](https://github.com/sheepdog0820/iaia/actions/runs/37014059175)。確認時点でproduction-database/lint-security/system/infrastructure成功、Unit/IntegrationとPlaywrightは実行中。全体成功を事前条件として残す |
| 全パッケージ監査 | 固定イメージの初回はcache-in-use timeoutで終了1。専用キャッシュとNO_CACHEによる再試行は268パッケージを検査、SARIF生成完了。16パッケージ・39指摘（HIGH 3 / MEDIUM 2 / LOW 34、全件Debian、Python/CRITICALは0）。今回のCLIは `--exit-code` なしで終了0だが、脆弱性の合格を意味しない。キャッシュ内の一時archive削除警告は残る |

試験用Web/PG/Redisの3コンテナとinternal networkは専用ラベル・イメージ・ポート公開なしを確認して停止・削除し、不在を確認した。DB/Redisのtmpfsデータは破棄。固定archive、配布イメージ、監査資料は保持し、実ユーザーデータは使っていない。

固定イメージの監査レポートは `C:/tmp/runtime-os-release-0bfd3503-retry-20261002.sarif.json`、SHA-256は `22c541de88658da9d64aa5b0166154fc9dfcf974feb0977af7dd6a7b6910dcf2`。同一依存構成の[先行監査記録](RUNTIME_SECURITY_2026-10-02.md)とSARIF内容も一致したが、今回は固定イメージを改めて検査した結果である。

HIGHはgcc-14由来の `CVE-2026-102010` / `CVE-2026-95619` とzlibの `CVE-2026-85091`。今回の監査でも修正版なし。指摘を抑制・受容済みとせず、限定開発反映の判断材料にする。現行稼働digestの監査は71件（CRITICAL 1 / HIGH 12 / MEDIUM 15 / LOW 43）であり、単純な旧版切戻しはセキュリティ上の解決ではない。

## 22:38〜22:42 JSTの読み取り確認

- AWSアカウント `083773015316`、`ap-northeast-1`、profile `tableno-pre` を照合。
- ECS `tableno-aws-pre` は定義52、desired/running/pending=1/1/0、rollout COMPLETED、実行タスクHEALTHY。
- 稼働タグ `aws-pre-c6226ddb` のECRと実行タスクは、ともに `sha256:bc951b76e612706ff8b50b590ea6add774d710fb8d8db05247f8c304b7e762b2`。
- Webは0.25 vCPU / 512 MiB。`RUN_MIGRATIONS=false` / `RUN_COLLECTSTATIC=false` / `STRIPE_CHECKOUT_ENABLED=False`。課金メールの実効値は未確認で、Secrets値は読んでいない。
- `stg.tableno.jp/health/ready/` はstatus/database/cacheともok、応答日時は22:38:51 JST。
- RDSはavailable、バックアップ保持7日、LatestRestorableTimeは22:34:06 JST。このメタデータは復元試験成功を示さない。
- GitHub mainは `35ecfd5c9b91cd0f6d5836660bbdac380afeb7e2`。既に承認され実施した9月25日のマージを取り消さず、今回の追加分とは区別する。

## 承認後の実行範囲と停止条件

1. 対象SHAのCI全6項目、固定イメージの監査完了・指摘一覧、main/稼働版が変わっていないことを再確認する。候補または稼働版が変わった場合は差分を見直す。CI失敗、監査未完了、未知の差分では反映しない。
2. 残るOS指摘を明示した限定開発反映と、mainへの追加マージが承認されてから実行する。新しい候補を黙って承認対象に含めない。通常マージ・pushのみで、force pushやユーザー変更の破棄をしない。mainのCI成功も確認する。
3. 上記の検証済みイメージをECR `tableno:aws-pre-0bfd3503` にpushし、実際に返されたregistry digestを記録する。ローカルimage IDとregistry digestを混同しない。承認後に別内容を再ビルドして置き換えない。
4. 実行直前のECS稼働タスク定義を基に、Webのイメージ参照だけを検証済みECR digestへ変更した新リビジョンを登録する。IAM、Secrets参照、環境変数、CPU/メモリ、台数、ネットワークは維持する。
5. **今回、migrate・collectstatic・CloudFront invalidationは実行しない。** 現行AWSとの差分にDB/静的変更がないため。起動時の自動実行もfalseを維持する。想定外の必要性が判明した場合は追加影響を確認して停止する。
6. Webサービスを新リビジョンへ更新し、安定化・実行digest・readiness・エラーログを確認。既存認証セッションでログイン状態・画像ギャラリー等の表示を確認する。実OAuthの取消/失効、購入、メール/外部通知、実データの書換え・削除はこの案に含めない。実画面確認ができない場合は未検証として残す。

一時的なECSタスク重複、ECR保存、通信・ログの従量費用は発生し得るが、常設容量やリソースは増やさない。従量費用ゼロや金額上限の保証ではない。常設worker/beat/Redis、Web増量、Secrets/OAuth/IAM変更、課金有効化、正式公開は別途判断が必要。

## 復旧と残る公開条件

稼働変更直前のタスク定義を復旧先として記録する。今回の確認時点では定義52。新Webが安定しない、認証に回帰がある等の場合はその定義へ戻し、digest/readiness/表示を再確認する。DBとS3を変更しないので逆移行や静的世代復元は行わない。旧版の既知脆弱性は再導入されるため、復旧をセキュリティ合格とはせず、影響箇所の利用制限か前進修正を判断する。

本反映が成功しても、[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は未達のまま。特に共有DB適用証拠、AWSでのStripeテスト購入・メール/worker運用、実Google/Discord/X/ICS/CCFOLIA、実AWS性能、DB/S3整合復旧、グループ所有権引継ぎの範囲、保存方針・事業者窓口の運用が残る。mockやreadinessで代替しない。
