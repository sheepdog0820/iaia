# テストデータ管理ガイド

## 概要
このドキュメントは、タブレノプロジェクトのテストデータ作成・管理方法を記載しています。

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
詳細は`TEST_DATA_README.md`を参照してください。

### 主要なテストユーザー
- **管理者**: admin / arkham_admin_2024
- **GM**: keeper1 / keeper123, keeper2 / keeper123
- **プレイヤー**: investigator1-6 / player123

## ベストプラクティス
1. 新しいテストデータ作成機能は必ず`{app}/management/commands/`に配置
2. 命名規則: `create_test_{機能名}.py`
3. 重複機能の作成を避ける
4. 既存のコマンドを拡張する場合は、新規作成ではなく既存ファイルを更新