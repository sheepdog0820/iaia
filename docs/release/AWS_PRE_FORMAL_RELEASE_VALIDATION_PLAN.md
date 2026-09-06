# 正式公開に向けたaws-pre検証・配備準備

## 現在の候補と承認前の残作業（01a52f52、2026-09-06）

候補ソースは `01a52f523ddcfa087d57b10c69c9f905dd1db44c`。4499b243以降の時間計測・動画操作テスト修正とホーム画面の配置修正を含む。通常Dockerfileから作成した `tableno-formal-release:01a52f52` のローカルIDは `sha256:b649686df0dc3d8d716c1e821af0339ca6d3cf8f3d7108214b56a3384c407de0`、revisionラベルは候補SHA、実行ユーザーはtableno。ECR未送信。

内部ネットワーク・公開ポートなし・外向き通信なしの専用PG16/Redis7と本番設定で、通常entrypointの空DB移行・静的収集・Daphne起動を確認した。readiness/登録画面200、登録画面のstatic5件、vendor8件のハッシュ付き配信・内容照合とCSS/JS gzipが成功。pip check、migrate --check、check --deployも終了0。実行コンテナの8領域499ファイルはarchiveとSHA-256一致。S3/Checkoutは無効で、Stripeキー等は検証用の仮値。実AWS・課金・OAuthの証拠とはしない。

証跡は `tmp/formal-release-01a52f52-production-build.log`、`tmp/runtime-source-01a52f52.json`、`tmp/static-runtime-01a52f52-{server,http,deploy-check}.log`。専用app/DB/cacheコンテナとネットワークは検証後に停止・削除した。全体テストも終了し、結果は下記の追加結果に記録した。共有環境・共有DB・Secrets・IAM・契約への変更はない。

AWS稼働版・DB履歴の未確認事項・復旧候補は以下の読み取り結果を引き継ぐ。最新候補の全体テスト・CIゲート・実サービス・共有DB差分の確認が残るため、配備承認用資料はまだ未完成。

追加結果: 01a52f52のブラウザ全体は25フローファイル、3ブラウザ各58件・計174成功（806.50秒、skip/retry/flakyなし、終了0）で完了した。flake8/Black/isortも終了0、BanditはLOW560・HIGH/MEDIUM 0・解析エラー0・終了1。SQLite1683成功/11skip・86.99%、PG1694成功/skipなし・87.62%、双方終了0で完了した。SQLiteのskip11件はPGで成功。リモートCI・実サービス・共有DBの未確認事項は維持する。

## 前候補の確認（4499b243、2026-09-06）

候補ソースは `4499b2433024415fe932ddb175b2cff5eb2e1d9f`。f016a66d以降のGoogle設定保存UIと追加認可の保存経路を含む。共有環境への反映、ECRへの送信、DB操作は未実施。

| 項目 | 現在の証拠と限界 |
| --- | --- |
| 本番用イメージ | 通常Dockerfile/requirements.lock.txtから `tableno-formal-release:4499b243` をビルド。ID `sha256:700a3d48b07fb404dbd73d227471d8bf840227cb3fda0e9673846f0866540286`、revisionは上記完全SHA、実行ユーザーtableno。ECR digest未取得 |
| ソース一致と起動 | archiveと実行コンテナのアプリ8領域のPython/HTML/JS/CSS 499ファイルが一致。APP_ENV=aws-prod、専用空PG16/Redis7、S3/Checkout無効、外向き通信・公開ポートなしで通常entrypointの移行・static199件収集/571件後処理・Daphne起動に成功 |
| 配信・設定 | readiness/登録画面200、登録画面のstatic5件、vendor8件のハッシュ付き配信・内容一致・CSS/JS gzipを確認。pip check、migrate --check、check --deploy成功。Stripe等は隔離用仮値であり実サービス検証には数えない |
| 全体検証 | 固定4499b243はSQLite1683成功/11skip、PG1693成功/1失敗、ブラウザ166成功/2失敗で終了。後続の時間計測テスト修正3b8d7fa9は両DB各24成功、動画操作テスト修正cb6027fdは3ブラウザ計9成功。ホーム画面は読み込み中クリックを再現・配置修正し関連15件成功。これらを含む固定候補の全体再検証が残る。flake8/Black/isort成功、Bandit LOW560・HIGH/MEDIUM 0・解析エラー0・終了1で、CIゲート未達 |
| 現在のAWS | 2026-09-06にprofile tableno-preと対象アカウントを確認。サービスACTIVE、desired/running=1、pending=0、タスク定義40、rollout COMPLETED、稼働タスクHEALTHY。イメージtag `aws-pre-8cf3c7f7`、稼働digest `sha256:551535a7219a599891d592346480803966abfb54f856656201ca08eec1d42b66`。readinessのDB/cacheともok |
| 配備差分・DB | 稼働ソース8cf3c7f7から266ファイル。accounts/0055・0058の修正、schedules/0055の新規追加を含む。サービスはECS Exec無効であり、この手段による共有DBの適用履歴・スキーマ確認は未実施。アクセス設定を変更していない |
| 承認時に示す影響 | 通常のECSイメージ更新に加え、DB移行の適用範囲確認が必要。Google追加連携後はトークンをDBに保存し、ユーザーごとに有効なGoogle資格情報を1件に揃える。以前のGoogleトークンのローカル置換はコードrevertでは戻らないため必要なら再認可する。通常ログイン・他プロバイダーは維持 |

