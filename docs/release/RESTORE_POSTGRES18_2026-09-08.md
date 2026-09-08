# PostgreSQL 18.3での候補復旧検証

2026-09-08。共有RDSの18.3と隔離試験の16.15の差を受け、固定アプリ候補10d21e42で18.3のバックアップ・復元を検証した。

## 実行条件と証拠

- アプリは `tableno-formal-release:10d21e42`。ソース上書きなし。前回と同じ合成データ/検証ロジックを新しい試験ディレクトリで利用。
- DBはDocker公式postgres:18.3、取得digest `sha256:7e32e9833a6fb1c92c32552794cb6ed569d51b445a54907d35fc112ef39684db`。実行時versionコマンドで18.3を確認。
- イメージ設定からPGDATAが `/var/lib/postgresql/18/docker`、volumeが `/var/lib/postgresql` と確認し、親ディレクトリをtmpfsにした。16系のマウント先をそのまま使って匿名永続volumeにデータを残す構成にはしていない。
- 専用internal network、ポート公開なし、合成データのみ。APP_ENV=local、locmemメール/キャッシュ、ローカル画像ストレージ。実RDSの拡張機能・設定・ネットワーク・Secretsは再現していない。
- 証跡はGit管理外の `tmp/restore-drill-pg18-10d21e42/` 内のrun.py、probe.py、drill_settings.py、results.jsonと各ログ。

## 結果

移行・データ作成・pg_dump・別の空DBへのpg_restoreが成功。91テーブル/608行の内容と件数、87シーケンスの状態、画像1件のパスとSHA-256が一致した。秘匿HOの所有関係、画像デコード、復元後の追加ユーザー採番も成功。

DBだけ復元した中間状態では、期待どおり終了1とmedia manifest differsを確認。画像の復元後は検査終了0。migrate --checkとDjango checkも終了0、実行スクリプト全体は終了0だった。

pg_restoreは0.484秒、画像復元は0.218秒、比較検査は1.875秒。合成データのコマンド時間であり、実規模のRTOではない。試験終了時は所有ラベルを確認してDBコンテナとnetworkを削除し、残存なしを確認した。

## CI変更と未完了範囲

`.github/workflows/django-ci.yml` のproduction-databaseサービスだけをpostgres:16からpostgres:18.3へ変更した。本番設定の移行・課金/権限ライフサイクル・並行処理テストを、確認済み実RDSと同じバージョンで継続実行する。他ジョブの範囲は変更しない。

この隔離復旧はproduction-databaseの全テストを代替しない。変更後CIはpush後に結果を確認する必要があり、本記録時点では合格未確認。実RDS/S3復元、RPO/RTO、全権限のHTTP検証、旧アプリへの切戻し、同時書き込みは残る。正式公開No-Goは維持する。

共有DB・実データ・Secrets・アクセス権・AWSリソースは変更していない。既存CIジョブのDBイメージ変更で、ジョブ数の追加や新しい有料契約はない。問題時はこのCIイメージ変更を戻せるが、16系成功だけで18系互換性を保証しない。
