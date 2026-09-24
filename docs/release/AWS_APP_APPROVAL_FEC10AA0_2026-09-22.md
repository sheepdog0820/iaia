# 非公開関連情報保護を含む開発AWS反映案

本案は[44a18301の旧案](AWS_APP_APPROVAL_44A18301_2026-09-22.md)を置き換える。承認待ちであり、マージ・ECR push・共有DB移行・AWS変更は未実施。実行前にはCI全体成功と以下の承認が必要。

## 固定対象・検証・未達

- アプリコミット: `fec10aa06d0337e4fb773cc98c7a2e8abd4c0d09`。
- イメージ: `tableno:history-permissions-fec10aa0`、ID `sha256:1658cb0b53a2a32e14464561d9d91f9676197e55ece84151bc75a229ff0c553b`。
- 旧案からの追加: 履歴作成/変更時に関連シナリオ・セッションの閲覧権限を検査し、失効後の読み出しでも関連情報を隠す。既存履歴そのものや本人の記録は削除しない。
- [配布物検証](RUNTIME_HISTORY_PERMISSIONS_FEC10AA0_2026-09-22.md): SQLite/PGそれぞれ関連19テスト成功。隔離PG18.3/Redis・aws-pre設定の通常起動、全移行、静的収集、readiness、deploy check成功。実AWSの成功ではない。
- [e2d08157のCI](https://github.com/sheepdog0820/iaia/actions/runs/35703522004)は17:21 JST頃に4ジョブ成功・2ジョブ実行中。fec10aa0との差分は文書3ファイルのみ。全体成功は未確認で、実行前ゲートとして残す。
- OS監査はHIGH 2 / MEDIUM 1 / LOW 33の36指摘、終了1。適用除外・リスク受容はしていない。この残存リスクを明示した限定開発反映の判断と、正式公開の判断を区別する。
- mainからの移行差分はaccounts0065/0066/0067の3ファイル。旧44a18301からDockerfile・entrypoint・依存関係の変更なし。

## 17:21 JSTの読み取り確認

GitHub mainは`d875d028ede0b3172780d54d4baacdb226a1d3b3`。AWSアカウント083773015316、ap-northeast-1、ECS `tableno-aws-pre` の定義49、desired/running=1、pending=0。stgのHTTP readinessはdatabase/cacheともok。

共有DBの移行履歴は直接照会していない。RDS復元可能時刻、稼働イメージdigest、S3 VersionIdは今回更新していない。[前回の復旧証拠](AWS_APP_APPROVAL_F8AA55A9_2026-09-22.md)を参照し、適用直前に必ず再取得する。認証失効や対象変更があれば停止する。

## 9月25日 06:51 JSTの追加読み取り確認

STS accountは083773015316。ECS定義49はdesired/running/pending=0/0/0、HTTP readinessは503。RDS `tableno-aws-pre` はstoppedで、バックアップ保持は7日。CloudTrailでは2時台のECS/RDS操作がEventBridge SchedulerのAWS SDK呼び出しとして記録され、スケジュール本体も次を確認した。

| 操作 | 有効スケジュール（Asia/Tokyo） |
| --- | --- |
| ECS desired count 0 | 毎日 02:00 |
| RDS停止 | 毎日 02:05 |
| RDS起動 | 毎日 07:30 |
| ECS desired count 1 | 毎日 08:00 |

したがって06:51の503は定期停止時間帯に一致する。7:30/8:00の再開成功は未確認であり、今回の読み取り確認ではサービスを起動していない。再開時刻後に利用・デプロイする場合はreadiness、ECS安定状態、RDS状態を実行直前に確認する。CloudTrail履歴はスケジューラによる実行を示すが、停止時間帯の利用合意や日中の起動成功を証明するものではない。

## 9月25日 08:15 JSTの反映準備確認

- `tableno-aws-pre` は定義49、desired/running/pending=1/1/0。実行中Webのdigestは `sha256:59542e45e5dc8e1e33cbf7202eb12911ffbb390156a778fe7eb11f0fe4c65f79`。RDS状態はavailable、バックアップ保持7日。HTTP readiness 200相当のJSONは `status=ok`、database/cacheとも`ok`。定期起動後の現行環境は復帰している。
- 稼働イメージはmainの現行版であり、候補イメージではない。過去の隔離環境での起動成功をAWS配信済みとは扱わない。
- 作業ブランチ `codex/google-token-expiry-20260922` のHEADは `fbf67c00439721e0bfbe89f585cff6aa9b289bdf`、main `d875d028` は祖先で、未push差分なし。`fec10aa0` のアプリ差分を含むHEADの[CI全6ジョブが成功](https://github.com/sheepdog0820/iaia/actions/runs/35705069778)。現行Docker候補は `tableno:history-permissions-fec10aa0`、digest `sha256:1658cb0b53a2a32e14464561d9d91f9676197e55ece84151bc75a229ff0c553b`、revision label `fec10aa0`。
- このブランチをheadにした既存PRは公開一覧に見当たらない。GitHub CLIは未認証のためPR作成はできていない。ブランチpushとCIは完了。

この確認で候補のPRレビュー可能性・ローカル固定イメージ・CI・現行サービスの復帰を確認したが、ECR候補push、mainマージ、DB移行、ECS更新、S3/CloudFront変更は未実施。実施には反映承認と、PR作成前のGitHub認証、および直前のAWS/DB/静的復旧情報再取得が必要。

## 承認対象と実行前ゲート

1. CI全体成功・対象差分・main不変・稼働状態を再確認後、上記アプリ候補をmainへ通常マージする。未知の更新や競合では停止する。
2. 固定イメージをECR `aws-pre-fec10aa0` へpushしdigestを記録する。定義49を基にWebイメージだけを更新し、CPU/メモリ/台数/IAM/Secrets参照/ネットワークを維持する。
3. RDS復旧可能性と静的復旧用VersionIdを確保後、単発タスクで`migrate --plan`を確認する。entrypointの先行副作用を避けるため、単発タスクでは`RUN_MIGRATIONS=false`、`RUN_COLLECTSTATIC=false`、`CREATE_DEV_LOGIN_USER=false`を明示し、指定コマンドだけを実行する。Web定義の環境変数変更とは分ける。
4. 想定のaccounts0065/0066/0067（新規3テーブル）だけなら、承認範囲内で共有DBに適用する。終了0と`migrate --check`を確認。想定外や失敗では停止し、旧Webを維持する。既存データ書換え・削除や逆移行は含めない。
5. `collectstatic --noinput`を単発タスクで実行し終了0を確認する。`staticfiles.json`と変更対象静的資産の旧VersionIdを保存し、旧ハッシュ付き資産を残す。`--clear`は禁止。復旧手段を確保できなければ更新しない。
6. Webを新定義へ更新し安定化を確認。CloudFront `E3RQ829D1NVY28` の`/static/*`を無効化して完了を確認する。
7. 稼働digest/readiness/ログイン/連携設定/統計/6版・7版作成/一覧/詳細/履歴と静的配信ハッシュを確認。権限修正の実データ書込み試験は別途専用fixture・削除範囲を確認する。実ユーザーへの攻撃文字列投入や無断のデータ変更は含めない。

## 復旧・費用・対象外

Web障害時は定義49へ戻す。静的障害は旧VersionIdの内容を同じキーの新しい最新バージョンとして復元し、マニフェストを読むWebプロセスも入れ替え、CDN無効化と実画面確認を行う。DB追加3テーブルは残す。逆移行・実データ復元は別途判断する。切戻しは修正前の表示・権限不備を再導入し得るため、安全性回復とは呼ばず、影響画面の利用制限か修正版再配信を判断する。

ECR保存・一時ECS・S3/CDN・ログの従量費用を伴う。常設Web増量、worker/beat/Redis増設、Stripeキー/Price/Webhook変更、購入/メール有効化、IAM/OAuth/Secrets変更、本番公開、実メール送信、全体terraform applyは対象外。

本案の承認だけでは正式公開できない。OS指摘、AWS課金一連動作、実OAuth/通知、常設worker、実メール、性能・復旧・事業運用の受入条件は残る。