本番用の専用コンテナ・DB/cache・ネットワークは検証後に停止・削除した。証跡は `tmp/formal-release-4499b243-production-build.log`、`tmp/static-runtime-4499b243-{server,http,deploy-check}.log`。復旧候補は再確認したタスク定義40と稼働digestだが、DBの旧制約復元可否・バックアップ・実データ影響は別途確認が必要。現在の稼働版へ戻せることだけでDBロールバック可能とは判定しない。

## 過去候補f016a66dの準備記録

候補ソースは `f016a66d2bd21e5f41b2e30265fffcc48bdbe1ea`。無料範囲・画像5枚共通・背景透過モデル・ハンドアウト本文・文字表示・履歴APIキャッシュの後続修正を含む。月額480円・年額4,800円と無料範囲は承認済みであり、下記の過去候補の「料金と有料範囲は未確定」は現在の状態ではない。実Stripe Price・公開条件の実証は残る。

| 項目 | 現在の証拠と限界 |
| --- | --- |
| 本番用イメージ | 通常Dockerfileと固定依存ロックから `tableno-formal-release:f016a66d` をビルド。ローカルID `sha256:477752156e723bbaccf581aced4ee8388413160428444330c98457a5c0ea3235`、revisionは上記完全SHA、実行ユーザーtableno。ECR未送信・manifest digest未取得 |
| ソース一致 | archiveと実行コンテナのアプリ8領域にあるPython・HTML・JS・CSS計496ファイルがSHA-256で一致。全依存・OSの再現性を証明するものではない |
| 本番設定の隔離起動 | APP_ENV=aws-prod、専用空PG16/Redis7、S3無効、Checkout無効、設定値は隔離検証用。外向き通信・公開ポートなし。通常entrypointで移行、static199件収集/571件後処理、Daphne起動、readiness/登録画面200。登録画面のstatic5件とvendor8件のハッシュ付き配信・内容一致・CSS/JS gzipを確認。pip check、migrate --check、check --deploy成功 |
| 検証用設定の訂正 | 最初の起動はStripeの仮値がsk_test形式だったため本番形式ガードで停止。通信遮断とCheckout無効を維持したまま、実キーではないsk_live形式の仮値で再実行した。実Stripe認証や販売設定の検証には数えない |
| 機能検証 | 履歴修正前の8f4bbc5dはブラウザ146成功/1失敗。修正後の関連バックエンド38件・3サブテスト、ブラウザ24件成功。f016a66dのブラウザ全体は147件成功（3ブラウザ各49件、再試行/skip/flakyなし、10.0分）で完了。a95e1a20の両DB全体成功を最新ソース全体の証明には使わない |
| 差分 | 記録済み稼働ソース8cf3c7f7からf016a66dまで262ファイル差分。704c6f06以降のaccounts/schedules/scenarios移行ファイル、Dockerfile、entrypoint、依存ロック、本番設定ファイルの差分なし。過去候補からのDB移行の適用確認は引き続き必要 |
| 配備前に残る確認 | 直前の実稼働版・復旧先、共有DB履歴とスキーマ、ECR digest、リモートCI、実S3/CDNの保護、実連携・宛先、復旧基準・費用。最新の実状態と照合してから操作内容を確定する |

証跡は `tmp/formal-release-f016a66d-production-build.log`、`tmp/static-runtime-f016a66d-server.log`（初回停止）、`tmp/static-runtime-f016a66d-server-final.log`、`tmp/static-runtime-f016a66d-http.log`、`tmp/static-runtime-f016a66d-deploy-check.log`。専用app/DB/cacheコンテナと内部ネットワークは検証後に削除した。実AWS・実データ・Secrets・権限・費用への変更はなく、配備承認を求める最終資料としては未完成である。

