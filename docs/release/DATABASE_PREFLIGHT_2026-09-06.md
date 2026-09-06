# 配備前のPostgreSQL読み取り検査

mainへ654d5bb2をマージ後、正式公開準備を再開した。2026-09-06T05:27ZのAWS読み取り確認では、aws-preはタスク定義40、旧イメージaws-pre-8cf3c7f7、desired/running=1/1、readinessのDB/cacheともokだった。worker/beatはMISSING、ECS Execは無効。共有DBの適用履歴・実制約は引き続き未確認である。

## 用意した検査

`python manage.py release_database_preflight` は接続先PostgreSQLの以下の情報をJSONで返す。検査成功は読み取り完了を意味し、配備許可・スキーマ整合・バックアップ復元成功を意味しない。

- accounts/schedulesの適用済み移行名。候補の移行ファイルと照合する。
- キャラクター登録テーブルの列名。accounts/0058の適用履歴と、旧列の残存を照合する。
- 参加者ロールテーブルの一意制約の対象列。schedules/0055前のparticipant_id単独と、適用後のparticipant_id/roleを区別する。
- 複数ロールを持つ参加者の件数。1件以上なら単一ロール制約へ戻す逆移行は行わない。
- 同じ参加者・ロールの重複組数。非ゼロの場合は履歴・実制約との不一致を調査する。

データ本文、利用者ID、氏名、資格情報、接続先、DB例外本文は出力しない。PostgreSQLのREPEATABLE READ・READ ONLYトランザクション内で検査し、各SQLの時間制限5秒・ロック待ち1秒をトランザクション内に限定する。既存トランザクション内とPostgreSQL以外では実行を拒否する。自動修復・移行適用・ファイル変更は行わない。失敗時は部分的なJSONを出さず終了1とする。

## 実環境へ適用する前の境界

現在の稼働イメージにはこのコマンドがない。候補イメージを用意したうえで、既存DBへ接続する一時検査タスクの構成・実行費用・終了確認を具体化する。ECS ExecやIAMを無断で変更しない。

一時タスクでは通常起動による移行・静的収集・開発ユーザー作成を起動させないよう、entryPointをtimeout 120 pythonへ明示し、commandをmanage.pyとrelease_database_preflightに限定する。共有環境でのタスク登録・実行はまだ行っていない。検査後の配備・共有DB移行・S3/CDN保護変更は、それぞれの対象と復旧方法を提示して承認を得る。

履歴とスキーマが食い違う場合や検査が失敗する場合は、配備を止めて原因を調べる。旧移行を再適用したり、複数ロールを削除して逆移行を成立させたりしない。

## 検証

使い捨てPostgreSQL 16で、実装前に6件の失敗を確認した。実装後は正常な履歴・スキーマ、複数ロール、旧スキーマの残存、テーブル欠落、既存トランザクション、非PostgreSQL、接続エラーの秘匿化を検査する。検査中に意図的にDDLを書き込ませる試験では、PostgreSQLが拒否しテーブルが作成されないことを確認する。共有DBや利用者データは使わない。

この検査はテーブルのスキーマ変更と集計を含む試験のため、CIのPostgreSQLジョブにも明示的に追加する。SQLiteでのskipを実証の代替にしない。

最終検証は検査8件と既存ロール移行2件、計10件・2サブテスト成功（23.44秒、終了0）。新規コマンド32文・6分岐のカバレッジ100%。途中の実行はテスト中の整形で行番号が変わり、テスト10件は成功したがカバレッジ97%・終了1となったため、整形を完了してから上記の最終検証を実行した。失敗実行を合格として扱わない。Black/isort/Flake8と対象2ファイルのBanditも成功した。

## 配備用イメージでの確認

候補0b0cea6fec716ed7dfda15546b471c9e90cc0d34のgit archiveから通常Dockerfileでビルドした。ローカルタグtableno-formal-release:0b0cea6f、IDはsha256:5d2c113a6488c0c772f798b250ef45d59878ac110c9cef851e0a677a29cfedd1。revisionラベルは候補SHA、実行ユーザーtableno。ECRへの送信は未実施で、このIDをECR manifest digestとして扱わない。

外向き通信・公開ポートのない専用ネットワークの空PostgreSQL 16/Redis 7で、APP_ENV=aws-prod、S3/Checkout無効、隔離用仮値を使って通常entrypointを起動した。初回はDBの起動が完了せず接続拒否で停止したため、pg_isready成功後に同じappコンテナを起動した。移行中のHTTP検査も接続拒否となり、リスナー起動後に検査全体を再実行して成功した。途中の失敗を起動成功とは扱わない。

