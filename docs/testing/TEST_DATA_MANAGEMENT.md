# テストデータ管理ガイド

## 概要
このドキュメントは、タブレノプロジェクトのテストデータ作成・管理方法を記載しています。

## 実行環境の制限

一括作成・リセット用の次の7コマンドは、`DEBUG=True`、`APP_ENV=local/dev/development`、`ENVIRONMENT=local/development` がすべて揃う場合だけ実行できます。aws-pre/aws-prodや不明な環境では、確認プロンプト・DBトランザクション・削除/作成の前に拒否します。`--clear`、`--reset`、`--force` でこの制限を解除することはできません。

- `create_sample_data`
- `create_test_data`
- `create_test_characters`
- `create_session_test_data`
- `create_flow_test_data`
- `create_advanced_scheduling_test_data`
- `reset_dev_session_data`

設定名の確認は実際のDB接続先の判別を代替しません。実行前に専用ローカルDB・画像領域への接続を確認してください。共有DBへ接続したまま環境名をlocalへ変えて実行する運用は対象外です。共有環境への試験データ投入は、この一括コマンドの制限を解除するのではなく、対象・変更内容・削除手順を具体化した別の承認済み手順で行います。

単一の開発ログイン利用者を明示的に用意する `ensure_dev_login_user` は、この7コマンドには含めていません。既存の `--allow-non-debug` オプションや実行権限の扱いは別に確認してください。

## 現在のテストデータ作成コマンド

### 1. 基本的なテストデータ作成
```bash
# 総合的なテストデータ作成（ユーザー、グループ、セッション、シナリオ）
python manage.py create_test_data

# オプション指定
python manage.py create_test_data --users 20 --sessions 100 --scenarios 50
```

### 2. キャラクター専用テストデータ
```bash
# キャラクターシートのテストデータ作成（画像付き）
python manage.py create_test_characters
```

### 3. サンプルデータ作成
```bash
# 本番環境に近いサンプルデータ作成
python manage.py create_sample_data

# 既存データをクリアしてから作成
python manage.py create_sample_data --clear
```

### 4. セッションテストデータ
```bash
# セッション専用のテストデータ作成
python manage.py create_session_test_data
```

## データ確認
```bash
# 作成されたテストデータの確認
python check_test_data.py
```

## 削除されたコマンド（2025年6月26日）
以下のコマンドは重複または古いバージョンのため削除されました：
- `create_investigator_history_data.py` - create_test_dataに統合
- ルートディレクトリの`create_test_characters.py` - 管理コマンド版を使用
- ルートディレクトリの`create_sample_characters.py` - 管理コマンド版を使用

## テストユーザー情報
詳細は`docs/testing/TEST_DATA_README.md`を参照してください。

### 主要なテストユーザー
- **管理者**: admin / `python scripts/dev/create_admin.py` 実行時に表示される値
- **GM**: keeper1 / keeper123, keeper2 / keeper123
- **プレイヤー**: investigator1-6 / player123

## ベストプラクティス
1. 新しいテストデータ作成機能は必ず`{app}/management/commands/`に配置
2. 命名規則: `create_test_{機能名}.py`
3. 重複機能の作成を避ける
4. 既存のコマンドを拡張する場合は、新規作成ではなく既存ファイルを更新