## 704c6f06の準備記録（2026-09-05時点の履歴）

候補ソースは `704c6f062ef73f64ee3b5eae43799264fb4dcbf9`。静的ファイル同梱・本番設定に加え、Axios代替処理、日程投票の時間帯/配色/キャッシュ、グループと招待の文字表示、グループ権限応答のキャッシュ、ゲスト参加の失効再確認・引き継ぎ案内/エラー表示を修正した。以下の過去候補の節は履歴として保持する。この資料は配備承認ではない。

本番用イメージ・ブラウザ・両DB全体検証の対象は `704c6f06`。同じ固定ソースで通常起動、3ブラウザ33件（4.5分、retryなし）、SQLite/PostgreSQL全体が成功した。リモートCIと実環境検証は未完了。

| 項目 | 最新の証拠と限界 |
| --- | --- |
| 配備用イメージ | `tableno-formal-release:704c6f06`、ローカルID `sha256:a10e440ae242b2e67dfab13dc590e2d9e707cef91579459992501be523de7e9a`。通常Dockerfile/固定依存から作成。ECRへ未送信でmanifest digestは未取得 |
| 隔離起動 | 704c6f06でpip check成功。専用の空PG16/Redis7、通常entrypointで移行・静的199件収集/571件後処理・Daphne起動・readiness/登録画面200。登録画面のstatic5件とvendor8件のハッシュ付き配信、CSS/JSのgzip内容一致を確認。check --deploy指摘0。S3なし構成であり、既存データ復元の最新再実証、実TLS/Stripe/OAuth/S3は未確認 |
| 全体検証 | 704c6f06のSQLite1665成功/10skip・86.94%、PostgreSQL1675成功/skipなし・87.51%、双方478 subtests・159 warnings、終了コード0。JUnit2153件、failure/error 0。SQLite skip10件はPGで成功。リモートCI・実環境検証は未完了 |
| 稼働版との比較 | 記録済み稼働ソース `8cf3c7f7` から704c6f06まで227ファイル差分。63bd2436以降のaccounts/schedules migrationファイル差分なし。現在のAWS稼働版は配備直前に再確認する。mainとの比較だけで配備範囲を決めない |
| DB差分 | 既存 `accounts/0055`・`accounts/0058` の変更、新規 `schedules/0055` の追加。0055修正はデータ移行後のFK検査をDDL前に完了させるもので、適用済み0055を再実行しない。適用済み0058は再実行されないため共有DBの移行履歴と実スキーマ確認が必要。ロール複数化後の旧制約復元はデータ次第で失敗し得る |
| 未確定事項 | ECR digest、直前の稼働タスク/復旧先、共有DB状態、実データを含む復元・更新・ロールバック、専用テスト利用者/宛先、料金と有料範囲、実連携設定、追加費用。承認対象を具体化してから配備する |

最新起動証跡は監査記録の704c6f06節、`tmp/static-runtime-704c6f06-http.log`、`tmp/static-runtime-704c6f06-server.log`、`tmp/static-runtime-704c6f06-deploy-check.log`。完了済み全体テストは`tmp/formal-release-704c6f06-full-output`。リモートCIの成功とは扱わない。秘匿画像のCloudFront迂回防止も別途承認・適用・実証が必要で、アプリ起動成功だけでは正式公開できない。

## 過去候補の準備記録

2026-09-05、コード候補 `b8fad941`。実行承認前の準備資料。実環境は読み取りのみ。ローカルで配備用イメージ作成と専用PostgreSQL検証を行ったが、ECR送信・ECS配備・共有DB変更・通知は実行していない。

後続の参加承認・報酬反映・ID・配列順序・画像配信修正により、この冒頭の候補は最新ではない。9b1c9043のSQLite/PostgreSQL全体成功は監査記録に保存している。後続の画像・権限画面修正を含む6608de6dの配備用イメージをローカルで作成・起動検証した（後述）が、ECR manifest digestは未取得。以下の過去候補の検証結果をそのまま最新の配備承認材料に使わない。

## 確認できた現状

