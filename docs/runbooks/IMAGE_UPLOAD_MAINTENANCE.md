# 画像アップロード運用

## シナリオ画像の上限

一般ユーザーとプレミアムユーザーの上限は、次の環境変数で個別に変更できます。
既定値は現時点では同一です。

| 設定 | 既定値 |
| --- | ---: |
| `SCENARIO_IMAGE_NORMAL_MAX_BYTES` | `5242880` (5MB) |
| `SCENARIO_IMAGE_PREMIUM_MAX_BYTES` | `5242880` (5MB) |
| `SCENARIO_IMAGE_NORMAL_MAX_FILES_PER_UPLOAD` | `10` |
| `SCENARIO_IMAGE_PREMIUM_MAX_FILES_PER_UPLOAD` | `10` |

## リンク切れ画像の確認と削除

ストレージ上の実ファイルがなくなったシナリオ画像、セッション画像、キャラクター画像を確認します。
引数なしではドライランになり、データは変更しません。

```bash
python manage.py cleanup_missing_upload_images
```

確認結果に問題がなければ、`--delete` を付けてリンク切れレコードを削除します。
旧形式のキャラクター画像フィールドについては、キャラクターレコードを残したまま画像参照だけを空にします。

```bash
python manage.py cleanup_missing_upload_images --delete
```

ストレージへの接続エラーが起きた画像は誤削除を避けるためスキップされ、`確認エラー` として集計されます。
