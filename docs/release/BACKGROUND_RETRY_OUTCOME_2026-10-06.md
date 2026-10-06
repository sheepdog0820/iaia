# 背景透過：SDK再試行後の拒否で入力を誤削除しない

## 問題・変更対象

基点は `62b86e650377e9c784670d7529c55adde70aa59a`、専用ブランチは `codex/background-retry-outcome-20261006`。[先行の起動結果不明対応](BACKGROUND_DISPATCH_UNCERTAIN_2026-10-06.md)は通信/5xx/ConflictExceptionを保護したが、SDKの初回timeout/500の後に最終400/403を受けると、最後のClientErrorだけを確定失敗と扱い、pending jobをfailedにして元画像を削除していた。

[ECS公式仕様](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html)はtimeout/server障害が処理変更後に発生し得ることを説明する。[Boto3公式retry情報](https://docs.aws.amazon.com/boto3/latest/guide/retries.html)とインストール済みbotocore endpoint実装は、最終response metadataへRetryAttemptsを記録する。この2情報から、最終拒否だけでは先行試行の受理を否定できないと判断し、実SDKのserializer/signing/retry/parserを使う合成通信で再現した。これは実AWSがその順序の応答を返した記録ではない。

## 修正の境界

- RunTaskのClientErrorに `ResponseMetadata.RetryAttempts > 0` があれば、既存のBackgroundRemovalDispatchUncertainとして扱う。5xx/ServerException/ConflictExceptionの既存判定は維持。
- 既存Web側の最新job行ロック処理へ戻し、pendingならstatus/source/error/updated_atを保持してjob ID付き202を返す。202は「起動確認済み」ではない。
- retry 0またはmetadata未指定の通常400/403は、従来の確定失敗503・元画像削除を維持。設定/資格情報/parameter検証、明示的taskなしfailure、成功ARN保存の既存経路は変更しない。
- 新たなアプリ再送、SDK retry設定変更、別token発行、timeout延長、quota変更、ECS task増加、既存jobキャンセルを追加しない。重複POSTは既存409、遅いworkerは保存された入力を処理可能、未確認jobは既存timeoutで終端化する。
- `RetryAttempts` はSDKが付ける回数であり、先行受理の証明ではない。保守的に結果不明として保持するため、実際には一度も受理されていなくてもtimeoutまでpendingになる場合がある。

SDK内部で最終response metadataがない別例外、設定変更をまたぐ再送parameters永続化/outbox、token TTLを超えるexactly-once、実IAM/ECS受理/S3・孤立task/画像回収・DB/storage分散原子性は今回の証明範囲外。管理者の所有権/削除方針や実ユーザー権限を変更しない。新しい利用者向け文字列はなく、既存の英語errorの翻訳完了とも扱わない。

## TDD・隔離検証

新規8テストはtimeout→400、500→403、timeout→resource不存在、legacy retry、1回目400/403の確定拒否、重複拒否/遅いworker完了、既存timeout/遅い推論抑止。実botocoreの最下位 `_send` とbackoff sleepだけを置換し、`after-call.ecs.RunTask` で最終RetryAttempts 1/0を観測する。2回のwire bodyが全parameters/clientTokenで同一、追加POSTからSDK呼び出しなし、backend詳細ログ非露出も確認した。認証は先行APIClient fixtureで、実HTTP/実Token認証の追加証明ではない。推論結果も合成PNGで、実U2NET追加検証ではない。

| 検証 | 結果 |
| --- | --- |
| RED・新規8件 | 6 failure/2成功、1.036秒・終了1。再試行後が202でなく503になる問題を確認 |
| 最小GREEN・新規8件 | 全8成功、0.589秒・終了0 |
| 整形後の初回SQLite回帰 | 165件中149成功/PG専用16省略、18.587秒・終了0 |
| 広いWindows SQLite回帰 | 210件中194成功/PG専用16省略、63.560秒・終了0。in-memory TEST DB |
| 同じ広い隔離PostgreSQL回帰 | 210成功/省略0、62.859秒・終了0 |
| 変更起動関数coverage | 36文/10分岐100%、除外0 |
| 新規test module coverage | 108文/8分岐100%、除外0 |
| tasks module全体coverage | 186/190文・57/58分岐。全モジュール100%とは扱わない |
| 品質 | Black/isort/Flake8・差分検査成功。最終Bandit2ファイル指摘0、テスト専用B106対象1件を限定注釈 |

新規テストhelperの応答選択をGREEN後に明確なif/elifへ整理した。Bandit初回は合成署名文字列をB106/LOWで1件検出（終了1）。実キーではなく、合成値を指定したclientの送信を `_send` で置換するテストだけに説明付き `nosec B106` を付けた。最初の注釈書式は説明語をtest IDと誤読するwarningが出たため、`#` で説明を分離して訂正。全体のtestやOS指摘の抑制ではない。初回報告・warning段階・最終報告を別ファイルで保持する。coverage JSON集計もempty function名/relative pathを扱わない診断エラー2回を訂正し、上表は正しく読み取った最終集計のみ。

回帰対象13モジュールは背景透過通常/dispatch/uncertain/retry/finalization/premium/retention、画像API/複数画像、有料機能ライフサイクル、背景model/infrastructure、release文書。既存の実PG lock16ケースも省略せず成功した。CI production-databaseの明示対象へ新規moduleを追加した。CIの合格条件・retry・待機上限は緩めていない。

Linuxは通常ba51bdd8 image `sha256:1e5d3114e2c23473fc1bcce06273aeca65d71811a89fea878b07294e98f49e11` に今回sourceとcoverage 7.15.4をread-onlyで重ねてpytrace計測。root read-only、1 CPU/512 MiB、一時/tmp/media、PG namespace以外へ通信不可。coverageだけを工具mountし、SDKやアプリ依存のoverlay/追加インストールはないが、今回commitの通常配布物同一性の検証とは扱わない。

PG18.3 imageは `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`。固有DB/user、network none、公開portなし、256 MiB/512 MiB tmpfs。初回readiness probeは初期化中でno response、後続acceptingを確認してからtestを開始した。終了後、test DBなし・基点DBのpublic table0を確認。名前/ID/network/tmpfsを照合した専用PGコンテナ `a577c037cfeddc7b499da3e1a9e2b8dd7948e48fc844431554d5076829abb788` を停止・削除し、tmpfs DBは破棄済み。検証アプリコンテナも--rm終了済み。外部証跡は保持し、旧cacheや他作業コンテナを削除していない。

## 証跡・影響・残作業

証跡は `D:/tmp/codex-tableno-retry-outcome-20261006`。Windows初回RED/GREENはこの検証checkoutの専用test_db.sqlite3だけを作成し、終了時に破棄した。広いWindows回帰はin-memory、全testは一時mediaと合成データに限定し、実データDBには接続していない。

| ファイル | SHA-256 |
| --- | --- |
| red.log | 13a261bcc32afeaad868be7bf1e24bf05c40808a6e3f930355186953cd756804 |
| green-targeted.log | b07473b4c0ca5005a86f5b24d96f56d965bfceb5ec3166ff4b49809a6d3c6a51 |
| sqlite-final.log | ca4f73bc4b87c1f095f470b41540335d34e62a3767e036d248d21f761870ddaa |
| sqlite-covered.log | 05dac30aba9d2397b8e2e13ca9620e1b13c2b5b17e8e650d1e364e122ef3015e |
| postgres-final.log | 7aa3024122a5ba7870586ba47837e5910499d92da149c2b9dc762260b6610826 |
| coverage-postgres-final.json | d7aac05fde578d0cb4ef6e6d13ffb155df443fe5c67d2c931ba95c34c769488d |
| coverage-sqlite-covered.json | 1e53b8c625b37b33d149591ecb16f8f4d42de6a72def5996722be9b01ea87dbe |
| bandit-initial.json | 8ef31479a25cffc28c3ccb1001882d460505cbcd719e14002ab9e6839d20814e |
| bandit-final.json | a9cac4be9d8ac6de3f446095dd19cc1335b125bd4328f42ed170caad9ae394d3 |
| bandit-corrected.json | 97ebbd55b6a4a943bba7d9c64228a8ee3dd9a55e90d5aa555c8b4604db7db0d8 |
| run_isolated_tests.py | 2cd2bfce7dd5a1257a2565a8d407ef776b26df0cca76880686cbbaecd959f015 |

追記後の文書関連39 test成功（0.035秒）、変更文書の相対参照202件/欠落0、上表11ハッシュ一致。最初のhash転記1件の誤りは照合で検出・訂正した。実差分をレビューし、再試行なし拒否・既存token/timeout/権限/最新行優先を維持する観点で修正を要する指摘なし。新規利用者向け文言は0件。ステージ済み5ファイルのUTF-8/LF/BOMなしと差分検査も成功した。

今回候補の全CI・通常配布物・実HTTP/実AWS/S3・実課金/常設worker/外部連携・性能/復旧/事業者条件等は未証明。新しいOSスキャンや依存更新はしておらず、最新通常ba51監査の39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2を解消/受容済みにしない。[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は **No-Go** を維持する。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/実データ、Secrets/IAM・課金/メール・容量/継続費用は変更していない。DB schema変更なし。既存main/AWS承認の対象へ追加しない。元checkoutの無関係な13変更は保持する。作業ブランチはrevert可能だが、入力誤削除を再導入するためfix-forwardを優先する。利用者向け文字列変更はなく、今回画面/ブラウザー検証は行っていない。
