# 正式公開に向けたaws-pre検証・配備準備

2026-09-05、コード候補 `f0f443f0`。実行承認前の準備資料。以下の調査では読み取りだけを行い、ECS起動・配備・DB変更・通知は実行していない。

## 確認できた現状

- AWS profile `tableno-pre`、region `ap-northeast-1`、cluster/service `tableno-aws-pre`。
- ECS desired/runningは **1/1**、PRIMARY deploymentはCOMPLETED、task definitionは `tableno-aws-pre:40`。前回の0/0から変化している。このタスクは起動していないため、検証後に勝手に0へ戻さない。
- 配備イメージは `tableno:aws-pre-8cf3c7f7`。CPU 256（0.25 vCPU）、memory 512MiB、コンテナ名はweb。
- `https://stg.tableno.jp/health/ready/` は200、database/cacheともok。公開可能な機能・最新コード・課金の正常性までは証明しない。
- task definitionの平文設定でAPP_ENV=aws-pre、DB_ENGINE=postgresを確認。秘密情報の値は取得していない。Checkout、起動時migrate、開発ユーザー作成等の実効設定は平文設定の不在だけでfalseと断定しない。
- ECS Execは無効。ローリング更新はminimumHealthyPercent=100、maximumPercent=200で、一時的に2タスクとなり得る。deployment circuit breaker/自動rollbackは無効。これらを変更する場合はイメージ更新と別の差分として提示する。

## 稼働版と候補の差分

比較はローカルmainとの比較だけでなく **`8cf3c7f7..f0f443f0`** を用いる。差分は104ファイルで、依存ロック、Dockerfile、背景除去、画面、静的ファイル、設定、DB移行等を含む。このタスクが追加した課金/通信修正だけの配備ではない。

| 対象 | 差分 | 配備への影響 |
| --- | --- | --- |
| `accounts/migrations/0058_minimize_character_sheet_registry.py` | 既存移行をDB種別に対応するRunPythonへ変更 | 既に適用済みなら自動再実行されない。実DBの適用履歴と実スキーマを確認する。逆操作はnoopで、削除列の復元を保証しない |
| `schedules/migrations/0055_allow_multiple_participant_roles.py` | participant単独の一意制約を(participant, role)へ変更 | 新規移行。複数ロールのデータ作成後は旧制約へ逆移行できない可能性がある |
| static/templates | カレンダー、セッション、キャラクター等 | collectstaticと該当するCloudFrontキャッシュの更新、画面確認が必要 |
| settings/tasks | 背景除去の制限・保持・清掃ジョブ、DB設定等 | webだけでなくworker/beatへの影響と削除ポリシーを確認する |
| Dockerfile/lock | 依存関係・実行構成 | 候補SHAから新規ビルドしdigest固定。過去のローカルイメージを現候補として使わない |

## 配備前に揃える証拠

1. 直前に稼働タスク定義・イメージdigest・desiredCountを再取得する。変更があれば本計画を更新する。
2. `f0f443f0` の固定依存関係で新規LINE修正まで含む関連検証を実施し、配備イメージdigestを記録する。過去の203テストは `c6d280d8` の結果である。
3. 共有DBの読み取りで適用済みマイグレーション、旧/新ロール制約、既存重複ロールの件数を確認する。資格情報を文書に含めない。直接接続が不可なら、実行方法と追加費用を具体化してから検証タスクの承認を求める。
4. DB・添付のバックアップと復元先を確定し、復元手順を検証する。バックアップの存在だけで復元成功としない。
5. 起動時のmigrate/collectstatic/開発ユーザー作成、worker/beat、背景除去清掃の実効設定を確認する。Secretsに含まれる値は必要な真偽や設定有無だけを報告する。
6. 検証に使用する専用アカウント・グループ・Stripeテストモード・Google/Discord等の専用宛先を確定する。実利用者への通知は対象外。

## 承認時に提示する具体的な変更

- ECRの新規タグ `aws-pre-f0f443f0` とdigest、同候補のテスト結果。
- ECSの新リビジョン。webのイメージ以外を維持する案を基本にし、追加変更が必要なら個別に列挙する。現在のdesired=1を増やす包括承認として扱わない。
- DB移行の適用対象、実行前バックアップ、制約確認結果、移行時間、障害時の復元方法。
- collectstaticの書き込み先とCloudFront invalidation範囲。旧静的ファイルとの整合性を戻せるようにする。
- ローリング更新・一時タスク・復元先による追加稼働時間、費用見積もり、終了条件。現時点では金額を見積もっていないため、費用承認を求められる状態ではない。
- テストデータの作成・削除対象、外部送信の宛先と内容。料金や契約の承認は別項目。

## 失敗時の判断

- ヘルス失敗、権限漏えい、課金権限不整合、データ破損があれば検証を止める。検証のために制約や権限を緩めない。
- webの旧タスク定義40への切り戻しは、DB・静的ファイルとの互換性確認が前提。単独のイメージ戻しを完全復旧と呼ばない。
- 0055適用後に同じ参加者の複数ロールが存在する場合は、旧単一ロール制約への逆移行を実行しない。データ削除で強引に通さず、前進修正または承認済みバックアップ復元を選ぶ。
- 検証前から稼働しているサービスは停止しない。追加で作成した一時リソースだけを作成記録と照合して後片付けする。

現在は上記の事前証拠が未完了。配備操作への承認依頼は、具体的なdigest・移行/復元・費用・宛先が揃ってから行う。

## ローカル移行検証の追加証拠

