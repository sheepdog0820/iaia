# AWSセッション招待状態調査

セッションと、そのセッションに紐づく招待状態を読み取り専用で確認する。

## 管理コマンド

```bash
python manage.py inspect_session_invitation_status --session-id 313
```

出力は1行のJSONで、次の情報を含む。

- セッションID、タイトル、グループID、グループ名
- 招待件数
- 各招待のID、招待先ユーザー名、状態、招待ロール

存在しないセッションIDを指定した場合は終了コード1で失敗する。データの更新は行わない。

## ECSタスクでの実行

リポジトリ直下の `aws_invitation_status.json` は、セッションID `313` を調査するためのECSコンテナオーバーライドである。

```bash
aws ecs run-task \
  --cluster <cluster-name> \
  --task-definition <task-definition> \
  --launch-type FARGATE \
  --network-configuration '<network-configuration>' \
  --overrides file://aws_invitation_status.json
```

実行結果は対象タスクの `web` コンテナのCloudWatch Logsで確認する。別のセッションを調査する場合は、コミット済みファイルを直接変更せず、JSONを一時コピーして `--session-id` の値を変更する。

出力にはユーザー名が含まれるため、調査結果をチケットやチャットへ貼り付ける際は必要な範囲だけを共有する。