- AWS profile `tableno-pre`、region `ap-northeast-1`、cluster/service `tableno-aws-pre`。
- ECS desired/runningは **1/1**、PRIMARY deploymentはCOMPLETED、task definitionは `tableno-aws-pre:40`。前回の0/0から変化している。このタスクは起動していないため、検証後に勝手に0へ戻さない。
- 配備イメージは `tableno:aws-pre-8cf3c7f7`。CPU 256（0.25 vCPU）、memory 512MiB、コンテナ名はweb。
- `https://stg.tableno.jp/health/ready/` は200、database/cacheともok。公開可能な機能・最新コード・課金の正常性までは証明しない。
- task definitionの平文設定でAPP_ENV=aws-pre、DB_ENGINE=postgresを確認。秘密情報の値は取得していない。Checkout、起動時migrate、開発ユーザー作成等の実効設定は平文設定の不在だけでfalseと断定しない。
- ECS Execは無効。ローリング更新はminimumHealthyPercent=100、maximumPercent=200で、一時的に2タスクとなり得る。deployment circuit breaker/自動rollbackは無効。これらを変更する場合はイメージ更新と別の差分として提示する。

## 稼働版と候補の差分

比較はローカルmainとの比較だけでなく **`8cf3c7f7..b8fad941`** を用いる。差分は121ファイルで、依存ロック、Dockerfile、背景除去、画面、静的ファイル、設定、DB移行、秘匿添付配信等を含む。このタスクが追加した課金/通信修正だけの配備ではない。

| 対象 | 差分 | 配備への影響 |
| --- | --- | --- |
| `accounts/migrations/0058_minimize_character_sheet_registry.py` | 既存移行をDB種別に対応するRunPythonへ変更 | 既に適用済みなら自動再実行されない。実DBの適用履歴と実スキーマを確認する。逆操作はnoopで、削除列の復元を保証しない |
| `schedules/migrations/0055_allow_multiple_participant_roles.py` | participant単独の一意制約を(participant, role)へ変更 | 新規移行。複数ロールのデータ作成後は旧制約へ逆移行できない可能性がある |
| static/templates | カレンダー、セッション、キャラクター等 | collectstaticと該当するCloudFrontキャッシュの更新、画面確認が必要 |
| settings/tasks | 背景除去の制限・保持・清掃ジョブ、DB設定等 | webだけでなくworker/beatへの影響と削除ポリシーを確認する |
| Dockerfile/lock | 依存関係・実行構成 | 候補SHAから新規ビルドしdigest固定。過去のローカルイメージを現候補として使わない |

## 配備前に揃える証拠

1. 直前に稼働タスク定義・イメージdigest・desiredCountを再取得する。変更があれば本計画を更新する。
2. `b8fad941` の新規イメージで、PostgreSQLの添付権限/課金関連227件と通常起動・ヘルス200を確認済み（後述）。最新候補の全体CI・全機能の検証は未完了。ECR送信後にmanifest digestを取得する。過去の203テストは `c6d280d8` の結果であり混同しない。
3. 共有DBの読み取りで適用済みマイグレーション、旧/新ロール制約、既存重複ロールの件数を確認する。資格情報を文書に含めない。直接接続が不可なら、実行方法と追加費用を具体化してから検証タスクの承認を求める。
4. DB・添付のバックアップと復元先を確定し、復元手順を検証する。バックアップの存在だけで復元成功としない。
5. 起動時のmigrate/collectstatic/開発ユーザー作成、worker/beat、背景除去清掃の実効設定を確認する。Secretsに含まれる値は必要な真偽や設定有無だけを報告する。
6. 検証に使用する専用アカウント・グループ・Stripeテストモード・Google/Discord等の専用宛先を確定する。実利用者への通知は対象外。

## 承認時に提示する具体的な変更

- ECRの新規タグ案 `aws-pre-b8fad941` とmanifest digest、同候補のテスト結果。ローカルイメージIDをECRのmanifest digestとして転記しない。
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

## 最新候補のローカル配備用イメージ

`b8fad941` のgit archiveから、リポジトリのDockerfileとrequirements.lock.txtを使ってビルドした。ローカルタグは `tableno-formal-release:b8fad941`、イメージIDは `sha256:45e2df5a6ada21fbe0209ca4943005b4ad969f08f58619ac21b0511194f39b27`。Python 3.11.16、Django 5.2.17、Stripe 15.5.1、実行ユーザーtableno。ベースOSとpip自体まで固定された再現可能ビルドを証明するものではない。

