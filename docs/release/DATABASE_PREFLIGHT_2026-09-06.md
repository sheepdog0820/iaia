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

一時タスクでは通常起動による移行・静的収集・開発ユーザー作成を起動させないよう、entryPointをpythonへ明示し、commandをmanage.pyとrelease_database_preflightに限定する。共有環境でのタスク登録・実行はまだ行っていない。検査後の配備・共有DB移行・S3/CDN保護変更は、それぞれの対象と復旧方法を提示して承認を得る。

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
