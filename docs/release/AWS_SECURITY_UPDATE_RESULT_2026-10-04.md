# 開発AWSの依存・構築セキュリティ更新記録

## 承認・固定対象

10月4日にユーザーから「反映案を承認します」と明示承認を得た。[承認した反映案](https://github.com/sheepdog0820/iaia/blob/3ff3e1cdbcf08e0f93cd57e71c960f3244e99dca/docs/release/AWS_SECURITY_UPDATE_APPROVAL_2026-10-02.md)の対象はアプリ `0bfd3503e137dea54bb2e5c06e2d80c5b7321d87`。DB変更・課金有効化・常設容量増加を含まないWebイメージ更新として実行する。

| 対象 | 結果 |
| --- | --- |
| mainマージ | `9ae40362783456956675e74f2ebf67666fe58028` を通常マージ・push済み。マージtreeは承認候補0bfd3503と一致、競合なし |
| 候補CI | [run 37014059175](https://github.com/sheepdog0820/iaia/actions/runs/37014059175)、全6項目成功 |
| main CI | [Django CI run 37173486193](https://github.com/sheepdog0820/iaia/actions/runs/37173486193)、12:32 JSTまでに全6項目success、head/main一致を確認 |
| 検証済みローカルimage ID | `sha256:177817c6a1dec7428b318a0ca35fb523963cfe1bf035e02395460f15d12d8ea3`、revision labelは0bfd3503 |
| ECRタグ | `083773015316.dkr.ecr.ap-northeast-1.amazonaws.com/tableno:aws-pre-0bfd3503`、push完了 |
| ECR digest | `sha256:d9bd92ffec87642aeb1ae429623e9a3c762db9567b756f95151bef72c4ec056f`。manifest内config digestが検証済みローカルimage IDと一致 |
| Web反映 | 12:33 JSTに定義53を登録してサービス更新。12:36:02 JSTにrollout COMPLETED、desired/running/pending=1/1/0、実行タスクHEALTHY、実行digestがECR digestと一致 |

## 反映前の確認

- 12:13 JSTにprofile `tableno-pre` のAWSアカウント `083773015316` を照合。地域は `ap-northeast-1`。
- ECS `tableno-aws-pre` は定義52、desired/running/pending=1/1/0、rollout COMPLETED。readinessはstatus/database/cacheともok。
- 稼働イメージは `aws-pre-c6226ddb`。CPU 256 / memory 512、Web1タスク。
- 新設定の事前比較で、変更項目は `web.image` だけ。環境変数52件・Secrets参照19件・IAM・ネットワーク・容量を維持する。
- `RUN_MIGRATIONS=false` / `RUN_COLLECTSTATIC=false` / `STRIPE_CHECKOUT_ENABLED=False` を維持する。DB/静的資産の差分がないため、migrate・collectstatic・CloudFront invalidationは実行しない。
- WindowsのAWS CLI出力を既定の文字コードでJSON解析した最初の試行は、日本語を含む環境変数で解析失敗。プロセス内のUTF-8出力設定で読み取りが成功した。登録時は構造化された設定を保持し、日本語を変換・置換しない。
- 既存画像ギャラリーJSのCDN応答はHTTP 200。ソース差分にこの資産の変更はない。
- 接続できたChromeはログイン画面へ遷移し、既存の認証セッションは利用できなかった。認証済みの画面操作は未検証として残す。

## 反映後の確認

- 12:36:44 JSTに定義53の単一デプロイ・1タスクHEALTHY・実行digest一致を再確認。新旧定義を構造化比較し、Web image以外の設定とタスクのタグが一致した。ネットワーク・desiredCountも更新前後で一致。
- 12:36:43 JSTの公開readinessはHTTP 200、status/database/cacheともok、errors空配列。ALBは新ターゲットhealthy、旧ターゲットdrainingだった。旧ターゲットの接続ドレイン完了とアプリのrollout完了は別の状態として扱う。
- 新タスクの起動から確認時点までのCloudWatchログ24件で、Traceback/ERROR/CRITICAL/Exceptionの文字列検出は0、起動マーカー3。移行適用・静的収集の実行マーカーも0。観測したログ範囲の結果であり、全操作でエラーがない証明ではない。
- 反映後にChromeのログイン画面を再読み込みし、日本語フォームとGoogle/Discord/Xの入口表示を確認。console error/warnは0件。ログイン・実OAuth・画像ギャラリー操作は行っておらず、認証回帰の一貫試験は未検証。
- 既存画像ギャラリーJSのCloudFront応答はHTTP 200、3,843 bytes。今回の差分にはstatic/templatesの変更がないため、migrate・collectstatic・CloudFront invalidationは実行していない。
- CI全6項目successの監視結果を取得後、追加のGitHub API再照合はHTTP 403（rate limit exceeded）となった。この試行ではAWS変更前に停止し、既に取得した同一run/SHAの完了結果と`git ls-remote`によるmain一致を根拠に反映した。APIエラーをCI失敗・成功として扱っていない。
- 購入開始は無効のまま。DBデータ、Secrets値・参照、IAM、OAuth権限、常設容量を変更していない。課金メールの実効値は未確認のままで、今回の反映で無効を実証したとは扱わない。外部メール/通知も送信していない。

## 復旧・公開条件

実行直前のタスク定義52を復旧先に記録した。今回は起動・安定化・readinessが成功し、切戻しは実施していない。問題が判明した場合は既存サービスを`tableno-aws-pre:52`へ更新し、旧digest `sha256:bc951b76e612706ff8b50b590ea6add774d710fb8d8db05247f8c304b7e762b2`、ヘルス、表示を再確認する。DB/S3を変更していないため逆移行や静的世代復元は不要。旧版には既知の脆弱性が残るため、切戻しをセキュリティ上の合格とは扱わない。

固定配布物の事前検証は581ファイル一致、隔離PG146テスト成功、通常起動・移行・静的収集・readiness成功。全パッケージ監査は39件（HIGH 3 / MEDIUM 2 / LOW 34、Python 0）で、適用除外や正式公開のリスク受容はしていない。今回の承認は限定した開発AWS反映への承認であり、[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)の合格を意味しない。

共有DBの0065〜0067適用証拠、常設worker・メール・AWSのStripe一連動作、実外部連携、実AWSの性能、DB/S3整合復旧、事業者窓口・保存方針等は引き続き未完了。
