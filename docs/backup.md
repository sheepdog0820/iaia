# バックアップ・復旧手順

最終更新: 2026-06-19

この手順では本番環境のDB、アップロード画像、Redis障害時の対応、復旧確認を扱います。実Secrets、DBパスワード、S3バケットの非公開値はリポジトリに記録しません。

## 対象

- DB: 本番RDSまたは本番PostgreSQL/MySQL
- 画像: `MEDIA_ROOT` または本番S3バケット配下のアップロードファイル
- Redis: キャッシュ、Channels、Celery broker/result backend

## DBバックアップ

### RDSを使う場合

1. 自動バックアップの保持期間を7日以上に設定する。
2. 一般公開前、リリース直前、マイグレーション直前に手動スナップショットを作成する。
3. スナップショット名には `tableno-prod-YYYYMMDD-HHMM` を含める。
4. 月1回、スナップショットから検証用DBを復元し、アプリが起動できることを確認する。

### pg_dumpを使う場合

```bash
mkdir -p backups/db
pg_dump "$DATABASE_URL" --format=custom --no-owner --no-acl \
  --file "backups/db/tableno-$(date +%Y%m%d-%H%M%S).dump"
```

復元:

```bash
pg_restore --clean --if-exists --no-owner --no-acl \
  --dbname "$RESTORE_DATABASE_URL" backups/db/tableno-YYYYMMDD-HHMMSS.dump
```

### MySQLを使う場合

```bash
mkdir -p backups/db
mysqldump --single-transaction --routines --triggers "$MYSQL_DATABASE" \
  > "backups/db/tableno-$(date +%Y%m%d-%H%M%S).sql"
```

復元:

```bash
mysql "$RESTORE_MYSQL_DATABASE" < backups/db/tableno-YYYYMMDD-HHMMSS.sql
```

## 画像バックアップ

### S3を使う場合

1. 本番メディアバケットでバージョニングを有効にする。
2. 誤削除対策としてライフサイクルで旧版を30日以上保持する。
3. 週1回、別プレフィックスまたは別バケットへ同期する。

```bash
aws s3 sync "s3://$MEDIA_BUCKET/" "s3://$MEDIA_BACKUP_BUCKET/tableno/media/" \
  --only-show-errors
```

復元:

```bash
aws s3 sync "s3://$MEDIA_BACKUP_BUCKET/tableno/media/" "s3://$MEDIA_BUCKET/" \
  --only-show-errors
```

### ローカルMEDIA_ROOTを使う場合

```bash
mkdir -p backups/media
tar -czf "backups/media/media-$(date +%Y%m%d-%H%M%S).tar.gz" media/
```

復元:

```bash
tar -xzf backups/media/media-YYYYMMDD-HHMMSS.tar.gz
```

## Redis障害時

Redisは永続データの正本ではありません。障害時はDBと画像を保護し、リアルタイム通知と非同期ジョブの縮退を優先します。

1. `/health/ready` とCloudWatch LogsでRedis接続エラーを確認する。
2. ElastiCacheの場合はフェイルオーバーまたはノード再作成を実施する。
3. アプリ側でCelery worker/beatを再起動する。
4. `AsyncJob` の失敗・保留状態を `/integrations/` で確認し、再試行可能なジョブを再送する。
5. Channels通知が復旧しない場合、Web画面の30秒ポーリングフォールバックで主要操作が継続できることを確認する。

## 復旧手順

1. 障害範囲をDB、画像、Redis、アプリのどれかに切り分ける。
2. 本番への書き込みを止める必要がある場合、メンテナンス表示またはECS service desired count調整で新規操作を止める。
3. DBを最新の正常スナップショットまたはdumpから復元する。
4. 画像をS3バックアップまたはMEDIA_ROOTアーカイブから復元する。
5. マイグレーションを確認する。

```bash
python manage.py migrate --check
python manage.py check --deploy
```

6. アプリ、Celery worker、Celery beatを再起動する。
7. 本番スモークテスト `docs/release/PRODUCTION_SMOKE_TEST_CHECKLIST.md` を実施する。
8. 復旧後、失われた可能性がある操作、再送したジョブ、ユーザー告知内容をインシデント記録へ残す。

## 定期確認

| 項目 | 頻度 | 記録 |
| --- | --- | --- |
| RDS自動バックアップ有効化 | 月1回 | スクリーンショットまたは設定値 |
| 手動スナップショットからの復元 | 月1回 | 復元DB名、確認者 |
| 画像バックアップ同期 | 週1回 | 実行ログ |
| Redis障害復旧リハーサル | 四半期1回 | 復旧時間、失敗ジョブ数 |
| 本番スモークテスト | リリースごと | Go/No-Go記録 |
