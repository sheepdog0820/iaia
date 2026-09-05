# バックアップ・復旧手順

最終更新: 2026-09-05

この手順では本番環境のDB、アップロード画像、Redis障害時の対応、復旧確認を扱います。実Secrets、DBパスワード、S3バケットの非公開値はリポジトリに記録しません。

## 対象

- DB: 本番RDSまたは本番PostgreSQL/MySQL
- 画像: `MEDIA_ROOT` または本番S3バケット配下のアップロードファイル
- Redis: キャッシュ、Channels、Celery broker/result backend

## 実行前に確定すること

- 本番・共有環境での取得/復元、書き込み停止、接続先変更、費用発生は、対象・時間・費用上限・復旧策を示して承認を受ける。以下のコマンド例は実行承認ではない。
- 復元先は本番と異なる専用DB・メディア領域とし、接続先、空であること、担当者、削除期限を記録する。本番への上書き復元を初手にしない。
- 利用者操作だけでなく、worker、beat、Webhook、定期処理など全書き込み経路を対象に、停止または受信保留の方法を決める。ECSのWebタスク停止だけで全書き込みが止まるとは限らない。
- DB取得時刻と画像の世代を揃える。書き込み停止中に両方を取得するか、DBが参照する各オブジェクトのキー・VersionId・サイズ・SHA-256を保存して同じ内容を復元する。別時刻のDBと最新画像の組み合わせだけでは整合性を保証しない。
- 記録には取得開始/終了時刻、アプリSHA/イメージ、DBバージョン、適用migration、バックアップ識別子、メディアのmanifest、ハッシュを含める。RPO/RTOの目標値は事前合意し、取得間隔と障害発生から利用再開までの実測で判定する。
- 復元先のメール・課金・外部通知とworker/beatを無効にして隔離する。バックアップ内の未処理ジョブや連携資格情報を使って実サービスへ自動送信しない。

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

復元（接続先が専用の空DBであることを確認してから実行）:

```bash
pg_restore --exit-on-error --single-transaction --no-owner --no-acl \
  --dbname "$RESTORE_DATABASE_URL" backups/db/tableno-YYYYMMDD-HHMMSS.dump
```