2026-09-05、専用SQLiteとPostgreSQL 16の両方で0054→0055の更新と逆移行を検証した。単一ロールは主キー・参加者参照・ロールを保持して往復できる。複数ロールを作成した後の逆移行はIntegrityErrorで停止し、2ロールのデータと0055の適用履歴が保持される。同じ参加者への同じロールの重複も拒否される。

各DBで2テスト・2サブテストが成功。これはコードの移行特性の証拠であり、共有DBの履歴・スキーマ・バックアップ/復元を確認した結果ではない。複数ロールが存在するDBでの逆移行を承認する根拠にはしない。

## 秘匿HO添付の直接配信対策（公開を妨げる未完了事項）

2026-09-05、ローカルで添付一覧の認可を迂回する直接URLの取得を再現した。APIの `file` / `file_url` とモデルのダウンロードURLを認可付きAPIへ変更し、Djangoの旧メディアURLも正規化後に同じ認可を通す修正を用意した。DB・ファイルの移動は不要。添付は都度S3等のstorageからアプリ経由で取得するため、最大100MBの添付と同時ダウンロードの負荷・タイムアウトは実環境で検証する。

Terraformの変更対象は `aws_s3_bucket_policy.assets`。対象CloudFrontサービスによる `handouts/*` と `*/handouts/*` のGetObjectを明示的に拒否する。ECSのstorageアクセス権限は維持する案であり、実際のTask Role/KMS・メディアlocationとの照合が必要。`terraform fmt -check` / `validate` は成功したが、plan/applyと実際の拒否確認は未実施。[AWSの明示的拒否の評価](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

承認依頼を具体化する際は、次を一体の変更として提示する。

1. 現行バケット、CloudFront distribution、MEDIA location、アプリ候補digest、S3読取権限を値を秘匿して照合し、無関係な変更を含まないTerraform planを保存する。
2. 認可付きダウンロードのアプリ反映、S3ポリシーの拒否、旧添付URLのCloudFront invalidationを実施する順序・時間・費用上限を決める。拒否を先に適用すると旧アプリの添付が一時利用できなくなる点も承認案に含める。
3. 対象の既存キャッシュを失効させ、完了後に未ログイン・別PLの旧CloudFront URLが内容を返さないことを確認する。オリジン拒否だけでキャッシュ済み内容が消えるとは扱わない。[AWS CloudFront invalidation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html)
4. 通常GM/対象PLの新APIが成功し、対象変更後の旧PLが拒否されること、直接S3・別CDN・nginx alias等の迂回経路がないことを確認する。過去に取得済みのブラウザ内コピーを回収できるとは扱わない。
5. 問題時も公開GetObjectへ戻すことで復旧扱いにしない。添付の一時停止と認可を維持する前進修正を優先し、旧アプリへの切戻し時の添付利用制限を明示する。

この構成は未適用であり、実環境の漏えい発生を確認したという意味でもない。実ファイルの無断取得による検証や、ポリシー変更・invalidationは行っていない。

### 現行設定の読み取りと応急措置案（2026-09-05）

- AWSアカウントは `083773015316`、ECSはdesired/running=1/1、タスク定義40、イメージ `aws-pre-8cf3c7f7` のまま。修正アプリ候補は `69d4468a`。稼働版との差分に0055等の移行が残るので、この候補の即時配備を承認済みとは扱わない。
- バケット `tableno-aws-pre-assets-083773015316` の現行ポリシーはCloudFront `E3RQ829D1NVY28` に全キーのGetObjectを許可する1文のみ。Public Access Blockは4項目すべてTrueだが、そのCloudFront許可を取り消すものではない。`media/handouts/` のオブジェクト数は486、応答のIsTruncated=False。件数だけを確認し、オブジェクトの内容や利用者との対応は取得していない。
- CloudFrontは有効、origin pathなし、S3 OACあり。署名者/鍵グループ、Functions/Lambda、追加behavior、cache policy、response headers policyはいずれも未設定。現行のMin/Default/Max TTLはすべて0。この現行設定ではCDNキャッシュ期限を待つことが主な反映待ちではないが、過去設定やブラウザ側の保存内容がない証拠ではない。invalidationをこの応急措置の自動実行対象には含めない。
- Task Roleの実inline policyで対象バケット/配下へのGetObject・PutObject・DeleteObject・ListBucketを確認した。提案DenyはCloudFrontサービスと当該distributionに限定するため、これらECSロールの許可を対象にしない。実S3/KMS読取の動作確認はアプリ配備後に別途実施する。
- 現行ポリシーにDeny文だけを追加したJSONを `tmp/handout-containment-20260905/proposed-policy.json` に用意した。元文が維持されていることを機械的に確認し、AWS Access AnalyzerのRESOURCE_POLICY/AWS::S3::Bucket検証はfindings=[]だった。これはポリシーを適用した証拠でも、実際の配送拒否を確認した証拠でもない。
- 元ポリシー保存ファイルのSHA-256: `96aad423a8a79088b9bb351fbbbfdc652785b36f916cd2ff7f616914ae132f05`。提案ファイル: `1a0bc2485f6c3d461ebc77e25e0b48f5efaa831980f6a157aed60562d29c9514`。承認後も適用直前に実ポリシーを読み直し、保存時から変更があれば差分を再評価する。古いコピーで第三者の変更を上書きしない。
- ユーザーには、応急措置としてこのDenyだけ先行適用するか、認可付きアプリと同時反映するかを質問済みで、回答待ち。前者は既存の添付ダウンロードを一時停止させる。ファイル削除、新規AWSリソース、アプリ配備、キャッシュ失効は今回の応急措置案に含めない。許可へ戻して情報保護を解除する操作も自動で行わない。