最終結果はreadiness/登録画面200、登録画面の静的資産5件とvendor8件のハッシュ付き配信・内容照合成功、CSS/JSのgzip確認成功。check --deploy・migrate --check・pip checkは終了0。イメージ内のrelease_database_preflightも終了0、read_only=true、新しいparticipant_id/role制約、複数ロール0・重複組0を返した。空DBの結果であり、共有DBの確認や旧版からの実データ移行成功を示さない。

ローカル証跡はtmp/release-preflight-0b0cea6f-build.log、同startup.log、同result.json。検査用app/DB/cacheコンテナと専用ネットワークは停止・削除済み。共有環境・共有DB・実Secrets・費用への変更なし。リモートCIは[作業ブランチの実行](https://github.com/sheepdog0820/iaia/actions/runs/34014342198)で別途確認する。

## 承認対象となる一時検査の具体案

1. 上記0b0cea6fのイメージを既存ECR tablenoへ専用タグdb-preflight-0b0cea6fで送信し、manifest digestを取得する。
2. 現行タスク定義40を基に、一時family tableno-aws-pre-db-preflightを登録する。既存のtask/execution role、DBのSecrets参照、ネットワーク、ログ先を使用する。変更はfamily、イメージ、entryPoint/command、不要なHTTP healthCheck/portMappingsの除去だけ。通常entrypointを通さず、timeout 120 python manage.py release_database_preflightだけを実行する。イメージ内にGNU timeout 9.7があることを確認済み。
3. 東京の既存clusterで0.25vCPU/512MiBのFargateタスクを1回実行する。既存サービスと同じ2サブネット・SG・public IPv4を使用し、ECSサービスへの関連付け・ALB登録はしない。タスク内120秒の制限に加え、イメージ取得を含む15分で未終了ならこの専用タスクをstop-taskする。自動再試行はしない。
4. 停止とexitCodeを確認し、専用ログストリームから検査JSONを取得して候補の移行・制約と照合する。終了1/124や欠落は未確認として報告する。
5. 作成した一時タスク定義を登録解除し、専用ECRタグだけを削除する。他のタグ・既存イメージ・既存サービスは削除しない。ログは既存の保持設定に従う。

登録用JSONはtmp/db-preflight-0b0cea6f-task.json、SHA256は94eb81bbc1fd966540d8598fa6f4a6e1ded78dfec370a56c6c3db4b8904916b2。実行前に現行タスク定義との相違が上記だけであることを再確認する。既存Secretsの設定が候補の起動要件を満たさない可能性は残る。その場合は検査を止め、値を表示せず不足項目を報告し、Secretsを変更して続行しない。

費用は2026-09-06にAWS Price List APIで東京Linux/x86のCPU 0.05056 USD/vCPU時、メモリ0.00553 USD/GiB時を再取得した。15分のCPU・メモリ・[public IPv4](https://aws.amazon.com/vpc/pricing/)の合計は約0.0051 USD。ローカルイメージ全容量約1.30GBを追加保管と仮定した[ECR](https://aws.amazon.com/ecr/pricing/)の月額換算は約0.13 USD（実際は圧縮・既存レイヤー共有・保管時間に依存）。専用タグは検査後に削除する。ログ・通信・税を含む承認予算案は1 USD以内。これは実請求額の保証や継続サービスの予算承認ではない。

承認対象はこの一時検査と後片付けのみ。アプリ配備、DB移行・データ更新、IAM/Secrets変更、S3/CDN変更、worker/beat/Redis作成、外部通知を含まない。DB変更を行わないためデータの切り戻し処理は不要で、失敗時は専用タスクの停止と上記の後片付けを行う。

## 承認待ちの間の追加検証

現行タスク定義40を再取得し、保存済み登録JSONとの差分が上記のfamily・image・entryPoint/command・HTTP設定除去だけであることを機械比較した。role・環境変数・Secrets参照は一致し、予定するECRタグはImageNotFoundで未使用だった。Secrets値の取得や登録・実行は行っていない。候補イメージのGNU timeoutを1秒にして5秒待つ隔離プロセスを起動し、終了124で停止することも確認した。

別の使い捨てPostgreSQL 16接続でキャラクターテーブルをACCESS EXCLUSIVEロックし、検査側がSQLSTATE 55P03（lock_not_available）で失敗することを追加試験した。失敗後のstatement_timeout/lock_timeoutは検査前と一致し、ロック解放後には正常に検査でき、成功後も設定が残らない。検査9件成功、32文・6分岐のカバレッジ100%、47.55秒、終了0。Black/isort/Flake8成功。検査用DBとネットワークは停止・削除した。アプリコードと承認対象のイメージ・タスクJSONは変更していない。