`--single-transaction` は全処理の成功時だけ反映し、エラー時の部分復元を避ける。終了コードを確認し、エラーを無視して次へ進まない。大容量で並列復元を選ぶ場合はこのオプションと併用できないため、別の検証済み手順を用意する。ロール・ACLはこの例では復元しないので、公開用の最小権限を別途検証する。[PostgreSQL 16公式資料](https://www.postgresql.org/docs/16/app-pgrestore.html)

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
3. 週1回という既存の取得案が合意RPOを満たすか確認する。バックアップは世代ごとの別プレフィックスへ保存し、同じ世代を後から上書きしない。バージョニング単独では別系統のバックアップ取得や復元成功の証拠にならない。

```bash
aws s3 sync "s3://$MEDIA_BUCKET/" "s3://$MEDIA_BACKUP_BUCKET/tableno/media/$BACKUP_ID/" \
  --only-show-errors
```

`BACKUP_ID` は取得ごとに新しい識別子を使う。syncは現行オブジェクトの同期であり、過去VersionIdの復元操作ではない。書き込み停止中の取得例として使用し、各オブジェクトのmanifestを別途保存・照合する。継続書き込み中の特定時点復元にはVersionIdを指定する手順が必要になる。[AWS CLI sync公式資料](https://docs.aws.amazon.com/cli/latest/reference/s3/sync.html)

復元（専用の空の復元先へ）:

```bash
aws s3 sync "s3://$MEDIA_BACKUP_BUCKET/tableno/media/$BACKUP_ID/" "s3://$RESTORE_MEDIA_BUCKET/$RESTORE_PREFIX/" \
  --only-show-errors
```

### S3のVersionIdを固定する取得・復元手順

以下は承認後に実行する手順であり、実S3での復元実績ではない。DBと画像の同時点を確保するため、最初の取得では全書き込み経路を停止し、DBバックアップと画像manifestが揃うまで再開しない。稼働中の一覧取得を後から日時で並べ替えても、DBとの一貫したスナップショットにはならない。

1. DBバックアップが参照する各画像・添付について、storage locationを含む完全なS3キーを取得する。公開URLからキーを推測しない。DB参照のない旧画像は別一覧とし、自動復元や削除の対象へ混ぜない。
2. 各キーの`head-object`でVersionIdとContentLengthを取得し、DBバックアップIDと対応付ける。403/404、削除マーカー、VersionId欠落・`null`は未解決として停止し、別世代へ自動的に差し替えない。既に消失した版はバージョニングから復元できるとは限らない。
3. 取得したVersionIdを指定した`get-object`で専用の保護された取得先へ保存する。ダウンロード後のVersionId・サイズを照合し、内容のSHA-256を計算してmanifestへ記録する。ETagをSHA-256や常にMD5の値として扱わない。ローカル保存名は連番等を使い、S3キーを直接ローカルのパスに連結しない。
4. manifestにはDBバックアップID、取得開始/終了UTC、bucket、key、VersionId、サイズ、SHA-256、取得先の識別子を含める。各DB参照にちょうど1つの取得成功が対応し、失敗・欠落が0件であることを照合する。manifest自体にもアクセス制御とハッシュを付け、会話や公開リポジトリへ実キー名や内容を貼らない。
5. 復元時はmanifestで指定した取得済み内容、または存在を再確認した同じVersionIdを使用する。旧版が消えていた場合に最新オブジェクトへフォールバックしない。専用の空の復元先に配置し、元バケットの現行版や削除マーカーを削除して戻す方法は使わない。
6. 復元先から再取得した内容のサイズ・SHA-256とDB参照を照合する。コピー先のVersionIdは元と同じ値である必要はない。元とコピー先の対応を記録し、GM/PLの閲覧範囲、画像のデコード、過去の削除・権限失効を確認してから公開先の切替を判断する。

1件のCLI形式例（Bash。各変数は承認済みの対象を指定し、出力先は既存ファイルと重ならない専用パスにする）:

```bash
aws s3api head-object --bucket "$MEDIA_BUCKET" --key "$MEDIA_KEY" \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --query '{VersionId:VersionId,ContentLength:ContentLength}' --output json

aws s3api get-object --bucket "$MEDIA_BUCKET" --key "$MEDIA_KEY" \
  --version-id "$MEDIA_VERSION_ID" --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  "$BACKUP_OBJECT_FILE"

sha256sum "$BACKUP_OBJECT_FILE"
```

これは一括取得・manifest生成の実装ではない。各コマンドの終了コードと照合を省略して処理を続行しない。バージョン指定の取得には`s3:GetObjectVersion`が必要であり、必要な権限がなければ対象を絞った変更案を別途承認する。[HeadObject](https://docs.aws.amazon.com/cli/latest/reference/s3api/head-object.html)、[GetObject](https://docs.aws.amazon.com/cli/latest/reference/s3api/get-object.html)、[過去版の復元](https://docs.aws.amazon.com/AmazonS3/latest/userguide/RestoringPreviousVersions.html)

### ローカルMEDIA_ROOTを使う場合

```bash
mkdir -p backups/media
tar -czf "backups/media/media-$(date +%Y%m%d-%H%M%S).tar.gz" media/
```

復元（専用の空ディレクトリを指定する）:

```bash
tar -xzf backups/media/media-YYYYMMDD-HHMMSS.tar.gz -C "$RESTORE_ROOT"
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

6. 復元先で件数・内容・主外部キー・sequence・画像参照を照合する。画像はキーの存在だけでなく保存時manifestのサイズ・ハッシュと一致させ、実際に開く。通常GM/PLで秘匿HOと添付の閲覧範囲、既存データの編集・新規作成も確認する。
7. DB取得後に届いたStripeイベント、解約、権限失効、外部配送を照合する。復元DBの古い有料状態や未処理ジョブをそのまま正しい現状と扱わない。既配送の再送、失効資格情報の復活を防ぐため、再処理対象を明示してからworker/beatを再開する。
8. 隔離先のスモーク確認後、切替案と残るデータ欠損を確認し、承認された手順で接続先を切り替える。元DB・画像は調査と切り戻しのため保持し、削除時期を記録する。
9. 本番スモークテスト `docs/release/PRODUCTION_SMOKE_TEST_CHECKLIST.md` を実施する。
10. 復旧後、計測RPO/RTO、失われた可能性がある操作、再送したジョブ、ユーザー告知内容をインシデント記録へ残す。

## 定期確認

| 項目 | 頻度 | 記録 |
| --- | --- | --- |
| RDS自動バックアップ有効化 | 月1回 | スクリーンショットまたは設定値 |
| 手動スナップショットからの復元 | 月1回 | 復元DB名、確認者 |
| 画像バックアップ同期 | 週1回 | 実行ログ |
| Redis障害復旧リハーサル | 四半期1回 | 復旧時間、失敗ジョブ数 |
| 本番スモークテスト | リリースごと | Go/No-Go記録 |