テスト用ソースの上書きマウントなしで、専用PostgreSQL 16に対して添付・HO権限・PL枠・課金・署名イベント統合の227件成功（55.953秒）。pip checkとmakemigrations --check --dry-runも成功した。さらに通常entrypointで専用DBへのmigrateを実行し、Daphne起動後に `/health/ready` のdatabase/cacheともok、HTTP 200を確認した。APP_ENV=local、locmem cache、外部通信不可のinternal networkであり、公開用Secrets/S3/Redisを使用するaws-pre設定の起動確認ではない。

証跡は `tmp/formal-release-b8fad941-build.log`、`tmp/formal-release-b8fad941-postgres.log`、`tmp/formal-release-b8fad941-runtime.log`、`tmp/formal-release-b8fad941-ready.json`、`tmp/formal-release-b8fad941-image.json`。検証用app/DBコンテナとnetworkは終了・削除済み。ECR送信、AWSタスク定義登録、配備、実ポリシー変更は未実施。

## セッション・シナリオ画像への保護範囲拡張（未適用）

ローカルでsession_images/とscenario_images/の未認可取得を再現し、両画像のアプリ認可付き配信を実装した。画像はS3オブジェクトを移動せずアプリ経由で読むため、既存のCloudFront/S3 URLの拒否も必須となる。Terraformはhandouts/に両画像のprefixを追加し、拡張した具体的なポリシー案も静的検査した（下記）。以前のhandouts/だけの応急案では画像保護は完了しない。

- 最終の拒否案には、実際のstorage locationを確認したうえでhandouts/、session_images/、scenario_images/を含める。公開シナリオ画像も認可付きAPIでvisibilityを都度確認するため、非公開化後に残る直URLを許可しない。正当な匿名閲覧は公開シナリオの新APIで維持する。
- アプリ候補と配信拒否の順序を一体で提示する。旧アプリは画像の直URLを返すため、拒否だけを先に適用すると画像表示が停止する。旧アプリへ戻す場合も、保護対象の公開GetObjectを復活させて復旧扱いにしない。
- 専用試験画像を用いて、公開シナリオの匿名表示、所有者/共有グループ、セッション経由の閲覧、無関係ユーザーの拒否、非公開化/脱退/参加解除後の失効、新APIと旧CDN・S3 URLを照合する。セッション経由URLはその画像とセッションのシナリオが一致することも確認する。
- 既存キャッシュの失効対象・費用・完了確認、アプリ配信の負荷とタイムアウトを計画に含める。実利用者の画像を無断で取得せず、専用試験データの作成・通知抑止・削除を承認案に含める。

この追記は実行要件の更新であり、AWS設定変更、キャッシュ失効、配備、実データ作成を実施した記録ではない。適用直前の稼働状態照合・最新候補digestの検証・実行承認はまだ必要である。

### 拡張ポリシーの具体案と静的検査

2026-09-05にバケットポリシーとCloudFront設定を再取得した。ポリシーは対象distributionからbucket/*へのAllowだけで、拒否は未適用。S3 Public Access Blockは4項目true。distributionのETagはETVPDKIKX0DER、S3 OAC付き、OriginPathは空、追加behaviorなし、TrustedSigners/KeyGroups/Functions/Lambda関連付けなし、既定behaviorのTTLはmin/default/maxとも0だった。これだけで既存コピーの消去や実オブジェクトの露出有無を証明しない。

`tmp/private-media-containment-34846799/proposed-policy.json` は再取得したAllowを保持して、対象CloudFront principalかつSourceArn一致の場合のGetObject拒否を1 statement追加したもの。対象resourceはhandouts/、session_images/、scenario_images/の直下と各 `*/prefix/*` の計6パターン。ECS task roleのAllowや他の静的ファイルのAllowをこの案では変更しない。

- 現行ポリシー保存ファイルSHA256: `04b660fe783b9966262cfba2a9373cf6c3dd2ede5f2b349d3f0d7b2d589453ab`
- 拡張案SHA256: `2ba55b16611afe7654da2f831dd65bde1eaaeb9247d8863a4bcc1ab63bb53db0`
- AWS Access AnalyzerのRESOURCE_POLICY / AWS::S3::Bucket検査: findings=[]。
- Terraform 1.15.6のfmt -check / validate: 両方終了コード0。変更対象はassets bucket policyのSidと拒否resource追加だけ。

これらは静的検査であり、Terraform plan/applyやIAM評価・実配信の成功証拠ではない。実ファイルの取得・ポリシー適用・invalidationは行っていない。適用時は保存した現行ポリシーとの再照合、旧アプリでの表示停止の扱い、アプリ配備と切り戻しの順序、試験画像・宛先・費用を具体化して承認を得る。

## 6608de6dの配備用イメージと隔離起動検証

2026-09-05、`6608de6d6e6d0dd3dbf854bd27a3dc07047a3d02` のgit archiveから、リポジトリのDockerfileとrequirements.lock.txtを使ってビルドした。ローカルタグは `tableno-formal-release:6608de6d`、イメージIDは `sha256:6a7ec1bd4450cf9bd736d49a86ef4905aecee2b7a74c4252c344196ad376e77d`。revisionラベルは上記の完全SHA、実行ユーザーはtableno/UID 10001。RepoDigestsは空で、ECRのmanifest digestではない。

外向き通信と公開ポートのない専用DockerネットワークでPostgreSQL 16とRedis 7を起動し、APP_ENV=aws-pre、ENVIRONMENT=stagingで通常entrypointを実行した。settings_productionのDEBUG=False、Redis利用、HTTPS向け設定を使い、S3は無効・ローカル保存。課金は無効で、Stripeキー・料金/事業者表示は隔離検証専用の値を設定した。実際のSecretsや販売条件を確認した結果ではない。

- entrypointのmigrateが完了し、collectstaticは179ファイルを収集した後、通常のDaphneが起動した。
- `pip check` はNo broken requirements found、`manage.py check --deploy` は指摘0件、`makemigrations --check --dry-run` は差分なし、`migrate --check` は成功。
- コンテナ内のHTTPリクエストにX-Forwarded-Proto: httpsを付け、readyが200、database/cacheともokを返した。これはプロキシ経由の判定を模擬したもので、実TLSやALBの検証ではない。HSTS、nosniff、X-Frame-Options: DENYも応答に確認した。
- 証跡は `tmp/formal-release-6608de6d-build.log`、同接頭辞のimage.json/ready.json/startup.log、`tmp/candidate-6608de6d-deploy-check.log` / migration-diff.log。終了後に専用app/DB/Redisコンテナ・ネットワークを停止・削除した。

この候補には画像配信と権限画面の修正が含まれる。一方、同じSHAの全体CI、S3ストレージの読取/迂回防止、AWS実効設定、復旧手順、実課金・外部連携の検証は未完了。ローカル起動成功をそのまま公開承認に置き換えない。実配備前にはECR送信後のmanifest digestと最終候補を照合する。
# 候補更新: 58a27172の隔離起動確認

2026-09-05。以下は反映許可ではなく、候補に関する追加証拠。

- アプリ候補: 58a2717282bc9e5a21894097ad883dde89bf1e49。配備用イメージID: sha256:8993fb43f519f89f7d9aad564480eeb6ea3a31d32383cc65e34396d9011861aa（ローカルのみ、ECR digest未取得）。
- 実Dockerfileと固定依存でビルドし、隔離したPostgreSQL/Redisで通常entrypoint、migrate/collectstatic、非root、DEBUG無効、ready 200を確認。check --deployと移行差分チェックも成功。
- S3・Stripe・OAuth・TLS/ALB・実データはこの起動試験の対象外。使用した架空の設定は配備に流用しない。全体テストとリモートCIはまだ完了していない。
- 反映前には全体結果、現在稼働版、対象差分、イメージ識別、ストレージ保護との順序、復旧手順、承認範囲を再確認する。詳細証跡は[監査記録](FORMAL_RELEASE_AUDIT_2026-09-05.md)を参照。

## 旧テンプレート画像を含めた配信拒否案の更新

2026-09-05の読み取り確認で、対象バケットのmedia/session_template_images/に119オブジェクト（計21264バイト）が残存。内容・所有者・削除失敗との関係は未確認。既存の6パターン案にsession_template_images/*と*/session_template_images/*を加えた8パターンを最新案とする。Terraformのaws_s3_bucket_policy.assetsへ同じ2パターンを追加した。

tmp/private-template-containment-42219b05/proposed-policy.jsonは再取得した現行Allowを保持する具体案。Terraform fmt -check / validate成功、AWS Access AnalyzerのS3 bucket RESOURCE_POLICY検査findings=[]。過去の6パターン案の検証記録は履歴として保持し、今回の案へそのまま適用したとは扱わない。

本変更は未適用。実施前に現行ポリシーとの再照合、専用試験オブジェクトと配信拒否の検証方法、キャッシュ失効範囲・費用、正規画像の利用と切り戻し手順を含めて承認を得る。旧モデルの復元や旧画像へのアクセス機能の再導入は行わない。残存画像の所有・保存義務・削除対象は別途確認し、削除承認なしに一括削除しない。
